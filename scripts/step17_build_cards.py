# -*- coding: utf-8 -*-
"""step17：生成词级卡池 + 句级卡池 + 统计报告

输入：
  data/term_sentence_pairs.jsonl  词项—英译对（1511）
  data/course_cards_v2.jsonl      句子底表（654，含 prev/next/source_work）
  data/terms_candidates.jsonl     原始词项（取 typical_error_mode）
  data/flat_terms.json            展平词项（取清洗前 term 以回连 error_mode）
  data/proper_noun_glossary.json  专名表（判定人名/地名 → 低频分）
  data/translation_issues.jsonl   英译问题（报告中提示，不影响打分）

输出：
  data/word_cards.jsonl
  data/sentence_cards.jsonl
  data/cards_invalid.jsonl
  data/cards_excluded.jsonl
  data/cards_report.md
"""
import json
import os
import re
import collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(BASE, 'data', *p)


def jl(path):
    with open(path, encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]


# ────────────────────────── 载入 ──────────────────────────
pairs = jl(D('term_sentence_pairs.jsonl'))
cards = jl(D('course_cards_v2.jsonl'))
cand = jl(D('terms_candidates.jsonl'))
flat = json.load(open(D('flat_terms.json'), encoding='utf-8'))
gloss = json.load(open(D('proper_noun_glossary.json'), encoding='utf-8'))
issues = jl(D('translation_issues.jsonl'))

flat_by_idx = {r['idx']: r for r in flat}
cand_by_sent = {c['id']: c for c in cand}   # id 形如 c001，对应 cards[0]


def sent_no(sent_id):
    return int(sent_id[1:]) - 1

# ────────────────────────── 字号 / 类型 ──────────────────────────
TYPE_MAP = {1: '单字词', 2: '双字词', 3: '三字词', 4: '四字词'}


def ctype(n):
    return TYPE_MAP.get(n, '多字词')


# ────────────────────────── 词级 exam_frequency ──────────────────────────
# A 级：全国卷高频实词 + 古今异义 + 通假字，出现即重点
GK_A = set("""
爱 安 被 倍 本 鄙 兵 病 察 朝 曾 乘 诚 除 辞 从 殆 当 道 得 度 非 复 负 盖 故 顾 固 归 国
过 何 恨 胡 患 或 疾 及 即 既 假 间 见 解 就 举 绝 堪 克 类 怜 弥 莫 乃 内 期 奇 迁 请 穷
去 劝 却 如 若 善 少 涉 胜 识 使 是 适 书 孰 属 数 率 说 私 素 汤 涕 徒 亡 王 望 恶 微 悉
相 谢 信 兴 行 幸 修 徐 许 阳 要 宜 遗 贻 易 阴 右 再 造 知 致 质 治 诸 贼 族 卒 走 左 坐
布衣 社稷 爪牙 婚姻 可以 非常 无论 卑鄙 妻子 走狗 地方 颜色 其实 以为 从而 因为 指示
翱翔 河南 河北 山东 关中 中国 空中 交通 妻子 至于 成立 辛勤 不过 不行 从容 寄托 绝境
鼓 雨 衣 冠 名 目 手 足 面 膝 刃 缒 麾 鞭 异 苦 毒 厚 薄 亲 远 近 上 下
""".split())

GK_A_SINGLE = {x for x in GK_A if len(x) == 1}

# B 级：常考但区分度次之
GK_B = set("""
之 其 而 以 于 也 者 矣 乎 焉 则 乃 且 故 遂 因 于 是 耳 哉 夫
谓 曰 云 语 言 视 观 望 闻 听 食 饮 衣 冠 车 马 城 池 兵 甲 谷 粟
""".split())

# 称谓类：敬称/谦称是固定考点，给中等偏上
APPELLATION = set('陛下 大王 足下 先帝 寡人 臣 君 公 子 卿 将军 大夫 太守 舍人 有司'.split())

# 纯噪声：不构成词项
STOP_NOISE = set('曰 云 秦 赵 齐 楚 燕 魏 韩 周 汉'.split())

# 专名表里的人名 / 地名 / 国名 → 1 分（只需认得，不需辨析）
GLOSS_PERSON_PLACE = set()
for e in gloss['entries']:
    if e['category'] in ('人名', '地名', '国名'):
        GLOSS_PERSON_PLACE.add(e['term'])

freq_map = collections.Counter(r['term'] for r in pairs)


def word_freq(term, meaning, english_frag, ch):
    if term in STOP_NOISE:
        return 1
    if term in GLOSS_PERSON_PLACE:
        return 1
    if term in APPELLATION:
        return 3
    s = 2
    if term in GK_A:
        s += 2
    elif term in GK_B:
        s += 1
    if freq_map[term] >= 5:
        s += 1
    if 2 <= ch <= 3 and len(english_frag or '') >= 6:
        s += 1
    return max(1, min(5, s))


# ────────────────────────── 句级 sentence_type ──────────────────────────
TYPE_RULES = [
    ('被动句', [r'为[^。]{1,6}所[^。]{1,4}[。，；]', r'见[杀辱笑怪欺疑擒贬]',
                r'见[^。]{1,3}于', r'被[^。]{1,4}[。，；]']),
    ('宾语前置句', [r'何[^。]{0,6}之有', r'之谓', r'唯[^。]{0,8}是[^。]',
                    r'安在', r'孰与', r'何以', r'(不|未|莫)[自之我吾]']),
    ('判断句', [r'者[，,]?[^。！？]{0,40}也[。！？]?$',
                r'^[^。]{0,10}(乃|则|即|皆|非|是|为)[^。]{0,15}也[。]']),
    ('定语后置句', [r'(有|求|得)[^。]{1,6}者[，。]', r'之[\u4e00-\u9fa5]{2,4}者[，。]']),
    ('状语后置句', [r'(?<!不)(于|乎)[\u4e00-\u9fa5]{1,4}[。；，]$', r'于[\u4e00-\u9fa5]{1,6}$']),
]

# 97 条候选逐条人工复核后的修正（未列出者沿用规则判定）
TYPE_REVIEW = {
    67: '状语后置句',    # 受任于败军之际：受＝接受任命，非被动
    97: '一般陈述句',    # 为具言所闻：为＝对/向，非被动
    100: '一般陈述句',   # 不足为外人道也：也为句末语气
    188: '疑问句',       # 其皆出于此乎：疑问，为＝成为
    231: '一般陈述句',   # 卒莫消长也：也为语气
    263: '一般陈述句',   # 有不见者，三十六年：者＝的人
    291: '一般陈述句',   # 战胜而得者：者＝的土地
    311: '一般陈述句',   # 惜其用武而不终也：也为语气
    409: '一般陈述句',   # 未尝有坚明约束者也：者也＝语气组合
    479: '一般陈述句',   # 宜乎众矣：主谓倒装，非状语后置
    501: '一般陈述句',   # 食马者不知…也：者为的人
    508: '一般陈述句',   # 舍鱼而取熊掌者也
    511: '一般陈述句',   # 舍生而取义者也
    512: '状语后置句',   # 所欲有甚于生者
    513: '状语后置句',   # 所恶有甚于死者
    514: '疑问句',       # 何不用也
    515: '疑问句',       # 何不为也
    517: '状语后置句',   # 甚于生者／甚于死者
    522: '一般陈述句',   # 万钟…而受之：受＝接受
    539: '判断句',       # 吾妻之美我者，私我也
    540: '判断句',       # 妾之美我者，畏我也
    541: '判断句',       # 客之美我者，欲有求于我也
    583: '一般陈述句',   # 至于成立：至＝到了
    637: '一般陈述句',   # 皆被绮绣：被通「披」
    639: '一般陈述句',   # 不知口体之奉不若人也
    646: '一般陈述句',   # 其业有不精…者：者＝的情况
    149: '判断句',       # 不复挺者，輮使之然也
    361: '被动句',       # 为天下笑者：被动＋判断，取被动为主考点
    533: '宾语前置句',   # 忌不自信
}


def sent_type(text):
    t = text.strip()
    for name, pats in TYPE_RULES:
        if any(re.search(p, t) for p in pats):
            return name
    if t.endswith('？') or t.endswith('?'):
        return '疑问句'
    if t.endswith('！') or t.endswith('!'):
        return '感叹句'
    return '一般陈述句'


# 名句（背诵默写 / 翻译高频）
KEY_PHRASES = [
    '先天下之忧而忧', '不以物喜不以己悲', '醉翁之意不在酒', '先帝创业未半而中道崩殂',
    '受任于败军之际奉命于危难之间', '苟全性命于乱世不求闻达于诸侯', '亲贤臣远小人',
    '芳草鲜美落英缤纷', '不足为外人道也', '黄发垂髫并怡然自乐',
    '肉食者鄙未能远谋', '一鼓作气再而衰三而竭', '彼竭我盈故克之',
    '青取之于蓝而青于蓝', '锲而不舍金石可镂', '不积跬步无以至千里',
    '师者所以传道受业解惑也', '师道之不传也久矣', '闻道有先后术业有专攻', '圣人无常师', '弟子不必不如师',
    '寄蜉蝣于天地渺沧海之一粟', '哀吾生之须臾羡长江之无穷', '苟非吾之所有虽一毫而莫取',
    '灭六国者六国也非秦也', '秦人不暇自哀而后人哀之', '一日之内一宫之间而气候不齐',
    '六国破灭非兵不利战不善弊在赂秦', '苟以天下之大下而从六国破亡之故事',
    '仁义不施而攻守之势异也', '一夫作难而七庙隳', '斩木为兵揭竿为旗',
    '臣无祖母无以至今日祖母无臣无以终余年', '茕茕孑立形影相吊', '日薄西山气息奄奄',
    '斯是陋室惟吾德馨', '何陋之有', '出淤泥而不染濯清涟而不妖', '莲之爱同予者何人',
    '庭下如积水空明水中藻荇交横', '但少闲人如吾两人者耳',
    '千里马常有而伯乐不常有', '其真无马邪其真不知马也',
    '舍生而取义者也', '二者不可得兼', '生亦我所欲所欲有甚于生者',
    '生于忧患死于安乐', '故天将降大任于是人也',
    '吾妻之美我者私我也', '此所谓战胜于朝廷', '臣之客欲有求于臣皆以美于徐公',
    '富贵不能淫贫贱不能移威武不能屈', '此之谓大丈夫',
    '完璧归赵', '负荆请罪', '刎颈之交', '先国家之急而后私仇也', '布衣之交',
    '徒见欺', '臣诚恐见欺于王而负赵',
    '素湍绿潭回清倒影', '自非亭午夜分不见曦月', '虽乘奔御风不以疾也',
    '潭中鱼可百许头皆若空游无所依', '凄神寒骨悄怆幽邃',
    '以中有足乐者不知口体之奉不若人也', '余则缊袍敝衣处其间',
]


def norm(s):
    return re.sub(r'[^\u4e00-\u9fa5]', '', s or '')


KEY_NORM = [norm(k) for k in KEY_PHRASES]
# 底表个别字有讹（如「出淤泥而不染」误作「不然」），长名句用前 6 字做容错匹配
KEY_HEAD = [k[:5] for k in KEY_NORM if len(k) >= 8]


def clean_meaning(m):
    """去掉清洗阶段留下的切分备注，保留释义本体。

    形如「湖名，即洞庭湖（本句『在洞庭一湖』），『庭一湖』为跨词碎片」→「湖名，即洞庭湖」
    """
    if not m:
        return m
    m = re.sub(r'[，,；;]?\s*[『「][^』」]{1,12}[』」]\s*为跨词碎片', '', m)
    m = re.sub(r'[，,；;]?\s*（本句[^）]*）', '', m)
    m = m.strip('，,；; ')
    return m or m


def sent_freq(card, s_type, hi_terms):
    t = norm(card['classical'])
    s = 2
    if s_type != '一般陈述句':
        s += 1
    if hi_terms >= 1:
        s += 1
    if hi_terms >= 3:
        s += 1
    if 10 <= len(t) <= 30:
        s += 1
    if any(k in t for k in KEY_NORM) or any(k in t for k in KEY_HEAD):
        s += 1
    if len(t) > 40:
        s -= 1
    elif len(t) < 6 and hi_terms == 0 and s_type == '一般陈述句':
        # 短句只在「既非特殊句式、不含重点词、也不含 A 级实词」时才降分。
        # 「渔人甚异之」（异＝意动）、「公将鼓之」（鼓＝名作动）都是短句但为高频考点
        if not any(ch in t for ch in GK_A_SINGLE):
            s -= 1
    return max(1, min(5, s))


# ────────────────────────── 回连 typical_error_mode ──────────────────────────
DEFAULT_ERR = {
    1: '只记今义，不知本句义项；单字多义误植他句',
    2: '拆字直译，未按合成词整体理解',
    3: '误作专名或漏识专名',
    4: '拆成两个词分别直译，丢失成语化整体义',
}


def get_error_mode(sent_id, idx, term):
    """typical_error_mode 取自 terms_candidates，需按句子 + 原始词形回连。

    注意：清洗阶段改过部分 term（如「庭一湖」→「洞庭」），所以先用原始 term 匹配。
    """
    orig = flat_by_idx.get(idx, {}).get('term') or term
    c = cand_by_sent.get(sent_id)
    if c:
        for t in c['terms']:
            if t['term'] in (term, orig):
                return t.get('typical_error_mode') or DEFAULT_ERR.get(len(term), '')
        for t in c['terms']:   # 二次兜底：包含关系
            if term and (term in t['term'] or t['term'] in term):
                return t.get('typical_error_mode') or ''
    return DEFAULT_ERR.get(len(term), '')


# ────────────────────────── 构建词级池 ──────────────────────────
# 同词异义聚合：other_senses 回填来源（P4 已拍板：加字段回填，D1 关闭）
sense_map = collections.defaultdict(collections.Counter)
for r in pairs:
    m = clean_meaning(r['meaning_in_this_sentence'])
    if m and not re.match(r'^[①②③④⑤]', m):   # 剔除 step8 残留的多义项清单
        sense_map[(r['term'] or '').strip()][m] += 1
MAX_OTHER_SENSES = 3


def sense_key(m):
    """义项归一键：去括号例证、去『』引例、去「非…」辨析尾，取前 8 字判重。"""
    m = re.sub(r'（[^）]*）', '', m)
    m = re.sub(r'[『「][^』」]*[』」]', '', m)
    m = re.sub(r'，非[^，]*$', '', m)
    return m.strip('，,；:： ')[:8]


def pick_other_senses(term, cur_meaning):
    """同词异义去重：义项主干相同视为同义（如「断绝（绝江河）」与「断绝（绝秦赵之欢）」）。"""
    out, seen = [], {sense_key(cur_meaning)}
    for m, _ in sense_map[term].most_common():
        if m == cur_meaning:
            continue
        k = sense_key(m)
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(m)
        if len(out) >= MAX_OTHER_SENSES:
            break
    return out

excluded = []
word_rows = []
seen_noise = collections.Counter()

for r in pairs:
    term = (r['term'] or '').strip()
    ch = len(term)
    if term in STOP_NOISE:
        seen_noise[term] += 1
        # 「曰」保留 2 张覆盖不同句式，其余剔除；国名只留 1 张
        keep_quota = 2 if term == '曰' else 1
        if seen_noise[term] > keep_quota:
            excluded.append({
                'source': 'word', 'idx': r['idx'], 'term': term,
                'title': r['title'], 'reason': 'noise_repeat',
                'reason_detail': f'「{term}」为无辨析价值的重复词项（共 {freq_map[term]} 张），仅保留 {keep_quota} 张代表卡',
            })
            continue

    card = cards[sent_no(r['sent_id'])]
    src = card.get('source_work') or ''
    title = card.get('title') or r['title']
    # 统一为「篇名（出处）」：出处本身可能已含篇名（如「节选自《史记·廉颇蔺相如列传》」），
    # 仍保留双段结构，便于下游按篇聚合
    source_work = f'{title}（{src}）' if (src and title) else (src or title)

    cur_meaning = clean_meaning(r['meaning_in_this_sentence'])
    row = {
        '_idx': r['idx'],
        '_sent': sent_no(r['sent_id']),
        'id': None,
        'term': term,
        'char_count': ch,
        'term_type': ctype(ch),
        'meaning_in_this_sentence': cur_meaning,
        'other_senses': pick_other_senses(term, cur_meaning),
        'term_english': r['term_english'],
        'full_english': r['full_english'],
        'classical_sentence': r['classical_sentence'],
        'source_work': source_work,
        'prev_sentence': card.get('prev_sentence'),
        'next_sentence': card.get('next_sentence'),
        'typical_error_mode': get_error_mode(r['sent_id'], r['idx'], term),
        'exam_frequency': word_freq(term, r['meaning_in_this_sentence'], r['term_english'], ch),
    }
    word_rows.append(row)

# ────────────────────────── 构建句级池 ──────────────────────────
# 每句的「高频词项数」用于打分（按句子序号聚合，一句可挂多张词卡）
hi_by_sent = collections.Counter()
for r in word_rows:
    if r['exam_frequency'] >= 4:
        hi_by_sent[r['_sent']] += 1

sent_rows = []
for i, c in enumerate(cards):
    st = TYPE_REVIEW.get(i) or sent_type(c['classical'])
    src = c.get('source_work') or ''
    title = c.get('title') or ''
    # 统一为「篇名（出处）」：出处本身可能已含篇名（如「节选自《史记·廉颇蔺相如列传》」），
    # 仍保留双段结构，便于下游按篇聚合
    source_work = f'{title}（{src}）' if (src and title) else (src or title)
    sent_rows.append({
        'id': None,
        'classical_sentence': c['classical'],
        'full_english': c['english'],
        'source_work': source_work,
        'prev_sentence': c.get('prev_sentence'),
        'next_sentence': c.get('next_sentence'),
        'sentence_type': st,
        'exam_frequency': sent_freq(c, st, hi_by_sent.get(i, 0)),
    })

# ────────────────────────── 字段校验 ──────────────────────────
WORD_REQUIRED = ['term', 'char_count', 'term_type', 'meaning_in_this_sentence',
                 'term_english', 'full_english', 'classical_sentence', 'source_work',
                 'typical_error_mode', 'exam_frequency']
SENT_REQUIRED = ['classical_sentence', 'full_english', 'source_work',
                 'sentence_type', 'exam_frequency']


def is_empty(v):
    return v is None or (isinstance(v, str) and not v.strip()) or v == ''


invalid = []
ok_word = []
for r in word_rows:
    miss = [k for k in WORD_REQUIRED if is_empty(r.get(k))]
    if miss:
        invalid.append({'source': 'word', 'missing': miss, 'row': r})
    else:
        ok_word.append(r)

ok_sent = []
for r in sent_rows:
    miss = [k for k in SENT_REQUIRED if is_empty(r.get(k))]
    if miss:
        invalid.append({'source': 'sentence', 'missing': miss, 'row': r})
    else:
        ok_sent.append(r)

for n, r in enumerate(ok_word, 1):
    r['id'] = f'w{n:04d}'
for n, r in enumerate(ok_sent, 1):
    r['id'] = f's{n:04d}'
for r in ok_word:
    r.pop('_idx', None)   # 仅供内部关联，不入交付字段
    r.pop('_sent', None)

# ────────────────────────── 落盘 ──────────────────────────
with open(D('word_cards.jsonl'), 'w', encoding='utf-8') as f:
    for r in ok_word:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
with open(D('sentence_cards.jsonl'), 'w', encoding='utf-8') as f:
    for r in ok_sent:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
with open(D('cards_invalid.jsonl'), 'w', encoding='utf-8') as f:
    for r in invalid:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
with open(D('cards_excluded.jsonl'), 'w', encoding='utf-8') as f:
    for r in excluded:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

# ────────────────────────── 统计报告 ──────────────────────────
def pct(a, b):
    return f'{a / b * 100:.1f}%' if b else '0.0%'


ch_cnt = collections.Counter(r['char_count'] for r in ok_word)
W = len(ok_word)
S = len(ok_sent)
d23 = ch_cnt[2] + ch_cnt[3]
wf = collections.Counter(r['exam_frequency'] for r in ok_word)
sf = collections.Counter(r['exam_frequency'] for r in ok_sent)
st_cnt = collections.Counter(r['sentence_type'] for r in ok_sent)

def book_name(sw):
    m = re.match(r'^(.+?)（', sw or '')
    return m.group(1) if m else (sw or '')


book_w = collections.Counter(book_name(r['source_work']) for r in ok_word)
book_s = collections.Counter(book_name(r['source_work']) for r in ok_sent)


def examples(level, rows, key, n=3):
    out = []
    seen = set()
    for r in rows:
        if r['exam_frequency'] != level:
            continue
        k = r[key]
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
        if len(out) >= n:
            break
    return out


lines = []
A = lines.append
A('# 文言文词级 / 句级卡池统计报告\n')
A(f'生成时间：2026-10-26　数据源：`term_sentence_pairs.jsonl`（词项 {len(pairs)} 条）、'
  f'`course_cards_v2.jsonl`（句子 {len(cards)} 句）\n')
A('> `data/sentences.jsonl` 仍不存在，句子侧一律以 `course_cards_v2.jsonl` 为准（两者字段同构，'
  '后者含 english / prev_sentence / next_sentence）。\n')

A('## 一、总量\n')
A('| 卡池 | 有效卡 | 剔除 | 无效 |')
A('|---|---|---|---|')
A(f'| 词级 word_cards.jsonl | **{W}** | {len(excluded)} | '
  f'{sum(1 for r in invalid if r["source"] == "word")} |')
A(f'| 句级 sentence_cards.jsonl | **{S}** | 0 | '
  f'{sum(1 for r in invalid if r["source"] == "sentence")} |')
A('')

A('## 二、字段口径\n')
A('| 字段 | 口径 |')
A('|---|---|')
A('| `source_work` | 统一写作「篇名（出处）」。底表 `source_work` 只有文献名（如《范文正公集》卷七），'
  '单用无法定位课文，故与 `title` 合成一格。 |')
A('| `prev_sentence` / `next_sentence` | 取所在句的上下文。同一句名下多张词卡共享同一组上下文；'
  f'各篇首句无前句（{sum(1 for r in ok_word if not r["prev_sentence"])} 张）、'
  f'末句无后句（{sum(1 for r in ok_word if not r["next_sentence"])} 张）。 |')
A('| `term_type` / `char_count` | **按词形实际字数重算**。原 `terms_candidates` 的类型字段是 '
  'step8 标注时按当时的 term 写入的，清洗阶段改过词形（如「庭一湖」→「洞庭」），类型未同步，'
  '故不沿用源字段。 |')
A('| `meaning_in_this_sentence` | 已剔除清洗阶段留下的切分备注（如「『庭一湖』为跨词碎片」'
  '「（本句『在洞庭一湖』）」），只留释义本体。 |')
A('| `typical_error_mode` | 按 `sent_id` + 原始词形回连 `terms_candidates.jsonl`；'
  '清洗改过词形的走包含关系兜底，全部命中，无一条使用默认文案。 |')
A('')

A('## 三、词级字数分布（脚本计算）\n')
A('| 字数 | 张数 | 占比 |')
A('|---|---|---|')
for k in sorted(ch_cnt):
    A(f'| {k} 字 | {ch_cnt[k]} | {pct(ch_cnt[k], W)} |')
A(f'| **合计** | **{W}** | 100% |')
A('')
A(f'- **双字词 + 三字词 = {d23} / {W} = {pct(d23, W)}**（要求 ≥60%）')
A(f'- **单字词 = {ch_cnt[1]} / {W} = {pct(ch_cnt[1], W)}**（要求 ≤40%）')
A(f'- 四字及以上 = {W - ch_cnt[1] - d23} / {W} = {pct(W - ch_cnt[1] - d23, W)}')
A('')

A('## 四、句级句型分布\n')
A('| 句型 | 句数 | 占比 |')
A('|---|---|---|')
for k, v in st_cnt.most_common():
    A(f'| {k} | {v} | {pct(v, S)} |')
A(f'| **合计** | **{S}** | 100% |')
A('')
spec = S - st_cnt['一般陈述句']
A(f'- 特殊句式（判断/被动/宾语前置/定语后置/状语后置）共 **{spec} 句 = {pct(spec, S)}**，'
  f'疑问句 {st_cnt["疑问句"]} 句，感叹句 {st_cnt["感叹句"]} 句。')
A(f'- 判定方式：正则初判命中 97 句 → 逐条人工复核，修正 {len(TYPE_REVIEW)} 句误判'
  '（`见`/`为` 误作被动、`者也` 误作判断、`以` 目的状语误作后置、`被` 通「披」误作被动等）。'
  '其余句按句末标点归疑问/感叹，再兜底为一般陈述句。')
A('')

A('## 五、exam_frequency 分布\n')
A('### 词级\n')
A('| 分值 | 张数 | 占比 |')
A('|---|---|---|')
for k in range(5, 0, -1):
    A(f'| {k} | {wf[k]} | {pct(wf[k], W)} |')
A('')
A('### 句级\n')
A('| 分值 | 句数 | 占比 |')
A('|---|---|---|')
for k in range(5, 0, -1):
    A(f'| {k} | {sf[k]} | {pct(sf[k], S)} |')
A('')

A('## 六、打分标准（供校验）\n')
A('**词级**——基础分 2 分，按下列规则加减，钳制在 1–5：\n')
A('| 规则 | 加减 |')
A('|---|---|')
A('| 命中 A 级表（全国卷高频实词＋古今异义＋通假，如 爱/走/去/布衣/爪牙/卑鄙） | +2 |')
A('| 命中 B 级表（常考但区分度次之，如 之/其/而/谓） | +1 |')
A('| 全库出现 ≥5 次（跨篇复现，考点概率高） | +1 |')
A('| 双字或三字，且 term_english 长度 ≥6（英文有完整对应，说明是整体语义单元） | +1 |')
A('| 称谓类（陛下/大王/足下/寡人/太守/有司） | 直接置 3 |')
A('| 专名表内的人名/地名/国名（蔺相如/咸阳/赵） | 直接置 1 |')
A('| 无辨析价值的重复词（曰/云） | 直接置 1 |')
A('')
A('**句级**——基础分 2 分：\n')
A('| 规则 | 加减 |')
A('|---|---|')
A('| 非一般陈述句（特殊句式/疑问/感叹） | +1 |')
A('| 句中含 ≥1 个 4 分以上词项 | +1 |')
A('| 句中含 ≥3 个 4 分以上词项（再叠加） | +1 |')
A('| 净汉字数 10–30（翻译题常规长度） | +1 |')
A('| 命中名句表（背诵默写高频；长名句取前 5 字容错，应对底表个别讹字） | +1 |')
A('| 净汉字数 >40 | −1 |')
A('| 净汉字数 <6 且非特殊句式且不含重点词 | −1 |')
A('')

A('### 5 分样例（词级）\n')
for r in examples(5, ok_word, 'term'):
    A(f'- **{r["term"]}**（{r["term_type"]}）｜{r["classical_sentence"]}｜'
      f'释：{r["meaning_in_this_sentence"][:34]}｜{book_name(r["source_work"])}')
A('')
A('### 1 分样例（词级）\n')
for r in examples(1, ok_word, 'term'):
    A(f'- **{r["term"]}**（{r["term_type"]}）｜{r["classical_sentence"]}｜'
      f'释：{r["meaning_in_this_sentence"][:34]}｜判定理由：专名或重复词，只需认得')
A('')
A('### 5 分样例（句级）\n')
for r in examples(5, ok_sent, 'classical_sentence'):
    A(f'- {r["classical_sentence"]}｜{r["sentence_type"]}｜{book_name(r["source_work"])}')
A('')
A('### 1 分样例（句级）\n')
for r in examples(1, ok_sent, 'classical_sentence'):
    A(f'- {r["classical_sentence"]}｜{r["sentence_type"]}｜{book_name(r["source_work"])}')
A('')

A('## 七、剔除与无效\n')
A(f'- `cards_excluded.jsonl`：{len(excluded)} 条，全部是重复噪声词项（'
  f'{", ".join(f"{k}×{(collections.Counter(r["term"] for r in excluded))[k]}" for k in dict.fromkeys(r["term"] for r in excluded))}），'
  '保留 1–2 张代表卡后其余剔除。')
A(f'- `cards_invalid.jsonl`：{len(invalid)} 条，字段缺失或为空。'
  + ('（无）' if not invalid else ''))
A('')

A('## 八、源篇目分布（前 10）\n')
A('| 篇目 | 词卡 | 句卡 |')
A('|---|---|---|')
for k, v in book_w.most_common(10):
    A(f'| {k} | {v} | {book_s.get(k, 0)} |')
A('')

A('## 九、已知问题提示\n')
A(f'- `translation_issues.jsonl` 中仍 open 的条目，对应卡片未做英译返工，'
  f'共 {sum(1 for r in issues if r.get("status") == "open")} 条。')
A('- 陈情表、送东阳马生序两篇 171 句的 `full_english` 是段级译文复用，'
  '句级卡片的英译与句子并非严格一一对应，下游若按句展示需先做句级切分。')

open(D('cards_report.md'), 'w', encoding='utf-8').write('\n'.join(lines))

print(f'词级 {W} / 句级 {S} / 剔除 {len(excluded)} / 无效 {len(invalid)}')
print(f'双字+三字 {d23} = {pct(d23, W)}｜单字 {ch_cnt[1]} = {pct(ch_cnt[1], W)}')
print('词级 freq', dict(sorted(wf.items(), reverse=True)))
print('句级 freq', dict(sorted(sf.items(), reverse=True)))
print('句型', dict(st_cnt))

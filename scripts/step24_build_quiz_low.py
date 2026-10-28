#!/usr/bin/env python3
"""step24: 词级 quiz 第二批（exam_frequency 3/2/1 档，共 1122 张）。

与 step20 的区别：5/4 档 296 张能靠「同词异义项」撑起来，这批不行——
784 个词里 660 个全库只有唯一英译，other_senses 字段也是空的，必须跨词构造。

四源策略（按优先级）：
  1. 同词异义项（同 term 在他句的 term_english）
  2. 跨词候选：同句 > 同文章 > 全库，且**同词性桶**（避免「樯→masts」配
     「holds/differ」这种一眼按词性排除的废选项）
  3. 人工词库（ast 从 step20 抽取 CURATED，不重复维护）
  4. 不足 3 条 → needs_manual，不硬凑

专名卡（Teng Zijing / Yueyang Tower）选英文译名没有考点，整体排除。

用法：
  python step24_build_quiz_low.py                 # 试运行，只打印统计
  python step24_build_quiz_low.py --apply         # 写入 data/word_quiz_low.jsonl
  python step24_build_quiz_low.py --show w0013    # 查看指定卡结果
"""
import ast
import collections
import difflib
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORD_CARDS = os.path.join(BASE, 'data', 'word_cards.jsonl')
WORD_QUIZ = os.path.join(BASE, 'data', 'word_quiz.jsonl')
OUT = os.path.join(BASE, 'data', 'word_quiz_low.jsonl')
STEP20 = os.path.join(BASE, 'scripts', 'step20_build_quiz_full.py')


# ─────────────── 从 step20 抽取人工词库，避免两份 CURATED 各自漂移 ───────────────
def load_curated():
    """用 ast 读 step20 的字面量。

    不能直接 import：step20 是脚本，import 会执行全量生成并覆写 word_quiz.jsonl。
    """
    tree = ast.parse(open(STEP20, encoding='utf-8').read())
    want = {'CURATED': {}, 'CURATED_BY_ID': {}, 'MANUAL_FLAG': {}}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            if isinstance(tgt, ast.Name) and tgt.id in want:
                want[tgt.id] = ast.literal_eval(node.value)
    return want['CURATED'], want['CURATED_BY_ID'], want['MANUAL_FLAG']


CURATED, CURATED_BY_ID, MANUAL_FLAG = load_curated()

MANUAL_FILES = [os.path.join(BASE, 'data', f'word_quiz_low_manual_{i}.jsonl')
                for i in (1, 2, 3)]


def load_manual():
    """人工手写覆盖：id → {correct?, distractors}。

    存在独立文件里，重跑脚本不会丢人工成果。correct 可省略（沿用原英译），
    但整句级英译的卡必须改写 correct——不然四个选项还是整句碎片。
    """
    m = {}
    for path in MANUAL_FILES:
        if not os.path.exists(path):
            continue
        for line in open(path, encoding='utf-8'):
            rec = json.loads(line)
            if rec['id'] in m:
                raise SystemExit(f'手写覆盖重复 id：{rec["id"]}')
            m[rec['id']] = rec
    return m

# ─────────────── 单单词词性字典（V/N/A/D/F）─────────────────────
# 全库单单词英译固定 253 个小写词，逐个标注。短语不查这张表，走 shape()。
# 为什么必须标：不标的话「樯→masts」的干扰项会抽到 holds/differ，学生不用懂
# 古文，看词性就能排除，题等于废掉。
POS = {}
for _w in ('admonish apologize appoint arise ask attack attain becloud believe beset '
           'bless block borrow branch build carve cherish clasp collapse complete '
           'confound connect crack creep defeat demote destroy differ disappear '
           'dread drift drizzle end engrave envy exaggerate examine exhaust '
           'exterminate eye fall fast fear fight flourish flutter follow gather '
           'grant guess hear hesitate hold hug humiliate hurry intertwine invade '
           'invite kneel know leave lend linger lose love match meet name nominate '
           'obtain overwhelm plan play praise prepare pursue raise reach rebuild receive '
           'recommend refuse reign reply restore return roam rise ruin rule say '
           'screen seek sit scorn sever shun slander spend split spread stand stop '
           'submit swallow '
           'branching disgrace pity '
           'toast take trail tune turn vanish veil visit wax weaken weigh witness '
           'wear').split():
    POS[_w] = 'V'
for _w in ('angelica attendant banner beauty carriage compassion concubine corridor '
           'courage delusion document doubt dragon extirpation favour feeling grain '
           'ill illness insolence islet lawsuit leg limb mast mayfly medicine '
           'misfortune mist moat moonlight morning mud negligence oar outsider '
           'partiality pincer principle punctuation pursuit quilt reason '
           'righteousness river shoe snake soil stableman stream sun waterfall '
           'waterweed weakness weaver woman').split():
    POS[_w] = 'N'
for _w in ('alone ashamed asleep boundless coquettish correct dark different disgraced '
           'dishonoured drizzling exceptional fathomless fluttering frail '
           'glimmering glistening limpid mournful needy private profound restless '
           'solitary sound swifter swirling towering unadorned unbroken uneven '
           'unlettered weak white').split():
    POS[_w] = 'A'
for _w in ('alas cheerfully gladly hence likewise never once only originally '
           'privately seldom solemnly soon specially thereupon together truly '
           'unevenly westward').split():
    POS[_w] = 'D'
for _w in ('against athwart because how me my or over this until').split():
    POS[_w] = 'F'
for _w in ('homesick inexhaustible terrorised').split():
    POS[_w] = 'A'
POS['question'] = 'V'

# 屈折形式 → 原形。数据里的英译大量用过去式/三单/复数/现在分词，
# 不归并的话「legs/masts/oars」查不到词性，词性桶失效，退化成「单词都算一类」。
LEMMA = {}
for _pair in (
        # 过去式 / 三单 / 现在分词
        'apologized apologize', 'appointed appoint', 'asked ask',
        'attacked attack', 'attained attain', 'beclouded becloud',
        'blocking block', 'borrowed borrow', 'borrows borrow',
        'built build', 'cherished cherish', 'collapsed collapse',
        'completed complete', 'connects connect', 'cracked crack',
        'creeping creep', 'defeated defeat', 'demoted demote',
        'destroyed destroy', 'disappears disappear', 'drifting drift',
        'ended end', 'engraved engrave', 'exhausts exhaust',
        'exterminated exterminate', 'eyeing eye', 'fasted fast',
        'feared fear', 'flourished flourish', 'followed follow',
        'follows follow', 'gathered gather', 'guessed guess',
        'hesitated hesitate', 'holds hold', 'hugging hug',
        'hurried hurry', 'invited invite', 'kneeling kneel',
        'known know', 'left leave', 'lost lose', 'loved love',
        'met meet', 'named name', 'nominated nominate',
        'overwhelmed overwhelm', 'planned plan', 'played play',
        'prepared prepare', 'pursued pursue', 'raising raise',
        'reaches reach', 'rebuilt rebuild', 'recommended recommend',
        'refused refuse', 'reigns reign', 'replied reply',
        'rose rise', 'said say', 'sat sit', 'scorned scorn',
        'sitting sit', 'sought seek', 'spent spend', 'standing stand',
        'submits submit', 'swallows swallow', 'toasted toast',
        'took take', 'trailed trail', 'turned turn',
        'vanishing vanish', 'veiling veil', 'visited visit',
        'waxes wax', 'weakening weaken', 'weighed weigh',
        'weighing weigh', 'witnessed witness', 'wore wear',
        # 复数 / 不规则
        'attendants attendant', 'banners banner',
        'concubines concubine', 'corridors corridor',
        'delusions delusion', 'documents document', 'doubts doubt',
        'dragons dragon', 'favours favour', 'feelings feeling',
        'grains grain', 'islets islet', 'lawsuits lawsuit',
        'legs leg', 'limbs limb', 'masts mast', 'mayflies mayfly',
        'mists mist', 'oars oar', 'outsiders outsider',
        'pincers pincer', 'principles principle', 'quilts quilt',
        'rivers river', 'shoes shoe', 'snakes snake',
        'stablemen stableman', 'streams stream',
        'waterfalls waterfall', 'waterweeds waterweed',
        'weavers weaver', 'women woman'):
    _f, _b = _pair.split()
    LEMMA[_f] = _b

# 同义/近义改写组：组内互换仍是同一义项，不能当干扰项。
#
# 这批是逐个核出来的：低档里 101 个词有「同一个文言词、不同卡给了不同英译」的情况，
# 其中 70 组只是换个说法，义项完全一样。最致命的是单单词那类——
# 「弱」一张卡给 weak、另一张给 frail，字面无重叠，规则相似度抓不到，
# 学生选 frail 全对。全部按组归并，canon 相同即视为同一义项。
EQUIV_GROUPS = [
    {'attendants', 'in attendance'},
    {'the feudal lords', 'feudal lords'},
    {'the late emperor', 'the former emperor', 'the deceased emperor'},
    {'the emperor', 'his majesty'},
    {'said', 'replied', 'answered', 'remarked', 'the speech'},
    {'hence', 'therefore', 'thus', 'so', 'thereupon', 'consequently'},
    {'boundless', 'unbounded', 'limitless', 'inexhaustible', 'the endless'},
    {'holds', 'embraces', 'contains'},
    {'swallows', 'takes in'},
    # ── 同词多译的义项归并 ──
    {'athwart', 'cross bars', 'criss-crossed'},
    {'boundless in every direction', 'spread over'},
    {'confound', 'scatter in confusion', 'to din'},
    {'the disorders', 'troubled times', 'all over the place'},
    {'weak', 'frail'},
    {'weaken', 'weakening'},
    {'mild spring', 'warmth return'},
    {'feelings', 'my private feelings', 'the private feeling'},
    {'like the big dipper', 'the dipper'},
    {'appointed', 'was appointed', 'appointing me'},
    {'this', 'like this'},
    {'disgrace', 'disgraced', 'dishonoured', 'humiliate'},
    {'hear', 'listen to opinions'},
    {'principles', 'reason', 'rule'},
    {'exhaust', 'exhausts', 'spent'},
    {'fresh and lovely', 'fresh or rich'},
    {'favoured by', 'receive'},
    {'dread', 'fear', 'feared', 'your fear'},
    {'compassion', 'pity'},
    {'homesick', 'my longing'},
    {'fallen petals', 'water fallen'},
    {'one and the same body', 'together'},
    {'hasten to serve', 'to serve'},
    {'outsiders', 'people outside', 'the outside world'},
    {'weavers', 'women'},
    {'invited', 'receive the enemy'},
    {'sought', 'to seek'},
    {'delusions', 'doubts', 'felt confused'},
    {'follow a teacher', 'followed teachers', 'seek my teachers'},
    {'the tradition of honouring teachers', 'the tradition of teachers'},
    {'concubines', 'your beauty-maids'},
    {'rivers', 'streams', 'the river'},
    {'beclouded', 'screen', 'veiling'},
    {'grains', 'grains of millet'},
    {'clasp', 'hugging'},
    {'across the realm', 'the four seas'},
    {'completed', 'ended'},
    {'asleep', 'lying abed', 'sound sleep'},
    {'only', 'specially'},
    {'known', 'named'},
    {'but when, then', 'yet, since'},
    {'drizzling', 'mists'},
    {'one unbounded expanse', 'the boundless expanse'},
    {'insolence', 'negligence'},
    {'bid farewell and left', 'let us retire'},
    {'cheerfully', 'gladly'},
    {'uneven', 'unevenly'},
    {'like a snake', 'snakes'},
    {'chariot wheels traces', 'the traces left'},
    {'pursued', 'pursuit'},
    {'at full', 'waxes'},
    {'fall', 'stepped back'},
    {'steamed and bent', 'steaming and bending'},
    {'a deep pool', 'the fathomless deep'},
    {'a good learner', 'those who studied'},
    {'ashamed', 'seems shameful'},
    {'a thread of silk', 'threads of silk'},
    {'eyeing', 'gazing in the mirror'},
    {'the land west of the yellow river', 'west of the yellow river'},
    {'strategic commanderies', 'the most important places'},
    {'hold equal rank', 'its fellow lords'},
    {'bare your shoulders', 'bared his shoulders and back'},
    {'fast', 'fasted'},
    {'the nine guests', 'the nine guests ceremony'},
    {'never', 'without the least'},
    {'lay down my life', 'losing my head'},
    {'copied them out by hand', 'copy by hand'},
    {'the elder', 'a learned elder of my home region'},
]

STOP = {'the', 'a', 'an', 'of', 'in', 'to', 'and', 'or', 'was', 'were', 'is',
        'are', 'be', 'been', 'being', 'his', 'her', 'their', 'its', 'it',
        'him', 'them', 'he', 'she', 'they', 'with', 'at', 'on', 'for',
        'from', 'by', 'as', 'that', 'this', 'these', 'those', 'had', 'has',
        'have', 'not', 'no', 'all', 'one', 'up', 'out', 'into', 'over'}
AUX = {'was', 'were', 'is', 'are', 'be', 'been', 'being', 'had', 'has', 'have',
       'did', 'does', 'do', 'can', 'could', 'will', 'would', 'shall', 'should',
       'may', 'might', 'must'}
TYPE_CN = {'wrong_sense': '多义项误选', 'modern_sense': '以今义解古义',
           'sense_shift': '整体义偏移', 'char_decompose': '拆字误解',
           'structure_error': '固定结构还原错误', 'proper_noun': '专名混淆',
           'cross_term': '他词义项串入'}


def words(s):
    return re.findall(r"[A-Za-z']+", s)


def norm(s):
    """语义归一化：去大小写、开头冠词、所有格、复数、标点。"""
    s = s.lower().strip()
    s = re.sub(r"'s\b", '', s)          # 先掉所有格，否则 the late emperor's ≠ the late emperor
    s = re.sub(r'^(the|a|an)\s+', '', s)
    s = re.sub(r'[^a-z0-9 ]', '', s)
    s = re.sub(r'\b(\w{3,})s\b', r'\1', s)   # 粗略去复数
    return re.sub(r'\s+', ' ', s).strip()


_EQUIV = {}
for _g in EQUIV_GROUPS:
    _rep = min(norm(x) for x in _g)
    for _x in _g:
        _EQUIV[norm(_x)] = _rep


def canon(text):
    n = norm(text)
    return _EQUIV.get(n, n)


def is_proper(te):
    ws = words(te)
    return bool(ws) and all(w[0].isupper() for w in ws)


SUBJ_PRON = {'he', 'she', 'they', 'we', 'i', 'you', 'it'}
CLAUSE_MARK = {'because', 'although', 'who', 'which', 'why', 'how', 'when', 'if'}
WH_FIRST = {'how', 'what', 'why', 'who', 'where', 'when', 'whether'}


def is_sentence_level(te):
    """term_english 是整句而不是词义。

    「何以」被译成 What are you basing your battle on、「曰」被译成 They would
    surely say、「邪」被译成 Is it truly that there are no horses——这些是上游
    抽词时把整句英译挂到了虚词上。拿它们出词义题，四个选项全是整句碎片，
    跟句级题重复，考点也没了。标 needs_manual 留给人工写词义。

    三条判据缺一不可：
      · 带主格代词（They would surely say / I told him）
      · 疑问词开头（how does General Lian compare with）
      · 4 词以上且含从句标记（because its mind is restless）
    """
    ws = [w.lower() for w in words(te)]
    if '?' in te:
        return True
    if any(w in SUBJ_PRON for w in ws):
        return True
    if len(ws) > 1 and ws and ws[0] in WH_FIRST:
        return True
    if len(ws) >= 4 and any(w in CLAUSE_MARK for w in ws):
        return True
    return False


def pos_of(te):
    ws = words(te)
    if len(ws) != 1:
        return None
    w = ws[0].lower()
    return POS.get(w) or POS.get(LEMMA.get(w, ''))


MISSING_POS = set()


CONJ = {'but', 'and', 'or', 'so', 'yet', 'if', 'when', 'while', 'though',
        'although', 'because', 'nor', 'then', 'than', 'as'}


# 大写开头的功能词。「Cao Qufu said」是人名短语，「Those in power」是代词短语，
# 同一个 caphead 桶会让「环滁→All around Chu」抽到人名当干扰项。
CAP_FUNC = {'all', 'those', 'these', 'this', 'that', 'such', 'without', 'with',
            'but', 'and', 'so', 'then', 'yet', 'if', 'when', 'both', 'each',
            'every', 'some', 'no', 'not', 'never', 'only', 'what', 'why', 'how',
            'unlike', 'among', 'through', 'after', 'before', 'beyond'}


def shape(te):
    """形态桶。单单词按词性细分，短语按首词结构＋词数。"""
    ws = words(te)
    if not ws:
        return 'empty'
    if len(ws) == 1:
        return f'single/{pos_of(te) or "?"}'
    head = ws[0].lower()
    n = len(ws)
    nsize = 2 if n == 2 else (3 if n == 3 else 4)
    if head in CONJ:
        # 「but in」是连词短语，「grow dark」是动词短语，同归 other 会让
        # 「阴翳→grow dark」抽到「but in」当干扰项
        kind = 'conj'
    elif head in ('was', 'were'):
        kind = 'be_past'
    elif head in ('is', 'are', 'be', 'been', 'being'):
        kind = 'be_pres'
    elif head in AUX:
        kind = 'aux'
    elif head in ('the', 'a', 'an'):
        kind = 'np'
    elif head in ('his', 'her', 'their', 'its', 'my', 'our', 'your'):
        kind = 'poss'
    elif head in ('to', 'in', 'at', 'on', 'with', 'by', 'from', 'for', 'into', 'upon'):
        kind = 'prep'
    elif head in ('not', 'no', 'never'):
        kind = 'neg'
    elif ws[0][0].isupper():
        # 大写开头的短语还要再分一层：功能词开头（All around Chu / Those in
        # power）和专名开头（Cao Qufu said）不能同桶。
        kind = 'capfunc' if head in CAP_FUNC or head in CONJ else 'namehead'
    elif head in ('he', 'she', 'it', 'they', 'we', 'you', 'i', 'there'):
        # 带主语的整句碎片：「he found a mountain」跟「bright moon」不是一类
        kind = 'subj'
    else:
        kind = pos_of(ws[0]) or 'other'
    return f'{kind}/{nsize}'


def family(sh):
    """桶不够用时可以互借的「同族」。

    单单词绝不互借——动词配名词正是要避免的错配；
    但 be_past / be_pres / aux 都以谓语动词开头，np / poss 都是名词短语，
    互借不会让学生靠外形排除。小桶（be_past/4 全库只有 2 张）不互借就凑不满。
    """
    kind = sh.split('/')[0]
    if kind in ('be_past', 'be_pres', 'aux'):
        return 'pred'
    if kind in ('np', 'poss'):
        return 'nominal'
    return None


ZH_STOP = set('之其而也者以于为所乃则焉矣乎哉夫且若故曰不无有是此')


def zh_sim(a, b):
    """中文释义的实字重叠度，用来给候选排「语义场接近度」。

    结构桶只能保证「外形同类」，管不了「意思离得远」——「情→feelings」的
    干扰项抽到 angelica（白芷）就是外形对、语义不搭。释义都提到「情感」的
    候选会更靠前。粗糙，但比随机强。
    """
    ca = {c for c in a if '\u4e00' <= c <= '\u9fff' and c not in ZH_STOP}
    cb = {c for c in b if '\u4e00' <= c <= '\u9fff' and c not in ZH_STOP}
    if not ca or not cb:
        return 0.0
    return len(ca & cb) / len(ca | cb)


class Guard:
    """选项质量闸门，所有来源的干扰项都必须过。"""

    def __init__(self, correct):
        self.correct = correct
        self.L = max(len(correct), 1)
        self.seen = {correct}
        self.seen_norm = {canon(correct)}

    def ok(self, text, same_term=False):
        if not text or text in self.seen:
            return False
        if canon(text) in self.seen_norm:
            return False
        ratio = len(text) / self.L
        if not (0.45 <= ratio <= 2.4):
            return False
        if abs(len(words(text)) - len(words(self.correct))) > 2:
            return False
        if same_term:
            # 同一个词在不同卡上的英译，措辞稍变但义项常常相同：
            # 「万顷」一张卡 one unbounded expanse、另一张 the boundless expanse，
            # 选哪个都对。「渊」a deep pool / the fathomless deep 同理。
            # 所以同词来源的候选要额外按「像不像」筛一遍——越像越可能是同义改写。
            ca = {w.lower() for w in words(self.correct) if w.lower() not in STOP}
            cb = {w.lower() for w in words(text) if w.lower() not in STOP}
            if ca and cb and len(ca & cb) / min(len(ca), len(cb)) >= 0.5:
                return False
            if difflib.SequenceMatcher(None, self.correct.lower(),
                                       text.lower()).ratio() >= 0.55:
                return False
        return True

    def take(self, text):
        self.seen.add(text)
        self.seen_norm.add(canon(text))


def usable_cand(correct, te):
    """跨词候选能不能上桌。

    「具兴」的干扰项抽到 glad because of external things（以物喜的整句英译），
    「择师」抽到 those who studied——都是从句碎片，一眼就知道不是词义。
    """
    if is_sentence_level(te) and not is_sentence_level(correct):
        return False
    cw_correct = {w.lower() for w in words(correct)}
    if any(w.lower() in CLAUSE_MARK for w in words(te)) \
            and not any(w in CLAUSE_MARK for w in cw_correct):
        return False
    return True


def main():
    cards = [json.loads(l) for l in open(WORD_CARDS, encoding='utf-8')]
    done = {json.loads(l)['id'] for l in open(WORD_QUIZ, encoding='utf-8')}

    by_term = collections.defaultdict(list)
    for c in cards:
        by_term[c['term']].append(c)

    pool = [c for c in cards if not is_proper(c['term_english'])
            and not is_sentence_level(c['term_english'])]
    by_shape = collections.defaultdict(list)
    for c in pool:
        by_shape[shape(c['term_english'])].append(c)
    by_sentence = collections.defaultdict(list)
    for c in pool:
        by_sentence[c['classical_sentence']].append(c)
    by_work = collections.defaultdict(list)
    for c in pool:
        by_work[c['source_work']].append(c)

    todo = [c for c in cards if c['id'] not in done]
    proper = [c for c in todo if is_proper(c['term_english'])]
    todo = [c for c in todo if not is_proper(c['term_english'])]
    sentl = [c for c in todo if is_sentence_level(c['term_english'])]
    todo = [c for c in todo if not is_sentence_level(c['term_english'])]

    manual = load_manual()
    by_id = {c['id']: c for c in cards}
    out, st = [], collections.Counter()

    # 0) 人工手写优先。注意下面两段循环都要显式跳过 handled——
    #    「先处理 A 再处理 B」时 B 不跳过 A 已处理的集合，人工成果会被再洗一遍
    #    （句级 step23 就踩过这个坑）。
    handled = set()
    for cid, rec in manual.items():
        c = by_id[cid]
        ds = rec['distractors'][:3]
        ok = len(ds) == 3
        out.append({
            'id': cid, 'term': c['term'], 'char_count': c['char_count'],
            'exam_frequency': c['exam_frequency'],
            'correct': rec.get('correct') or c['term_english'],
            'distractors': ds,
            'needs_manual': not ok,
            'note': '' if ok else f'手写仅 {len(ds)} 条',
        })
        if ok:
            handled.add(cid)
            st['manual_ok'] += 1
        else:
            st['manual_short'] += 1

    for c in todo:
        if c['id'] in handled:
            continue
        correct = c['term_english']
        sh = shape(correct)
        g = Guard(correct)
        ds = []
        src = collections.Counter()

        def add(text, etype, expl, same_term=False):
            # usable_cand 对**所有来源**生效：同词异义项这条路径也会带进整句级
            # 英译（「蒙」的 I have been promoted、「学者」的 those who studied），
            # 只在跨词那条路径上过滤会漏掉一半。
            if len(ds) >= 3 or not usable_cand(correct, text):
                return False
            if not g.ok(text, same_term):
                return False
            g.take(text)
            ds.append({'text': text, 'error_type': etype, 'explanation': expl})
            return True

        # 1) 同词异义项
        others = sorted({x['term_english'] for x in by_term[c['term']]} - {correct},
                        key=len)
        for t in others:
            if len(ds) >= 3:
                break
            if is_proper(t):
                continue
            m = next(x['meaning_in_this_sentence'] for x in by_term[c['term']]
                     if x['term_english'] == t)
            if add(t, 'wrong_sense', f'误取「{c["term"]}」在他句的义项（{m[:20]}）',
                   same_term=True):
                src['same_term'] += 1

        # 2) 人工词库
        for t, et, ex in CURATED_BY_ID.get(c['id'], []) + CURATED.get(c['term'], []):
            if len(ds) >= 3:
                break
            if add(t, et, ex):
                src['curated'] += 1

        # 3) 跨词：同词性桶 + 同句 > 同文章 > 全库
        #    scope 决定「像不像」，shape 决定「能不能靠外形排除」，两者都要管。
        if len(ds) < 3:
            fam = family(sh)
            cands = []
            for strict in (True, False):
                for scope, group in (('same_sentence', by_sentence[c['classical_sentence']]),
                                     ('same_work', by_work[c['source_work']]),
                                     ('global', by_shape[sh] if strict else pool)):
                    for x in group:
                        if x['term'] == c['term']:
                            continue
                        xs = shape(x['term_english'])
                        if strict:
                            if xs != sh:
                                continue
                        elif not fam or family(xs) != fam:
                            continue
                        if is_proper(x['term_english']):
                            continue
                        if not usable_cand(correct, x['term_english']):
                            continue
                        cands.append((0 if strict else 1, scope, x))
                if len(cands) >= 8:
                    break
            rank = {'same_sentence': 0, 'same_work': 1, 'global': 2}
            cm = c['meaning_in_this_sentence']
            cands.sort(key=lambda t: (t[0], rank[t[1]],
                                      -zh_sim(cm, t[2]['meaning_in_this_sentence']),
                                      abs(len(t[2]['term_english']) - len(correct))))
            for _, scope, x in cands:
                if len(ds) >= 3:
                    break
                if add(x['term_english'], 'cross_term',
                       f'误作「{x["term"]}」的义项（{x["meaning_in_this_sentence"][:14]}）'):
                    src[scope] += 1

        needs_manual = len(ds) < 3
        st['ok' if not needs_manual else 'short'] += 1
        st[f'have{len(ds)}'] += 1
        for k, v in src.items():
            st['src_' + k] += v
        out.append({
            'id': c['id'], 'term': c['term'], 'char_count': c['char_count'],
            'exam_frequency': c['exam_frequency'],
            'correct': correct, 'distractors': ds,
            'needs_manual': needs_manual,
            'note': '' if not needs_manual else f'仅凑到 {len(ds)} 条',
        })

    # 整句级英译的卡也写进结果，但标 needs_manual——留在文件里才能追踪缺口，
    # 直接丢掉的话下一个人不知道这 65 张去哪了。
    for c in sentl:
        if c['id'] in handled:
            continue
        out.append({
            'id': c['id'], 'term': c['term'], 'char_count': c['char_count'],
            'exam_frequency': c['exam_frequency'],
            'correct': c['term_english'], 'distractors': [],
            'needs_manual': True,
            'note': 'term_english 为整句级英译，需人工补词义后再出题',
        })

    n_ok = sum(1 for q in out if not q['needs_manual'])
    n_short = len(out) - n_ok
    print(f'底层卡 {len(todo) + len(proper) + len(sentl)} 张 = 专名 {len(proper)}（排除）'
          f' + 整句级英译 {len(sentl)} + 普通卡 {len(todo)}')
    print(f'人工手写 {st["manual_ok"]} 张（{st["manual_ok"] * 3} 条）')
    print(f'自动凑满 3 条 {st["ok"]}，不足 {st["short"]}')
    print(f'→ 合计可出题 {n_ok} / {len(out)}，待人工 {n_short}')
    print('条数分布:', {k[4:]: v for k, v in sorted(st.items()) if k.startswith('have')})
    print('来源分布:', {k[4:]: v for k, v in st.items() if k.startswith('src_')})
    ty = collections.Counter(d['error_type'] for q in out for d in q['distractors'])
    print('error_type:', dict(ty.most_common()))

    if '--show' in sys.argv:
        idx = {q['id']: q for q in out}
        for i in sys.argv[sys.argv.index('--show') + 1:]:
            q = idx.get(i)
            if not q:
                print(i, '不在待做集合')
                continue
            print('=' * 72)
            print(f"{q['id']} f{q['exam_frequency']} 「{q['term']}」 [{shape(q['correct'])}]")
            print('  ✓', q['correct'])
            for d in q['distractors']:
                print('   ✗', d['text'], '|', d['error_type'])
                print('      ', d['explanation'][:70])

    if '--apply' in sys.argv:
        with open(OUT, 'w', encoding='utf-8') as f:
            for q in out:
                f.write(json.dumps(q, ensure_ascii=False) + '\n')
        print(f'写出 {OUT}')
    else:
        print('（试运行，未落盘；加 --apply 写入）')


if __name__ == '__main__':
    main()

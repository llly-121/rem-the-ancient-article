# -*- coding: utf-8 -*-
"""step18：词级干扰项生成

本轮交付 30 条样本（全手工撰写），同时给出全量规则引擎的骨架与覆盖率测算。

干扰项错误类型（error_type）：
  char_decompose   拆字误解——把合成词逐字直译
  sense_shift      整体义偏移——方向、程度、范围、主体被改
  wrong_sense      多义项误选——取了该词的另一个真实义项
  modern_sense     以今义解古义
  structure_error  固定结构还原错误
  proper_noun      专名混淆
"""
import json
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(BASE, 'data', *p)

cards = [json.loads(l) for l in open(D('word_cards.jsonl'), encoding='utf-8')]
by_id = {r['id']: r for r in cards}

# (card_id, [(text, error_type, explanation), x3])
SAMPLE = [
    ('w0010', [  # 属 asked me
        ('belonged to me', 'char_decompose', '按今义「属于」拆解，未辨出通『嘱』，丢了托付义'),
        ('told me', 'sense_shift', '把「嘱」弱化为一般的「告诉」，抹去「托付、请托」的分量'),
        ('wrote it for me', 'wrong_sense', '「属」另有「撰写」义（属文），此处是嘱托我写，不是替我写'),
    ]),
    ('w0082', [  # 绝 without cease
        ('cut off', 'char_decompose', '取「绝」本义「切断」，用于道路；本句是往来不断'),
        ('crossed the river', 'wrong_sense', '「绝」有「横渡」义（绝江河），本句并非渡水'),
        ('died out', 'wrong_sense', '「绝」有「灭绝」义，用于国祚家族，本句指人流不断'),
    ]),
    ('w0808', [  # 私 privately
        ('selfishly', 'wrong_sense', '「私」在「莫不私王」中是「偏爱」，本句是「私下」'),
        ('without leave', 'wrong_sense', '「私」有「私自、擅自」义，本句强调「暗中」而非「擅权」'),
        ('personally', 'sense_shift', '「亲自」与「私下」不同：原文燕王是暗中拉拢，不是亲自出面'),
    ]),
    ('w0023', [  # 异 differ
        ('wonder at', 'wrong_sense', '「异」有「以……为异、惊异」义（渔人甚异之），本句问的是「不同」'),
        ('be altered', 'wrong_sense', '「异」有「变化」义，本句问的是有无差别，不是会不会变'),
        ('strange things', 'sense_shift', '把形容词「不同」误作名词「异事」，词性错'),
    ]),
    ('w0086', [  # 坐 sitting
        ('being punished', 'wrong_sense', '「坐」有「因罪获罚」义（坐法），本句只是起身坐下'),
        ('seated guests', 'sense_shift', '动词误作名词；「众宾欢也」才是宾客，此处写的是动作'),
        ('taking seats', 'sense_shift', '添出「依次入座」的秩序感，原文是觥筹交错间的杂乱起坐'),
    ]),
    ('w0102', [  # 盖 because
        ('probably', 'wrong_sense', '「盖」表推测「大概」，本句引出原因，是实义连词'),
        ('a covering', 'char_decompose', '取「盖」本义「覆盖、盖子」，未识其连词功能'),
        ('to begin with', 'structure_error', '当句首发语词处理，未承当因果'),
    ]),
    ('w0016', [  # 汤 vast and mighty
        ('hot water', 'char_decompose', '按今义「热水」读 tāng，未辨此处读 shāng'),
        ('a bowl of soup', 'char_decompose', '今义「汤羹」，与「浩浩」完全不搭'),
        ('turbulent and muddy', 'sense_shift', '「水势浩大」误加「浑浊」，原文只言其广阔'),
    ]),
    ('w0001', [  # 谪守
        ('was appointed governor', 'sense_shift', '丢掉「谪」的贬谪义，译成正常任命，方向反了'),
        ('was banished to guard the border', 'char_decompose', '拆「谪」为流放、「守」为守卫，把文职守郡当作戍边'),
        ('resigned as governor', 'wrong_sense', '「守」误作「辞官」，与被贬出仕正好相反'),
    ]),
    ('w0134', [  # 布衣 a commoner
        ('a cloth seller', 'char_decompose', '拆成「布」＋「衣」的买卖方，未识其借代身份'),
        ('a poor scholar', 'sense_shift', '窄化为「贫寒读书人」，原文泛指平民'),
        ('plain-clothed man', 'sense_shift', '字面直译成穿着，未抽象为「无官职者」'),
    ]),
    ('w1240', [  # 可以（可以凭借）
        ('it is possible to', 'modern_sense', '今义「可以」表可能，丢掉「可以凭借」里的「以」'),
        ('you are allowed to', 'modern_sense', '表许可，原文强调的是「凭这一点」，不是谁批准'),
        ('he may become a teacher', 'structure_error', '把「可以」整体当能愿动词，「以」字无着落，主语也换成了第三人称'),
    ]),
    ('w0101', [  # 陛下
        ('the palace steps', 'char_decompose', '「陛」＝台阶，逐字直译，未转敬称'),
        ('Your Highness', 'sense_shift', '对亲王、高位者的称呼，不是皇帝的专称'),
        ('My Lord', 'sense_shift', '泛称，抬不出「皇帝」这一身份'),
    ]),
    ('w0785', [  # 上卿
        ('above the ministers', 'char_decompose', '读成方位结构「在卿之上」，把官职名拆成位置关系'),
        ("a senior official's wife", 'wrong_sense', '「卿」另有夫妇间爱称义，此处是爵位'),
        ('a top-ranking general', 'sense_shift', '「卿」误作武将；本句是文职最高阶'),
    ]),
    ('w0114', [  # 有司
        ('those who own the office', 'char_decompose', '拆「有」为「拥有」，「司」为官署，合起来讲不通'),
        ("the emperor's attendants", 'sense_shift', '窄化为近侍，原文指各有专职的管事官员'),
        ('the law court', 'sense_shift', '窄化为司法机关，原文还包括行政、财务等职司'),
    ]),
    ('w0903', [  # 汤镬
        ('a pot of soup', 'char_decompose', '汤＝汤羹、镬＝锅，把刑具读成炊具'),
        ("the executioner's block", 'wrong_sense', '与「斧质」混淆，同属刑名但刑具不同'),
        ('boiling oil', 'sense_shift', '介质误作油；「汤」是滚水，不是油'),
    ]),
    ('w1006', [  # 孰与
        ('who is with General Lian', 'structure_error', '拆作「孰」＝谁＋「与」＝和……一起，比较结构全失'),
        ('is General Lian as good as', 'structure_error', '把「哪一个更」抹平成「一样好」，比较方向丢失'),
        ('General Lian and the King of Qin', 'sense_shift', '只列出双方，没有任何比较含义'),
    ]),
    ('w0268', [  # 何以
        ('why must we fight', 'structure_error', '「何以」＝凭什么，误作「为什么」，凭仗义丢失'),
        ('how can you fight', 'structure_error', '「以」的凭借义未译出，只剩「怎么」'),
        ('with what weapons', 'sense_shift', '窄化为武器，本句问的是凭仗什么条件（民心、祭祀、断案）'),
    ]),
    ('w0130', [  # 长史
        ('the long history', 'char_decompose', '逐字 long＋history，典型拆字误解'),
        ('senior recorders', 'sense_shift', '按「史官」理解，未取丞相府属官之长的职能'),
        ('the chief of staff', 'sense_shift', '现代军职，时代与职能双错'),
    ]),
    ('w0210', [  # 无论
        ('no matter what', 'modern_sense', '今义连词「无论」，原文是「不要说，更不必说」的递进'),
        ('without debate', 'char_decompose', '拆作「不＋论」，读成「不讨论」'),
        ('even so', 'sense_shift', '读成让步，原文是递进'),
    ]),
    ('w0757', [  # 山东
        ('Shandong Province', 'modern_sense', '今省名，原文指崤山、华山以东的广大地区'),
        ('the eastern hills', 'sense_shift', '泛化为「东部山地」，未落实为地理区域'),
        ('mountain east', 'char_decompose', '硬拼两字，未成地名'),
    ]),
    ('w0898', [  # 见欺
        ('to see the deception', 'structure_error', '「见」误作「看见」，被动标记「见……于」丢失'),
        ('to meet the cheat', 'structure_error', '「见」误作「遇见」，与「欺」组成动宾'),
        ('to be looked down upon', 'sense_shift', '被动结构对了，但动词错成「轻视」，不是「欺骗」'),
    ]),
    ('w0002', [  # 滕子京
        ('the governor of Teng', 'char_decompose', '把姓名读成「滕地的长官」，姓当封地、名当职官'),
        ("Teng Zijing's son", 'proper_noun', '误作其子，人物关系错'),
        ('Teng Zongliang', 'proper_noun', '同姓他人，名被替换'),
    ]),
    ('w0047', [  # 以物喜
        ('give things away gladly', 'char_decompose', '拆「以」＝用、「喜」＝高兴，拼成「高兴地送东西」'),
        ("rejoice in one's own gains", 'sense_shift', '把「物」换成「己」，与下句「不以己悲」混为一谈'),
        ('be pleased with material wealth', 'sense_shift', '窄化为「财物」，原文的「物」指外在境遇'),
    ]),
    ('w0189', [  # 才通人
        ('only a talented man can enter', 'char_decompose', '「才」＝才能、「通人」＝通达之人，三个字全读错'),
        ('it was open to everyone', 'sense_shift', '「通人」误解为「对所有人开放」，与原意「仅容一人」相反'),
        ('the tunnel led to the village', 'sense_shift', '「通」误作「通向」，宾语由「人」换成「村」'),
    ]),
    ('w0119', [  # 远小人
        ('faraway petty men', 'char_decompose', '「远」作形容词「遥远的」，整句变名词短语，动词性丢失'),
        ('despise the lowly', 'sense_shift', '「远」加重为「鄙视」，原文是保持距离而非轻贱'),
        ('distance yourself from the young', 'wrong_sense', '「小人」误作「年幼者」，道德判断变成了年龄'),
    ]),
    ('w0118', [  # 亲贤臣
        ("one's own worthy ministers", 'char_decompose', '「亲」作形容词「亲信的」，动作变成修饰语'),
        ('marry into a worthy family', 'wrong_sense', '「亲」误作「结亲」，与政治语境完全不搭'),
        ('love the virtuous officials', 'sense_shift', '「亲近」偏移为「爱戴」，君臣关系被情感化'),
    ]),
    ('w0004', [  # 越明年
        ('leap over next year', 'char_decompose', '「越」＝跨越，把时间推进读成跳跃动作'),
        ('in the past year', 'sense_shift', '「越」误作「越过→过去」，时间方向反了'),
        ('at the end of next year', 'sense_shift', '添出「末」义；「越明年」指到了第二年，不含年末'),
    ]),
    ('w0008', [  # 岳阳楼
        ('the sunlit tower', 'char_decompose', '「阳」＝山南水北的向阳面，把专名当方位描写'),
        ('Yueyang Pavilion', 'proper_noun', '建筑类型误作亭阁；楼与亭在形制上不同'),
        ('the west gate tower', 'proper_noun', '泛化为城门楼，丢了「岳阳」这一地名'),
    ]),
    ('w0003', [  # 巴陵郡
        ('the tomb at Baling', 'char_decompose', '「陵」＝陵墓，把郡名读成墓葬'),
        ('Baling County', 'proper_noun', '郡误作县，行政级别降了一等'),
        ('the prefect of Baling', 'sense_shift', '行政区误作人，主语类别错'),
    ]),
    ('w1083', [  # 林寒涧肃
        ('the woods are cold and the stream is strict', 'char_decompose', '逐字对译：「肃」作「严厉」，与「寂静」无关'),
        ('the forest is silent in winter', 'sense_shift', '丢掉「涧」，还添出「冬季」这一限定'),
        ('the hills are bleak and the gorge is dry', 'sense_shift', '「寒」作荒凉、「肃」作干涸，两处都偏'),
    ]),
    ('w0343', [  # 积土成山
        ('earth is carried to the mountain', 'sense_shift', '方向反转：成了往山上运土，而非土堆积成山'),
        ('earth accumulates, the mountain succeeds', 'char_decompose', '「成」误作「成功／接着」，动词读错'),
        ('a mound built of earth and stone', 'sense_shift', '添出「石」，且把「山」降为「土丘」'),
    ]),
]

# ────────────────────────── 校验 ──────────────────────────
TYPES = {'char_decompose', 'sense_shift', 'wrong_sense', 'modern_sense',
         'structure_error', 'proper_noun'}


def validate(item):
    """返回问题列表；空表示合格。"""
    problems = []
    correct = item['correct']
    ds = item['distractors']
    if len(ds) != 3:
        problems.append(f'干扰项数 {len(ds)}≠3')
    texts = [d['text'] for d in ds]
    if len(set(texts)) != len(texts):
        problems.append('干扰项文本重复')
    if correct in texts:
        problems.append('干扰项与正确答案相同')
    # 长度相当：以字符数计，比值限制在 0.4–2.6
    cl = len(correct)
    for t in texts:
        r = len(t) / cl if cl else 0
        if r < 0.4 or r > 2.6:
            problems.append(f'长度失衡 {t!r}={len(t)} vs correct={cl}（比值 {r:.2f}）')
    # 类型多样：至少 2 种
    if len({d['error_type'] for d in ds}) < 2:
        problems.append('error_type 只有一种')
    for d in ds:
        if d['error_type'] not in TYPES:
            problems.append(f'未知 error_type {d["error_type"]}')
        if not d.get('explanation'):
            problems.append('缺 explanation')
    return problems


rows = []
bad = []
for cid, dists in SAMPLE:
    c = by_id.get(cid)
    if not c:
        bad.append({'id': cid, 'reason': '卡不存在'})
        continue
    item = {
        'id': cid,
        'term': c['term'],
        'char_count': c['char_count'],
        'correct': c['term_english'],
        'distractors': [{'text': t, 'error_type': e, 'explanation': x} for t, e, x in dists],
    }
    p = validate(item)
    if p:
        item['needs_manual'] = True
        item['_problems'] = p
        bad.append(item)
    rows.append(item)

with open(D('word_quiz_sample.jsonl'), 'w', encoding='utf-8') as f:
    for r in rows:
        r.pop('_problems', None)
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

# ────────────────────────── 统计 ──────────────────────────
import collections
tc = collections.Counter(r['char_count'] for r in rows)
ec = collections.Counter(d['error_type'] for r in rows for d in r['distractors'])
print(f'样本 {len(rows)} 条，校验不通过 {len(bad)} 条')
if bad:
    for b in bad:
        print('  ✗', b.get('id'), b.get('_problems') or b.get('reason'))
print('字数分布', dict(sorted(tc.items())))
print('error_type 分布', dict(ec.most_common()))
print()
print('每条 error_type 构成：')
for r in rows:
    kinds = [d['error_type'] for d in r['distractors']]
    tag = '★拆字' if 'char_decompose' in kinds else ''
    print(f"  {r['char_count']}字 {r['term']:6s} {','.join(k[:6] for k in kinds):44s} {tag}")
print()
tri = [r for r in rows if r['char_count'] == 3]
print(f'三字词 {len(tri)} 条，其中含 char_decompose 的 {sum(1 for r in tri if any(d["error_type"]=="char_decompose" for d in r["distractors"]))} 条')

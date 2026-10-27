# -*- coding: utf-8 -*-
"""step15: 生成专有名词对照表 data/proper_noun_glossary.json

范围：出师表、廉颇蔺相如列传、过秦论（共 166 句）
类别：人名 / 官职 / 地名 / 刑名礼俗
字段：
  term        中文专名（原文写法）
  category    类别
  canonical   规范英译（唯一标准形式）
  accept      可接受变体（正则，仅用于合规检查）
  note        译法依据 / 常见错法
  occurrences 在 166 句中的出现位置（course_cards_v2 行号）
"""
import json
import re

CARDS = 'data/course_cards_v2.jsonl'
OUT = 'data/proper_noun_glossary.json'
TITLES = ['出师表', '廉颇蔺相如列传', '过秦论']

cards = [json.loads(l) for l in open(CARDS, encoding='utf-8')]
scope_idx = [i for i, c in enumerate(cards) if c['title'] in TITLES]

# term, category, canonical, accept(正则), note
E = [
    # ───────── 人名 ─────────
    ('蔺相如', '人名', 'Lin Xiangru', r'Lin Xiangru|Xiangru',
     '姓蔺名相如。常见错法：Lian Xiangru（把廉颇的姓「廉」Lián 拼上来）、Li Xiangru'),
    ('廉颇', '人名', 'Lian Po', r'Lian Po', '不作 Lian Po-po / Lianpo'),
    ('缪贤', '人名', 'Miao Xian', r'Miao Xian',
     '缪作姓氏读 Miào。「宦者令缪贤」＝宦者令（官）＋缪贤（人名），不可连读成 Ling Miuxian'),
    ('赵奢', '人名', 'Zhao She', r'Zhao She', ''),
    ('秦王', '人名', 'the King of Qin', r'the King of Qin|The King of Qin',
     '统一带定冠词。原译并存 King Qin / King of Qin / king of Qin 四种形式'),
    ('赵王', '人名', 'the King of Zhao', r'the King of Zhao|The King of Zhao',
     '统一带定冠词。原译并存 King Zhao / King of Zhao / the King of Zhao'),
    ('秦昭王', '人名', 'King Zhao of Qin', r'King Zhaoxiang of Qin', '即秦昭襄王。原译 King Zhao of Qin 会被读成「秦国的赵王」'),
    ('缪公', '人名', 'Duke Mu of Qin', r'Duke Mu', '秦穆公，作 Duke Mu（不写 Duke Mou）'),
    ('蒙恬', '人名', 'Meng Tian', r'Meng Tian', ''),
    ('孟尝君', '人名', 'Lord Mengchang', r'Lord Mengchang',
     '战国四公子皆称「君」（封君），非「王」；原译 King Meng Chang 双重错误：爵称错＋名字拆开'),
    ('平原君', '人名', 'Lord Pingyuan', r'Lord Pingyuan', '同上，原译 King Pingyuan'),
    ('春申君', '人名', 'Lord Chunshen', r'Lord Chunshen', '同上，原译 King Chun Shen（名亦拆错）'),
    ('信陵君', '人名', 'Lord Xinling', r'Lord Xinling', '同上，原译 King Xinling'),
    ('陈涉', '人名', 'Chen She', r'Chen She', ''),
    ('始皇', '人名', 'the First Emperor', r'First Emperor|Qin Shi Huang', 'Qin Shi Huang 亦为通行译法'),
    ('秦孝公', '人名', 'Duke Xiao of Qin', r'Duke Xiao', ''),
    ('惠文王', '人名', 'King Huiwen of Qin / of Zhao', r'King Huiwen', '原文省称「惠文」，须补「王」与国名'),
    ('武王', '人名', 'King Wu of Qin', r'King Wu of Qin|King Wu', '原文省称「武」'),
    ('昭襄王', '人名', 'King Zhaoxiang of Qin', r'King Zhaoxiang', '原文省称「昭襄」'),
    ('孝文王', '人名', 'King Xiaowen of Qin', r'King Xiaowen', '原译仅 Xiaowen，丢了「王」'),
    ('庄襄王', '人名', 'King Zhuangxiang of Qin', r'King Zhuangxiang', '原译仅 Zhuangxiang'),
    ('商君', '人名', 'Lord Shang', r'Lord Shang', '商鞅封于商，号商君'),
    ('郭攸之', '人名', 'Guo Youzhi', r'Guo Youzhi', ''),
    ('费祎', '人名', 'Fei Yi', r'Fei Yi',
     '原文省称「祎」，须还原全名。原译仅作 Fei，只留姓不留名'),
    ('董允', '人名', 'Dong Yun', r'Dong Yun', '原文省称「允」'),
    ('向宠', '人名', 'Xiang Chong', r'Xiang Chong', ''),

    # ───────── 官职 ─────────
    ('侍中', '官职', 'Palace Attendant', r'Palace Attendant', '皇帝近侍加官'),
    ('尚书', '官职', 'Imperial Secretary', r'Imperial Secretar',
     '掌文书章奏。原译 government officials 泛化失指'),
    ('长史', '官职', 'Chief Secretary', r'Chief Secretar',
     '丞相／将军府属官之长，掌文书总务。原译 historiographers（史官）系按字面猜译，属误译'),
    ('参军', '官职', 'Staff Officer', r'Staff Officer', '军府属官'),
    ('有司', '官职', 'the officials in charge', r'the officials in charge',
     '「有司」＝主管该事的官吏，是泛称。原译并存 the proper officials / the officials in charge / '
     'the petty officials 三种，须统一'),
    ('上卿', '官职', 'High Minister', r'High Minister',
     '卿的最高等级（爵位），不是丞相。原译 Chief Minister / Prime Minister 混淆了「上卿」与「丞相」'),
    ('上大夫', '官职', 'Grand Master of the Highest Rank', r'Grand Master',
     '大夫分上、中、下三等。原译 Grand Minister 把爵称译成官职'),
    ('大夫', '官职', 'Grand Master', r'Grand Master', ''),
    ('舍人', '官职', 'retainer', r'retainer', '贵族门下的食客／家臣。原译 a guest 不确'),
    ('宦者令', '官职', 'Chief Eunuch', r'Chief Eunuch',
     '宦官之长。原译 the Zhao eunuch and governor 误加 governor'),
    ('将军', '官职', 'General', r'General', ''),
    ('郎中', '官职', 'Gentleman of the Palace', r'Gentleman of the Palace', ''),
    ('洗马', '官职', 'Expositor-in-Waiting', r'Expositor-in-Waiting', '太子属官，读 xiǎn mǎ'),
    ('东宫', '官职', 'the Heir Apparent', r'Heir Apparent', '以居所代指太子'),
    ('太守', '官职', 'Governor', r'Governor', ''),
    ('刺史', '官职', 'Inspector', r'Inspector', ''),
    ('孝廉', '官职', 'Filial and Incorrupt', r'Filial and Incorrupt', '汉代察举科目'),
    ('秀才', '官职', 'Flourishing Talent', r'Flourishing Talent', '汉代察举科目，非「秀才」今义'),

    # ───────── 地名 ─────────
    ('崤函', '地名', 'Mount Xiao and the Hangu Pass', r'Mount Xiao and the Hangu Pass',
     '崤山＋函谷关的并称。原译 Xiao and Han / Xiao-Han 把「函」拼成 Han，与韩国、汉朝混同'),
    ('雍州', '地名', 'Yongzhou', r'Yongzhou', '古九州之一'),
    ('汉中', '地名', 'Hanzhong', r'Hanzhong', ''),
    ('巴蜀', '地名', 'Ba and Shu', r'Ba and Shu', ''),
    ('咸阳', '地名', 'Xianyang', r'Xianyang', '秦都'),
    ('关中', '地名', 'Guanzhong', r'Guanzhong', '函谷关以西'),
    ('西河', '地名', 'the land west of the Yellow River', r'west of the Yellow River',
     '魏国黄河以西之地，非「West River」。原译 the West River 系字面直译'),
    ('桂林象郡', '地名', 'Guilin and Xiang commanderies', r'Guilin', '秦所置二郡'),
    ('百越', '地名', 'the Hundred Yue', r'Hundred Yue|Baiyue', '南方诸部族总称'),
    ('山东', '地名', 'east of the mountains', r'east of the mountains',
     '崤山以东，非今山东省'),
    ('中山', '地名', 'Zhongshan', r'Zhongshan', '中山国'),
    ('渑池', '地名', 'Mianchi', r'Mianchi', ''),
    ('邯郸', '地名', 'Handan', r'Handan', '赵都'),
    ('周室', '地名', 'the Zhou royal house', r'Zhou (?:royal house|court)', ''),
    ('二周', '地名', 'the two Zhous', r'(?i)two Zhous', '东周、西周'),
    ('六合', '地名', 'the Six Directions', r'Six Directions', '天地四方，代指天下'),
    ('八荒', '地名', 'the eight wilds', r'eight wilds', '八方荒远之地'),

    # ───────── 刑名 / 礼俗 ─────────
    ('汤镬', '刑名礼俗', 'the boiling cauldron', r'boiling cauldron',
     '汤＝滚水，镬＝无足大鼎，为烹人之刑。原译 boiled in oil 把「汤」误作「油」'),
    ('斧质', '刑名礼俗', "the executioner's block", r"executioner's block",
     '斧＝刑刀，质（锧）＝伏卧受刑的砧板，合为刑具。原译 the axe blade 只取刀刃，且 kowtow 误译「伏」'),
    ('肉袒', '刑名礼俗', "bare one's shoulders and back", r'bar(?:e|ed) (?:his|your|their)? ?shoulders',
     '脱去上衣露出肩背，表示认罪受罚。原译 took off his coat 只译「脱衣」，丢「袒」'),
    ('负荆', '刑名礼俗', "carry bramble thorns on one's back", r'bramble thorns',
     '背负荆条请对方鞭打。荆＝荆条／荆棘，非 wicker（柳条）'),
    ('刎颈之交', '刑名礼俗', 'friends sworn to die for each other', r'sworn to die for each other',
     '固定成语，指生死之交。原译 neck-cutting friends 是逐字直译，英文不可解'),
    ('九宾', '刑名礼俗', 'the Nine Guests ceremony', r'Nine Guests',
     '天子朝会大礼，九位礼宾依次传呼迎客'),
    ('斋戒', '刑名礼俗', 'fast and purify oneself', r'fast', '祭祀或大礼前洁身禁欲'),
    ('布衣', '刑名礼俗', 'commoner', r'commoner|plain cloth|ordinary people', '平民，以麻布衣着的代称；布衣之交＝平民之间的交往'),
    ('寡人', '刑名礼俗', 'I, the unworthy one', r'unworthy one|\bI\b|\bmy\b|\bWe\b',
     '诸侯自称的谦辞。英文无对应谦称，通行作 I / my（或 royal We）；谦称色彩不可复现，属可接受损失'),
]

entries = []

# 原文省称：这些专名在三篇中以简称出现，按实际字样扫描
ABBREV = {
    '孟尝君': '孟尝', '平原君': '平原', '春申君': '春申', '信陵君': '信陵',
    '昭襄王': '昭襄', '郭攸之': '攸之', '费祎': '、祎', '董允': '、允',
    '秦昭王': '昭王',
}
# 本三篇未出现（属陈情表等其他篇目），保留词条供后续复用
OUT_OF_SCOPE = {'郎中', '洗马', '东宫', '太守', '刺史', '孝廉', '秀才',
                '向宠', '邯郸', '赵奢', '武王'}

for i, (term, cat, canon, accept, note) in enumerate(E, 1):
    key = ABBREV.get(term, term)
    occ = [j for j in scope_idx if key in cards[j]['classical']]
    if term == '巴蜀':
        occ = [j for j in scope_idx if '巴' in cards[j]['classical'] and '蜀' in cards[j]['classical']]
    if term == '桂林象郡':
        occ = [j for j in scope_idx if '桂林' in cards[j]['classical']]
    in_scope = term not in OUT_OF_SCOPE
    entries.append({
        'id': f'PN{i:03d}',
        'term': term,
        'category': cat,
        'canonical': canon,
        'accept_pattern': accept,
        'note': note + ('' if in_scope else '（本三篇未出现，供其他篇目回改时复用）'),
        'occurrences': occ,
        'occur_count': len(occ),
        'in_scope': in_scope,
    })

glossary = {
    'version': '1.0',
    'scope': TITLES,
    'scope_sentences': len(scope_idx),
    'created': '2026-10-26',
    'conventions': [
        '人名：姓在前名在后，用汉语拼音连写（Lin Xiangru）；首次出现用全名，其后可只用名（Xiangru）。',
        '封君：战国封君一律作 Lord + 封号（Lord Mengchang），不作 King。',
        '国君：统一作 the King of + 国名，带定冠词；句首大写 The。',
        '官职：取职能对应的英文官称（Chief Secretary），不逐字直译；无法对应者用音译 + 括注。',
        '地名：山、关、水作 Mount / Pass / River 前置结构（Mount Xiao, the Hangu Pass）；郡县作音译 + 通名（Xiang commandery）。',
        '刑名礼俗：先译出制度实质（the boiling cauldron），必要时补括注，不作字面拆分。',
    ],
    'entries': entries,
}

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(glossary, f, ensure_ascii=False, indent=1)

print(f'写入 {OUT}：{len(entries)} 条')
by_cat = {}
for e in entries:
    by_cat.setdefault(e['category'], []).append(e['term'])
for k, v in by_cat.items():
    print(f'  {k}: {len(v)} 条')
print(f'\n覆盖句数: {len(scope_idx)}（{", ".join(TITLES)}）')
print('零出现条目（需人工确认是否漏扫）:',
      [e['term'] for e in entries if e['occur_count'] == 0] or '无')

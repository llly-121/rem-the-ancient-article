#!/usr/bin/env python3
"""step16b: 陈情表 / 送东阳马生序 段级英译 → 句级切分。

流程：
1. 按 title 圈定行，按共享段落文本分组；
2. 段落按 [.!?] + 大写字母边界切成英文句；
3. 用词项 term_english 的偏移做单调对齐，每行取 [首锚点句, 末锚点句] 跨度（支持一中对两英）；
4. 连续多行共用同一跨度时，按 '; ' 细分（子句数须与行数一致）；
5. MANUAL 覆盖表处理自动切不开的组（人工核对过原文）；
6. 写回 course_cards_v2.jsonl 并打上 english_source 标记。

标准重放链路：cp bak → step14b → step16 → step16b → step10 → step12 → step17
用法：python step16b_split_paragraph.py [--write]   # 默认 dry-run
"""
import json
import re
import sys

TITLES = ['陈情表', '送东阳马生序']
SOURCE_TAG = 'AI译(WorkBuddy)+句级切分'

# 人工覆盖（row -> english）。每条必须是原段落英译的连续子串（保证 term_english 子串校验不破）。
MANUAL = {
    # 前太守逵/后刺史荣/辞不赴命：一句拆三段
    591: 'First Governor Kui recommended me as Filial and Incorrupt',
    592: 'later Inspector Rong nominated me as Flourishing Talent',
    593: 'because no one was left to care for my grandmother, I declined both',
    # 诏书切峻/郡县逼迫/州司临门
    598: 'Yet the edict grew urgent and stern, reproaching me for evasion and insolence',
    599: 'the commandery and county pressed me onto the road',
    600: 'the prefecture officials called at my door, swifter than a falling star',
    # 伏惟圣朝/况臣孤苦/且臣少仕伪朝（原文 ! 处断句）
    604: 'I humbly reflect that the sagely dynasty rules the realm by filial piety: even aged former officials receive compassion and care',
    605: 'how much more I, whose orphaned bitterness is exceptional!',
    606: 'Moreover, in my youth I served the fallen dynasty, holding office in its secretariat, aiming only at advancement and caring nothing for name or integrity.',
    # 今臣亡国贱俘/岂敢盘桓/但以刘日薄西山
    607: 'Now, a lowly captive of a conquered state, most insignificant and base, I have been promoted beyond measure with lavish favour',
    608: 'how would I dare linger and harbour other hopes!',
    609: 'Only because Granny Liu is like the sun nearing the western hills, her breath faint, her life precarious: the morning cannot reckon on the evening.',
    # 愿陛下矜悯愚诚/庶刘侥幸
    618: 'I beg Your Majesty to pity my foolish sincerity and grant my humble wish',
    619: 'so that Granny Liu may by good fortune be spared to live out her years',
    # 余则缊袍敝衣/以中有足乐者
    638: 'I, in worn padded gown and ragged clothes, dwelt among them without the least envy',
    639: 'for what sufficed to make me happy was within: I did not feel my food and clothing inferior.',
}

cards = [json.loads(l) for l in open('data/course_cards_v2.jsonl', encoding='utf-8')]
pairs = [json.loads(l) for l in open('data/term_sentence_pairs.jsonl', encoding='utf-8')]

anchors_by_row = {}
for p in pairs:
    n = int(p['sent_id'][1:]) - 1
    if p['term_english'] and p['term_english'] in p['full_english']:
        anchors_by_row.setdefault(n, []).append(p['term_english'])


def split_esents(para):
    """按 [.!?]+空格+大写（或段尾）切句，返回 [(text, start, end)]。"""
    out, start = [], 0
    for m in re.finditer(r'[.!?](?= [A-Z"\']|$)', para):
        end = m.end()
        t = para[start:end].strip()
        if t:
            out.append((t, start, end))
        start = end
    tail = para[start:].strip()
    if tail:
        out.append((tail, start, len(para)))
    return out


def split_clauses(esent):
    return [c.strip(' ;') for c in esent.split('; ') if c.strip(' ;')]


report, bad = [], []
new_english = {}

for title in TITLES:
    rows = [i for i, c in enumerate(cards) if c['title'] == title]
    groups, cur = [], [rows[0]]
    for i in rows[1:]:
        if cards[i]['english'] == cards[cur[-1]]['english']:
            cur.append(i)
        else:
            groups.append(cur)
            cur = [i]
    groups.append(cur)

    for g in groups:
        para = cards[g[0]]['english']
        es = split_esents(para)

        def esent_at(pos):
            for k, (t, a, b) in enumerate(es):
                if a <= pos < b:
                    return k
            return len(es) - 1

        # 单调对齐：最长锚点为主定位；≥15 字符的锚点允许把跨度扩展到相邻句；
        # 无锚行继承前一行的跨度（同句多行靠分号细分）
        span, cursor, pending = {}, 0, []
        prev_span = None
        for i in g:
            tes = anchors_by_row.get(i, [])
            cands = {}
            for te in tes:
                start = 0
                occ = []
                while True:
                    pos = para.find(te, start)
                    if pos < 0:
                        break
                    if pos >= cursor:
                        occ.append(pos)
                    start = pos + 1
                if occ:
                    cands[te] = min(occ)
            if not cands:
                pending.append(i)
                continue
            primary = max(cands, key=len)          # 最长锚点最具体
            pos_p = cands[primary]
            e_p = esent_at(pos_p)
            lo = hi = e_p
            for te, pos in cands.items():
                if te != primary and len(te) >= 15:  # 短锚点歧义大，不参与扩跨
                    e = esent_at(pos)
                    if abs(e - e_p) <= 2:
                        lo, hi = min(lo, e), max(hi, e)
            span[i] = (lo, hi)
            prev_span = span[i]
            cursor = pos_p + len(primary)
            while pending:                            # 先前无锚的行继承前行
                span[pending.pop(0)] = prev_span
        first_span = span[g[0]] if span else (0, len(es) - 1)
        for i in pending:                             # 段首一直无锚 → 用首个有锚行
            span[i] = first_span

        # 相邻行合并同跨度组 → 分号细分
        k = 0
        while k < len(g):
            j = k
            while j + 1 < len(g) and span[g[j + 1]] == span[g[k]]:
                j += 1
            grp = g[k:j + 1]
            e0, e1 = span[grp[0]]
            text = ' '.join(t for t, _, _ in es[e0:e1 + 1]).strip()
            if len(grp) == 1:
                new_english[grp[0]] = text
            else:
                cls = split_clauses(text)
                if len(cls) == len(grp):
                    for r, cl in zip(grp, cls):
                        new_english[r] = cl
                    report.append(f'{title} {grp[0]}-{grp[-1]}: 分号细分 {len(grp)} 段')
                elif all(r in MANUAL for r in grp):
                    for r in grp:
                        new_english[r] = MANUAL[r]
                    report.append(f'{title} {grp[0]}-{grp[-1]}: 人工覆盖 {len(grp)} 段')
                else:
                    for r in grp:
                        new_english[r] = text
                    report.append(f'⚠ {title} {grp[0]}-{grp[-1]}: 未细分（{len(grp)} 行共用）')
            k = j + 1

# 人工覆盖（含单行场景），覆盖时校验必须仍是原段落子串
def title_of(r):
    return cards[r]['title']


para_by_row = {i: cards[i]['english'] for i in new_english}
for r, e in MANUAL.items():
    if r in new_english and new_english[r] != e:
        assert e in para_by_row[r], f'MANUAL #{r} 不是原段落子串: {e[:50]}'
        new_english[r] = e
        report.append(f'{title_of(r)} {r}: 人工覆盖生效')

# 子串校验（锚点应落在本行或相邻行的切分结果里）
for p in pairs:
    n = int(p['sent_id'][1:]) - 1
    if n in new_english and p['term_english'] not in new_english.get(n, ''):
        if not any(p['term_english'] in new_english.get(n + d, '') for d in (-2, -1, 1, 2)):
            bad.append((n, p['term'], p['term_english']))

print(f'覆盖行数：{len(new_english)}')
for line in report:
    print(' ', line)
print(f'锚点失配：{len(bad)}')
for n, t, te in bad:
    print(f'  #{n} {t} | {te!r}')

if '--write' in sys.argv:
    for i, e in new_english.items():
        assert e, i
        cards[i]['english'] = e
        if 'english_source' in cards[i]:
            cards[i]['english_source'] = SOURCE_TAG
    with open('data/course_cards_v2.jsonl', 'w', encoding='utf-8') as f:
        for c in cards:
            f.write(json.dumps(c, ensure_ascii=False) + '\n')
    print(f'已写回 {len(new_english)} 行')
else:
    print('(dry-run，未写回；加 --write 生效)')

# -*- coding: utf-8 -*-
"""合并 en_batch_*.json 译文回 course_cards_v2.jsonl"""
import json, glob, sys

rows = [json.loads(l) for l in open('data/course_cards_v2.jsonl', encoding='utf-8')]
trans = {}
for fp in sorted(glob.glob('data/en_batch_*.json')):
    for line in open(fp, encoding='utf-8'):
        line = line.strip()
        if line:
            d = json.loads(line)
            trans[d['i']] = d['english']

print('批内译文条数:', len(trans))
applied = skipped = 0
for i, r in enumerate(rows):
    if i in trans:
        if (r.get('english') or '').strip():
            skipped += 1  # 已有英文，不覆盖
            continue
        r['english'] = trans[i]
        r['english_source'] = 'AI译(WorkBuddy)'
        r['english_ambiguous'] = False
        applied += 1

print('应用:', applied, ' 跳过(已有):', skipped)
miss = [i for i, r in enumerate(rows) if not (r.get('english') or '').strip()]
print('剩余缺英文:', len(miss), miss[:10])

with open('data/course_cards_v2.jsonl', 'w', encoding='utf-8', newline='\n') as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
print('写回完成')

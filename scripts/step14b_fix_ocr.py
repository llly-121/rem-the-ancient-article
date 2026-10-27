#!/usr/bin/env python3
"""step14b: OCR 讹字修正（可重复执行，幂等）。

背景：course_cards_v2.bak_2026-10-26.jsonl 及 terms_candidates.jsonl 历史版本中
爱莲说名句误作「出淤泥而不然」，应为「染」。此修正必须纳入标准重放链路：
    cp bak → step14b → step16 → step10 → step12 → step17
否则从备份重跑时讹字会复活，导致爱莲说 8 个词项锚点失配。
"""
import json

FIXES = [
    ('出淤泥而不然', '出淤泥而不染'),
]

# scope 外的直接英译修复：{行号: (新英译, 理由)}，幂等（已是新值则跳过）
DIRECT_FIXES = {
    536: ('The guest said: "Lord Xu is not as handsome as you."',
          '「徐公不若君之美」主客颠倒（translation_issues T 项收口）；邹忌篇不在 step16 scope，在此直改'),
}

def patch(path, field):
    rows = [json.loads(l) for l in open(path, encoding='utf-8')]
    n = 0
    for r in rows:
        for old, new in FIXES:
            if old in (r.get(field) or ''):
                r[field] = r[field].replace(old, new)
                n += 1
            # terms_candidates 的 terms 数组内也有句子字段
        if 'terms' in r:
            for t in r['terms']:
                for old, new in FIXES:
                    if old in (t.get('meaning_in_this_sentence') or ''):
                        pass  # 释义不含原句，略
    with open(path, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    return n

if __name__ == '__main__':
    n1 = patch('data/course_cards_v2.jsonl', 'classical')
    n2 = patch('data/course_cards_v2.jsonl', 'modern')
    n3 = patch('data/terms_candidates.jsonl', 'classical_sentence')

    # scope 外英译直改
    rows = [json.loads(l) for l in open('data/course_cards_v2.jsonl', encoding='utf-8')]
    n4 = 0
    for i, (new, reason) in DIRECT_FIXES.items():
        if rows[i]['english'] != new:
            rows[i]['english'] = new
            n4 += 1
    with open('data/course_cards_v2.jsonl', 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    print(f'OCR 修正：course_cards classical {n1} 处 / modern {n2} 处 / terms_candidates {n3} 处')
    print(f'scope 外英译直改：{n4} 处')

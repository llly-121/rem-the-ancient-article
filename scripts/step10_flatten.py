# -*- coding: utf-8 -*-
"""step10：把 terms_candidates 展平到词项级，关联句子英文，导出待标注工作清单"""
import json

cards = [json.loads(l) for l in open('data/course_cards_v2.jsonl', encoding='utf-8')]
terms = [json.loads(l) for l in open('data/terms_candidates.jsonl', encoding='utf-8')]

# 句子 key：classical 文本 -> english（terms 行按顺序对应 cards 行）
eng_by_sent = {c['classical']: (c.get('english') or '') for c in cards}
sent_idx = {c['classical']: i for i, c in enumerate(cards)}

flat = []
for ti, t in enumerate(terms):
    sent = t['classical_sentence']
    en = eng_by_sent.get(sent, '')
    for term in t['terms']:
        flat.append({
            'idx': len(flat),
            'sent_id': t['id'],
            'title': t['title'],
            'term': term['term'],
            'term_type': term['term_type'],
            'meaning': term['meaning_in_this_sentence'],
            'classical': sent,
            'english': en,
        })

print('词项总数:', len(flat))
with open('data/flat_terms.json', 'w', encoding='utf-8') as f:
    json.dump(flat, f, ensure_ascii=False, indent=0)

# 前200条
for r in flat[:200]:
    print(f"[{r['idx']}] {r['term']} | {r['meaning'][:40]}")
    print(f"    ZH: {r['classical'][:60]}")
    print(f"    EN: {r['english']}")

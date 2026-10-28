#!/usr/bin/env python3
"""step25: 合并词级题库（5/4 档 + 3/2/1 档）。

输入  data/word_quiz_high.jsonl  296 题（step20 产出，5/4 档）
      data/word_quiz_low.jsonl   992 题（step24 产出，3/2/1 档）
输出  data/word_quiz.jsonl      1288 题

high 单独存一份基线是为了幂等：如果直接从 word_quiz.jsonl 累加 low，
重跑一次就会把 992 条再叠一遍。基线固定，产物可反复重建。

用法：python step25_merge_word_quiz.py
"""
import collections
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(BASE, 'data')


def load(name):
    return [json.loads(l) for l in open(os.path.join(D, name), encoding='utf-8')]


def main():
    high = load('word_quiz_high.jsonl')
    low = load('word_quiz_low.jsonl')

    seen = {}
    for r in high + low:
        if r['id'] in seen:
            raise SystemExit(f'重复 id：{r["id"]}')
        seen[r['id']] = r

    merged = []
    for r in high + low:
        merged.append({
            'id': r['id'],
            'term': r.get('term', ''),
            'char_count': r.get('char_count'),
            'exam_frequency': r.get('exam_frequency'),
            'correct': r['correct'],
            'distractors': r['distractors'],
            'needs_manual': bool(r.get('needs_manual')),
            'note': r.get('note', ''),
        })

    out = os.path.join(D, 'word_quiz.jsonl')
    with open(out, 'w', encoding='utf-8') as f:
        for r in merged:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    ok = sum(1 for r in merged if not r['needs_manual'])
    short = [r['id'] for r in merged if len(r['distractors']) != 3]
    print(f'合并 {len(merged)} 题 = 5/4 档 {len(high)} + 3/2/1 档 {len(low)}')
    print(f'可出题 {ok}，待人工 {len(merged) - ok}')
    print(f'干扰项 {sum(len(r["distractors"]) for r in merged)} 条')
    print('条数不足 3 的题:', short or '无')
    print('档位分布:', dict(sorted(collections.Counter(
        str(r['exam_frequency']) for r in merged).items())))
    print(f'写出 {out}')


if __name__ == '__main__':
    main()

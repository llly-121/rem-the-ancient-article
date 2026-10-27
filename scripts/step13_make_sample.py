# -*- coding: utf-8 -*-
"""step13: 从全量对齐结果中分层抽取 200 条，生成验收样本。

抽样策略：
  - 按篇分层，每篇按比例分配名额，篇内均匀取样（覆盖全文，不偏向开头）
  - 强制纳入全部 needs_revision=True 的条目（19 条），其余为正常条目
  - 保证每篇至少 2 条
"""
import json
import collections

SRC = 'data/term_sentence_pairs.jsonl'
DST = 'data/term_pairs_sample.jsonl'
TOTAL = 200

rows = [json.loads(l) for l in open(SRC, encoding='utf-8')]
by_title = collections.OrderedDict()
for r in rows:
    by_title.setdefault(r['title'], []).append(r)

flagged = [r for r in rows if r['needs_revision']]
quota = TOTAL - len(flagged)

# 按篇内条目数比例分配名额
total_n = len(rows)
alloc = {}
for t, items in by_title.items():
    alloc[t] = max(2, round(quota * len(items) / total_n))
# 归一化到 quota
while sum(alloc.values()) > quota:
    t = max(alloc, key=lambda k: alloc[k] - 2 * len(by_title[k]) / total_n)
    if alloc[t] <= 2:
        break
    alloc[t] -= 1
while sum(alloc.values()) < quota:
    t = max(by_title, key=lambda k: len(by_title[k]) - alloc[k])
    alloc[t] += 1

pick = list(flagged)
for t, items in by_title.items():
    k = min(alloc[t], len(items))
    if k <= 0:
        continue
    step = len(items) / k
    idxs = sorted({int(i * step) for i in range(k)})
    idxs = idxs[:k]
    while len(idxs) < k:
        for j in range(len(items)):
            if j not in idxs:
                idxs.append(j)
                break
        idxs = sorted(idxs)
    pick.extend(items[j] for j in idxs)

# 去重 + 按 idx 排序
seen = set()
final = []
for r in sorted(pick, key=lambda x: x['idx']):
    if r['idx'] in seen:
        continue
    seen.add(r['idx'])
    final.append(r)

with open(DST, 'w', encoding='utf-8') as f:
    for r in final:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

# ── 统计 ──
print(f'样本条数: {len(final)} / 全量 {len(rows)}')
print(f'覆盖篇目: {len({r["title"] for r in final})} / {len(by_title)}')
sub = sum(1 for r in final if r['match_type'] == 'substring')
print(f'子串命中: {sub}/{len(final)} = {sub/len(final)*100:.1f}%')
nr = sum(1 for r in final if r['needs_revision'])
print(f'needs_revision: {nr}/{len(final)} = {nr/len(final)*100:.1f}%')
print('\n按篇分布:')
c = collections.Counter(r['title'] for r in final)
for t, n in c.most_common():
    print(f'  {t}: {n}')

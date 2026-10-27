"""Full-corpus check on the parquet: info field granularity + per-document counts.

Reads only the `info` column (cheap) from the local parquet. Used to judge whether
"filter by 篇目" is viable at scale, and to correct the sample-only impression.
"""
import re
import sys
import collections

import pyarrow.parquet as pq

PQ = "D:/guwen-cache/parquet/train.parquet"


def main():
    t = pq.read_table(PQ, columns=["info"])
    info = t.column("info").to_pylist()
    n = len(info)
    print(f"rows = {n:,}")

    pat = re.compile(r"^《([^·》]+)(?:·([^》]*))?》$")
    books = collections.Counter()
    editions = collections.Counter()
    unmatched = 0
    detail = collections.Counter()
    vol_pat = re.compile(r"^(.*?)(?:卷[一二三四五六七八九十百千零〇\d]+.*|第[一二三四五六七八九十百\d]+[章回篇].*)$")

    for s in info:
        m = pat.match(s or "")
        if not m:
            unmatched += 1
            continue
        book, rest = m.group(1), m.group(2) or ""
        books[book] += 1
        first = rest.split("·")[0]
        core = vol_pat.sub(r"\1", first) if first else ""
        editions[(book, core)] += 1
        detail[s] += 1

    print(f"unmatched format : {unmatched} ({unmatched/n:.4%})")
    print(f"books (顶层书目)  : {len(books)}")
    print(f"editions (书+体例): {len(editions)}")
    print(f"distinct info    : {len(detail)}")

    print("\n=== 顶层书目 top 25（全量） ===")
    for k, v in books.most_common(25):
        print(f"  {k:14s} {v:>7,}")

    print("\n=== 书目规模分布（每书行数） ===")
    sizes = sorted(books.values())
    import statistics
    print(f"  min={sizes[0]}  median={statistics.median(sizes):.0f}  mean={statistics.mean(sizes):.0f}  max={sizes[-1]:,}")
    buckets = {"<100": 0, "100-999": 0, "1k-9k": 0, "10k-99k": 0, ">=100k": 0}
    for v in sizes:
        if v < 100: buckets["<100"] += 1
        elif v < 1000: buckets["100-999"] += 1
        elif v < 10000: buckets["1k-9k"] += 1
        elif v < 100000: buckets["10k-99k"] += 1
        else: buckets[">=100k"] += 1
    for k, v in buckets.items():
        print(f"  {k:9s} : {v:3d} 种书")

    print("\n=== 最大 10 种书的篇目粒度分布 ===")
    for book, _ in books.most_common(10):
        subs = {e[1]: c for e, c in editions.items() if e[0] == book}
        top = sorted(subs.items(), key=lambda x: -x[1])[:5]
        s = ", ".join(f"{k or '(无体例)'}={v:,}" for k, v in top)
        print(f"  {book:12s} 体例数={len(subs):4d} | {s}")

    # exact -info rows
    multi = sum(1 for v in detail.values() if v > 2)
    print(f"\ninfo 精确值出现 >2 次 的篇目数: {multi}")
    print("最大 info 精确值:")
    for k, v in detail.most_common(5):
        print(f"  {v:>6,}  {k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

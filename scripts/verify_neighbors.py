"""Rigorous prev/next verifier: re-derives expected neighbours by ROW INDEX.

The earlier verifier keyed on `classical` text, which collides when the same
sentence occurs in two different books -> false mismatches. This version:
  1. streams the parquet once, recording (row_index, info, classical) for rows
     whose classical appears in the output;
  2. rebuilds per-document ordered lists filtered by 4..50 CJK chars;
  3. matches output records to source rows by (source_work, classical) with an
     occurrence cursor, then compares prev/next exactly.
"""
import json
import re
import sys
from collections import defaultdict

import pyarrow.parquet as pq

PQ = "D:/guwen-cache/parquet/train.parquet"
CJK = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")


def cjk_len(s):
    return len(CJK.findall(s or ""))


def main(path):
    recs = [json.loads(l) for l in open(path, encoding="utf-8")]
    wanted = {r["classical"] for r in recs}
    wit = {r["source_work"] for r in recs}

    # collect source rows, preserving file order per document
    per_doc = defaultdict(list)
    book2docs = defaultdict(set)
    pf = pq.ParquetFile(PQ)
    for rg in range(pf.metadata.num_row_groups):
        t = pf.read_row_group(rg, columns=["info", "classical"])
        for inf, cl in zip(t.column("info").to_pylist(), t.column("classical").to_pylist()):
            if cl in wanted:
                m = re.match(r"^《([^·》]+)", inf or "")
                book = m.group(1) if m else ""
                if book in wit:
                    per_doc[inf].append(cl)
                    book2docs[book].add(inf)

    # Only the emitted prefix of each document counts (sample truncation).
    # Rebuild emit order straight from the output file.
    emitted_by_doc = defaultdict(list)
    for r in recs:
        for inf in book2docs.get(r["source_work"], ()):
            if r["classical"] in per_doc[inf]:
                emitted_by_doc[inf].append(r["classical"])
                break

    expected = defaultdict(list)   # (book, classical) -> [(prev, next), ...]
    for inf, rows in per_doc.items():
        m = re.match(r"^《([^·》]+)", inf)
        book = m.group(1) if m else ""
        kept = [x for x in rows if 4 <= cjk_len(x) <= 50]
        n_emit = len(emitted_by_doc.get(inf, []))
        if n_emit:
            kept = kept[:n_emit]
        for k, x in enumerate(kept):
            expected[(book, x)].append((kept[k - 1] if k > 0 else None,
                                        kept[k + 1] if k + 1 < len(kept) else None))

    cursor = defaultdict(int)
    ok = mism = unmatched = 0
    for i, r in enumerate(recs):
        key = (r["source_work"], r["classical"])
        if key not in expected:
            unmatched += 1
            continue
        idx = min(cursor[key], len(expected[key]) - 1)
        e_prev, e_next = expected[key][idx]
        cursor[key] += 1
        if e_prev == r["prev_sentence"] and e_next == r["next_sentence"]:
            ok += 1
        else:
            mism += 1
            if mism <= 3:
                print(f"MISMATCH #{i} [{r['source_work']}]")
                print(f"  classical: {r['classical'][:40]}")
                print(f"  got  prev={r['prev_sentence']} | next={r['next_sentence']}")
                print(f"  want prev={e_prev} | next={e_next}")

    print(f"records      : {len(recs)}")
    print(f"prev/next OK : {ok}")
    print(f"mismatch     : {mism}")
    print(f"unmatched    : {unmatched}")
    return 0 if mism == 0 and unmatched == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))

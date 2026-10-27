"""Step 3/4: build sentence-level card pool from matched document_info.

Memory-safe version: streams the parquet row-group by row-group, never materialising
the full 972k-row table as Python lists.

Fields (strict order):
  classical, english, modern, source_work, prev_sentence, next_sentence, char_length

Rules:
  * prev/next taken by ORIGINAL ROW ORDER within the same document_info
    (nearest neighbouring row that also survives the 4-50 char filter;
     null when no such row exists -- never fabricated)
  * char_length counts CJK characters only, must be 4..50
  * source_work = the book name inside 《》 (never empty)

Two passes:
  pass 1 -> count qualifying rows per document_info (group sizes + in-doc position)
  pass 2 -> emit records with correct prev/next

Usage:
  python step3_build_cards.py                # sample -> data/sentences_sample.jsonl (200)
  python step3_build_cards.py --full         # full   -> data/sentences.jsonl
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict

import pyarrow.parquet as pq

PQ = "D:/guwen-cache/parquet/train.parquet"
BASE = "E:/Users/asus/workbuddy/guwen-project/data"
MATCHED_TSV = os.path.join(BASE, "matched_sources.tsv")

MIN_LEN, MAX_LEN = 4, 50
CJK = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")


def cjk_len(s):
    return len(CJK.findall(s or ""))


def book_of(info):
    m = re.match(r"^《([^·》]+)", info or "")
    return m.group(1) if m else ""


def load_matched():
    keep = set()
    with open(MATCHED_TSV, encoding="utf-8") as f:
        next(f)
        for line in f:
            p = line.rstrip("\n").split("\t")
            if p and p[0]:
                keep.add(p[0])
    return keep


def iter_batches(columns, batch_size=20000):
    pf = pq.ParquetFile(PQ)
    for rg in range(pf.metadata.num_row_groups):
        tbl = pf.read_row_group(rg, columns=columns)
        cols = {c: tbl.column(c).to_pylist() for c in columns}
        n = tbl.num_rows
        for s in range(0, n, batch_size):
            e = min(s + batch_size, n)
            yield {c: cols[c][s:e] for c in columns}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--limit", type=int, default=200)
    a = ap.parse_args()

    matched = load_matched()
    print(f"matched document_info: {len(matched):,}", flush=True)

    # ---- pass 1: how many qualifying rows each doc has, and which docs to emit ----
    sizes = defaultdict(int)
    order = []
    seen = set()
    total_rows = 0
    skipped = 0
    for b in iter_batches(["info", "classical"]):
        for inf, cl in zip(b["info"], b["classical"]):
            if inf not in matched:
                continue
            total_rows += 1
            if not (MIN_LEN <= cjk_len(cl) <= MAX_LEN):
                skipped += 1
                continue
            sizes[inf] += 1
            if inf not in seen:
                seen.add(inf)
                order.append(inf)
    print(f"rows in matched docs: {total_rows:,}  skipped by len: {skipped:,}", flush=True)
    print(f"qualifying records  : {sum(sizes.values()):,}", flush=True)

    # ---- decide how many docs to emit (sample = enough docs to reach limit) ----
    if a.full:
        target_docs = order
    else:
        target_docs, acc = [], 0
        for d in order:
            target_docs.append(d)
            acc += sizes[d]
            if acc >= a.limit:
                break
    emit = set(target_docs)
    print(f"docs to emit: {len(emit):,}", flush=True)

    # ---- pass 2: emit with prev/next by in-doc original order ----
    out_path = os.path.join(BASE, "sentences.jsonl" if a.full else "sentences_sample.jsonl")
    tmp = out_path + ".part"

    last_doc, prev_cls = None, None
    pending = None  # (record, doc) waiting to learn next_sentence

    written = prev_non_null = next_non_null = empty_src = 0
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        def flush_pending(nxt):
            nonlocal written, prev_non_null, next_non_null, empty_src
            if pending is None:
                return
            rec, doc = pending
            rec["next_sentence"] = nxt
            if rec["prev_sentence"] is not None:
                prev_non_null += 1
            if nxt is not None:
                next_non_null += 1
            if not rec["source_work"]:
                empty_src += 1
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            written += 1

        stop = False
        for b in iter_batches(["info", "classical", "modern", "english"]):
            if stop:
                break
            for inf, cl, md, en in zip(b["info"], b["classical"], b["modern"], b["english"]):
                if inf not in emit:
                    continue
                if not (MIN_LEN <= cjk_len(cl) <= MAX_LEN):
                    continue
                # a new document starts -> close the pending record with next=None
                if inf != last_doc:
                    flush_pending(None)
                    prev_cls = None
                    last_doc = inf
                else:
                    flush_pending(cl)  # this row is the next sentence of pending
                rec = {
                    "classical": cl,
                    "english": en,
                    "modern": md,
                    "source_work": book_of(inf),
                    "prev_sentence": prev_cls,
                    "next_sentence": None,
                    "char_length": cjk_len(cl),
                }
                pending = (rec, inf)
                prev_cls = cl
                if not a.full and written >= a.limit:
                    stop = True
                    pending = None   # drop the look-ahead record: keep exactly `limit`
                    break
        flush_pending(None)
    os.replace(tmp, out_path)

    print(f"\nwritten: {out_path}", flush=True)
    print(f"  records       : {written:,}")
    print(f"  prev non-null : {prev_non_null:,} ({prev_non_null/max(written,1):.1%})")
    print(f"  next non-null : {next_non_null:,} ({next_non_null/max(written,1):.1%})")
    print(f"  empty source  : {empty_src}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

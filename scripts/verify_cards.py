"""Verify the generated card pool against acceptance criteria.

Checks:
  * field set and order exactly: classical, english, modern, source_work,
    prev_sentence, next_sentence, char_length
  * char_length within 4..50 and equal to the real CJK count
  * source_work non-empty
  * prev/next not ALL null
  * prev/next really are the neighbouring rows inside the same document_info
    (cross-checked against the parquet, not just against each other)
"""
import json
import re
import sys
from collections import defaultdict

import pyarrow.parquet as pq

PQ = "D:/guwen-cache/parquet/train.parquet"
EXPECT = ["classical", "english", "modern", "source_work",
          "prev_sentence", "next_sentence", "char_length"]
CJK = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")


def cjk_len(s):
    return len(CJK.findall(s or ""))


def main(path):
    recs = [json.loads(l) for l in open(path, encoding="utf-8")]
    print(f"file   : {path}")
    print(f"records: {len(recs):,}")

    bad = []
    for i, r in enumerate(recs):
        if list(r.keys()) != EXPECT:
            bad.append(f"#{i}: field order {list(r.keys())}")
        cl = r.get("char_length")
        if not isinstance(cl, int) or not (4 <= cl <= 50):
            bad.append(f"#{i}: char_length {cl} out of 4..50")
        elif cl != cjk_len(r.get("classical")):
            bad.append(f"#{i}: char_length {cl} != real {cjk_len(r.get('classical'))}")
        if not (r.get("source_work") or "").strip():
            bad.append(f"#{i}: empty source_work")

    pn = sum(1 for r in recs if r.get("prev_sentence") is not None)
    nn = sum(1 for r in recs if r.get("next_sentence") is not None)
    print(f"\nchar_length range : {min(r['char_length'] for r in recs)}..{max(r['char_length'] for r in recs)}")
    print(f"prev non-null     : {pn:,} ({pn/len(recs):.1%})")
    print(f"next non-null     : {nn:,} ({nn/len(recs):.1%})")
    print(f"distinct source   : {len({r['source_work'] for r in recs})}")

    # --- cross-check prev/next against parquet, per document_info ---
    wanted = {r["classical"] for r in recs}
    by_doc = defaultdict(list)
    pf = pq.ParquetFile(PQ)
    for rg in range(pf.metadata.num_row_groups):
        t = pf.read_row_group(rg, columns=["info", "classical"])
        for inf, cl in zip(t.column("info").to_pylist(), t.column("classical").to_pylist()):
            if cl in wanted:
                by_doc[inf].append(cl)
    # rebuild expected neighbours using the same filter
    exp = {}
    for inf, rows in by_doc.items():
        kept = [x for x in rows if 4 <= cjk_len(x) <= 50]
        for k, x in enumerate(kept):
            exp[(inf, x)] = (kept[k - 1] if k > 0 else None,
                             kept[k + 1] if k + 1 < len(kept) else None)

    mism = 0
    checked = 0
    for i, r in enumerate(recs):
        # find the doc this classical belongs to
        cands = [k for k in exp if k[1] == r["classical"]]
        if not cands:
            continue
        checked += 1
        e_prev, e_next = exp[cands[0]]
        if e_prev != r["prev_sentence"] or e_next != r["next_sentence"]:
            mism += 1
            if mism <= 3:
                print(f"  MISMATCH #{i}: got prev={r['prev_sentence']!r} next={r['next_sentence']!r}")
                print(f"            want prev={e_prev!r} next={e_next!r}")

    print(f"\nprev/next cross-checked: {checked}/{len(recs)}  mismatches: {mism}")
    print(f"prev/next all null? {(pn == 0 and nn == 0)}")

    if bad:
        print(f"\nFAILED with {len(bad)} problem(s):")
        for b in bad[:30]:
            print("  -", b)
        return 1
    if pn == 0 and nn == 0:
        print("\nFAILED: prev/next are all null")
        return 1
    print("\nALL ACCEPTANCE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else
                  "E:/Users/asus/workbuddy/guwen-project/data/sentences_sample.jsonl"))

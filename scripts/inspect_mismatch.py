"""Inspect the single prev/next mismatch: dump the raw rows around it from parquet."""
import json
import re

import pyarrow.parquet as pq

PQ = "D:/guwen-cache/parquet/train.parquet"
CJK = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")


def cjk_len(s):
    return len(CJK.findall(s or ""))


recs = [json.loads(l) for l in open("E:/Users/asus/workbuddy/guwen-project/data/sentences_sample.jsonl", encoding="utf-8")]
target = recs[-1]
print("OUTPUT #199")
print("  source_work :", target["source_work"])
print("  classical   :", target["classical"])
print("  prev        :", target["prev_sentence"])
print("  next        :", target["next_sentence"])
print()

cls_key = target["classical"]
rows = []
pf = pq.ParquetFile(PQ)
for rg in range(pf.metadata.num_row_groups):
    t = pf.read_row_group(rg, columns=["info", "classical"])
    infos = t.column("info").to_pylist()
    for inf, cl in zip(infos, t.column("classical").to_pylist()):
        if cl == cls_key and inf.startswith("《" + target["source_work"]):
            rows.append((rg, inf, cl))

print(f"parquet 中出现该句 且同书 的行数: {len(rows)}")
for rg, inf, cl in rows:
    print(f"  rowgroup={rg} info={inf}")

# dump the document's kept-sequence around each occurrence
docs = {inf for _, inf, _ in rows}
for doc in docs:
    seq = []
    pf = pq.ParquetFile(PQ)
    for rg in range(pf.metadata.num_row_groups):
        t = pf.read_row_group(rg, columns=["info", "classical"])
        for inf, cl in zip(t.column("info").to_pylist(), t.column("classical").to_pylist()):
            if inf == doc:
                seq.append(cl)
    kept = [x for x in seq if 4 <= cjk_len(x) <= 50]
    print(f"\ndoc={doc}  原始行={len(seq)}  过滤后={len(kept)}")
    hits = [k for k, x in enumerate(kept) if x == cls_key]
    print(f"  该句在过滤序列中的位置: {hits}")
    for h in hits:
        lo, hi = max(0, h - 2), min(len(kept), h + 3)
        print(f"  --- 位置 {h} 邻近 ---")
        for k in range(lo, hi):
            mark = " <<<" if k == h else ""
            print(f"    [{k}] {kept[k][:50]}{mark}")

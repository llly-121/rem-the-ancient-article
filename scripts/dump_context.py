"""Ground-truth dump: for the document(s) contributing the sample, print the
first N kept rows with running index so prev/next can be read off directly."""
import json
import re
import sys

import pyarrow.parquet as pq

PQ = "D:/guwen-cache/parquet/train.parquet"
CJK = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")


def cjk_len(s):
    return len(CJK.findall(s or ""))


recs = json.load(open(sys.argv[1], encoding="utf-8")) if sys.argv[1].endswith(".json") else \
    [json.loads(l) for l in open(sys.argv[1], encoding="utf-8")]
targets = {r["source_work"] for r in recs}
print("output books:", targets, flush=True)

# gather ALL docs of those books
docs = {}
pf = pq.ParquetFile(PQ)
for rg in range(pf.metadata.num_row_groups):
    t = pf.read_row_group(rg, columns=["info", "classical"])
    for inf, cl in zip(t.column("info").to_pylist(), t.column("classical").to_pylist()):
        m = re.match(r"^《([^·》]+)", inf or "")
        if m and m.group(1) in targets:
            docs.setdefault(inf, []).append(cl)

for doc, seq in docs.items():
    kept = [x for x in seq if 4 <= cjk_len(x) <= 50]
    print(f"\n=== {doc}  原始 {len(seq)} 行 / 过滤后 {len(kept)} 行 ===")
    for k in range(190, min(205, len(kept))):
        print(f"  [{k:3d}] {kept[k][:44]}")
    print(f"  ... 末尾 [{len(kept)-1}] {kept[-1][:44]}")

# now print output tail with resolved source index
print("\n=== 输出末尾 6 条 ===")
for i, r in enumerate(recs[-6:], start=len(recs) - 6):
    print(f"  #{i} len={r['char_length']:2d} {r['classical'][:40]}")
    print(f"       prev={(r['prev_sentence'] or 'null')[:34]}")
    print(f"       next={(r['next_sentence'] or 'null')[:34]}")

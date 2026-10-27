"""Probe WenYanWen_English_Parallel: load train split via hf-mirror, dump first 200 rows.

Env vars must be set before importing datasets (see run_probe.bat / shell exports).
"""
import json
import os
import sys

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HOME", "D:/guwen-cache/hf")
os.environ.setdefault("HF_DATASETS_CACHE", "D:/guwen-cache/hf/datasets")

from datasets import load_dataset  # noqa: E402

REPO = "KaifengGGG/WenYanWen_English_Parallel"
OUT = "E:/Users/asus/workbuddy/guwen-project/data/sample_200.tsv"


def main():
    print(f"HF_ENDPOINT={os.environ['HF_ENDPOINT']}")
    print(f"loading {REPO} split=train ...", flush=True)
    ds = load_dataset(REPO, split="train", streaming=True)

    feats = ds.features
    print("\n=== FEATURES ===")
    for k, v in feats.items():
        print(f"  {k}: {v}")

    print("\n=== FIRST 200 (streaming) ===", flush=True)
    rows = []
    for i, r in enumerate(ds):
        rows.append(r)
        if i >= 199:
            break
    print(f"collected {len(rows)} rows")

    cols = list(rows[0].keys())
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write("\t".join(cols) + "\n")
        for r in rows:
            vals = []
            for c in cols:
                v = r[c]
                v = "" if v is None else str(v)
                v = v.replace("\t", " ").replace("\r", " ").replace("\n", "\\n")
                vals.append(v)
            f.write("\t".join(vals) + "\n")
    print(f"written {OUT}")

    print("\n=== 10 document_info (info) samples ===")
    for i, r in enumerate(rows[:10]):
        print(f"[{i:03d}] {r.get('info')!r}")

    print("\n=== row 0 full ===")
    print(json.dumps({k: (str(v)[:200] if v is not None else None) for k, v in rows[0].items()},
                     ensure_ascii=False, indent=1))

    return 0


if __name__ == "__main__":
    sys.exit(main())

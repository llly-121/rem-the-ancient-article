"""Step 1: extract unique `info` values from the full parquet into a sorted list file.

Output: data/document_info_list.txt  (one value per line, with a leading count column?
-- NO: plain value per line, so it can be diffed / grepped directly.)
Also writes data/document_info_counts.tsv (value \t count) for later filtering steps.
"""
import collections
import os
import sys

import pyarrow.parquet as pq

PQ = "D:/guwen-cache/parquet/train.parquet"
BASE = "E:/Users/asus/workbuddy/guwen-project/data"
LIST = os.path.join(BASE, "document_info_list.txt")
COUNTS = os.path.join(BASE, "document_info_counts.tsv")


def main():
    col = pq.read_table(PQ, columns=["info"]).column("info").to_pylist()
    print(f"rows read = {len(col):,}")

    cnt = collections.Counter(col)
    print(f"unique info = {len(cnt):,}")

    # plain list, sorted by UTF-8 code point order (stable, diff-friendly)
    with open(LIST, "w", encoding="utf-8", newline="\n") as f:
        for v in sorted(cnt):
            f.write(v + "\n")
    print(f"written {LIST}")

    # counts, sorted by descending frequency
    with open(COUNTS, "w", encoding="utf-8", newline="\n") as f:
        f.write("document_info\trows\n")
        for v, c in cnt.most_common():
            f.write(f"{v}\t{c}\n")
    print(f"written {COUNTS}")

    # integrity: counts must sum to total rows
    total = sum(cnt.values())
    print(f"count sum = {total:,}  (matches rows: {total == len(col)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

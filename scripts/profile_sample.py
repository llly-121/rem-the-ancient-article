"""Profile sample_200.tsv: columns, info format, uniqueness, filterability assessment."""
import collections
import json
import os
import re
import sys

import pandas as pd

TSV = "E:/Users/asus/workbuddy/guwen-project/data/sample_200.tsv"
OUT_JSON = "E:/Users/asus/workbuddy/guwen-project/data/profile_sample_200.json"


def main():
    df = pd.read_csv(TSV, sep="\t", dtype=str, keep_default_na=False, quoting=3)
    print(f"shape = {df.shape}")
    print(f"columns = {list(df.columns)}")
    print("\n=== dtypes / non-null ===")
    print(df.notna().sum().to_string())

    print("\n=== null-ish (empty string) counts ===")
    print((df == "").sum().to_string())

    print("\n=== char length stats per column ===")
    for c in ["classical", "modern", "english"]:
        ln = df[c].str.len()
        print(f"  {c:10s} min={ln.min():4d} med={int(ln.median()):4d} mean={ln.mean():6.1f} max={ln.max():4d}")

    # ---- info field structure ----
    info = df["info"]
    pat = re.compile(r"^《(?P<book>[^·》]+)(?:·(?P<part>[^》]+))?》$")
    parsed = info.str.extract(pat)
    matched = parsed["book"].notna().sum()
    print(f"\n=== info format: 《...》 matched {matched}/{len(info)} ({matched/len(info):.1%}) ===")
    parsed["book"] = parsed["book"].fillna("")
    parsed["part"] = parsed["part"].fillna("")
    parsed["n_parts"] = info.str.count("·")

    print("\n=== 点号(·)分段数分布 ===")
    print(parsed["n_parts"].value_counts().sort_index().to_string())

    print("\n=== 顶层书目分布 (top 20) ===")
    vc = parsed["book"].value_counts()
    for k, v in vc.head(20).items():
        print(f"  {k:12s} {v}")
    print(f"  共 {vc.size} 种书目")

    print("\n=== 第二段（体例/篇名）分布 (top 20) ===")
    part1 = parsed["part"].str.split("·").str[0]
    for k, v in part1.value_counts().head(20).items():
        print(f"  {str(k):20s} {v}")

    # ---- filterability diagnostics ----
    print("\n=== 按篇目筛选可行性诊断 ===")
    n_rows = len(df)
    n_uniq_info = info.nunique()
    print(f"  sample rows        : {n_rows}")
    print(f"  unique info values : {n_uniq_info}  ({n_uniq_info/n_rows:.1%} of rows)")
    vc_info = info.value_counts()
    print(f"  max rows per info  : {vc_info.iloc[0]}  ({vc_info.index[0]})")
    print(f"  median rows/info   : {int(vc_info.median())}")
    print(f"  info 出现 1 次的书 : {(vc_info == 1).sum()} 种")
    print(f"  info 出现 >=5 次   : {(vc_info >= 5).sum()} 种")

    # frequency of second-level segment (e.g. 列传 / 本纪 / 志)
    print("\n=== 核心粒度：book + 体例（去掉卷号） ===")
    canon = parsed["book"] + "·" + part1.fillna("")
    # strip 卷号-like suffix: 卷二十八, 卷十四, 第四章
    body_pat = re.compile(r"^(.*?)(?:卷[一二三四五六七八九十百千零〇\d]+.*|第[一二三四五六七八九十百\d]+[章回篇].*)$")
    core = part1.fillna("").map(lambda s: body_pat.sub(r"\1", s) if s else "")
    edition = parsed["book"] + "·" + core
    print(f"  edition 粒度 unique : {edition.nunique()} 种 / {n_rows} 行")
    for k, v in edition.value_counts().head(15).items():
        print(f"    {k:28s} {v}")

    # ---- duplicate classical sentences ----
    print("\n=== 重复度检查 ===")
    print(f"  classical 完全重复: {df['classical'].duplicated().sum()} 行")
    print(f"  english 完全重复  : {df['english'].duplicated().sum()} 行")

    print("\n=== 前 5 行实拍 ===")
    print(df.head(5).to_string(max_colwidth=40))

    payload = {
        "shape": list(df.shape),
        "columns": list(df.columns),
        "info_unique": int(n_uniq_info),
        "info_format_match_rate": float(matched / len(info)),
        "edition_unique": int(edition.nunique()),
        "books": {str(k): int(v) for k, v in vc.items()},
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"\nprofile -> {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

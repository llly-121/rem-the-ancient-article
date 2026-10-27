"""Step 2: match document_info values against the curriculum whitelist.

Two match channels:
  A. 篇目白名单 -> 按"书"（《》内第一段）精确匹配
  B. 作者白名单 -> document_info 子串匹配

Writes data/matched_sources.txt (report, for user review) and
data/matched_sources.tsv (machine-readable, consumed by step 3).

Design note: the 篇目 entries like 出师表/陈情表/兰亭集序 are prose titles whose
carrier collections (诸葛亮集/陶渊明集/王临川集...) are NOT part of this corpus,
so they can never match. They are reported explicitly as NO_CARRIER instead of
being silently dropped or force-fuzzy-matched.
"""
import collections
import os
import re
import sys

BASE = "E:/Users/asus/workbuddy/guwen-project/data"
LIST = os.path.join(BASE, "document_info_list.txt")
COUNTS = os.path.join(BASE, "document_info_counts.tsv")
OUT_TXT = os.path.join(BASE, "matched_sources.txt")
OUT_TSV = os.path.join(BASE, "matched_sources.tsv")

# ---- whitelist A: 按"书"精确匹配 ----
BOOK_WHITELIST = [
    "论语", "孟子", "左传", "战国策", "史记", "汉书", "后汉书", "三国志",
]
# 以下为单篇课文名（非书名）。保留在清单里以防未来数据集扩充，但本语料无载体。
PROSE_WHITELIST = [
    "出师表", "陈情表", "兰亭集序", "滕王阁序", "阿房宫赋", "赤壁赋",
    "岳阳楼记", "醉翁亭记", "爱莲说", "陋室铭", "师说", "桃花源记",
    "曹刿论战", "邹忌讽齐王纳谏", "鸿门宴", "陈涉世家",
]

# ---- whitelist B: 作者子串匹配 ----
AUTHORS = ["韩愈", "柳宗元", "欧阳修", "苏轼", "王安石", "归有光", "姚鼐"]


def main():
    vals = [l.rstrip("\n") for l in open(LIST, encoding="utf-8")]
    cnt = {}
    with open(COUNTS, encoding="utf-8") as f:
        next(f)
        for line in f:
            v, c = line.rstrip("\n").rsplit("\t", 1)
            cnt[v] = int(c)

    book_of = {}
    for v in vals:
        m = re.match(r"^《([^·》]+)", v)
        book_of[v] = m.group(1) if m else ""

    rows = []          # (document_info, rows, match_type, matched_token)
    per_book = collections.Counter()

    # A: exact book match
    for v in vals:
        if book_of[v] in BOOK_WHITELIST:
            rows.append((v, cnt[v], "篇目-书名", book_of[v]))
            per_book[book_of[v]] += 1

    # A2: prose titles -- 在 document_info 中出现（含书名/篇名位置）
    prose_hits = collections.Counter()
    for kw in PROSE_WHITELIST:
        for v in vals:
            if kw in v:
                prose_hits[kw] += 1
                rows.append((v, cnt[v], "篇目-篇名", kw))

    # B: author substring
    author_hits = collections.Counter()
    for kw in AUTHORS:
        for v in vals:
            if kw in v:
                author_hits[kw] += 1
                rows.append((v, cnt[v], "作者", kw))

    # dedupe (same document_info may hit multiple tokens), keep all match reasons
    merged = collections.OrderedDict()
    for v, c, t, tok in rows:
        if v not in merged:
            merged[v] = {"rows": c, "reasons": []}
        merged[v]["reasons"].append(f"{t}:{tok}")

    total_rows = sum(m["rows"] for m in merged.values())

    with open(OUT_TSV, "w", encoding="utf-8", newline="\n") as f:
        f.write("document_info\trows\tmatch_reasons\n")
        for v, m in sorted(merged.items()):
            f.write(f"{v}\t{m['rows']}\t{';'.join(m['reasons'])}\n")

    # ---- report ----
    L = []
    L.append("document_info 白名单匹配清单")
    L.append("=" * 70)
    L.append(f"语料总量        : 972,467 行 / 7,304 个 document_info")
    L.append(f"匹配到 document_info : {len(merged):,} 个")
    L.append(f"匹配到句数      : {total_rows:,} 行  ({total_rows/972467:.2%})")
    L.append("")

    L.append("一、篇目白名单 · 按书名精确匹配")
    L.append("-" * 70)
    L.append(f"{'书名':10s}{'document_info数':>16s}{'句数':>12s}   状态")
    for b in BOOK_WHITELIST:
        n = per_book.get(b, 0)
        r = sum(cnt[v] for v in merged if book_of[v] == b and "篇目-书名" in ";".join(merged[v]["reasons"]))
        L.append(f"  {b:8s}{n:>14d}{r:>12,d}   {'OK' if n else 'NO MATCH'}")
    L.append("")

    L.append("二、篇目白名单 · 单篇课文（需载体别集）")
    L.append("-" * 70)
    L.append(f"{'篇目':18s}{'命中数':>8s}   说明")
    for kw in PROSE_WHITELIST:
        n = prose_hits.get(kw, 0)
        note = "命中" if n else "语料无该篇载体"
        L.append(f"  {kw:16s}{n:>8d}   {note}")
    L.append("")

    L.append("三、作者白名单 · document_info 子串匹配")
    L.append("-" * 70)
    L.append(f"{'作者':10s}{'命中document_info数':>20s}")
    for kw in AUTHORS:
        L.append(f"  {kw:8s}{author_hits.get(kw, 0):>18d}")
    L.append("")

    # 作者命中的真实样例
    L.append("四、作者命中的真实 document_info 样例（每条作者最多 5 例）")
    L.append("-" * 70)
    for kw in AUTHORS:
        ex = [v for v in merged if f"作者:{kw}" in ";".join(merged[v]["reasons"])][:5]
        L.append(f"  【{kw}】{len(ex)} 例:")
        for v in ex:
            L.append(f"      {v}   ({cnt[v]:,} 行)")
    L.append("")

    L.append("五、全部匹配到的 document_info 明细（按句数降序）")
    L.append("-" * 70)
    for v, m in sorted(merged.items(), key=lambda x: -x[1]["rows"]):
        L.append(f"  {m['rows']:>5,d} 行  {v}   [{' ; '.join(m['reasons'])}]")
    L.append("")

    L.append("六、无法匹配的篇目白名单（需你决策）")
    L.append("-" * 70)
    dead = [kw for kw in PROSE_WHITELIST if prose_hits.get(kw, 0) == 0]
    if dead:
        L.append("  以下篇目在 7,304 个 document_info 中 0 命中：")
        for kw in dead:
            L.append(f"    - {kw}")
        L.append("")
        L.append("  根因：本数据集只收**史书/子书/经书原典**（97 种，全部为整书），")
        L.append("        不含《诸葛亮集》《陶渊明集》《王临川集》《范文正公集》等别集，")
        L.append("        故这些单篇散文没有载体可承载。")
    L.append("")
    L.append("七、匹配口径说明")
    L.append("-" * 70)
    L.append("  · 篇目类一律按『书名精确匹配』，不做跨书模糊匹配（避免把《汉书》的句子")
    L.append("    混进《史记》卡池这类语义污染）。")
    L.append("  · 『曹刿论战』属《左传》，『邹忌讽齐王纳谏』属《战国策》，『陈涉世家』属")
    L.append("    《史记》 —— 它们在语料中的载体情况各不相同，不能一概说『已被书名匹配覆盖』：")
    L.append("      - 陈涉世家：语料有独立条目《史记·三十世家·陈涉世家》，已随《史记》纳入（见第八节）")
    L.append("      - 邹忌讽齐王纳谏：语料原题为《战国策·齐一·邹忌修八尺有余》，已随《战国策》纳入")
    L.append("      - 曹刿论战：语料 0 条对应篇目，仅《国语·鲁语》有两篇『曹刿』相关文，**不是课内那篇**（见第九节）")
    L.append("  · 作者匹配依赖 document_info 中出现人名，命中即为该人著作/传记。")
    L.append("")
    L.append("八、白名单之外、但确实属于课内的篇目（原题收录，需你决定是否纳入）")
    L.append("-" * 70)
    L.append("  以下 document_info 用的是**古文原题**，与课内标题不同，故未命中上面的白名单，")
    L.append("  但内容即课内篇目。列出真实值供你判断：")
    for v in vals:
        for kw, note in [
            ("邹忌修八尺有余", "＝课内《邹忌讽齐王纳谏》全文原题（《战国策·齐一》）"),
            ("陈涉世家", "＝课内《陈涉世家》"),
            ("项羽本纪", "含课内《鸿门宴》段落（鸿门宴为项羽本纪节选）"),
        ]:
            if kw in v:
                mark = "已匹配" if v in merged else "未匹配"
                L.append(f"    [{mark}] {v}  ({cnt[v]:,} 行)  {note}")
    L.append("")
    L.append("九、只命中书、但课内对应篇目在语料中无独立条目的情况")
    L.append("-" * 70)
    L.append("  · 《左传》中的『曹刿论战』：语料里 0 条《左传·曹刿论战》，")
    L.append("    只存在《国语·鲁语·曹刿谏庄公如齐观社》《国语·鲁语·曹刿问战》——")
    L.append("    这是**另一本书里的另两篇文章**，不是课内那篇，不能替代。")
    L.append("  · 『鸿门宴』：语料无独立条目，仅在《史记·项羽本纪》正文内，需正文检索定位。")

    report = "\n".join(L)
    with open(OUT_TXT, "w", encoding="utf-8", newline="\n") as f:
        f.write(report + "\n")

    print(report)
    print(f"\n[written] {OUT_TXT}")
    print(f"[written] {OUT_TSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Probe: locate course-text openings anywhere in the corpus (full-text scan).

Answers one question only: for each 课内篇目, does its opening sentence exist
somewhere in the 972k rows, and inside which document_info?  No filtering, no
card building -- this is evidence gathering for the user's whitelist decision.
"""
import re
import sys
from collections import defaultdict

import pyarrow.parquet as pq

PQ = "D:/guwen-cache/parquet/train.parquet"

# 篇目 -> 该篇首句/特征句（用于在正文中定位）
PROBES = {
    "岳阳楼记": ["先天下之忧而忧", "庆历四年春，滕子京谪守巴陵郡", "予观夫巴陵胜状"],
    "醉翁亭记": ["环滁皆山也", "醉翁之意不在酒"],
    "出师表": ["臣亮言", "先帝创业未半而中道崩殂"],
    "桃花源记": ["晋太元中，武陵人捕鱼为业", "豁然开朗", "不知有汉，无论魏晋"],
    "小石潭记": ["从小丘西行百二十步", "潭中鱼可百许头"],
    "曹刿论战": ["十年春，齐师伐我", "肉食者鄙", "一鼓作气，再而衰，三而竭"],
    "送东阳马生序": ["余幼时即嗜学", "天大寒，砚冰坚"],
    "论语十二章": ["学而时习之", "人不知而不愠", "吾日三省吾身"],
    "劝学": ["青，取之于蓝", "学不可以已", "锲而不舍，金石可镂"],
    "师说": ["古之学者必有师", "师者，所以传道受业解惑也"],
    "赤壁赋": ["壬戌之秋，七月既望", "清风徐来，水波不兴"],
    "阿房宫赋": ["六王毕，四海一", "灭六国者六国也"],
    "六国论": ["六国破灭，非兵不利", "赂秦而力亏"],
    "陈情表": ["臣密言", "夙遭闵凶", "茕茕孑立"],
    "过秦论": ["秦孝公据崤函之固", "仁义不施而攻守之势异也"],
    "廉颇蔺相如列传": ["廉颇者，赵之良将也", "完璧归赵", "负荆请罪"],
    "陋室铭": ["山不在高，有仙则名", "斯是陋室，惟吾德馨"],
    "爱莲说": ["水陆草木之花", "出淤泥而不染"],
    "三峡": ["自三峡七百里中", "虽乘奔御风"],
    "记承天寺夜游": ["元丰六年十月十二日夜", "庭下如积水空明"],
    "富贵不能淫": ["富贵不能淫，贫贱不能移", "公孙衍、张仪岂不诚大丈夫哉"],
    "生于忧患死于安乐": ["舜发于畎亩之中", "天将降大任于是人也", "入则无法家拂士"],
    "马说": ["世有伯乐，然后有千里马", "千里马常有，而伯乐不常有"],
    "鱼我所欲也": ["鱼，我所欲也", "舍生而取义者也"],
    "邹忌讽齐王纳谏": ["邹忌修八尺有余", "臣诚知不如徐公美", "王之蔽甚矣"],
}


def main():
    pf = pq.ParquetFile(PQ)
    # probe -> [(info, classical)]
    hits = defaultdict(list)
    flat = [(t, p) for t, ps in PROBES.items() for p in ps]
    total = 0
    for rg in range(pf.metadata.num_row_groups):
        tbl = pf.read_row_group(rg, columns=["info", "classical"])
        infos = tbl.column("info").to_pylist()
        cls = tbl.column("classical").to_pylist()
        for inf, cl in zip(infos, cls):
            total += 1
            if not cl:
                continue
            for title, p in flat:
                if p in cl:
                    hits[title].append((inf, cl))
    print(f"scanned rows: {total:,}")

    out = []
    for title in PROBES:
        hs = hits.get(title, [])
        docs = sorted({i for i, _ in hs})
        out.append(f"\n【{title}】 命中句数={len(hs)}  涉及 document_info={len(docs)}")
        for d in docs[:8]:
            snip = next(c for i, c in hs if i == d)
            out.append(f"    {d}   e.g. {snip[:40]}")
    report = "\n".join(out)
    with open("E:/Users/asus/workbuddy/guwen-project/data/course_text_probe.txt",
              "w", encoding="utf-8", newline="\n") as f:
        f.write(f"课内篇目正文检索探针（全语料 {total:,} 行逐行扫描）\n" + "=" * 66 + "\n" + report + "\n")
    sys.stdout.reconfigure(encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()

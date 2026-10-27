import json
import re

rs = [json.loads(l) for l in open("data/course_cards.jsonl", encoding="utf-8")]

bad = []
CJK = re.compile(r"[\u4e00-\u9fff]")
for i, r in enumerate(rs, 1):
    problems = []
    if list(r) != ["classical", "modern", "source_work", "author", "prev_sentence",
                   "next_sentence", "char_length", "para_index", "translation_scope"]:
        problems.append("字段顺序")
    real = len(CJK.findall(r["classical"]))
    if real != r["char_length"]:
        problems.append("char_length不符(%d vs %d)" % (r["char_length"], real))
    if not (4 <= r["char_length"] <= 50):
        problems.append("长度越界")
    if not r["source_work"]:
        problems.append("source_work空")
    if not r["modern"]:
        problems.append("modern空")
    # 段级译文必须明显长于本句（否则说明该段只有一句，标成段级也可接受）
    if r["translation_scope"] not in ("句", "段"):
        problems.append("scope非法")
    if problems:
        bad.append((i, problems, r["classical"]))

print("总卡片:", len(rs))
print("问题卡片:", len(bad))
for b in bad[:10]:
    print("  #%d %s | %s" % b)
from collections import Counter
print("translation_scope 分布:", Counter(r["translation_scope"] for r in rs))
print("篇目数:", len({r["author"] + r["source_work"] for r in rs}))
print("prev非空:", sum(1 for r in rs if r["prev_sentence"]), " next非空:", sum(1 for r in rs if r["next_sentence"]))
print("长度区间:", min(r["char_length"] for r in rs), "-", max(r["char_length"] for r in rs))

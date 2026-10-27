import json
from collections import Counter

rs = [json.loads(l) for l in open("data/course_cards_v2.jsonl", encoding="utf-8")]
bad = []
CJK = re = __import__("re")
CJK = CJK.compile(r"[\u4e00-\u9fff]")
EXPECT = ["classical", "modern", "source_work", "author", "prev_sentence",
          "next_sentence", "char_length", "para_index", "translation_scope",
          "title", "english", "english_source", "english_ambiguous"]
for i, r in enumerate(rs, 1):
    p = []
    if list(r) != EXPECT:
        p.append("字段顺序")
    real = len(CJK.findall(r["classical"]))
    if real != r["char_length"]:
        p.append("char_length不符(%d vs %d)" % (real, r["char_length"]))
    if not (4 <= r["char_length"] <= 50):
        p.append("长度越界")
    if not r["source_work"]:
        p.append("source_work空")
    if not r["modern"]:
        p.append("modern空")
    if not r["title"]:
        p.append("title空")
    if r["translation_scope"] not in ("句", "段"):
        p.append("scope非法")
    if p:
        bad.append((i, p, r["classical"]))

print("总卡片:", len(rs))
print("问题卡片:", len(bad))
for b in bad[:10]:
    print("  #%d %s | %s" % b)
print("篇目数:", len({r['title'] for r in rs}))
print("translation_scope:", Counter(r["translation_scope"] for r in rs))
print("有英文:", sum(1 for r in rs if r["english"]), "/", len(rs))
print("英文来源:", Counter(r["english_source"] for r in rs if r["english"]))
print("歧义:", [r["classical"] for r in rs if r.get("english_ambiguous")])
print("长度区间:", min(r["char_length"] for r in rs), "-", max(r["char_length"] for r in rs))
# 空间抽查
print("--- 样例 ---")
for t in ("陈情表", "富贵不能淫", "论语十二章"):
    s = next(r for r in rs if r["title"] == t)
    print(f"[{t}] {s['classical'][:30]} | 现:{s['modern'][:25]} | 英:{(s['english'] or '')[:60]}")

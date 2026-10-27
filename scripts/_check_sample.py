import json

rs = [json.loads(l) for l in open("data/course_cards.jsonl", encoding="utf-8")]

print("=== 句级对齐（陋室铭）===")
for r in rs:
    if r["author"] == "刘禹锡":
        print("[%s] %s  ||  %s" % (r["translation_scope"], r["classical"], r["modern"]))

print()
print("=== 段级退回（劝学）===")
n = 0
for r in rs:
    if r["author"] == "荀子" and r["translation_scope"] == "段":
        print("[%s] %s  ||  %s..." % (r["translation_scope"], r["classical"], r["modern"][:60]))
        n += 1
        if n >= 2:
            break

print()
print("=== 段级退回（阿房宫赋）===")
n = 0
for r in rs:
    if r["author"] == "杜牧" and r["translation_scope"] == "段":
        print("[%s] %s  ||  %s..." % (r["translation_scope"], r["classical"], r["modern"][:50]))
        n += 1
        if n >= 2:
            break

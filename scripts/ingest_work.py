# -*- coding: utf-8 -*-
"""把一篇新文章入库：追加到 data/course_cards_v2.jsonl（可选再生成句子题）。

# 为什么是脚本而不是界面粘贴框

「粘一段原文就能刷题」这件事前端做不到：四选一题目 = 一句英文译文 + 3 个
干扰项，而干扰项必须挑「意思沾边但不对」的译法，靠纯前端没有翻译能力、更
没有判断力。所以入库走这条离线流程：先由人（或 AI 检索 + 人工校对）写出
逐句的原文 / 白话 / 英译，再用本脚本落盘。

宁可慢一点，也不要往语料库里灌机器瞎翻的东西——那会污染整个题库。

# 输入格式

一个 JSON 文件，形如：

    {
      "title": "归去来兮辞",
      "author": "陶渊明",
      "source": "《陶渊明集》卷五",
      "sentences": [
        {"c": "归去来兮，田园将芜胡不归？",
         "m": "回去吧！田园快要荒芜了，为什么还不回去呢？",
         "e": "Let us go back! The fields and garden will soon be overgrown — why not return?"},
        {"p": 1, "c": "既自以心为形役，奚惆怅而独悲？",
         "m": "既然自己让心灵被形体驱使，为什么还惆怅独自悲伤？",
         "e": "Since I let my mind be the slave of my body, why should I grieve alone?"}
      ]
    }

* `c` 原文，`m` 白话，`e` 英译，三者必填。
* `p` 段号，默认全在同一段。同一段里若多句共用同一句白话，会自动标成
  「段级白话」（translation_scope=段），前端显示的标签会跟着变成「本段白话」。
* 顺序即原文顺序，脚本不排序。

# 用法

    python scripts/ingest_work.py _ingest/归去来兮辞.json --dry-run
    python scripts/ingest_work.py _ingest/归去来兮辞.json --with-sentence-quiz
    python scripts/build_web_demo_data.py          # 重建 data.js（记得先升版本号）

落盘之后必须重建 data.js，否则网页看不到新篇。
"""

import argparse
import json
import os
import random
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
COURSE = os.path.join(DATA, "course_cards_v2.jsonl")
SENT = os.path.join(DATA, "sentence_cards.jsonl")
QUIZ = os.path.join(DATA, "sentence_quiz.jsonl")

# 干扰项只从别的篇里挑，且长度接近，避免「一眼就能排除」的荒谬选项
DISTRACTOR_RATIO = (0.6, 1.6)


def load(name):
    with open(name, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def append(name, rows):
    with open(name, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def next_id(rows, prefix):
    n = 0
    for r in rows:
        m = re.match(re.escape(prefix) + r"(\d+)$", str(r.get("id", "")))
        if m:
            n = max(n, int(m.group(1)))
    width = len(str(rows[0]["id"])) - len(prefix) if rows else 4
    return n + 1, width


def validate(spec, existing_titles):
    errs = []
    title = (spec.get("title") or "").strip()
    if not title:
        errs.append("缺 title（篇名）")
    if title in existing_titles:
        errs.append(f"篇名「{title}」已经在 course_cards_v2 里，换个名字或手工处理")

    sents = spec.get("sentences") or []
    if len(sents) < 2:
        errs.append("sentences 至少要有 2 句（一句话成不了篇）")

    seen = set()
    for i, s in enumerate(sents):
        for k in ("c", "m", "e"):
            if not (s.get(k) or "").strip():
                errs.append(f"第 {i + 1} 句缺 {k}")
        c = (s.get("c") or "").strip()
        if c in seen:
            errs.append(f"第 {i + 1} 句与前面完全重复：{c[:16]}")
        seen.add(c)
        # 英译必须是英文：混进中文说明基本是漏译或占位
        e = (s.get("e") or "")
        if re.search(r"[\u4e00-\u9fff]", e):
            errs.append(f"第 {i + 1} 句的英译里还有中文，疑似没译完")
    return errs


def build_rows(spec):
    """组装 course_cards_v2 的行。段号自己排，不沿用外部 para_index —
    库里那列有过跳号（出师表缺 5、6），新篇没必要继承这种历史包袱。"""
    title = spec["title"].strip()
    author = (spec.get("author") or "").strip()
    source = (spec.get("source") or "").strip()

    sents = spec["sentences"]
    # 段号：按 p 字段分组，保持出现顺序；没写 p 的归到当前段
    paras, order = {}, []
    cur = 0
    for s in sents:
        if "p" in s:
            cur = int(s["p"])
        if cur not in paras:
            paras[cur] = []
            order.append(cur)
        paras[cur].append(s)

    rows = []
    pid = 0
    for key in order:
        block = paras[key]
        moderns = [(b.get("m") or "").strip() for b in block]
        # 同一段里白话完全一致 → 这是「段级白话」，前端要标「本段白话」
        shared = len(block) > 1 and len(set(moderns)) == 1
        scope = "段" if shared else "句"
        for i, b in enumerate(block):
            rows.append({
                "classical": (b.get("c") or "").strip(),
                "modern": moderns[i],
                "source_work": source,
                "author": author,
                "prev_sentence": None,
                "next_sentence": None,
                "char_length": len((b.get("c") or "").strip()),
                "para_index": pid,
                "translation_scope": scope,
                "title": title,
                "english": (b.get("e") or "").strip(),
                "english_source": spec.get("english_source") or "manual",
                "english_ambiguous": bool(b.get("ambiguous") or False),
            })
        pid += 1

    # 前后句用最终顺序回填（跨段也算前后句，通读时不至于断了）
    for i, r in enumerate(rows):
        if i > 0:
            r["prev_sentence"] = rows[i - 1]["classical"]
        if i + 1 < len(rows):
            r["next_sentence"] = rows[i + 1]["classical"]
    return rows


def build_sentence_quiz(rows, spec, sent_rows, existing, seed):
    """句级四选一：正确项是本文句的英译，干扰项从别的篇里抽。

    干扰项是自动抽的，质量一定不如人工校订的那批 —— 所以 explanation 里
    如实写明来路，`needs_manual` 标 true，方便以后回查。
    """
    rnd = random.Random(seed)
    pool = [r for r in existing
            if r.get("full_english") and r.get("source_work", "").split("（")[0] != spec["title"]]
    out_cards, out_quiz = [], []
    sid, swidth = next_id(sent_rows, "s")

    for r in rows:
        e = r["english"]
        L = len(e)
        lo, hi = L * DISTRACTOR_RATIO[0], L * DISTRACTOR_RATIO[1]
        cand = [p for p in pool if lo <= len(p["full_english"]) <= hi]
        if len(cand) < 3:
            cand = pool
        picks = rnd.sample(cand, 3) if len(cand) >= 3 else cand
        if len(picks) < 3:
            continue
        cid = f"s{sid:0{swidth}d}"
        sid += 1

        out_cards.append({
            "id": cid,
            "classical_sentence": r["classical"],
            "full_english": e,
            "source_work": (f"{r['title']}（{r['source_work']}）" if r["source_work"] else r["title"]),
            "prev_sentence": r["prev_sentence"],
            "next_sentence": r["next_sentence"],
            "sentence_type": "一般陈述句",
            "exam_frequency": 3,
        })
        out_quiz.append({
            "id": cid,
            "classical_sentence": r["classical"],
            "correct": e,
            "sentence_type": "一般陈述句",
            "source_work": out_cards[-1]["source_work"],
            "distractors": [
                {"text": p["full_english"],
                 "error_type": "other_sentence",
                 "explanation": f"这是《{p['source_work'].split('（')[0]}》里另一句的译文"}
                for p in picks
            ],
            "needs_manual": True,
            "note": "自动生成的干扰项，没逐条人工校订",
        })
    return out_cards, out_quiz


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", help="入库用的 JSON，见文件头部说明")
    ap.add_argument("--dry-run", action="store_true", help="只打印结果，不写文件")
    ap.add_argument("--with-sentence-quiz", action="store_true",
                    help="同时生成句级四选一（干扰项自动抽，需人工过一遍）")
    ap.add_argument("--seed", type=int, default=20261029)
    args = ap.parse_args()

    if not os.path.exists(args.spec):
        print(f"找不到 {args.spec}", file=sys.stderr)
        return 1
    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)

    course = load(COURSE)
    titles = {r["title"] for r in course}
    errs = validate(spec, titles)
    if errs:
        print("入库被拒绝：", file=sys.stderr)
        for e in errs:
            print("  ×", e, file=sys.stderr)
        return 1

    rows = build_rows(spec)
    n_char = sum(r["char_length"] for r in rows)
    n_para = len({r["para_index"] for r in rows})
    n_scope = sum(1 for r in rows if r["translation_scope"] == "段")
    print(f"《{spec['title']}》 {len(rows)} 句 / {n_para} 段 / {n_char} 字"
          f"（其中 {n_scope} 句是段级白话）")

    if args.dry_run:
        for r in rows[:3]:
            print(json.dumps(r, ensure_ascii=False)[:220])
        print("--dry-run：没有写任何文件")
        return 0

    append(COURSE, rows)
    print(f"已追加 {len(rows)} 行 → {COURSE}")

    if args.with_sentence_quiz:
        sent_rows = load(SENT)
        cards, quiz = build_sentence_quiz(rows, spec, sent_rows, sent_rows, args.seed)
        append(SENT, cards)
        append(QUIZ, quiz)
        print(f"已生成句级卡 {len(cards)} 张 / 句级题 {len(quiz)} 道"
              f"（干扰项自动抽的，提示语已标 needs_manual）")

    print("下一步：")
    print("  1) 把 scripts/build_web_demo_data.py 的 DATA_VERSION 加 1")
    print("  2) python scripts/build_web_demo_data.py")
    print("  3) 重新发布")
    return 0


if __name__ == "__main__":
    sys.exit(main())

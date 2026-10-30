#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 jsonl 题库打包成网页体验版可直接读取的 data.js。

为什么需要这一步：iOS 版把 jsonl 编进 App bundle 走 SwiftData 导入，网页版没有
这套机制，而且浏览器在 file:// 下 fetch 会被 CORS 拦死。所以改成生成一个
`window.GUWEN = {...}` 的 JS 文件，用 <script src> 加载——script 标签不受 CORS 限制，
双击 index.html 就能直接用，不需要起服务器。

字段名做了压缩（term→tm、fullEnglish→fe …），纯粹为了缩小体积；映射关系写在
web-demo/README 与 index.html 顶部的注释里，两边必须同步改。

用法：
    python scripts/build_web_demo_data.py
产物：
    web-demo/data.js
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "web-demo", "data.js")

# 与 Library.swift 的 dataVersion 保持一致：题库一改就要往上涨，
# 网页端拿它做 localStorage 的缓存键，版本变了自动作废旧进度。
#
# v7：新增 works（篇章视图）。卡片 id 一张没变，web-demo 里做了 v6 → v7 的
# 一次性迁移，用户已经刷过的进度不会清零。
DATA_VERSION = 8

# 重点 / 次重点的分档人数：25 篇按「篇内考频五星卡片数」降序，
# 前 10 篇重点、11–19 篇次重点、其余普通。
TIER_TOP = 10
TIER_MID = 19


def load(name):
    path = os.path.join(DATA, name + ".jsonl")
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def clean(text):
    """空串统一成 None，让 JS 侧可以用 `||` 判空，也省掉 JSON 里的空字符串。"""
    if text is None:
        return None
    text = text.strip()
    return text or None


def build_works(quizzable, word_by_cl, sent_by_cl):
    """把 course_cards_v2 全量打成「篇 → 段块 → 句 → 卡片」的篇章索引。

    为什么单独读 course_cards_v2 而不从 cards 反推：cards 只保留「凑得出 4 个
    干扰项」的卡（1346 / 2072），直接反推会缺句——廉颇缺 5 句、论语缺 4 句，
    整篇原文就有洞。

    段号一律由 ps（每段句数）累加推出，**不用 para_index**：出师表那列跳号
    （缺 5、6），爱莲说还有 OCR 变体（不然 / 不染）会让 prev/next 断链。
    """
    rows = load("course_cards_v2")
    works, cur = [], None

    i = 0
    while i < len(rows):
        r = rows[i]
        if cur is None or r["title"] != cur["t"]:
            cur = {"t": r["title"], "a": r.get("author") or "", "lv": 3,
                   "ps": [], "m": [], "s": [], "_ef5": 0, "_nq": 0}
            works.append(cur)

        # 同 (篇名, para_index) 连续的一段行算一个段
        j = i
        while (j < len(rows) and rows[j]["title"] == r["title"]
               and rows[j]["para_index"] == r["para_index"]):
            j += 1
        block = rows[i:j]

        if block[0]["translation_scope"] == "段":
            # 整段共用一段白话 → 只存一份，多句指向同一个块
            mi = len(cur["m"])
            cur["m"].append([block[0]["modern"], 1])
            mids = [mi] * len(block)
        else:
            mids = []
            for b in block:
                mids.append(len(cur["m"]))
                cur["m"].append([b["modern"], 0])

        for b, mi in zip(block, mids):
            cl = b["classical"]
            wids = [c["id"] for c in word_by_cl.get(cl, []) if c["id"] in quizzable]
            sc = sent_by_cl.get(cl)
            qid = sc["id"] if sc and sc["id"] in quizzable else None
            cur["s"].append({"c": cl, "m": mi, "e": b.get("english") or "",
                             "w": wids, "q": qid})
            cur["_ef5"] += sum(1 for c in word_by_cl.get(cl, [])
                               if (c.get("exam_frequency") or 0) >= 5)
            cur["_nq"] += len(wids) + (1 if qid else 0)

        cur["ps"].append(len(block))
        i = j

    # 排序：考频五星卡片多的在前；同分看可出题数，再看篇幅。
    # 前端 DATA.works 已经是「重点 → 普通」的顺序，目录里直接按数组顺序渲染，
    # 用户手动改档只覆盖 lv，不动这个顺序。
    order = sorted(range(len(works)),
                   key=lambda k: (-works[k]["_ef5"], -works[k]["_nq"], -len(works[k]["s"])))
    for pos, k in enumerate(order):
        works[k]["lv"] = 1 if pos < TIER_TOP else (2 if pos < TIER_MID else 3)
    works = [works[k] for k in order]
    for w in works:
        del w["_ef5"], w["_nq"]
    return works


def build():
    word_cards = {c["id"]: c for c in load("word_cards")}
    sent_cards = {c["id"]: c for c in load("sentence_cards")}
    word_quiz = {q["id"]: q for q in load("word_quiz")}
    sent_quiz = {q["id"]: q for q in load("sentence_quiz")}

    cards = []

    # ---- 词卡 ----
    for cid, q in word_quiz.items():
        card = word_cards.get(cid)
        ds = q.get("distractors") or []
        # 与 Library.swift 同口径：凑不满 3 个干扰项就不进抽题池
        if card is None or not q.get("correct") or len(ds) < 3:
            continue
        cards.append({
            "id": cid,
            "t": "w",
            "tm": card["term"],
            "cc": card.get("char_count", 0),
            "m": clean(card.get("meaning_in_this_sentence")),
            "os": [s for s in (card.get("other_senses") or []) if s],
            "te": clean(card.get("term_english")),
            "fe": clean(card.get("full_english")),
            "cl": clean(card["classical_sentence"]),
            "sw": clean(card.get("source_work")),
            "pv": clean(card.get("prev_sentence")),
            "nx": clean(card.get("next_sentence")),
            "em": clean(card.get("typical_error_mode")),
            "ef": card.get("exam_frequency") or 0,
            "q": {
                "c": q["correct"],
                "d": [[d.get("text", ""), clean(d.get("explanation"))] for d in ds],
            },
        })

    # ---- 句卡 ----
    for cid, q in sent_quiz.items():
        card = sent_cards.get(cid)
        ds = q.get("distractors") or []
        if card is None or not q.get("correct") or len(ds) < 3:
            continue
        cards.append({
            "id": cid,
            "t": "s",
            "cl": clean(card["classical_sentence"]),
            "fe": clean(card.get("full_english")),
            "sw": clean(card.get("source_work")),
            "pv": clean(card.get("prev_sentence")),
            "nx": clean(card.get("next_sentence")),
            "st": clean(card.get("sentence_type")),
            "ef": card.get("exam_frequency") or 0,
            "q": {
                "c": q["correct"],
                "d": [[d.get("text", ""), clean(d.get("explanation"))] for d in ds],
            },
        })

    # ---- 篇章索引（读 course_cards_v2 全量 654 句） ----
    quizzable = {c["id"] for c in cards}
    word_by_cl, sent_by_cl = {}, {}
    for c in word_cards.values():
        word_by_cl.setdefault(c["classical_sentence"], []).append(c)
    for c in sent_cards.values():
        sent_by_cl[c["classical_sentence"]] = c
    works = build_works(quizzable, word_by_cl, sent_by_cl)

    payload = {
        "v": DATA_VERSION,
        "nWordCard": len(word_cards),
        "nSentCard": len(sent_cards),
        "cards": cards,
        "works": works,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("// 由 scripts/build_web_demo_data.py 生成，勿手改\n")
        f.write("window.GUWEN=")
        f.write(body)
        f.write(";\n")

    n_word = sum(1 for c in cards if c["t"] == "w")
    n_sent = len(cards) - n_word
    n_all_sent = sum(len(w["s"]) for w in works)
    n_blocks = sum(len(w["m"]) for w in works)
    tier = {1: 0, 2: 0, 3: 0}
    for w in works:
        tier[w["lv"]] += 1
    print(f"卡片总数 {len(cards)}（词 {n_word} + 句 {n_sent}）")
    print(f"词卡源 {payload['nWordCard']} / 句卡源 {payload['nSentCard']}")
    print(f"篇目 {len(works)} 篇 / {n_all_sent} 句 / 白话块 {n_blocks} 个")
    print(f"分档：重点 {tier[1]} / 次重点 {tier[2]} / 普通 {tier[3]}")
    print(f"输出 {OUT}  {os.path.getsize(OUT) / 1024 / 1024:.2f} MB")

    bad = 0
    # 自检 1：可出题数不该少于 iOS 侧断言的 1,346。
    # 网页版会持续入库新篇，这里只能是下界；写等号会在每次加篇后误报。
    if len(cards) < 1346:
        print(f"警告：可出题数 {len(cards)} 少于 iOS 侧断言的 1346（卡被删了？）",
              file=sys.stderr)
        bad = 1
    # 自检 2：篇章必须覆盖全库，篇/句数同理只能是下界（基线 25 / 654）
    if len(works) < 25 or n_all_sent < 654:
        print(f"警告：篇目 {len(works)} / 句数 {n_all_sent}，少于基线 25 / 654",
              file=sys.stderr)
        bad = 1
    # 自检 3：ps 累加必须正好覆盖本篇句数（前端靠它切段）
    for w in works:
        if sum(w["ps"]) != len(w["s"]):
            print(f"警告：{w['t']} 的 ps 累加 {sum(w['ps'])} != 句数 {len(w['s'])}", file=sys.stderr)
            bad = 1
    # 自检 4：每张卡都必须能通过某篇某句找到，否则篇内刷题会漏题
    reachable = set()
    for w in works:
        for s in w["s"]:
            reachable.update(s["w"])
            if s["q"]:
                reachable.add(s["q"])
    if reachable != quizzable:
        print(f"警告：{len(quizzable - reachable)} 张卡在篇章索引里找不到", file=sys.stderr)
        bad = 1
    return bad


if __name__ == "__main__":
    sys.exit(build())

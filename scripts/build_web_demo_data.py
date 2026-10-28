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
DATA_VERSION = 6


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

    payload = {
        "v": DATA_VERSION,
        "nWordCard": len(word_cards),
        "nSentCard": len(sent_cards),
        "cards": cards,
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
    print(f"卡片总数 {len(cards)}（词 {n_word} + 句 {n_sent}）")
    print(f"词卡源 {payload['nWordCard']} / 句卡源 {payload['nSentCard']}")
    print(f"输出 {OUT}  {os.path.getsize(OUT) / 1024 / 1024:.2f} MB")

    # 自检：与 iOS 侧验收测试断言的 1,346 对齐
    if len(cards) != 1346:
        print(f"警告：可出题数 {len(cards)} 与 iOS 侧断言的 1346 不一致", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(build())

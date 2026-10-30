# -*- coding: utf-8 -*-
"""生成 web-demo/dict.js —— 只覆盖题库出现过的英文词的离线英汉词库。

# 为什么是离线词库

答案页想支持「点英文单词看释义」。有道没有对网页开放的免费接口，有道智云的
API 要 appKey/appSecret，而密钥放前端等于公开（F12 就能看到），必须有后端代理，
可这是个纯静态站。

更硬的约束是这个 App 承诺「地铁里、飞行模式下也能刷」：词典一旦要联网，断网
时点词就废了。所以释义走离线，只有发音是联网优先（见 index.html 的 P4-b）。

# 词表从哪来

不猜、不用通用词表，直接从 web-demo/data.js 里把实际出现过的英文 token 抽出
来：题库 4.3 万个 token，unique 只有 2,886 个。全量 ECDICT 有 66 MB，只留这些
词之后约 200 KB。

# 用法

    python scripts/build_dict.py --ecdict /path/to/ecdict.csv

数据源：ECDICT（MIT 许可）https://github.com/skywind3000/ECDICT
国内直连 GitHub 常常不通，可用镜像：
    https://ghfast.top/https://raw.githubusercontent.com/skywind3000/ECDICT/master/ecdict.csv
"""

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_JS = os.path.join(ROOT, "web-demo", "data.js")
OUT = os.path.join(ROOT, "web-demo", "dict.js")

# 必须与 index.html 里的 WORD_RE 逐字一致。
# 漏了连字符，thousand-li 会被拆成两个半词，两边都查不到；漏了撇号，
# Zhao's 就永远查不出 Zhao —— 这类错最难查，所以两个文件里各写一份，
# check_mobile.py 会把两边的源串取出来比对。
WORD_RE = re.compile(r"[A-Za-z]+(?:['\u2019-][A-Za-z]+)*")

# 每条释义最多留这么多字。手机上浮卡只有 240 宽，超了会被截断，
# 与其让用户看到「...」不如只给最常用的两个义项。
GLOSS_MAX = 56


def load_corpus_texts():
    """从 data.js 里取出所有英译文（卡片 fe + 篇目每句的 e）"""
    with open(DATA_JS, encoding="utf-8") as f:
        src = f.read()
    head = "window.GUWEN="
    i = src.index(head)
    payload = json.loads(src[i + len(head):].strip().rstrip(";"))

    texts = [c.get("fe", "") for c in payload["cards"]]
    for w in payload.get("works", []):
        for s in w.get("s", []):
            texts.append(s.get("e", ""))
    return texts


def token_stats(texts):
    cnt = Counter()
    cap = Counter()      # 只在大写形式出现过几次（判专名用）
    for t in texts:
        for m in WORD_RE.finditer(t):
            w = m.group(0).lower()
            cnt[w] += 1
            if m.group(0)[0].isupper():
                cap[w] += 1
    return cnt, cap


# [计] [医] [化] 这类领域标签：正文有用，标签本身没用，去掉标签留内容。
# 但整行只有标签没有正文的（"网络释义"那种）要整行丢掉，见下。
DOMAIN_TAG = re.compile(r"^\[[^\]]{1,6}\]\s*")


def clean_gloss(translation):
    """ECDICT 的 translation 是多行、带词性前缀的，压成一行短释义。

    坑：ecdict.csv 里的换行是**字面量** \\n 两个字符，不是真换行（CSV 字段里
    保存的是转义后的文本）。只按 "\\n" 切会把三行释义连成一整句，
    浮卡上就是「如果, 是否, 无论何时, 假设, 即使\\nn. 条件\\n[计] DOS 批处理…」。
    """
    t = (translation or "").replace("\\r\\n", "\n").replace("\\r", "\n").replace("\\n", "\n")
    lines = [x.strip() for x in t.split("\n")]
    lines = [x for x in lines if x]
    if not lines:
        return "", ""

    pos = []
    keep = []
    for line in lines:
        if line.startswith("[网络]"):
            continue                      # 网络释义噪音太大，不用
        line = DOMAIN_TAG.sub("", line).strip()   # 去掉 [计]/[医] 前缀，留下正文
        if not line:
            continue
        m = re.match(r"^([a-z]+\.(?:\s*&\s*[a-z]+\.)*)\s*(.*)$", line)
        if m:
            tag, body = m.group(1), m.group(2).strip()
            for t in re.findall(r"[a-z]+\.", tag):
                if t not in pos:
                    pos.append(t)
            if body:
                keep.append(body)
        else:
            keep.append(line)

    # 同一义项常在不同行重复出现（"条件"、"条件"），去重后浮卡才不啰嗦
    seen = set()
    keep = [x for x in keep if not (x in seen or seen.add(x))]

    if not keep:
        return "/".join(pos[:2]), ""

    gloss = "；".join(keep[:2])
    gloss = re.sub(r"\s+", " ", gloss).strip()
    # 太长的只留第一个分句，别在手机上截成半句
    if len(gloss) > GLOSS_MAX:
        first = gloss.split("；")[0]
        if len(first) > GLOSS_MAX:
            # 在标点处断开，实在没有标点才硬切 —— 硬切容易切出半个词
            cut = max(first.rfind("，", 0, GLOSS_MAX), first.rfind(",", 0, GLOSS_MAX),
                      first.rfind("、", 0, GLOSS_MAX))
            first = first[:cut] if cut > GLOSS_MAX // 2 else first[:GLOSS_MAX - 1]
        gloss = first if len(first) <= GLOSS_MAX else first[:GLOSS_MAX - 1] + "…"
    return "/".join(pos[:2]), gloss    # 词性最多两个，多了浮卡第一行会挤爆


def wrap_ipa(phonetic):
    p = (phonetic or "").strip().strip('"')
    if not p:
        return ""
    if p.startswith("/") or p.startswith("["):
        return p
    return "/" + p + "/"


def load_ecdict(path, need):
    """扫一遍 ECDICT，只留需要的词，并顺手建「变形 → 原形」的反查表。

    为什么要第二遍逻辑：demoted 这种词在 ECDICT 里根本没有独立词条，
    它是 demote 的 exchange 字段（p:demoted/d:demoted/...）里的一条。
    所以看某行时要反过来问：它的变形有没有命中我们的词表？
    """
    entries = {}
    lemma = {}
    total = 0

    with open(path, encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            total += 1
            w = (row.get("word") or "").strip()
            if not w:
                continue
            lw = w.lower()

            hit_self = lw in need
            forms = []
            ex = (row.get("exchange") or "").strip()
            if ex:
                for part in ex.split("/"):
                    if ":" in part:
                        forms.append(part.split(":", 1)[1].strip().lower())
            hit_form = [x for x in forms if x in need]

            if not hit_self and not hit_form:
                continue

            pos, gloss = clean_gloss(row.get("translation"))
            entry = (wrap_ipa(row.get("phonetic")), pos, gloss)
            # 同一个词可能有多行（大小写不同/词条重复），留信息量最大的那条
            if hit_self:
                old = entries.get(lw)
                if old is None or (not old[2] and gloss):
                    entries[lw] = entry
            for x in hit_form:
                lemma.setdefault(x, lw)
                # 原形本身也存一份：点了 demoted 要显示 demote 的释义
                if lw not in entries or not entries[lw][2]:
                    entries[lw] = entry

    print(f"ECDICT 行数 {total:,}，命中词条 {len(entries):,}，变形映射 {len(lemma):,}")
    return entries, lemma


# 运行期不做词形还原（us→u、was→wa 会给出更离谱的释义）。
# 这里只是为了补 ECDICT exchange 漏掉的那点，按顺序试。
SUFFIX = [
    ("'s", ""), ("\u2019s", ""),
    ("ies", "y"), ("ied", "y"), ("ier", "y"), ("iest", "y"),
    ("ing", ""), ("ing", "e"), ("ed", ""), ("ed", "e"), ("es", ""),
    ("s", ""), ("ly", ""), ("er", ""), ("est", ""),
]


def guess_base(word, known):
    for suf, rep in SUFFIX:
        if word.endswith(suf):
            cand = word[: len(word) - len(suf)] + rep
            if cand in known:
                return cand
            # 双写辅音：stopped → stop
            if len(cand) > 2 and cand[-1] == cand[-2]:
                if cand[:-1] in known:
                    return cand[:-1]
    return None


def build_rows(cnt, cap, entries, lemma):
    rows = []
    unresolved = []
    known = set(entries) | set(lemma)
    for w, n in cnt.most_common():
        ipa = pos = gloss = ""
        base = ""

        e = entries.get(w)
        if e:
            ipa, pos, gloss = e
        elif w in lemma and lemma[w] in entries:
            base = lemma[w]
            ipa, pos, gloss = entries[base]
        else:
            gb = guess_base(w, known)
            if gb and entries.get(gb):
                ipa, pos, gloss = entries[gb]
                base = gb if gb != w else ""
            if not gloss:
                # 复合词（thousand-li、yi-wu）：拆开查第一个查得到的部分
                for part in re.split(r"[-'\u2019]", w):
                    if part and part in entries and entries[part][2]:
                        ipa, pos, gloss = entries[part]
                        break

        if not gloss:
            # 专名兜底：整首都大写、出现两次以上，八成是秦/赵/蔺相如这类。
            # 显示「人名/地名」比显示「未收录」有用得多。
            if n >= 2 and cap[w] == n:
                pos, gloss = "专名", "人名 / 地名音译"
            else:
                unresolved.append((w, n))
                continue

        if base == w:
            base = ""
        rows.append((w, ipa, pos, gloss, base))

    return rows, unresolved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ecdict", default=os.environ.get("ECDICT_CSV", ""),
                    help="ECDICT 的 ecdict.csv 路径")
    args = ap.parse_args()

    if not args.ecdict or not os.path.exists(args.ecdict):
        print("找不到 ecdict.csv。先下载（GitHub 直连常不通，用镜像）：", file=sys.stderr)
        print("  curl -L https://ghfast.top/https://raw.githubusercontent.com/"
              "skywind3000/ECDICT/master/ecdict.csv -o ecdict.csv", file=sys.stderr)
        return 1

    texts = load_corpus_texts()
    cnt, cap = token_stats(texts)
    # 撇号所有格：语料里是 sovereign's，运行期 lookupWord 会先去掉 's 再查，
    # 所以构建期必须把去壳后的词也加进 need，否则 ECDICT 里明明有 sovereign，
    # 这里却因为 need 里只有 sovereign's 而把它整行跳过 → 点词显示「未收录」。
    need = set(cnt) | {w[:-2] for w in cnt
                       if w.endswith("'s") or w.endswith("\u2019s")}
    print(f"题库 token {sum(cnt.values()):,}，unique {len(cnt):,}"
          f"（含去壳 {len(need):,}）")

    entries, lemma = load_ecdict(args.ecdict, need)
    rows, unresolved = build_rows(cnt, cap, entries, lemma)

    raw = "\n".join("\t".join(r) for r in rows)
    header = (
        "/* 自动生成，勿手改 —— 见 scripts/build_dict.py\n"
        "   数据源 ECDICT（MIT 许可）：https://github.com/skywind3000/ECDICT\n"
        "   只收录题库里出现过的英文词；格式 word\\tipa\\tpos\\tgloss\\tlemma */\n"
    )
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("window.GUWEN_DICT=")
        f.write(json.dumps({"v": 1, "n": len(rows), "raw": raw}, ensure_ascii=False))
        f.write(";\n")

    size = os.path.getsize(OUT)
    print(f"收录 {len(rows):,} 词，未收录 {len(unresolved):,}，输出 {OUT}  {size / 1024:.0f} KB")

    if unresolved:
        sample = "、".join(w for w, _ in unresolved[:12])
        print(f"未收录示例：{sample}")

    # 自检：词表必须覆盖 token 的绝大部分，否则说明 ECDICT 没读对
    covered = sum(cnt[w] for w, *_ in rows) / max(1, sum(cnt.values()))
    print(f"token 覆盖率 {covered * 100:.1f}%")
    if covered < 0.9:
        print("警告：覆盖率低于 90%，检查 ECDICT 是否完整", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

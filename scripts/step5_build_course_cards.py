"""Stage A: split course texts into sentence-level cards with paragraph-aligned translation.

Source : github abdulle-sabaf/yuwen  src/中学/中学古文阅读课文.json
         (85 课文, metadata + content.raw / translation / text)
         fetched via gh-proxy.com into D:/guwen-env/.tmp/yuwen_gw.json

Why paragraph alignment, not sentence alignment:
  the repo gives ONE translation block per paragraph, with the same paragraph
  count as the source (verified for all 85 texts).  A paragraph usually holds
  several sentences, so a per-sentence translation does NOT exist in the source.
  We therefore fan the paragraph translation out to each sentence and mark it
  `translation_scope: "段"`, keeping the paragraph index so the UI can group.
  Sentences are never paired with a translation from another paragraph.

Fields (strict order):
  classical, modern, source_work, author, prev_sentence, next_sentence,
  char_length, para_index, translation_scope
"""
import json
import re
import sys

SRC = "D:/guwen-env/.tmp/yuwen_gw.json"
OUT_JSONL = "E:/Users/asus/workbuddy/guwen-project/data/course_cards.jsonl"
OUT_AUDIT = "E:/Users/asus/workbuddy/guwen-project/data/course_cards_audit.txt"

# 课内标题 -> yuwen 仓库 key（用户 25 篇；陈情表仓库内确实没有）
TITLE2KEY = [
    ("岳阳楼记", "yueyanglouji"),
    ("醉翁亭记", "zuiwengtingji"),
    ("出师表", "chushibiao"),
    ("桃花源记", "taohuayuanji"),
    ("小石潭记", "xiaoshitanji"),
    ("曹刿论战", "caoguilunzhan"),
    ("论语十二章", "lunyu1"),
    ("劝学", "quanxue"),
    ("师说", "shishuo"),
    ("赤壁赋", "chibifu"),
    ("阿房宫赋", "epanggongfu"),
    ("六国论", "liuguolun"),
    ("过秦论", "guoqinlun"),
    ("廉颇蔺相如列传", "lianpo"),
    ("陋室铭", "loushiming"),
    ("爱莲说", "ailianshuo"),
    ("三峡", "sanxia"),
    ("记承天寺夜游", "chengtiansi"),
    ("马说", "mashuo"),
    ("鱼我所欲也", "yuwosuoyu"),
    ("邹忌讽齐王纳谏", "zouji"),
]

MIN_LEN, MAX_LEN = 4, 50
CJK = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
FOOTNOTE = re.compile(r"<footnote:[^>]*>")
# 分句：在句末标点后断开，保留标点与后引号/后括号
SPLIT = re.compile(r"(?<=[。！？；])|(?<=[。！？；][”’」』）])")


def cjk_len(s):
    return len(CJK.findall(s or ""))


def clean(s):
    return FOOTNOTE.sub("", s or "").strip()


def split_sentences(para):
    parts = [p.strip() for p in SPLIT.split(para) if p and p.strip()]
    return [p for p in parts if p]


def n_ends(text):
    """句末标点数量：用来判断译文能否与原文句级一一对应。"""
    return len(re.findall(r"[。！？]", text or ""))


def align_paragraph(rp, tp):
    """返回 [(句子, 该句译文 or None, 对齐粒度)]。

    优先做句级对齐：原文段句末标点数 == 译文段句末标点数时，按标点位置
    逐句配对（很多篇目的译文就是逐句翻的）。对不上则退回段落对齐：
    整段译文发给段内每一句，translation_scope='段'，绝不猜测哪句对应哪句。
    """
    sents = split_sentences(rp)
    if not sents:
        return []
    if n_ends(rp) == n_ends(tp):
        trs = split_sentences(tp)
        if len(trs) == len(sents):
            return [(s, t, "句") for s, t in zip(sents, trs)]
    return [(s, tp, "段") for s in sents]


def main():
    data = json.load(open(SRC, encoding="utf-8"))
    rows, audit = [], []
    missing = []

    for title, key in TITLE2KEY:
        if key not in data:
            missing.append(title)
            continue
        item = data[key]
        meta = item["metadata"]
        raw_paras = [clean(p) for p in (item["content"]["raw"] or "").split("\n\n")]
        raw_paras = [p for p in raw_paras if p]
        tr_paras = [clean(p) for p in (item["content"].get("translation") or "").split("\n\n")]
        tr_paras = [p for p in tr_paras if p]

        if len(raw_paras) != len(tr_paras):
            audit.append(f"[段落数不一致·跳过] {title} raw={len(raw_paras)} tr={len(tr_paras)}")
            continue

        doc_rows = []
        n_sent_lv = n_para_lv = 0
        for pi, (rp, tp) in enumerate(zip(raw_paras, tr_paras)):
            for s, t, lv in align_paragraph(rp, tp):
                n_sent_lv += lv == "句"
                n_para_lv += lv == "段"
                doc_rows.append({
                    "classical": s,
                    "modern": t,
                    "source_work": meta.get("provenance") or "",
                    "author": meta.get("author") or "",
                    "para_index": pi,
                    "translation_scope": lv,
                })
        # prev/next 在本篇内按句序取相邻合格句
        kept = [r for r in doc_rows if MIN_LEN <= cjk_len(r["classical"]) <= MAX_LEN]
        for i, r in enumerate(kept):
            r["prev_sentence"] = kept[i - 1]["classical"] if i > 0 else None
            r["next_sentence"] = kept[i + 1]["classical"] if i + 1 < len(kept) else None
            r["char_length"] = cjk_len(r["classical"])
        rows.extend(kept)
        audit.append(
            f"{title:12s} 段落={len(raw_paras):3d}  切句={len(doc_rows):3d}  "
            f"保留(4-50字)={len(kept):3d}  句级译文={n_sent_lv:3d} 段级译文={n_para_lv:3d}  "
            f"书名={meta.get('provenance','')}  作者={meta.get('author','')}"
        )

    order = ["classical", "modern", "source_work", "author", "prev_sentence",
             "next_sentence", "char_length", "para_index", "translation_scope"]
    with open(OUT_JSONL, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps({k: r[k] for k in order}, ensure_ascii=False) + "\n")

    lines = ["课内篇目卡池生成审计", "=" * 78]
    lines += audit
    lines += ["", f"合计卡片 {len(rows)} 句", f"缺失篇目 {len(missing)} 个: {missing}"]
    with open(OUT_AUDIT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(audit))
    print(f"\n合计 {len(rows)} 句；缺失 {missing}")


if __name__ == "__main__":
    main()

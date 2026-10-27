# 课内篇目卡池 v2 · Step 6 交付报告

日期：2026-10-25　|　产物：`data/course_cards_v2.jsonl`（654 句 / 25 篇 / 0 问题卡）

## 本轮完成

| 事项 | 结果 |
|---|---|
| 富贵不能淫 | 新增 8 句，源《孟子·滕文公章句下·第二节》（HF 语料，自带白话+英文） |
| 生于忧患死于安乐 | 新增 5 句，源《孟子·告子章句下·第十五节》（同上） |
| 论语十二章 | 从 HF《论语》按教材 12 章锚点重建，12/12 命中，替换原"十则"版 18 句 |
| 陈情表 | 新增 44 句，原文取自维基文库（已存 `data/wiki_text_chenqingbiao.txt`） |
| 送东阳马生序 | 新增 32 句，原文取自维基文库（已存 `data/wiki_text_songdongyang.txt`） |
| 全量英文匹配 | 与 HF 97 部书语料逐句精确匹配（去标点去空白 CJK 键），221/654 句有英文 |
| 全量 title 字段 | 25 篇全部回填（修复了《韩昌黎文集》《东坡志林》书名冲突拆分） |

## 英文来源分布

- HF 语料（NiuTrans 配套 Gemini 机翻）：145 句
- AI 试译（小沃，限《陈情表》《送东阳马生序》两篇）：76 句
- 其余 433 句暂无英文（其原文出自《文选》《樊川文集》等别集，不在 HF 97 部书内）

## 字段（v2 在原 9 字段后新增 4 个）

`title`、`english`、`english_source`、`english_ambiguous`

## 遗留事项

1. **AI 试译需人工过目**：《陈情表》《送东阳马生序》的白话与英文是我按通行理解试译的，未与教材译文逐字比对，建议抽查。
2. **歧义英文 2 句**（均出自《出师表》）：同句在《三国志》与其他书中英译不同，已按"同书优先"选取，并置 `english_ambiguous=true`。
3. **英文缺口 433 句**：如需补齐，下一步可用 LLM 批量机翻（按段级 scope 整段翻译，标注 AI 来源），或接入其他英译语料。
4. 原 `course_cards.jsonl`（571 句）保留未动，v1→v2 可随时回滚。

## 复跑方式

```bash
cd E:/Users/asus/workbuddy/guwen-project
D:/guwen-env/Scripts/python.exe scripts/step6_expand_cards.py   # 重建 v2
D:/guwen-env/Scripts/python.exe scripts/_accept_check_v2.py     # 验收
```

# 专有名词对照表 + 三篇英译回改 报告

日期：2026-10-26
工作目录：`~/workbuddy/guwen-project/`
覆盖范围：出师表（24 句）、廉颇蔺相如列传（98 句）、过秦论（44 句），共 166 句

---

## 一、交付物

| 文件 | 内容 |
|---|---|
| `data/proper_noun_glossary.json` | **专名对照表**，70 条（人名 26 / 官职 18 / 地名 17 / 刑名礼俗 9），含规范英译、可接受变体、译法依据、出现位置 |
| `data/course_cards_v2.jsonl` | 三篇英译已回改（源数据，166 句中改 46 句） |
| `data/glossary_apply_log.jsonl` | 逐句变更日志（old_english → new_english + 改动理由） |
| `data/clean/18_te_after_glossary.py` | 回改后失效的 56 条 `term_english` 的补齐记录 |
| `data/translation_issues.jsonl` | 15 条问题样本，已更新 `status` / `applied_english`（10 条 fixed，5 条 open） |
| `data/course_cards_v2.bak_2026-10-26.jsonl` | 回改前备份 |

---

## 二、对照表设计

### 六条译法约定

1. **人名**：姓在前名在后，拼音连写（Lin Xiangru）；首次全名，其后可只称名（Xiangru）。
2. **封君**：战国封君一律 `Lord + 封号`（Lord Mengchang），**不作 King**。
3. **国君**：统一 `the King of + 国名`，带定冠词；句首大写。
4. **官职**：取职能对应的英文官称（Chief Secretary），**不逐字直译**。
5. **地名**：山、关、水用前置结构（Mount Xiao, the Hangu Pass）；郡县用音译＋通名（Xiang commandery）。
6. **刑名礼俗**：先译制度实质（the boiling cauldron），必要时补括注，**不作字面拆分**。

### 结构示例

```json
{
  "id": "PN030",
  "term": "长史",
  "category": "官职",
  "canonical": "Chief Secretary",
  "accept_pattern": "Chief Secretar",
  "note": "丞相／将军府属官之长，掌文书总务。原译 historiographers（史官）系按字面猜译，属误译",
  "occurrences": [64],
  "occur_count": 1,
  "in_scope": true
}
```

---

## 三、回改结果

**46 句改动**：手改 33 句 + 机械规范化 13 句。
按篇：廉颇蔺相如列传 33、出师表 7、过秦论 6。

### 三类改动

**1. 专名统一（机械规范化，13 句）**

| 专名 | 改前（并存形态） | 改后 |
|---|---|---|
| 秦王 | King Qin (12) / King of Qin (5) / king of Qin (1) | the King of Qin |
| 赵王 | King Zhao (11) / King of Zhao (4) | the King of Zhao |
| 缪贤 | Miu Xian / Miuxian | Miao Xian |

**2. 制度词纠错（手改，节选）**

| 句 | 原文 | 改前 | 改后 |
|---|---|---|---|
| #364 | 拜为上卿 | Chief Minister | a High Minister |
| #417 | 拜相如为上大夫 | Grand Minister | a Grand Master of the Highest Rank |
| #64 | 长史 | historiographers | Chief Secretaries |
| #371 | 宦者令缪贤 | Ling Miuxian（人名连读） | Miao Xian, the Chief Eunuch |
| #373 | 臣舍人相如 | My guest Xiangru | My retainer Xiangru |
| #325 | 齐有孟尝… | King Meng Chang / King Chun Shen | Lord Mengchang / Lord Chunshen |
| #421 | 西河外渑池 | west of the West River | beyond the land west of the Yellow River |
| #413 | 就汤镬 | boiled in oil | thrown into the boiling cauldron |
| #377 | 伏斧质 | kowtow on the axe blade | lie face down on the executioner's block |
| #460 | 为刎颈之交 | neck-cutting friends | friends sworn to die for each other |

**3. 硬缺陷（未译出 / 主体错置）**

| 句 | 改前 | 问题 |
|---|---|---|
| #458 | `…took off his coat, 露出上身, carried a wicker stick…` | 英文句中夹带中文 |
| #426 | `…to cut off Qin state's妄想` | 英文句中夹带中文 |
| #56 | `…in the DPRK…` | 宫廷译成「朝鲜」 |
| #431 | `赵王窃闻` → `I have privately heard` | 主语由赵王换成蔺相如 |
| #374 | `臣语曰` → `My messenger said` | 「臣」误作使者、「语」误作 said |
| #443 / #452 | 蔺相如 → `Lian Xiangru` | 把廉颇的姓拼到相如头上 |
| #55 | `The great cause…and died` | 主谓错配（大业死了） |

---

## 四、回改的连带影响与处理

改英译会让原先锚定的 `term_english` 失效。重建链路后第一轮出现 **56 条子串失效**（96.3%），集中在这三篇的专名类词项（秦/秦王/赵王/上卿/崤函/汤镬/肉袒/负荆…）。

处理方式：新增 `data/clean/18_te_after_glossary.py`，按新英文重截 56 条片段（term/meaning 不动），利用清洗模块「后载入覆盖前值」的机制自动生效，未改动 01–17 号文件。

---

## 五、验收指标

| 指标 | 目标 | 实际 |
|---|---|---|
| 专名合规率（166 句 × 命中条目） | 100% | **100%**（0 处不合规） |
| 英译句中残留中文 | 0 | **0** |
| 重复冠词（The the） | 0 | **0** |
| `term_english` 子串命中 | 100% | **1,511 / 1,511 = 100%** |
| 三篇内 `needs_revision` | 归零 | **0** |
| 全库 `needs_revision` | ≤5% | **17 / 1,511 = 1.1%** |

### 回改前后对比（抽样）

| 项 | 改前 | 改后 |
|---|---|---|
| needs_revision（全库） | 19 条 / 1.3% | 17 条 / 1.1% |
| needs_revision（三篇内） | 2 条 | **0 条** |
| 专名不合规处 | 12 处 + 4 种并存形态 | 0 |

---

## 六、遗留

**1. 未在本次范围、仍 open 的 5 条问题**

| id | 篇目 | 问题 |
|---|---|---|
| T08 | 醉翁亭记 | 滁人 → the people of Chu（与「楚」混淆） |
| T12 | 曹刿论战 | 可以一战 → one can fight（「以」凭借义丢失） |
| T13 | 鱼我所欲也 | 行道之人 → a beggar（挪用下句「乞人」） |
| T14 | 富贵不能淫 | 淫 → excessive（使动未体现） |
| T15 | 送东阳马生序 | 整段译文复用，句级对照不可用 |

**2. 全库其余 17 条 needs_revision 分布**：曹刿论战 4、六国论 3、生于忧患 3、邹忌 2、桃花源记 1、阿房宫赋 1、记承天寺 1、富贵不能淫 1、陈情表 1、醉翁亭记 1。

**3. 对照表可复用但尚未覆盖的篇目**：陈情表（郎中、洗马、东宫、太守、刺史、孝廉、秀才 7 条已入表、`in_scope=false`）、曹刿论战、六国论等。下一轮回改可直接引用现表，按「未出现条目」补齐。

**4. 结构性未解**：陈情表、送东阳马生序共 171 句仍是段级译文，需独立做句级切分（T15）。

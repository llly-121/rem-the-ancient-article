# 词项—英译对齐 最终报告（step9–13）

生成时间：2026-10-26
工作目录：`~/workbuddy/guwen-project/`

---

## 一、交付物

| 文件 | 内容 | 规模 |
|---|---|---|
| `data/term_sentence_pairs.jsonl` | **全量词项级对齐结果**（主交付） | 1,511 条 |
| `data/terms_candidates_clean.jsonl` | 按句聚合版（每句带多个词项 + term_english） | 654 句 |
| `data/term_pairs_sample.jsonl` | 200 条分层验收样本，25 篇全覆盖 | 200 条 |
| `data/clean/*.py` | 17 个清洗记录模块（可复现、可回滚） | 1,518 条记录 |
| `scripts/step10~13_*.py` | 展平 / 应用清洗 / 抽样脚本 | 4 个 |

### 主交付字段说明（term_sentence_pairs.jsonl）

```json
{
  "idx": 682,                          // 词项全局序号
  "sent_id": "c432",                   // 所属句 ID
  "title": "过秦论",                    // 篇目
  "term": "天下",                       // 词项（已清洗）
  "term_type": "双字词",                 // 单字词 / 双字词 / 三字词
  "meaning_in_this_sentence": "全国、整个天下",  // 本句义（已清洗）
  "classical_sentence": "秦孝公据崤函之固……",
  "full_english": "Duke Xiao of Qin, holding the fastness……",
  "term_english": "the world",          // 承载该词语义的英文片段
  "match_type": "substring",            // substring / MISMATCH
  "needs_revision": false,              // 英译本身是否有问题
  "note": ""                            // 问题说明 + 修改建议
}
```

---

## 二、验收指标

| 指标 | 目标 | 实际 | 结论 |
|---|---|---|---|
| 标注覆盖率 | 100% | **1,511 / 1,511 = 100%** | 通过 |
| `term_english` 为 `full_english` 子串 | 100% | **1,511 / 1,511 = 100%** | 通过 |
| `needs_revision` 比例 | ≤ 5%（方案A目标）／熔断线 20% | **19 / 1,511 = 1.3%** | 通过 |
| 双字+三字词占比 | ≥ 60%（step7/8 约定） | (746+196)/1511 = **62.3%** | 通过 |
| 篇目覆盖 | 25 篇 | **25 篇** | 通过 |

### needs_revision 下降轨迹

```
step11 首轮样本（清洗前）   29.5%   ← 触发熔断，用户裁决走方案A
方案A 执行中（第14批）      21.2%
方案A 完成（陈情表后）       6.4%
方案A 完成（全量）           1.3%   ← 终值
```

---

## 三、清洗动作统计

原始 1,518 条词项 → 清洗后 **1,511** 条（删除 7 条）。

| 动作 | 条数 | 说明 |
|---|---|---|
| keep（原样保留） | 866 | 词项与释义均无问题，仅补 term_english |
| fix（修正） | 645 | 其中 **term 改写 157 条**、**meaning 改写 645 条**（重叠） |
| del（删除） | 7 | 纯噪声，无对应真词 |

### 三类缺陷的实际处理

**1. 占位专名（原 272 条，step8 兜底规则误产）**
`（专名·待考）逗号并列的县名／邑名` 这类模板释义，实际是 `PLACE_SUFFIX` 兜底把动宾／主谓短语切片：

| 原词项 | 实际应为 | 处理 |
|---|---|---|
| 庭一湖 | 洞庭 | fix term |
| 处江湖 | 处 | fix term |
| 退亦忧 | 退 | fix term |
| 射者中 / 弈者胜 / 有亭 / 前者呼 / 阳在山 / 鸟知山 | —— | **del**（醉翁亭记 6 条） |
| 蒙（蒙恬） | 蒙恬 | fix term |
| 臣亡国 | 亡国 | fix term |
| 裂山河 | 分裂 | fix term |
| 丈之城 | 亿丈之城 | fix term |
| 自若也 | 自若 | fix term |
| 有司业 | 司业 | fix term |
| 余虽愚 / 天大寒 / 砚冰坚 / 录毕 / 既加冠 / 色愈恭 / 礼愈至 / 左佩刀 | 整句短语，补齐规范释义 | fix meaning |
| 益州 / 琅琊 / 酿泉 / 雍州 / 汉中 / 咸阳 | 真专名，补规范释义 | fix meaning |

**2. 单字多义项误植（原 333 条）**
单字词条把该字在**全书各处**的义项全塞进本句释义，与本句语义不符：

| 字 | 原释义（他句义） | 本句实际义 |
|---|---|---|
| 落 | 量词「几千万落」 | 水落（降下） |
| 举 | 被攻占「函谷举」 | 包举宇内（全部占有）／举荐（举臣秀才） |
| 衡 | 通横、梗塞 | 连衡（连横策略）／离衡（离散连横） |
| 斗 | 斗折蛇行／星宿名 | 使……相斗（斗诸侯） |
| 度 | 推测「相如度秦王」 | 法度（laws）／度长（量长短） |
| 修 | 长、高／修习 | 整治、备办（修守战之具） |
| 疾 | 劲疾、洪亮 | 病痛（疾病） |
| 曾 | 通「增」 | 不曾（未曾）／乃、竟 |
| 坐 | 因……获罪 | 坐在（坐大厦之下）／陪侍（侍坐） |
| 顾 | 只是／回头看 | 顾询（备顾问） |
| 景 | 日光／景物 | 通「影」，像影子一样 |

**3. 英译本身的问题（19 条，即终版 needs_revision）**

| idx | 篇目 | 词项 | 问题 | 建议 |
|---|---|---|---|---|
| 203 | 桃花源记 | 悉 | 未译出「都、全都」 | all were dressed like people outside |
| 269 | 曹刿论战 | 曹刿 | 人名音译错作 Cao Cuo | Cao Gui |
| 289 | 曹刿论战 | 对 | 译作 said，未体现「回答」 | replied |
| 320 | 曹刿论战 | 再 | 「一鼓作气，再而衰，三而竭」与「彼竭我盈」混作一句 | 重译该段 |
| 322 | 曹刿论战 | 鼓 | 同上，整段混译 | 重译该段 |
| 562 | 阿房宫赋 | 听 | 未直译，以 rumble 承载 | 可接受 |
| 654 | 六国论 | 斯 | 未直译，以 the effect 承载 | 可接受 |
| 662 | 六国论 | 数 | 「天数、命运」未单独体现 | victory or defeat 覆盖 |
| 663 | 六国论 | 理 | 「道理」未单独体现 | survival or ruin 覆盖 |
| 841 | 廉颇蔺相如列传 | 语 | 「臣语曰」作 My messenger said，主客错置 | I told him |
| 1007 | 廉颇蔺相如列传 | 赵王 | 「赵王窃闻」化为主语 I，主体略去 | the King of Zhao has privately heard |
| 1177 | 记承天寺夜游 | 耳 | 语气词以 Only 承载 | 可接受 |
| 1253 | 邹忌讽齐王纳谏 | 徐公 | 「徐公不若君之美」主客颠倒 | Lord Xu is not as handsome as you |
| 1276 | 邹忌讽齐王纳谏 | 寡人 | 未译出 | those who remonstrate with me |
| 1302 | 富贵不能淫 | 广居 | 曲解为 the many recognizable things | the broad dwelling（喻仁） |
| 1313 | 生于忧患 | 衡 | 通横、梗塞，以 adversity 意译 | 可接受 |
| 1314 | 生于忧患 | 征 | 「征于色」作 are expressed in words | shown in the countenance |
| 1323 | 生于忧患 | 曾 | 「曾益其所不能」曲解为「给机会」 | increase his capacity |
| 1438 | 陈情表 | 不胜 | 未单独译出，以 trembling 概括 | unable to bear the fear of dog and horse |

其中**必须返工的严重问题 6 条**：269（人名声调）、320+322（曹刿论战整段混译）、841（主客错置）、1253（徐公主客颠倒）、1323（曾益曲解）。其余为可接受的意译承载或轻微遗漏。

---

## 四、方法说明

### 清洗记录驱动架构

```
data/clean/01_yueyanglou.py ~ 17_songdongyang.py
        │  每篇一个模块，R = {idx: (action, term, meaning, term_english, note?)}
        ▼
scripts/step12_apply_clean.py
        │  importlib 动态加载全部模块 → 合并记录 → 逐条应用
        │  子串校验：te in full_english → substring，否则 MISMATCH
        ▼
data/term_sentence_pairs.jsonl（词项级）
data/terms_candidates_clean.jsonl（按句聚合）
```

**渐进式推进**：每完成一篇立即跑校验器，错误不累积。未标注项自动降级为 `needs_revision=True, note='未标注'`，不会被误判为已完成。

### 陈情表 / 送东阳马生序的特殊处理

这两篇的 `english` 是**按段复用**——同一段内每句共用同一整段英文（陈情表 5 段覆盖 93 句，送东阳 4 段覆盖 78 句）。处理方式：`term_english` 仍从该整段中截取对应小句的连续片段，因此依然是 `full_english` 的合法子串，子串校验 100% 通过。

**遗留风险**：这两篇的「句—译」并非严格一对一，若下游要按句展示英译，需再做一次句级切分（不影响本交付的 term_english 正确性）。

---

## 五、遗留事项

1. **6 条严重英译错误待返工**（见上表），返工后需重跑对应 `data/clean/*.py` 的 term_english。
2. **陈情表 / 送东阳马生序 171 句为 AI 试译**，未做质量抽查（其余 433 句已人工核对合格）。
3. **陈情表 / 送东阳马生序 段落级英译**若需句级呈现，需补一次切分。
4. `data/flat_terms.json`（step10 展平中间产物）可保留作回溯用。

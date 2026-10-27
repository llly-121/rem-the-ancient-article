# 文言文学习引擎规格（iOS 实现参考）

> 版本 v1.0 · 2026-10-27 · **全部待确认项已拍板，本文为最终实现依据**
> 调度思想参考 RetainCraft 的 FSRS-5 间隔重复逻辑（§7），但 MVP 不引入 FSRS 权重，用简化阶梯间隔（§2.4）。
> 每条规则均标注 **[测试判定]**，可直接写成单元测试断言。

---

## 0. 数据源与依赖

| 数据文件 | 规模 | 用途 |
|---|---|---|
| `data/word_cards.jsonl` | 1418 张 | 词级卡（13 字段，含 exam_frequency 1–5、typical_error_mode） |
| `data/sentence_cards.jsonl` | 654 张 | 句级卡（8 字段，含 sentence_type） |
| `data/word_quiz.jsonl` | **待生成**（样本 30 条已确认） | 词级选择题的正确项 + 3 干扰项 |
| `data/sentence_quiz.jsonl` | **待生成**（样本 30 条已确认） | 句级选择题的正确项 + 3 干扰项 |

**注意**：
- 词卡 id 形如 `w0001`，句卡 id 形如 `s0001`，可直接作主键。
- 选择题题干 = `classical_sentence`，正确项 = `correct`（词级即 `term_english`，句级即 `full_english`），干扰项 = `distractors[].text`。
- quiz 全量文件未生成前，iOS 端可先用两份 30 条样本文件联调，字段结构完全一致。

---

## 1. 卡片状态模型

### 1.1 存储字段（每张卡一条学习状态记录，与卡内容分离）

| 字段 | 类型 | 初始值 | 说明 |
|---|---|---|---|
| `id` | String | — | 即 `w0001` / `s0001` |
| `type` | Enum | — | `word` / `sentence`，随卡来源固定 |
| `consecutive_correct` | Int | 0 | 连续答对次数（常规轮次，不含默写） |
| `total_attempts` | Int | 0 | 累计作答次数（**含**常规轮次与默写） |
| `total_correct` | Int | 0 | 累计答对次数（**含**常规轮次与默写） |
| `last_seen_at` | Date? | nil | 最近一次出现在常规轮次或默写中的时间 |
| `in_mistake_book` | Bool | false | 是否已加入错题本 |
| `status` | Enum | `new` | `new` / `learning` / `mastered` |

### 1.2 派生字段（不落库，随时计算）

| 派生字段 | 公式 | 用途 |
|---|---|---|
| `error_rate` | `total_attempts > 0 ? (total_attempts - total_correct) / total_attempts : 0` | 抽题加权（§2.5） |
| `due_at` | `last_seen_at + interval(consecutive_correct)` | learning 卡是否"满足间隔"（§2.4） |

### 1.3 状态机

```
new ──首次作答──> learning ──consecutive_correct 达到 3──> mastered
                     │  ▲                                      │
                     │  └────────── 答错：归零并降回 ────────────┘
                     └─ 答错：consecutive_correct 归零，保持 learning
```

**[测试判定 S1]** 初始导入后：全部卡 `status == .new`，三个计数器均为 0，`last_seen_at == nil`。
**[测试判定 S2]** `status == .new` 的卡首次作答后（无论对错）变为 `.learning`。
**[测试判定 S3]** learning 卡答对：`consecutive_correct += 1`；达到 3 → `status == .mastered`。
**[测试判定 S4]** learning 卡答错：`consecutive_correct == 0`，`status` 保持 `.learning`。
**[测试判定 S5]** mastered 卡答错（仅可能来自错题本"再练一次"，见 §6）：`consecutive_correct == 0` 且 `status == .learning`。
**[测试判定 S6]** 词卡与句卡的状态完全独立：对同一张词卡操作不得改变任何句卡字段，反之亦然。测试时取一对 (word, sentence) 卡交叉操作后断言互不影响。

---

## 2. 每轮 20 题的构成规则

### 2.1 词句比例

- 默认词级 : 句级 = **6 : 4**（12 词 + 8 句）。
- 设置项 `word_ratio`：可调范围 **0.5 – 0.8**，步长 0.1（即 5:5 / 6:4 / 7:3 / 8:2 四档）。词级题数 = `round(20 × word_ratio)`，句级题数 = `20 − 词级题数`。

**[测试判定 R1]** 对四档 ratio 分别构造轮次：词级题数为 10/12/14/16，句级为 10/8/6/4，总数恒为 20。

### 2.2 前 5 题：全部新卡

- 第 1–5 题只从 `status == .new` 的卡中抽取，词句按 2.1 比例分摊（默认 3 词 + 2 句）。
- 抽取优先级：`exam_frequency` 降序 → 随机。

**[测试判定 R2]** 轮次前 5 题的 `status` 均为 `new`；且作答后这 5 张卡变为 `learning`。

### 2.3 第 6–20 题：到期复习卡为主，混入新卡

- 候选池 = `status == .learning` **且** `now ≥ due_at`（满足间隔）。
- 从候选池抽满 15 题；不足 15 时，用 `new` 卡补位，**混入的 new 最多 3 道**（含前 5 题后本轮 new 总数上限为 8）。
- 补满后仍不足 20 题 → **从 `mastered` 卡中以 `exam_frequency` 降序补位，此类题不计入状态流转**（P2 已拍板 = a）。

**[测试判定 R3a]** 第 6–20 题中，来自 learning 候选池的卡满足 `now ≥ due_at`。
**[测试判定 R3b]** 第 6–20 题中 new 卡数量 ≤ 3；全轮 new 卡数量 ≤ 8。
**[测试判定 R3c]** 构造 learning.due 仅有 5 张的场景：第 6–20 题中 new 卡恰为 3 道，其余按补位策略填充且不重复。

### 2.4 learning 卡的间隔（MVP 简化阶梯）

`interval(consecutive_correct)` 默认阶梯，可配置：

| consecutive_correct | 间隔 |
|---|---|
| 0（刚答错） | 10 分钟 |
| 1 | 1 天 |
| 2 | 3 天 |
| （达到 3 即 mastered，退出常规池） | — |

**[测试判定 R4]** cc=0 的卡在 `last_seen_at + 10min` 之前不满足间隔，之后满足；cc=1 / cc=2 分别按 1 天 / 3 天判定。FSRS-5 升级路径见 §7。

### 2.5 高错率加权

- 对 2.2 / 2.3 的候选卡：`error_rate > 0.5`（且 `total_attempts ≥ 3`，避免 1 错 0 对的小样本放大）的卡，抽题权重 **×2**。
- 实现口径：候选池内每张卡基础权重 1，满足条件记 2；加权随机不放回抽取。
- 作用范围：仅常规轮次抽题（§2），默写抽样不加权。

**[测试判定 R5]** 统计模拟：构造 100 张普通卡 + 100 张高错率卡，跑 1000 轮，高错率卡的单轮出现率约为普通卡的 2 倍（容差 ±20%）。

### 2.6 多字词保底

- 每轮至少 **3 道** `type == word` 且 `char_count ≥ 2` 的词级题。
- 判定字段直接用词卡的 `char_count`（= `term` 字符数，生成时已与词形一致）。

**[测试判定 R6]** 任意一轮：`round.filter { $0.type == .word && $0.charCount >= 2 }.count >= 3`。若正常抽样不足 3 道，替换掉本轮 `char_count == 1` 的词级题（优先替换 exam_frequency 最低者）直至达标。

### 2.7 轮内去重

**[测试判定 R7]** 同一轮 20 题中卡 id 无重复。

---

## 3. 常规轮次的作答与计数

| 事件 | consecutive_correct | total_attempts | total_correct | status 影响 |
|---|---|---|---|---|
| 常规题答对 | +1 | +1 | +1 | 见 S2/S3 |
| 常规题答错 | 归零 | +1 | — | 见 S4 |
| 默写判对 | 不变 | +1 | +1 | 不影响 |
| 默写判错 | 不变 | +1 | — | 不影响 |
| 错题本"再练一次"答对/答错 | **不变** | +1 | 按结果 | **不变**（P8 已拍板 = b：只计次数，不动连对） |

- 每次作答后刷新 `last_seen_at = now`。
- 选择题判分：选中 `correct` 为对，选中任一 `distractors[].text` 为错，自动判分。

**[测试判定 A1]** 一张新卡经历"对、对、错、对、对、对"六次常规作答：cc 序列为 1,2,0,1,2,3，最终 `status == .mastered`，`total_attempts == 6`，`total_correct == 5`。
**[测试判定 A2]** 该卡再经历一次默写判错：`total_attempts == 7`，`total_correct` 不变，`consecutive_correct` 与 `status` 不变（不降级）。

---

## 4. 检查环节（每轮默写）

### 4.1 触发与抽样

- 第 20 题作答完成后，立即弹窗进入默写环节，抽 **10 题**。
- 抽样池 = 本轮 20 题；默认规则：**优先抽本轮答错的题，不足 10 道按 `exam_frequency` 降序随机补齐**；词句比例跟随本轮（不强制）。（P6 已拍板 = a）

### 4.2 默写形态

| 卡型 | 题面 | 要求输入 | 正确答案 |
|---|---|---|---|
| 词级 | `term` + 所在句 `classical_sentence` | 英文短语 | `term_english` |
| 句级 | `classical_sentence` | 完整英文句 | `full_english` |

### 4.3 提示按钮

- 点击后显示正确答案的**前 2 个字母**：取 `correct` 中前 2 个 `[A-Za-z]` 字符（跳过开头的引号、空格、冠词处理不特殊化，仅按字符序取），保留原始大小写。
- 可多次点击不重复显示；不提供后续字符；**用提示判对的题只计 `total_attempts`、不计 `total_correct`**（P9 已拍板 = b）。

**[测试判定 H1]** correct = `"the boiling cauldron"` → 提示显示 `th`；correct = `"'I told him: ..."`（首字符为引号）→ 显示 `It`。

### 4.4 默写判分

- 词级：输入去除首尾空格、忽略大小写后与 `term_english` 全等 → 对；**额外忽略开头冠词 the / a / an**（P7 已拍板 = b）。同义改写不做，v2 需同义词表再议。
- 句级：MVP 采用**自评按钮**（对 / 错，界面并列展示用户输入与正确答案）（P10 已拍板 = a）；相似度自动判分列入 v2。
- 判分结果**只**计入 `total_attempts` / `total_correct`，不影响 `consecutive_correct` 与 `status`（§3 A2）。

**[测试判定 C1]** 默写 10 题 → 本轮全部卡的 `total_attempts` 增量之和为 10；`consecutive_correct` 与 20 题答完后的快照完全一致。

---

## 5. 错题本

- **加入**：每题答案页有"加入错题本"按钮（无论答对答错均可加入）；重复加入置顶不新增记录。记录字段：`card_id`、`added_at`。
- **列表**：词卡、句卡统一列表；`type == word` / `sentence` 用不同图标区分；条目显示题面 + `source_work`。
- **筛选**：按 `source_work` 下拉筛选（取值为该卡 source_work 全文，如「岳阳楼记（《范文正公集》卷七）」）。
- **排序**：按 `added_at` 降序（最近加入在最上）。
- **再练一次**：单卡立即重出该题（选择题形态，同一 correct + 3 干扰项可随机重排）。计数规则（P8 已拍板 = b）：计入 `total_attempts` / `total_correct`，**不影响** `consecutive_correct` 与 `status`。

**[测试判定 M1]** 加入 3 张卡（2 词 1 句）：列表 3 条，词图标 2、句图标 1，按加入时间降序。
**[测试判定 M2]** 重复加入同一卡：列表仍 1 条，`added_at` 更新为最新时间并置顶。
**[测试判定 M3]** 按「岳阳楼记」筛选：仅剩 source_work 前缀匹配该篇的条目。

---

## 6. 全局约束

- mastered 卡**不进常规抽题池**（§2 候选池只有 new / learning.due），但保留在默写与错题本路径中。
- 全库 2072 张卡（1418 + 654）随包内置为只读题库；学习状态记录独立存储，可整体导出/清除。

---

## 7. 与 FSRS-5 的关系（v2 升级路径）

MVP 用 §2.4 的固定阶梯；数据积累后可平滑升级为 FSRS-5：

| 概念 | MVP | FSRS-5 |
|---|---|---|
| 记忆状态 | `consecutive_correct`（0–3） | Stability S、Difficulty D |
| 间隔 | 固定阶梯 [10min, 1d, 3d] | `I(r, S) = (S/f × (r^(1/DECAY) − 1) + 1)`，DECAY=−0.5，f=19/81 |
| 评分 | 对/错二元 | 四级 Again/Hard/Good/Easy |
| 默认权重 | 无 | w[0..18] = 0.40255, 1.18385, 3.173, 15.69105, 7.1949, 0.5345, 1.4604, 0.0046, 1.54575, 0.1192, 1.01925, 1.9395, 0.11, 0.29605, 2.2698, 0.2315, 2.9898, 0.51655, 0.6621 |
| 参数个性化 | 无 | ≥1000 条复习记录后可用梯度下降优化（RetainCraft `optimize-params` 同款流程，建议每 2–3 个月一次） |

升级时只需替换 `interval()` 实现并把二元判分映射为 Again（错）/ Good（对）；状态字段与抽题规则不变。参考：RetainCraft（github.com/kaixiad/RetainCraft）的 FSRS-5 调度与个性化参数流程。

---

## 8. 伪代码：抽 20 题完整调度

```swift
// 依赖：cards（全库）、progress（状态记录，按 id 索引）、config（word_ratio 等）
func pickRound(now: Date) -> [Card] {
    var round: [Card] = []

    // 1. 词句比例
    let nWord = Int((20.0 * config.wordRatio).rounded())   // 默认 12
    let nSent = 20 - nWord                                  // 默认 8

    // 2. 候选池划分
    func pool(_ type: CardType, _ pred: (Progress) -> Bool) -> [Card] {
        cards.filter { $0.type == type && pred(progress[$0.id]!) }
    }
    let weighted: ([Card]) -> [(Card, Double)] = { list in
        list.map { c in
            let p = progress[c.id]!
            let w = (p.totalAttempts >= 3 && p.errorRate > 0.5) ? 2.0 : 1.0  // R5
            return (c, w)
        }
    }
    var newWord    = pool(.word,     { $0.status == .new })
    var newSent    = pool(.sentence, { $0.status == .new })
    var dueWord    = pool(.word,     { $0.status == .learning && now >= $0.dueAt })
    var dueSent    = pool(.sentence, { $0.status == .learning && now >= $0.dueAt })

    // 3. 前 5 题：全 new（R2），按比例分摊（3 词 + 2 句）
    let headWord = min(3, nWord), headSent = min(2, nSent)
    round += sampleWeighted(weighted(newWord), headWord); round += sampleWeighted(weighted(newSent), headSent)

    // 4. 第 6–20 题：learning.due 优先（R3a），new 混入 ≤3（R3b）
    let tailWord = nWord - round.wordCount, tailSent = nSent - round.sentCount
    var tail: [Card] = []
    tail += sampleWeighted(weighted(dueWord), tailWord)   // 加权随机不放回
    tail += sampleWeighted(weighted(dueSent), tailSent)

    let newQuota   = max(0, 3 - 0)                        // 尾段 new 上限 3
    let shortage   = (tailWord + tailSent) - tail.count
    if shortage > 0 {
        tail += sampleWeighted(weighted(newWord + newSent), min(newQuota, shortage))
    }
    if tail.count < tailWord + tailSent {
        tail += fillFromMastered(exclude: round + tail, need: (tailWord + tailSent) - tail.count)  // P2 默认补位
    }
    round += tail

    // 5. 多字词保底（R6）：char_count≥2 的词级题 ≥3，不足则替换单字词
    round = ensureMultiCharWords(round, minCount: 3)

    // 6. 轮内去重校验（R7）
    assert(Set(round.map(\.id)).count == 20)

    return round.shuffled()   // 输出顺序仅前 5 题需保持 new 在前，其余打乱
}

func ensureMultiCharWords(_ round: [Card], minCount: Int) -> [Card] {
    var r = round
    var multi = r.filter { $0.type == .word && $0.charCount >= 2 }
    if multi.count >= minCount { return r }
    // 从单字词卡中换出，换入卡须不在本轮且满足原槽位来源约束
    let singles = r.filter { $0.type == .word && $0.charCount == 1 }
                     .sorted { progress[$0.id]!.examFrequency < progress[$1.id]!.examFrequency }
    for s in singles {
        let rep = pickReplacement(of: s, exclude: r)      // 优先 learning.due，其次 new
        guard let rep = rep else { break }
        r[r.firstIndex(of: s)!] = rep
        multi = r.filter { $0.type == .word && $0.charCount >= 2 }
        if multi.count >= minCount { break }
    }
    return r
}
```

---

## 9. 待确认参数（✅ 已全部拍板，2026-10-27，本文为最终依据）

| # | 参数 | 拍板结果 |
|---|---|---|
| P1 | 词句比例调节粒度 | **四档滑块**（0.5 / 0.6 / 0.7 / 0.8），不做任意值 |
| P2 | new + learning.due 不足 20 时的补位 | **a**：从 `mastered` 卡按 `exam_frequency` 降序补位，此类题不计入状态流转 |
| P3 | learning 卡间隔阶梯 | **[10min, 1d, 3d]**（文言短期重复优先） |
| P4 | 同一轮是否允许同卡重复 | **不允许**（维持 R7） |
| P5 | error_rate 加权门槛 | **`> 0.5` 且 `total_attempts ≥ 3`**（防小样本误加权） |
| P6 | 默写 10 题抽样 | **a**：优先本轮答错，不足按 `exam_frequency` 降序补齐 |
| P7 | 词级默写容差 | **b**：忽略大小写、首尾空格 + 开头冠词 the/a/an；不做同义改写 |
| P8 | 错题本"再练一次"的计数 | **b**：计入 `total_attempts` / `total_correct`，不影响 `consecutive_correct` 与 `status` |
| P9 | 使用"提示"是否影响默写计分 | **b**：用提示判对只计 `total_attempts`，不计 `total_correct` |
| P10 | 句级默写判分方式 | **a**：自评按钮；编辑距离判分列入 v2 |
| P11 | mastered 卡重置 | **提供**：错题本/统计页加"重新学习"入口，清零全部计数回 `new` |
| P12 | quiz 全量交付时间 | **先用 30 条样本联调**；全量按 exam_frequency 5/4 档分批交付 |

---

## 附：验收断言汇总（可直接转为 XCTest）

| 编号 | 断言 |
|---|---|
| S1–S6 | 状态机与词句独立性（§1.3） |
| R1–R7 | 抽题规则：比例、前5新卡、尾段上限、间隔、加权、多字词保底、去重 |
| A1–A2 | 计数与默写不影响 consecutive_correct |
| H1 | 提示按钮取前 2 个字母（含跳过引号） |
| C1 | 10 道默写只动 total_attempts/total_correct |
| M1–M3 | 错题本图标、置顶、source_work 筛选 |

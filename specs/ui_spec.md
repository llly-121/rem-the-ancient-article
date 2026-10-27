# 文言文学习 App · SwiftUI 界面规格

> 版本 v1.0 · 2026-10-27 · 与 `specs/learning_engine.md` v1.0 配套 · **全部待确认项已拍板，本文为最终实现依据**
> v1.0 变更：P4/P6/P7 + 剩余全部待确认项拍板落地；进度指示改为 20 段方块分格（P9）
> 四个页面：选择题页、答案展示页、检查默写页、错题本页。
> 每页固定三段：**数据来源** / **状态变化** / **跳转**，可直接转成 ViewModel 的输入输出约定。

---

## 0. 数据来源总览

| 数据 | 文件 | 字段 |
|---|---|---|
| 词级卡 | `data/word_cards.jsonl`（1418） | `id, term, char_count, term_type, meaning_in_this_sentence, term_english, full_english, classical_sentence, source_work, prev_sentence, next_sentence, typical_error_mode, exam_frequency` |
| 句级卡 | `data/sentence_cards.jsonl`（654） | `id, classical_sentence, full_english, source_work, prev_sentence, next_sentence, sentence_type, exam_frequency` |
| 选择题干扰项 | `data/word_quiz.jsonl` / `sentence_quiz.jsonl`（全量待生成） | `correct`, `distractors[3]{text, error_type, explanation}` |

App 启动时把三个文件解析为只读题库 `CardStore`；学习状态（`consecutive_correct` 等 8 字段）由 `ProgressStore` 单独持久化，与题库解耦。

---

## 1. 设计令牌

### 1.1 颜色

| Token | 值 | 用途 |
|---|---|---|
| `bg` | `#F5E6D3` | 主背景（宣纸色） |
| `surface` | `#FFFBF4` | 卡片/输入框底色（比 bg 亮一档） |
| `accent` | `#C97B4A` | 强调色：选中边框、高亮底色、主按钮填充、对勾 |
| `textPrimary` | `#3E2C1E` | 正文、古文 |
| `textSecondary` | `#7A6552` | 出处、时间、辅助说明 |
| `errorTone` | `#8B7A8B` | 错误反馈（柔和灰紫），禁止使用高对比红 |
| `divider` | `#E3D3BF` | 分割线、未选中卡片描边 |

**硬性约束**：全 App 不出现 `Color.red` / `Color.green`。正确＝`accent` 细边框＋对勾；错误＝`errorTone` 细边框＋叉号，均为 **1.5pt 描边**，不做整块填色。

**P6 已拍板：`accent` 只作装饰色**——仅用于边框、底色、按钮填充、对勾、下划线，**禁止用于正文级文字**（浅色下对比度 2.8:1，不达 WCAG AA）。凡是"读的字"一律 `textPrimary` / `textSecondary`。

### 1.1b 暗色模式（P7 已拍板：做）

同一套 Token 名，浅色/深色各一组值，实现用 Asset Catalog 的 `Any/Dark` 外观变体（或 `Color(light:dark:)` 扩展），**代码中禁止硬编码色值**，一律引用 Token 名：

| Token | 浅色 | 深色（夜读） | 深色用途说明 |
|---|---|---|---|
| `bg` | `#F5E6D3` | `#2A211A` | 墨色宣纸底 |
| `surface` | `#FFFBF4` | `#3A2E24` | 卡片/输入框，比 bg 亮一档 |
| `accent` | `#C97B4A` | `#D99462` | 暗色下提亮一档，对 `bg` 深色对比度约 7:1，仍**只作装饰色** |
| `textPrimary` | `#3E2C1E` | `#F0E4D4` | 正文、古文 |
| `textSecondary` | `#7A6552` | `#B5A08C` | 出处、时间、辅助说明 |
| `errorTone` | `#8B7A8B` | `#A892A8` | 错误反馈，暗色下同步提亮 |
| `divider` | `#E3D3BF` | `#4A3B2E` | 分割线、未选中描边 |

暗色适配规则：

1. 高亮底色 `accent.opacity(0.25)` 在两套模式下通用，无需单独调色。
2. 自绘插图（§7）的画笔色引用 Token：线条用 `textSecondary`，点缀用 `accent`，两套模式自动成立，不画两版。
3. 跟随系统外观（不提供 App 内明暗开关，P7 范围内最简实现）；如后续要 App 内开关，加 `@AppStorage("appearance")` + `.preferredColorScheme` 即可，Token 不变。

### 1.2 字体

| 场景 | 字号/字重 | 字体 | 行距 |
|---|---|---|---|
| 选择题古文 | 28pt / regular | Songti SC 或 Noto Serif SC（衬线） | 1.5 |
| 默写页古文 | 32pt / regular | 同上 | 1.6 |
| 英文正确答案 | 17pt / regular | New York（衬线） | 1.4 |
| 释义正文 | 16pt / regular | 系统中文 | 1.5 |
| 辅助信息（出处、第 X/20 题） | 13pt / regular | 系统 | — |

### 1.3 尺寸与动效

| Token | 值 |
|---|---|
| 卡片圆角 | 16pt |
| 卡片内边距 | 16pt（垂直 14pt） |
| 选项间距 | 12pt |
| 页面左右边距 | 20pt |
| 进度指示 | **20 段方块分格**（P9 已拍板 = b）：每段 12×6pt、圆角 2pt、间距 4pt；已完成段 `accent` 填充，未完成 `divider` |
| 选中→答案页延迟 | **0.4s**（delay，非动画时长） |
| 选中态动画 | `easeOut(duration: 0.18)` |
| 转场 | 下一页 `.move(edge: .trailing)`，返回 `.move(edge: .leading)` |
| 最小点击区 | 44×44pt |

---

## 2. 页面一：选择题页（QuizView）

### 2.1 布局

```
┌──────────────────────────────┐
│  第 7/20 题            [退出] │  13pt textSecondary
│  ▪▪▪▪▪▪▪□□□□□□□□□□□□□□□□  │  20 段方块，已完成段 accent 填充
├──────────────────────────────┤
│                              │
│      环滁皆山也。              │  28pt 衬线，居中，行距 1.5
│                              │
├──────────────────────────────┤
│  ┌────────────────────────┐  │
│  │ All around Chu are...  │  │  选项卡：圆角16、surface底
│  └────────────────────────┘  │  选中：accent 1.5pt 边框
│  ┌────────────────────────┐  │
│  │ Chu encircles all the  │  │
│  └────────────────────────┘  │
│  ┌────────────────────────┐  │
│  │ The area around Chu... │  │
│  └────────────────────────┘  │
└──────────────────────────────┘
```

### 2.2 数据来源

- 题干 `classical_sentence`、选项文本：词级取 `word_quiz.correct` + 3 个 `distractors[].text`；句级取 `sentence_quiz.correct` + 3 个 `distractors[].text`。
- 页码：`session.roundIndex`（1…20）、`session.round.count`（20）。
- 选项顺序：**每轮进场时洗牌**，正确项位置不固定；洗牌种子随题存储，便于答案页复现同一顺序。

### 2.3 状态变化

| 用户事件 | 状态变更 | 跳转 |
|---|---|---|
| 进入页面 | `session.currentIndex = N`；若该题未洗牌则洗牌并缓存顺序 | — |
| 点击某选项 | `selectedOption = 文本`；`isLocked = true`（禁二次点击）；按 §1.3 高亮选中边框；启动 0.4s 定时 | 0.4s 后 push 答案页 |
| 0.4s 定时到 | 写入作答结果：`progress[card.id].total_attempts += 1`；对则 `total_correct += 1`、`consecutive_correct += 1`（达 3 转 `mastered`）；错则 `consecutive_correct = 0`；`last_seen_at = now`；`status` 按引擎 §1.3 流转 | 进答案页（携带判分结果） |
| 点「退出」 | 弹确认框；确认后丢弃本轮未完成进度（已作答部分保留计数） | 回首页 |

### 2.4 视觉反馈

- **未选中**：`divider` 1pt 边框，`surface` 底，文字 `textPrimary`。
- **选中**：`accent` 1.5pt 边框，底色 `accent.opacity(0.08)`，右侧出现对勾（仅答案页显示结果，选择题页不提前揭示对错）。
- 选项文字 ≥2 行时 `lineLimit(nil)`，垂直居中，字号 16pt。

**[验收 U1]** 20 题依次答完后，已填充方块段数 = 已完成题数（共 20 段），且「第 X/20 题」字符串与之一致。
**[验收 U2]** 连点两个选项：仅第一个生效，第二次点击无任何状态变化。
**[验收 U3]** 选项卡片圆角恰为 16pt、选中边框恰为 1.5pt（用 `GeometryReader` 快照断言）。

---

## 3. 页面二：答案展示页（AnswerView）

### 3.1 词级题布局（从上到下）

```
┌──────────────────────────────┐
│ 先帝在时，每与臣论此事…桓、灵也。│  28pt，term 加下划线（accent 波浪/直线 1.5pt）
├──────────────────────────────┤
│ Prior to this, whenever we... │  17pt 衬线
│ ...about Huan and Ling ▌      │  term_english 片段：accent 底色 0.25 高亮
├──────────────────────────────┤
│ ┌ 桓灵 ────────────────────┐ │
│ │ 本句义：汉桓帝、汉灵帝     │ │  释义卡：圆角16、surface 底
│ │ 其他义项：横渡（绝江河）…  │ │  13pt textSecondary 分节标题；other_senses 为空则整行隐藏
│ │ 常见错法：误作「桓、灵二帝」…│ │
│ └──────────────────────────┘ │
│ 出师表（《昭明文选》）          │  13pt textSecondary
│ 前：先帝在时…   后：未尝不叹息… │  13pt，可折叠，lineLimit 1
├──────────────────────────────┤
│  [ 加入错题本 ]  [   下一题   ] │  描边按钮 / 填充按钮
└──────────────────────────────┘
```

### 3.2 句级题布局

- 顶部改为 `classical_sentence`（28pt，**不加下划线**）。
- 中部 `full_english` **整句 accent 底色 0.25 高亮**；若 `full_english` 长度 > 400 字符（77 张段级复用卡，最长 1224），改为**分句逐行高亮**：按 `. ` 切分后每句一段、行距 1.6，可滚动，不做截断。
- 释义卡替换为「句型卡」：`sentence_type` + `exam_frequency` + 可选干扰项解析（`distractors[].explanation` 取与用户所选对应的那条）。
- 底部按钮同上。

### 3.3 数据来源

| 区块 | 字段 |
|---|---|
| 原文 | `classical_sentence` |
| 词项定位 | `term`（见 §3.5 容错规则） |
| 英译 | `full_english` |
| 词项片段高亮 | `term_english`（引擎已保证是 `full_english` 的连续子串，1418/1418 通过） |
| 释义卡 | `term`、`meaning_in_this_sentence`、`other_senses: [String]`（0–3 条，回填自同词异句义项，29.8% 的卡非空；为空时隐藏该行）、`typical_error_mode` |
| 出处 | `source_work` |
| 上下文 | `prev_sentence` / `next_sentence`（各篇首末句为 nil，此时隐藏该行） |

### 3.4 状态变化

| 用户事件 | 状态变更 | 跳转 |
|---|---|---|
| 页面出现 | 展示判分结果：正确→选项卡 `accent` 边框＋对勾；错误→用户所选卡 `errorTone` 边框＋叉号，正确项同时以 `accent` 边框标出 | — |
| 点「加入错题本」 | `progress[card.id].in_mistake_book = true`；插入 `MistakeItem(cardID, addedAt: now)`；若已存在则仅更新 `addedAt`（置顶）；按钮态变「已加入」并禁用 | 无跳转，Toast「已加入错题本」 |
| 点「下一题」 | `session.currentIndex += 1` | 若 < 20 → 回选择题页（同轮内不重建轮次）；若 == 20 → 进默写页 |
| 点前后句 | 展开为两行（`lineLimit(nil)`），再点收起 | 无跳转 |

### 3.5 词项高亮定位（必须按此实现）

1. 先做**原文精确匹配**：`classical_sentence.range(of: term)`。
2. 若失败（1418 张中 1 张，如 `w0126` 的「桓灵」在原文写作「桓、灵」），退化为**去标点匹配**：把原文与 `term` 同时剔除 `、，。；：！？「」（）` 后求位置，再把范围映射回原串。
3. 若仍失败：不画下划线，改为在释义卡显示「原句写作『桓、灵』」提示，不允许静默失败。
4. 同一句中 `term` 出现多次（34 张卡）：**全部出现处均加下划线**；`term_english` 片段只高亮 `full_english` 中**首个**匹配。

**[验收 U4]** 对 `w0126` 打开答案页：原文「桓、灵」整段加下划线，且释义卡出现「原句写作『桓、灵』」提示。
**[验收 U5]** 对任一多次出现卡（如「之」类）打开答案页：原文所有出现位置均有下划线，`full_english` 中仅一处高亮。
**[验收 U6]** 对 1224 字符的段级卡：英译区可滚动、无截断、按句分行。

---

## 4. 页面三：检查默写页（RecallView）

### 4.1 布局

```
┌──────────────────────────────┐
│  检查 3/10              [退出] │
├──────────────────────────────┤
│                              │
│      环滁皆山也。              │  32pt 衬线居中
│                              │
├──────────────────────────────┤
│ ┌──────────────────────────┐ │
│ │ All around Chu are ...   │ │  TextEditor，多行，surface 底，
│ │                          │ │  圆角16，最小高 120pt
│ └──────────────────────────┘ │
│  [ 提示 ]        [ 查看答案 ]  │  描边按钮 ×2
└──────────────────────────────┘
```

### 4.2 数据来源

- 题面：词级 `term` + `classical_sentence`（题干显示古文，要求写 `term_english`）；句级 `classical_sentence`（要求写 `full_english`）。
- 正确答案：`correct`（= `term_english` / `full_english`）。
- 抽样：由引擎 §4 给出 10 个 `cardID`，`session.recallIndex` 1…10。

### 4.3 状态变化

| 用户事件 | 状态变更 | 跳转 |
|---|---|---|
| 页面出现 | `hintUsed = false`；`input = ""`；若该题此前有草稿则恢复 | — |
| 点「提示」 | 取 `correct` 首 2 个字母（跳过非字母字符，保留大小写）**插入** `TextEditor` 末尾；`hintUsed = true`；按钮变「已使用提示」并 `disabled`；提示文案可为 `已插入：th` | 无跳转 |
| 点「查看答案」 | 进入对比态：上方只读显示用户输入与正确答案的 word-level diff（见 §4.5）；按钮区换成「对 / 错」自评（句级）或自动判分结果（词级）；写 `total_attempts += 1`，对则 `total_correct += 1`；**不改** `consecutive_correct`、**不改** `status`；`last_seen_at = now` | 停留本页，露出「下一题」 |
| 点「下一题」（对比态下） | `recallIndex += 1`；清空输入与提示状态 | < 10 → 下一题；== 10 → 默写小结页 → 回首页 |

### 4.4 判分口径（与引擎 §4.4 一致）

- 词级：输入 trim + 小写化、剥离开头冠词 the/a/an 后与 `term_english` 全等 → 对；否则错（P2 已拍板 = b，与引擎 P7 一致）。
- 句级：MVP 用「对 / 错」自评按钮，不做字符串比对。

### 4.5 差异对比渲染

以**正确答案为基准**做 word-level LCS 对齐（按空白切词，标点随词）：

- 用户输入中**不在 LCS** 的词：`textPrimary` + `.strikethrough()`（删除线）。
- 正确答案中**未被匹配**的词：`accent` 底色 0.25 高亮 + 下划线，表示遗漏。
- 用户多写的内容：单独一行「多余：xxx」，删除线。

**[验收 U7]** 正确答案 `All around Chu are mountains.`、输入 `All around Chu are hills.`：`hills` 带删除线，`mountains` 高亮加下划线。
**[验收 U8]** 点提示后按钮文案为「已使用提示」且 `disabled == true`；再点无任何变化。
**[验收 U9]** 默写 10 题后，本轮每张卡的 `total_attempts` 增量之和 == 10，`consecutive_correct` 与进入默写前快照完全一致。

---

## 5. 页面四：错题本页（MistakeBookView）

### 5.1 布局

```
┌──────────────────────────────┐
│  错题本                  [编辑] │
│  [全部 ▾]  共 27 条            │  筛选栏：全部 / 按篇目
├──────────────────────────────┤
│  〔词〕 环滁皆山也。            │  图标区分类型：词=「文」方章，句=「句」圆章
│        醉翁亭记（《欧阳文忠公集》）│  13pt textSecondary
│        3 分钟前加入            │  相对时间
├──────────────────────────────┤
│  〔句〕 先帝创业未半而中道崩殂…  │
│        出师表（《昭明文选》）    │
│        昨天加入                │
└──────────────────────────────┘
```

空状态：居中自绘「灯烛＋书卷」插图（见 §7），下方 15pt 文案「还没有错题，继续做题吧」，再下 13pt 次要文案「答案页可随时把题目收进来」。

### 5.2 数据来源

- `MistakeItem` 列表：`cardID`、`addedAt`；按 `cardID` 回查 `CardStore` 取 `classical_sentence` 摘要（`lineLimit(2)`）与 `source_work`。
- 类型图标：`card.type`（word/sentence）。
- 筛选选项：对列表内 `source_work` 去重后按出现次数降序生成；`source_work` 形如「岳阳楼记（《范文正公集》卷七）」，**筛选项显示括号前的篇名**，匹配用全文前缀。

### 5.3 状态变化

| 用户事件 | 状态变更 | 跳转 |
|---|---|---|
| 页面出现 | 读 `MistakeItem` 按 `addedAt` 降序；`filter = .all` | — |
| 切换筛选 | `filter = .work(篇名)`；列表重算 | 无跳转 |
| 左滑 | 露「删除」（`errorTone` 文字，非红色）；确认后删 `MistakeItem`，同时 `in_mistake_book = false` | 无跳转 |
| 右滑 | 露「再练一次」；点击后以该卡组一轮 1 题的小测（选择题形态，选项重新洗牌），作答计数按已拍板口径：计入 `total_attempts` / `total_correct`，不影响 `consecutive_correct` 与 `status`（P1，与引擎 P8 一致） | 进入选择题页（单题模式，`session.mode = .retrain`） |
| 点列表项 | 无（避免误触），仅滑动操作 | — |

**[验收 U10]** 加入 3 张（2 词 1 句）后列表 3 条，词图标 2 个、句图标 1 个，按时间降序。
**[验收 U11]** 左滑删除后：列表少 1 条，该卡 `in_mistake_book == false`，重新加入可恢复。
**[验收 U12]** 筛选「岳阳楼记」后仅剩该篇条目；切回「全部」恢复 27 条。

---

## 6. 导航与全局状态

```
TabView
├─ 今日  HomeView ──「开始一轮」→ RoundFlow
└─ 错题本 MistakeBookView ──右滑再练──→ QuizView(retrain)

RoundFlow（NavigationStack，独立于 Tab）
  QuizView(1…20) ──select→ AnswerView ──下一题→ QuizView / RecallView(1…10) → RecallSummary → 关闭
```

- `RoundSession`（`@Observable`）：`round: [Card]`、`currentIndex`、`recallIDs: [String]`、`recallIndex`、`mode`（`.normal` / `.retrain`）。
- 每轮开始时调用引擎 `pickRound(now:)` 生成 20 题并锁定；中途退出不回收已作答卡片。
- 状态栏：古文页隐藏状态栏背景色差，保持 `bg` 连续。

---

## 7. 自绘插图（纯 SwiftUI Shape，不引外部图片）

| 图形 | 实现要点 |
|---|---|
| 远山 | `Path` 三段折线（`move/addLine`）＋底部圆角封口，两层叠加：后层 `textSecondary.opacity(0.15)`，前层 `accent.opacity(0.12)` |
| 竹 | 竖 `Capsule` 竹节（3–4 段，段间留 3pt 空隙）＋ `Path` 斜置叶片（两段二次贝塞尔），色 `textSecondary.opacity(0.25)` |
| 书卷 | `RoundedRectangle(cornerRadius: 6)` 卷轴主体 ＋ 两端 `Capsule` 轴头，色 `accent.opacity(0.35)`；卷面画 3 条 `divider` 横线 |
| 灯烛 | `Capsule` 烛身 + `Path` 火焰（上下镜像二次贝塞尔），火焰 `accent.opacity(0.6)` |
| 类型徽标 | 词级：`RoundedRectangle(4)` 内「文」；句级：`Circle` 内「句」，均 20×20pt，`accent` 描边 1pt |

**[验收 U13]** 断网、删除 Assets 中所有位图后，四页插图仍完整显示（全部为代码绘制）。

---

## 8. 数据缺口（实现前需补，非视觉参数）

| # | 缺口 | 影响 | 建议 |
|---|---|---|---|
| ~~D1~~ | ~~词卡无「其他常见义项」字段~~ | — | **已关闭（P4=a）**：`other_senses: [String]` 已回填进 `word_cards.jsonl`（1418 张全部带此字段，422 张非空），由 `step17_build_cards.py` 自动聚合，不手填 |
| D2 | 77 张句卡 `full_english` 是段级译文（>400 字符，最长 1224） | 句级「整句高亮」实际是整段高亮 | 需句级切分或接受分段展示（§3.2 已定分段可滚动） |
| D3 | `word_quiz.jsonl` / `sentence_quiz.jsonl` 全量未生成 | 选择题页只有 30 条样本可用 | 联调期先用样本，上线前需全量 |

---

## 9. 待确认（✅ 已全部拍板，2026-10-27）

| # | 参数 | 拍板结果 |
|---|---|---|
| P1 | 错题本「再练一次」的计数口径 | **= 引擎 P8 = b**：计入 `total_attempts` / `total_correct`，不影响 `consecutive_correct` 与 `status` |
| P2 | 词级默写判分容差 | **= 引擎 P7 = b**：忽略大小写、首尾空格 + 开头冠词 the/a/an |
| P3 | 句级默写判分 | **= 引擎 P10 = a**：自评按钮（对/错），v2 再考虑自动判分 |
| P4 | 「其他常见义项」处理 | ✅ = a：`other_senses` 已回填（D1 关闭），为空隐藏该行 |
| P5 | 三态描边宽度 | **1.5pt**（暗色下更精致，不加粗） |
| P6 | `accent` 用途 | ✅ 只作装饰色：边框/底色/按钮/对勾/下划线，正文一律 `textPrimary`/`textSecondary` |
| P7 | 暗色模式 | ✅ 做：§1.1b 双值 Token，跟随系统外观 |
| P8 | 默写「查看答案」能否在提示前点 | **a**：可，仅记录 `hintUsed`；用提示判对只计 `total_attempts`（与引擎 P9 联动） |
| P9 | 进度条形态 | **b**：20 段方块分格（12×6pt、圆角 2pt、间距 4pt），已完成段 `accent` 填充 |
| P10 | 错题本列表密度 | **a**：两行摘要（classical + 出处/时间） |

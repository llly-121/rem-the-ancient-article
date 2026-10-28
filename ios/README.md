# 古文英译刷词 · iOS（SwiftUI 原生）

基于 `specs/learning_engine.md v1.0` 与 `specs/ui_spec.md v1.0` 实现的原生 iPhone 应用。
纯 SwiftUI + SwiftData，**完全离线**，无任何网络请求与第三方依赖。

> **Windows 用户请先读 `REMOTE_BUILD.md`**：本仓库已配置 GitHub Actions 云端 Mac 编译工作流
> （`.github/workflows/ios-build.yml`），push 即自动出「无 error 编译」结论与产物下载。
>
> **当前状态（2026-10-28 实测）**：云端 Mac（macos-15 + Xcode 26.3）编译 **通过，0 error**；
> UI 测试 **11 个用例全部通过**（2 个四页导航冒烟 + 9 个 U 系列验收），0 失败，耗时约 7.7 分钟。
> 仓库：https://github.com/llly-121/rem-the-ancient-article
>
> 在 Windows 上随时自查结果：`bash scripts/ci_status.sh`
> （绿勾/红叉 + 失败时的 error 行一屏出结果，不需要开浏览器，也不需要 Mac）。
>
> **v7 起不需要 Mac 也能完成全部验收**：ui_spec 的 U1–U13 已从「人眼判断」改为可重复执行的断言，
> 全部由云端 CI 出结论——详见下文第六节。


## 一、环境要求

| 项 | 要求 |
|---|---|
| Mac + Xcode | **Xcode 16.0 或更高**（工程使用 Xcode 16 的文件系统同步格式，Xcode 15 打不开） |
| 模拟器 | iOS 17.0 及以上任意 iPhone 模拟器 |
| 真机 | iOS 17.0+ 的 iPhone；首次真机运行需在 Xcode → Settings → Accounts 登录 Apple ID（免费个人签名即可） |

## 二、打开与运行

1. 把整个 `guwen-project/ios/` 文件夹拷贝到 Mac（保持目录结构不变）。
2. 双击 `GuwenApp.xcodeproj`，或打开 Xcode → File → Open → 选择它。
3. **模拟器运行**：顶部工具栏 Scheme 选 `GuwenApp`，设备选任意 iPhone（建议 iPhone 15 / 16 系列模拟器），按 `⌘R`。
4. **真机运行**：数据线连接 iPhone → 设备栏选你的手机 → 首次会提示"信任此开发者"，去 设置 → 通用 → VPN 与设备管理 里信任你的 Apple ID → 再按 `⌘R`。

## 三、项目结构

```
ios/
├─ GuwenApp.xcodeproj/          # Xcode 工程文件
├─ GuwenApp/                    # 源码（Xcode 16 文件系统同步：加文件即自动纳入编译）
│  ├─ GuwenApp.swift            # 入口：容器注册 / 全局流程 AppFlow / RootTabView
│  ├─ Models.swift              # jsonl 解码模型 + 运行期 Card / ProgressState
│  ├─ Persistence.swift         # SwiftData 实体（题库 4 实体 + 进度 + 错题本）
│  ├─ Library.swift             # 首次启动 jsonl→SwiftData 导入（幂等）+ 只读题库
│  ├─ ProgressStore.swift       # 学习状态（引擎 §1 状态机 / §3 计数 / §5 错题本）
│  ├─ Scheduler.swift           # 抽题引擎（§2 全部规则 + 默写抽样 + 词级判分）
│  ├─ Session.swift             # RoundSession / 词项定位容错 / word-level LCS 差异
│  ├─ RoundFlow.swift           # 轮次导航：选择题→答案→默写→小结
│  ├─ Theme.swift               # 设计令牌（浅色/深色双值，P7 暗色模式）
│  ├─ Components.swift          # 进度条/徽标/选项卡/自绘插图/按钮
│  ├─ Resources/                # 四个 jsonl 随包打包
│  └─ Views/
│     ├─ HomeView.swift         # 首页：统计 + 词句比例四档 + 开始一轮
│     ├─ QuizView.swift         # 页面一：选择题（20 段进度、0.4s 延迟、防连点）
│     ├─ AnswerView.swift       # 页面二：答案（词项下划线、片段高亮、长段切分）
│     ├─ RecallView.swift       # 页面三：默写（提示前2字母、LCS 对比、词自动/句自评）
│     └─ MistakeBookView.swift  # 页面四：错题本（筛选、左滑删、右滑再练）
└─ README.md
```

## 四、数据

- 四个 jsonl（word_cards 1418 / sentence_cards 654 / word_quiz 1288 / sentence_quiz 269）作为 bundle resource 打包；**首次启动**自动导入 SwiftData，之后读取全部走本地 SwiftData。
- 导入带数据版本号（`LibraryImporter.dataVersion`）：版本一致才跳过，不一致会清空旧题库重导。所以换题库不用重装 App，**但必须把 `dataVersion` 递增**，否则老数据不会更新。
- 学习状态（ProgressRecord）与错题本（MistakeRecord）独立持久化、按 card id 关联，与只读题库解耦——重导题库不会丢进度。
- 只有「正确答案 + 3 个干扰项」齐全的题才进抽题池（UI 是固定四选项，缺项会破版）。当前可出题 **1,346 张**（词 1,077 + 句 269），词句两侧全部可出题。
- 句题侧 269 道全部经人工通读：v3 清崩坏、v5 重写 30 题、v6 修 54 题的槽位错配，四类自动化扫描（碎片比、名词槽塞动词、`to`+过去式、首词小写）现均 0 命中。
- 词题里另有 211 道「同词同义项重复题」：同一个词同一义项在 21 个句子里各出一道、选项还完全一样（如「天下」21 道、「相如」34 道），已合并为该义项的代表题，其余存库但干扰项置空、不进抽题池（导出字段 `note` 写着由哪道代表）。

## 五、当前已知边界

1. **选择题已覆盖全部 1–5 档**：可用 1,346 张（词 1,077 + 句 269）。3/2/1 档由 `scripts/step24` 跨词构造 + 75 张人工手写补齐；5/4 档的 53 个高频词由 `scripts/word_quiz_tables.py` 按「词 × 义项」人工重写（见下条）。
2. **词题的两类系统性缺陷（v4 已处理，需持续抽检）**：
   - **同词多译**：同一文言词在不同句里被译成不同英文（天下 → the world / the empire / the realm；赂秦 → bribing Qin / bribe Qin / bribed Qin），拿其中一个当另一个的干扰项，学生选哪个都对。字符串归一化救不了，v4 改为按「同词 + 中文释义相近」聚成义项簇，同簇互斥。
   - **答案本身是错译**：上游把整句英译挂到虚词上（鼓「一鼓作气」→ `morale had already been lost`、对「对曰」→ `Cao Qufu said`、盖「盖失强援」→ `deprived of`）。这类只能人工重写，全在 `scripts/word_quiz_tables.py`，改完重跑 `scripts/step26`（幂等）。
3. **句级干扰项的质量风险（v3/v5 已处理，需持续抽检）**：v2 及以前的干扰项由「把某词的英文换成该词在别句里的 `term_english`」生成，而 `term_english` 是短语级、随句而变（`曰` 在「其必曰」那张卡里就是 `They would surely say`），跨句替换必然崩坏。v3 已删除 191 条崩坏项、102 题改人工手写。**v5 又清了一轮同类残留 30 题**：`族秦` 的动词被换成名词（`He who clan the Qin clan...`）、`至于` 被换成 `until/in summer`（`until weighing measures..., that is the duty of...`）、`假` 被换成 `borrowed`（`good at borrowed external things`）、`客有吹洞箫者` 被换成 `Heshi Bi the song`。这类无法用替换修补，只能整题重写，条目在 `scripts/step27_repair_content_defects.py` 的 `SENT_REWRITE` / `SENT_CORRECT_TEXT`（幂等，可反复跑）。
4. **单字多义项被塞进语法槽（v6 已处理）**：v5 之后仍有一批选项通顺度问题，根源是同一个字在别处的义项译文被填进了错误的词性位置——`坐`→`be punished for`（`straightened his robes and be punished for`）、`属`→`and the like`（`bamboos and the like` 改成 `bamboos asked me`）、`汤`→`vast and mighty`（`poured vast and mighty over me`）、`修`→`prepared`（`Zou Ji is prepared and has a beautiful appearance`）、`曾`→`great-grand`（`heaven and earth great-grand the blink of an eye`）。v6 逐题读过全部 269 道句题，把 54 道题、130 条选项按「片段级替换」改成同类词性、语义仍错的说法（`坐`→`submitted to punishment`、`属`→`entrusted to him`、`汤`→`vast quantities`、`修`→`under repair`），表格在 `SENT_DIST_PATCH` / `SENT_DIST_EXACT`，只替换坏片段、不动句子其余部分，重复执行无副作用。
5. **解释文本的截断**：上游按固定字数切断了干扰项解释（`误取「属」在他句的义项（通『嘱』，劝酒（举匏尊以相属：举葫芦杯互相劝…`），留下悬空括号。v5 改为「砍到最后一个完整单元再补收尾符」，并把 `本句为『到达」` 这类引号错配一并修掉；修正后全库 0 条括号不配对。
6. 默写判分：词级自动（忽略大小写/空格/开头冠词 the/a/an），句级自评按钮——与引擎 P7/P10 一致。
7. 暗色模式跟随系统外观（设置 → 显示 → 深色），App 内无开关（ui_spec P7）。
8. 冷启动（没有到期复习卡时）一轮按词句比例补满 20 题；有 due 卡时尾段新卡仍限 3 张（引擎 R3b/R3c/R3d）。

## 六、验收清单（对应 ui_spec U1–U13 / 引擎附录）

> **v7 起这十项不再需要 Mac。** 原先标注「请在 Mac 上手动过一遍」的人眼项，已全部换成
> 云端可重复执行的断言：
>
> - **UI 行为** → `ios/GuwenAppUITests/UAcceptanceTests.swift`（XCUITest，9 个用例）
> - **代码里不该存在的东⻄**（U13 无位图/断网、深色模式无硬编码色）→
>   `scripts/check_static_acceptance.py`，在 CI 编译**之前**跑，几秒出结论
>
> 全部由 `bash scripts/ci_status.sh` 一屏查结果，不需要开浏览器、也不需要 Mac。

- [x] ✅ 编译通过：`xcodebuild build` 0 error（CI 全绿）
- [x] ✅ 四页导航可达：`testFourPagesNavigate` 自动点击走通 选择题 → 答案 →（20 题后）默写 → 小结 → 错题本
- [x] ✅ 首启数据导入：`testImportedCardCounts` 校验 2,072 张卡 / 1,346 张可出题
- [x] ✅ 一轮 20 题：截图 `01-选择题页.png` 显示「第 1/20 题」
- [x] ✅ 题干标出划线词：词级题 term 加下划线 +「选出划线词的释义」
- [x] ✅ 默写输入框有 placeholder
- [x] ✅ 插图全部代码绘制：静态检查确认无 Assets、无位图文件、无 `Image("名称")`
- [x] ✅ U1 进度条 20 段随答题填充｜`testU1ProgressBarFills` 连答 3 题，断言段数 0→1→2→3
- [x] ✅ U2 连点两个选项只有第一个生效｜`testU2RapidTapsOnlyFirstCounts` 在 0.4s 窗口内连点，断言只推进一题
- [x] ✅ U4 词项下划线（多出现全标）｜`testU4UnderlineEveryOccurrence` 靶卡 `w0053`「天下」出现 2 次 → 断言标 2 处
- [x] ✅ U5 term_english 只高亮首处｜`testU5HighlightOnlyFirstHit` 同一张卡 `the world` 出现 2 次 → 断言只高亮 1 处
- [x] ✅ U6 长段级译文分句滚动显示｜`testU6LongSentenceSplits` 靶卡 `s0566`（423 字符）→ 断言拆成 ≥2 句并进滚动容器
- [x] ✅ U7 默写对比删除线/高亮｜`testU7RecallDiffMarks` 故意默写全错，断言缺词被标出、多写词有删除线
- [x] ✅ U8 提示按钮置灰｜`testU8HintButtonDisablesAfterUse` 用过提示后断言按钮 `isEnabled == false`
- [x] ✅ U9 默写只动 total_attempts/total_correct｜`testU9RecallOnlyTouchesAttempts` 断言 attempts +1 而 status / consecutive_correct 不变
- [x] ✅ U10–U12 错题本加入/置顶/筛选/左滑删除｜`testU10toU12MistakeBookFlow` 加入→「共 1 条」→左滑删除→空状态
- [x] ✅ U13 断网与无位图情况下插图完整｜静态检查：源码无 `URLSession`/网络库/URL 字面量，插图全为 SwiftUI Shape
- [x] ✅ 深色模式下四页无硬编码色残留｜静态检查：视图层只引用 `Theme` 令牌，且 7 个颜色令牌均为浅色/深色双值

### 靶卡的读取点约定（数据变动时需要同步复核）

`-ui-testing-card <cardID>` 是只看 UI 测试用的启动参数（正常启动不走这条分支），
让 U4/U5/U6 精确打到需要的卡，而不是靠随机抽 20 题撞运气：

| 靶卡 | 用途 | 依赖的数据事实 |
|---|---|---|
| `w0053`「天下」 | U4 + U5 | `classical_sentence` 里出现 2 次；`term_english` = `the world` 在 `full_english` 里出现 2 次 |
| `s0566`《生于忧患》 | U6 | `full_english` 长 423 字符，超过 `TermLocator.splitLongEnglish` 的 400 阈值 |

题库若被改写导致这两条事实不再成立，对应用例会红——这是有意的：它同时充当数据哨兵。

### 实拍留档

`ios/screenshots/` 是四页界面（由 CI 实拍，非人工截图）；
`ios/screenshots/u-acceptance/` 是每个 U 用例的现场截图，命名即对应条款（`U1-答完3题进度条.png`、
`U4-选择题页下划线.png`、`U5-答案页高亮.png`、`U7-默写对比.png` …），共 13 张。
不用登 GitHub，直接看这些图就能复核验收结论。


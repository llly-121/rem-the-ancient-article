# 古文英译刷词 · iOS（SwiftUI 原生）

基于 `specs/learning_engine.md v1.0` 与 `specs/ui_spec.md v1.0` 实现的原生 iPhone 应用。
纯 SwiftUI + SwiftData，**完全离线**，无任何网络请求与第三方依赖。

> **Windows 用户请先读 `REMOTE_BUILD.md`**：本仓库已配置 GitHub Actions 云端 Mac 编译工作流
> （`.github/workflows/ios-build.yml`），push 即自动出「无 error 编译」结论与产物下载。
>
> **当前状态（2026-10-27 实测）**：云端 Mac（macos-15 + Xcode 26.3）编译 **通过，0 error**，
> 用时 36 秒，产物 `GuwenApp-simulator-build`（0.92 MB）。
> 仓库：https://github.com/llly-121/rem-the-ancient-article
>
> 在 Windows 上随时自查编译结果：`bash scripts/ci_status.sh`
> （绿勾/红叉 + 失败时的 error 行一屏出结果，不需要开浏览器）。


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

- 四个 jsonl（word_cards 1418 / sentence_cards 654 / word_quiz 296 / sentence_quiz 269）作为 bundle resource 打包；**首次启动**自动导入 SwiftData（幂等：已有数据则跳过），之后读取全部走本地 SwiftData。
- 学习状态（ProgressRecord）与错题本（MistakeRecord）独立持久化，与只读题库解耦——符合引擎 §6。
- 替换数据：用新版 jsonl 覆盖 `GuwenApp/Resources/` 同名文件后，删除 App 重装（或首页右上角菜单"清除全部学习记录"后重装）即可重新导入。

## 五、当前已知边界

1. **选择题覆盖 5/4 档**：word_quiz 296 + sentence_quiz 269 = 565 张可出选择题；引擎只抽有 quiz 数据的卡，其余卡轮空。3/2/1 档 quiz 生成后覆盖 `Resources/` 即自动生效。
2. 句级 quiz 中 69 句 needs_manual 的干扰项为自动生成（partial corruption），上线前建议手写替换后重新打包。
3. 默写判分：词级自动（忽略大小写/空格/开头冠词 the/a/an），句级自评按钮——与引擎 P7/P10 一致。
4. 暗色模式跟随系统外观（设置 → 显示 → 深色），App 内无开关（ui_spec P7）。

## 六、验收清单（对应 ui_spec U1–U13 / 引擎附录）

- [ ] 编译通过：`⌘B` 无 error
- [ ] 四页导航可达：首页「开始一轮」→ 选择题 → 答案 →（第 20 题后）默写 → 小结；底部 Tab「错题本」
- [ ] U1 进度条 20 段随答题填充
- [ ] U2 连点两个选项只有第一个生效
- [ ] U4/U5 词项下划线（多出现全标）、term_english 只高亮首处
- [ ] U6 长段级译文分句滚动显示
- [ ] U7–U9 默写对比：删除线/高亮、提示按钮置灰、默写 10 题只动 total_attempts/total_correct
- [ ] U10–U12 错题本：加入/置顶/筛选/左滑删除
- [ ] U13 断网与无位图情况下插图完整（全部代码绘制）
- [ ] 深色模式下四页无硬编码色残留

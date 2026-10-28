# 古文英译刷词 · 网页体验版

Windows 上用来试玩 iOS 版的同一套题库与同一套流程。**双击 `index.html` 即可打开**，不需要装任何东西、不需要联网、不需要服务器。

## 它是什么

iOS 版（`ios/GuwenApp/`）只能在 macOS 模拟器或 iPhone 上跑。这一版是把 SwiftUI 的三个核心页（选择题 / 答案 / 默写）与错题本，用 HTML + CSS + 原生 JS 逐行复刻出来的等价物：

| 复刻对象 | 对应实现 |
|---|---|
| `TermLocator` | `termRanges()` / `markTerm()`，多出现处全部加下划线 |
| `DiffBuilder` | `diff()`，词级 LCS，缺词高亮+下划线、多写词删除线 |
| `Scheduler` | `pickRound()` / `pickRecallIDs()`，同一套 new/learning/due 抽样规则 |
| `ProgressStore` | `localStorage`，键名带数据版本号，题库更新自动失效 |
| `Theme.swift` | CSS 变量，浅色 `#F5E6D3` / 深色 `#2A211A` 与 iOS 完全一致 |

题库就是仓库里的 `data/word_cards.jsonl` + `data/sentence_cards.jsonl` 经人工校订后的 1,346 张可出题卡，**与 iOS 版同源**，不是另做的样例数据。

## 怎么玩

1. 首页点「开始一轮」→ 20 道选择题，点选项即判分，0.4 秒后进答案页
2. 20 题答完自动进默写，10 题（本轮答错的优先），输入后「查看答案」看词级对错
3. 句级默写没有标准答案比对，改成自己点「判对 / 判错」
4. 答案页可「加入错题本」，底部第二个 Tab 里能筛选、再练、删除
5. 右上角 `⋯` 可切深色模式、清除全部学习记录

数据存在浏览器本地，刷新不丢；想重来就 `⋯` → 清除全部学习记录。

## 它不是什么

- 不是正式发布的产品。它是验收用的体验版，方便在 Windows 上肉眼过一遍交互。
- 没有账号、没有云同步、没有排行榜，也不打算加。
- 真机装包（.ipa）需要 Apple 开发者签名，Windows 上做不了，所以才有这个网页版。

## 数据来源

`data.js` 由脚本生成，不要手改：

```bash
python scripts/build_web_demo_data.py
```

题库改动后重跑这条命令即可同步；`data.js` 里的 `v` 字段会跟着数据版本走。

图标由 `python scripts/make_icons.py` 生成（PIL 画「文」字 + 一道划线，
输出 180/192/512 与 maskable 四张），不要手改 PNG。

---

## 装到 iPhone 主屏（当 App 用）

线上地址：<https://guwen-flashcards.app.workbuddy.host/?sharecode=5BOBJUPCXS>

iPhone 上用 **Safari** 打开（微信/QQ 内置浏览器不行，它们不支持添加到主屏），
点底部分享按钮 → **添加到主屏幕** → 命名「古文刷词」→ 添加。
之后从桌面图标打开就是全屏无地址栏，行为接近原生 App。

### 三个技术细节，都是踩过的坑

**1. `?sharecode=` 不能丢。**
这个托管地址对子资源有校验：第一次带 sharecode 访问时服务端下发
`__wb_rsc` cookie（30 天），之后 `data.js` / `manifest` / 图标才放行；
不带 sharecode 直接请求子资源一律 403。所以：

- `manifest.webmanifest` 里**故意不写 `start_url`**。写了 `./index.html` 会让
  安卓/iOS 的部分场景丢掉查询串，启动即 403 白屏；不写则默认用当前文档 URL，
  sharecode 自然带过去。
- Service Worker 里所有 `cache.match` 都带 `ignoreSearch: true`，
  否则请求上的 `?sharecode=` 会让缓存永远不命中。

**2. Service Worker 只缓存 `res.ok` 的响应。**
上面的 403 返回的是一张正常的 HTML 错误页，HTTP 状态是 403 但 `res.ok` 为 false。
如果无脑 `cache.put`，那张错误页会被永久缓存，App 从此打不开——
这是这类带鉴权的托管地址最容易埋的雷。

**3. 图标用线性 SVG，不用 emoji。**
底部 Tab 一开始用的 📖 和 ▤，在真机上会被系统渲染成彩色贴图，和墨色纸色的调子完全不搭，
且不同手机长得不一样。改成 `stroke: currentColor` 的 SVG 后跟着主题色走。

### 验证过的

- 线上页面端到端 9 项：数据加载 1,346 张、标题、开始一轮、选项可点、进答案页、
  Service Worker active、缓存 6 条、无 JS 报错 —— 全过。
- 真断网重载 5 项：CDP `Network.emulateNetworkConditions` 断网后 reload，
  仍能出 1,346 张卡、首页渲染、能开一轮、能进答案页 —— 全过。
- 本地交互 26 项（抽题比例、下划线、锁定防连点、默写 diff、错题本）—— 全过。

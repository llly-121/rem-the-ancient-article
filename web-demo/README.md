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

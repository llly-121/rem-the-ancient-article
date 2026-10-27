# Windows 远程构建 iOS 指南

> 结论先行：Apple 授权限制，**iOS 编译只能跑在 macOS 上**，Windows 本机无论装什么工具都编不了。
> 但你不需要买 Mac —— 下面三条路线全部有 GitHub 开源项目支撑，按推荐顺序排列。

---

## 路线一：GitHub Actions 云 Mac（已为你的项目配好，推荐）

**原理**：GitHub 免费提供云端 Mac（`macos-15` runner，Apple Silicon，预装 Xcode 16.x）。
你在 Windows 上只做 `git push`，云端自动完成编译，产物（.app）可从网页下载。

**已就绪的文件**：

| 文件 | 作用 |
|---|---|
| `.github/workflows/ios-build.yml` | 云端 Mac 编译工作流（免签名、模拟器目标） |
| `ios/GuwenApp.xcodeproj/xcshareddata/xcschemes/GuwenApp.xcscheme` | CI 必需的共享 Scheme（本地 Xcode 打开时会自动生成 scheme，但 CI 不会，必须提交此文件） |
| 依赖的 GitHub 开源项目 | `maxim-lobanov/setup-xcode`（选 Xcode 版本）、`actions/checkout`、`actions/upload-artifact` |

**你要做的（一次性，5 分钟）**：

```bash
# 1. 在 GitHub 网页新建仓库（右上角 + → New repository）
#    ⚠️ 建议选 Public（公开仓库 Actions 完全免费，见下方费用说明）
#    建议名：guwen-project

# 2. Windows 本机（在 guwen-project 目录下，git 已初始化）：
git remote add origin https://github.com/<你的用户名>/guwen-project.git
git push -u origin main

# 3. 网页打开 https://github.com/<你的用户名>/guwen-project/actions
#    等待约 8–15 分钟 → 绿色对勾 = 编译通过（等于你的验收第一条 ✅）
#    点进本次运行 → 底部 Artifacts → 下载 GuwenApp-simulator-build
```

**费用账（重要）**：
- **Public 仓库：完全免费，不限次数**。
- Private 仓库：每月送 2000 分钟额度，但 macOS runner 按 **×10 倍**计费——
  一次 12 分钟的编译实际扣 120 分钟 ≈ 每月只够 16 次。所以**强烈建议 Public**。
  如果介意数据公开，可以先脱敏（见下）再公开。

**触发的三种方式**：push 到 main 且改动涉及 `ios/**` 自动触发；PR 触发；Actions 页面右上角 `Run workflow` 手动触发。

**公开前脱敏检查**（若选 Public）：本仓库含你生成的古文数据（course_cards / jsonl）与脚本，
均为自产内容，无密钥无隐私；确认 `.env` 之类文件不在仓库即可（当前没有）。

---

## 路线二：xtool —— 真·Windows 无 Mac 出 ipa（进阶，需 WSL）

**项目**：[xtool-org/xtool](https://github.com/xtool-org/xtool)（11k+ star，MIT 协议）
跨平台 Xcode 替代品：在 Linux/Windows(WSL2) 上把 SwiftPM 工程编译成 iOS 应用、签名、直装真机。

**能做到**：不碰任何 Mac，在 Windows 上产出可安装到真 iPhone 的 ipa（免费 Apple ID 签名 7 天有效）。
**做不到/限制**：
- 只认 **SwiftPM 工程**（`xtool new` / `Package.swift` + `xtool.yml`），不认 .xcodeproj —— 需把现有工程改造成 SwiftPM 格式；
- 需要从 Xcode.xip 提取 iOS SDK（Apple 框架不在 xtool 里分发，需有渠道拿到 Xcode 安装包）；
- 无模拟器、无 SwiftUI 预览、Interface Builder 部分功能缺失、App Store 上架仍要走 Mac。

**适用场景**：想完全摆脱云端、直接在 Windows 迭代 + 真机调试。等你用路线一验证 App 可用后，
若想脱离 GitHub，我可以再帮你做 SwiftPM 改造。

**Windows 安装要点**（官方文档 xtool.sh）：
1. 安装 WSL2（`wsl --install`，Ubuntu 24.04 推荐）；
2. WSL 内装 Swift 6.x 工具链 + usbmuxd（USB 直通把 iPhone 绑定到 WSL，或改用 Windows 端 iTunes 转发）；
3. `xtool setup`（装 Darwin Swift SDK）→ `xtool auth`（登 Apple ID）→ `xtool dev` 构建并装真机。

---

## 路线三：租云 Mac（兜底）

MacinCloud（托管型 $15/月起）/ MacStadium / AWS EC2 Mac 实例。
Windows 用远程桌面/VNC 连上去，Xcode 体验和本地一致，还能跑模拟器点按操作。
适合：需要真实模拟器交互调试、且不想把代码放上 GitHub 时。
其他时间用路线一就够，不必常租。

---

## 三条路线怎么组合（建议）

```
日常迭代（Windows 写码）
   │ git push
   ▼
GitHub Actions 云 Mac ──编译验证 + 产物下载──────► 确认"无 error 编译"验收
   │
   ├─ 想在真机上点一点 ──► 路线二 xtool 出 ipa 装机（或花 $99/年 开发者账号走 TestFlight）
   └─ 想跑模拟器交互 ──► 路线三 按小时租云 Mac
```

## 当前项目的下一步

1. 网页建 GitHub 仓库（Public）→ 按上面 3 条命令 push；
2. 等 Actions 变绿 → 下载 Artifact，用任意模拟器工具（如 Corellium/云模拟器）或直接确认编译通过；
3. 把 Actions 第一次运行的编译日志发我，若有 error 我立即修源码。

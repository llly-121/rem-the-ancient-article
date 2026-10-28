# 在 iPhone 上装这个 App

## 先说清楚：iOS 没有「直接给个安装包就能装」这回事

安卓给个 `.apk` 双击就装了，iOS 不行。任何 App 要装进 iPhone，安装包里必须带**苹果签发的签名和描述文件**，而签名只认两样东西：

1. 一个 Apple ID（免费的就够）
2. 由该 Apple ID 向苹果申请到的开发证书

证书私钥只能存在你自己的机器上，**不能、也不该经过任何 CI 或第三方**。所以流程必然是两段：

```
GitHub 云端 Mac 编译  →  未签名 .ipa  →  你本机用 Sideloadly 用你的 Apple ID 现场签名  →  装进 iPhone
```

本仓库的 CI 负责第一段，产出 `GuwenApp-unsigned.ipa`；第二段在你电脑上做。

---

## 你需要准备什么

| 项 | 要求 | 说明 |
|---|---|---|
| iPhone | iOS **17.0 及以上** | 工程的 `IPHONEOS_DEPLOYMENT_TARGET = 17.0` |
| 电脑 | Windows 10/11 | 你现有的这台就行 |
| 数据线 | Lightning 或 USB-C | 第一次安装必须插线，之后可以无线 |
| Apple ID | 任意，**不需要付费** | 免费账号也能签，见下方限制 |
| 工具 | Sideloadly（免费） | <https://sideloadly.io> |

---

## 第一步：拿到 .ipa

**已经打好了**：`dist/GuwenApp-unsigned.ipa`（767 KB，2026-10-28 构建）。

这份包已核验：架构 `arm64`、平台 `iOS(设备)`、`MinimumOSVersion 17.0`、
Bundle ID `com.guwen.flashcards`、四个题库 jsonl 都在 `Payload/GuwenApp.app/` 里。

要重新打一份（改过代码之后）：

1. 打开 <https://github.com/llly-121/rem-the-ancient-article/actions>
2. 左侧选 **iOS Build (远程构建)**，右上角 **Run workflow** → 分支 `main` → 运行
3. 等约 6–8 分钟，跑完后点进这次运行，页面底部 **Artifacts** 里下载
   **`GuwenApp-unsigned-ipa`**（保留 30 天）
4. 解压得到 `GuwenApp-unsigned.ipa`

> `Artifacts` 里如果只有 `GuwenApp-simulator-build`，说明 `ipa` 任务还没进仓库
> （那个包只能在 Mac 的模拟器里跑，真机装不了）。

---

## 第二步：用 Sideloadly 签名并安装

1. 装 Sideloadly，同时装好 **iTunes**（Sideloadly 依赖它的驱动与 iPhone 通信）
2. iPhone 用数据线连电脑，解锁，弹出「是否信任此电脑」选**信任**
3. 打开 Sideloadly：
   - **IPA 文件**：选刚下载的 `GuwenApp-unsigned.ipa`
   - **Apple ID**：填你的 Apple 账号
   - 点 **Start**
4. 会提示输入密码。**如果你开了双重认证**（大多数人都开了），
   要去 <https://account.apple.com> → 登录与安全 → **App 专用密码** 生成一个，
   用它代替账号密码填进去
5. 等进度条走完，手机上会出现 App 图标

### 第一次打开会提示「不受信任的开发者」

去 iPhone **设置 → 通用 → VPN 与设备管理**，找到你的 Apple ID，
点 **信任"xxx"**，然后就能正常打开了。

---

## 免费 Apple ID 的三个限制（必须知道）

| 限制 | 具体表现 |
|---|---|
| **7 天过期** | 装好 7 天后 App 打不开，提示"开发者证书已失效"。重新用 Sideloadly 签一次即可，**学习记录不会丢**（数据在 App 沙盒里，重签不覆盖） |
| **最多 3 个自签 App** | 手机里同时只能有 3 个自己签的 App |
| **需要定期连电脑** | 过期后必须插线重签，不能纯无线续期 |

付费开发者账号（688 元/年）可解除这三条，签名有效期 1 年，但对你「自己用一个学习 App」的场景，免费账号足够。

---

## 备选：不想折腾签名

| 方案 | 成本 | 体验 |
|---|---|---|
| **网页版**（`web-demo/`） | 零 | 手机 Safari 打开，可「添加到主屏幕」变成全屏图标，离线可用，数据存本地。缺点：不是原生 App，没有系统级动效 |
| **模拟器包**（CI 的 `GuwenApp-simulator-build`） | 零 | 只能在 macOS 的 iOS 模拟器里跑，你需要一台 Mac |
| **TestFlight** | 688 元/年 + 苹果审核 | 最正规，可发给别人测试，但审核要几天，且题库类 App 有被拒风险 |

---

## 常见报错

| 报错 | 原因 | 处理 |
|---|---|---|
| `Signing for "GuwenApp" requires a development team` | CI 漏配 `CODE_SIGNING_ALLOWED=NO` | 已在 workflow 里关掉签名，若仍报说明推送的不是最新版 |
| `not a valid IPA` | 压缩包内不是 `Payload/GuwenApp.app` 结构 | 用 CI 产的包，不要自己重新压缩 |
| `Unable to install ... device not supported` | 手机系统低于 iOS 17 | 升级系统，或改工程的部署目标后重新打包 |
| `The maximum number of apps for free development profiles has been reached` | 免费账号已签满 3 个 | 删掉一个旧的，或换账号 |
| 安装后图标在但点开闪退 | 没信任开发者证书 | 设置 → 通用 → VPN 与设备管理 → 信任 |

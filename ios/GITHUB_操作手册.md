# 你需要做什么（Windows 上把项目推到 GitHub，让云端 Mac 编译）

> 你机器上已装好 Git（`D:\Git`，带凭据管理器），项目已初始化并提交，**只差一个 GitHub 仓库地址**。
> 全程只有 3 件事需要你亲手做，其余我都能代做。

---

## 第 1 件：注册 GitHub（已有账号可跳过，约 2 分钟）

1. 打开 https://github.com/signup
2. 填邮箱 → 设密码 → 起用户名（英文/数字，例如 `asus-guwen`）
3. 收到验证邮件，点里面的按钮激活

> 免费账号足够：公开仓库的 macOS 编译额度不限量。

---

## 第 2 件：创建一个空仓库（**唯一必须你亲手做的操作**，约 1 分钟）

1. 浏览器打开 https://github.com/new
2. 填三项：
   - **Repository name**：`guwen-project`
   - **Description**：随便写或留空
   - 选 **Public**（公开＝免费不限量；选 Private 则每月只够编 16 次左右）
3. **下面三个勾全部不要勾**：
   - ☐ Add a README file
   - ☐ Add .gitignore
   - ☐ Choose a license
   （勾了会和本地已有文件冲突，push 会被拒绝）
4. 点绿色按钮 **Create repository**
5. 新页面顶部有一行地址，形如：
   ```
   https://github.com/你的用户名/guwen-project.git
   ```
   **复制这一行**。

---

## 第 3 件：把地址填进去并推送 —— 二选一

### 方式 A（推荐，你只需把地址发我）

把上面复制的地址发给我，我在你的项目目录执行远程配置和推送。
过程中你的屏幕会弹出一个 **Git Credential Manager** 小窗口：

1. 点 **Sign in with your browser**（用浏览器登录）
2. 浏览器里点 **Authorize Git Credential Manager**
3. 窗口自动关闭，推送完成

### 方式 B（自己敲，两条命令）

打开 PowerShell 或 CMD，**逐条复制**执行（把地址换成你自己的）：

```
cd /d E:\Users\asus\workbuddy\guwen-project
git remote add origin https://github.com/你的用户名/guwen-project.git
git push -u origin main
```

- 第 1 条：进入项目目录（CMD 用 `cd /d`；PowerShell 用 `cd` 即可）
- 第 2 条：告诉 git"云端仓库在哪"
- 第 3 条：上传，首次会弹浏览器登录（同上，点两下授权）
- 看到 `main -> main` 且没有报错，就是成功了

---

## 第 4 件：看编译结果（约 10 分钟后）

1. 打开 `https://github.com/你的用户名/guwen-project/actions`
2. 状态含义：
   - 🟡 黄点 = 排队或编译中（正常，8–15 分钟）
   - ✅ 绿勾 = **编译通过**（你任务里的"无 error 编译"验收达成）
   - ❌ 红叉 = 编译报错
3. 点进绿勾那一次运行 → 页面最下方 **Artifacts** → 点 `GuwenApp-simulator-build` 下载，里面就是编好的 `GuwenApp.app`

**如果是红叉**：点进去 → 左侧点带红叉的 `编译（iOS 模拟器目标，免签名）` → 复制最后 30 行日志发我，我立刻改代码。

---

## 常见问题对照表

| 报错/现象 | 原因 | 解决 |
|---|---|---|
| `remote origin already exists` | 之前配过远程地址 | `git remote set-url origin 你的仓库地址` |
| `Updates were rejected ... fetch first` | 建仓库时勾了 README | `git push -u origin main --force` |
| `Authentication failed` 反复弹 | 存了错的旧凭据 | 控制面板 → 凭据管理器 → Windows 凭据 → 删掉含 `git:https://github.com` 的条目，重新 push |
| `'git' 不是内部或外部命令` | 终端没读到 PATH | 把命令里的 `git` 换成 `"D:\Git\cmd\git.exe"` |
| 浏览器登录后仍失败 | 账号未验证邮箱 | 去邮箱点激活链接，再 push |
| Actions 页面没有任何运行 | 触发条件是 `ios/**` 变更 | 手动点右上角 **Run workflow** |

---

## 隐私提醒

仓库里的内容全部是自产的：`data/`（古文卡片、选择题）、`scripts/`（处理脚本）、`ios/`（App 源码）。
没有 .env、没有 token、没有密钥。即便如此，若你不想公开数据，可选 Private——
代价是 macOS 编译分钟数按 10 倍计费（免费额度 2000 分钟/月，约够 16 次编译）。

---

## 以后每次改了代码怎么办

```bash
cd /d E:\Users\asus\workbuddy\guwen-project
git add -A
git commit -m "改了什么地方"
git push
```

push 上去后 Actions 自动重跑，你只需回 Actions 页面看绿勾。

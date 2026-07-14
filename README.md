# mybt-signin

纸鸢下载（https://mybt.kiteyuan.info）每日自动签到，支持 GitHub Actions 托管。

## 功能

- 每日自动签到：`POST /api/auth/points/tasks/signin`
- 可选访问任务：`POST /api/auth/points/tasks/visit`
- 自动生成 `X-Sign` / `X-Timestamp`
- “今日已签到 / 今日已领取” 视为成功，避免 Actions 误报

## 仓库结构

```text
mybt-signin/
├─ signin.py
├─ .github/workflows/signin.yml
├─ .env.example
├─ .gitignore
└─ README.md
```

## 1. 获取 Token 和 User ID

1. 浏览器登录 https://mybt.kiteyuan.info/
2. `F12` → `Network`
3. 刷新页面，找到 ` /api/auth/me `
4. 在请求头复制：
   - `Authorization: Bearer <MYBT_TOKEN>`
   - 只要 **Bearer 后面** 那串 JWT
5. User ID 获取方式任选其一：
   - `/api/auth/me` 响应里的 `user.id`
   - 或 JWT 中间段解码后的 `uid`
   - 控制台执行：`localStorage.getItem('magnetflow_user')`

> Token 通常约 24 小时有效，过期后重新抓包并更新 Secrets。

## 2. 配置 GitHub Secrets

仓库 → **Settings** → **Secrets and variables** → **Actions**

### Secrets（必填）

| Name | 值 |
|------|----|
| `MYBT_TOKEN` | JWT（不要带 `Bearer ` 前缀） |
| `MYBT_USER_ID` | 用户 id |

### Secrets（可选）

| Name | 值 |
|------|----|
| `MYBT_COOKIE` | 若 Actions 被 Cloudflare 拦截，再填 `cf_clearance=...` |
| `MYBT_SECRET` | 默认不需要；只有前端改密钥时才填 |

### Variables（可选）

| Name | 值 | 说明 |
|------|----|------|
| `MYBT_DO_VISIT` | `1` 或 `0` | 是否做访问任务，默认脚本内为 1 |
| `MYBT_BASE_URL` | `https://mybt.kiteyuan.info` | 一般不用改 |

## 3. 推送并运行

```bash
git init
git add .
git commit -m "feat: mybt daily signin"
git branch -M main
git remote add origin https://github.com/<你的用户名>/mybt-signin.git
git push -u origin main
```

然后：

1. 打开仓库 **Actions**
2. 选择工作流 `mybt-signin`
3. 点击 **Run workflow** 手动测一次
4. 看日志是否出现 `DONE: success`

默认定时：每天 **北京时间 09:30**（cron: `30 1 * * *` UTC）

## 4. 本地测试（可选）

PowerShell:

```powershell
cd D:\study\project\mybt-signin
$env:MYBT_TOKEN="你的JWT"
$env:MYBT_USER_ID="你的用户id"
python signin.py
```

## 常见问题

### 1) `authentication failed` / `token is malformed`
- `MYBT_TOKEN` 填错
- 不要包含 `Bearer ` 前缀
- token 过期，重新抓包

### 2) `missing signature headers`
- 脚本太旧或请求被中间层改写
- 确认用的是本仓库 `signin.py`

### 3) `今日已签到`
- 正常，脚本会当作成功

### 4) GitHub Actions 里 Cloudflare 403/5xx
- 先更新 `MYBT_TOKEN`
- 再尝试添加 `MYBT_COOKIE=cf_clearance=...`
- cookie 也有有效期，需要时再更新

### 5) 签名失败
- 确认 `MYBT_USER_ID` 与账号一致
- 一般不要改 `MYBT_SECRET`

## 安全建议

- 仓库请用 **Private**
- 不要把 token/cookie 写进代码
- 不要在 issue/聊天里发完整 token
- token 泄露后立刻重新登录替换

## 免责声明

本项目仅供学习与个人自动化使用。请遵守目标网站规则，账号风险自负。

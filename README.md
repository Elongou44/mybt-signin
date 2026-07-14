# mybt-signin

纸鸢下载自动签到 + Casdoor 自动续期（GitHub Actions）

## 已实现

- 每日签到 / 访问任务
- 优先用 `MYBT_USERNAME` + `MYBT_PASSWORD` 自动登录拿新 token
- 失败时回退 `MYBT_TOKEN`

## 关键限制

登录页启用了 **Cloudflare Turnstile**。  
GitHub Actions 里纯密码登录可能被验证码拦截。  
若日志出现 `login requires captcha/turnstile`，说明自动续期被拦，需要：

1. 先继续用 `MYBT_TOKEN` 兜底，或
2. 再升级为浏览器自动化/验证码方案

## Secrets

推荐：
- `MYBT_USERNAME`
- `MYBT_PASSWORD`

兜底：
- `MYBT_TOKEN`
- `MYBT_USER_ID`（可选）

可选：
- `MYBT_COOKIE`
- `MYBT_TURNSTILE_TOKEN`

## 使用

1. 推送代码
2. 配置 Secrets
3. Actions -> mybt-signin -> Run workflow

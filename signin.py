#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
纸鸢下载(mybt.kiteyuan.info) 每日签到脚本
用于 GitHub Actions / 本地 Python 定时执行。

必需环境变量:
  MYBT_TOKEN    JWT (Bearer 后面那串，不要带 Bearer 前缀)
  MYBT_USER_ID  用户 id（/api/auth/me 返回的 user.id，或 JWT 里的 uid）

可选环境变量:
  MYBT_COOKIE   例如 cf_clearance=...（Cloudflare 拦截时再填）
  MYBT_BASE_URL 默认 https://mybt.kiteyuan.info
  MYBT_SECRET   前端签名密钥，默认 change-this-secret（一般不用改）
  MYBT_DO_VISIT 是否顺带做访问任务，默认 1
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple


def env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(name)
    if v is None:
        return default
    v = v.strip()
    return v if v != "" else default


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def signing_key(secret: str, user_id: str) -> str:
    # 前端: Co(secret, userId) = HmacSHA256(userId, secret).toString()
    return hmac.new(secret.encode("utf-8"), user_id.encode("utf-8"), hashlib.sha256).hexdigest()


def build_sign_headers(
    method: str,
    api_path: str,
    body: str,
    user_id: str,
    secret: str,
) -> Dict[str, str]:
    """
    api_path 必须是 /api 开头，例如 /api/auth/points/tasks/signin
    body 是原始 JSON 字符串；无 body 时传空字符串。
    """
    path = api_path
    query = ""
    if "?" in api_path:
        path, query = api_path.split("?", 1)

    ts = str(int(time.time()))
    body = body or ""
    canonical = "\n".join(
        [
            method.upper(),
            path,
            query,
            sha256_hex(body),
            ts,
        ]
    )
    key = signing_key(secret, user_id)
    sign = hmac.new(key.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    return {"X-Sign": sign, "X-Timestamp": ts}


class MybtClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        user_id: str,
        secret: str = "change-this-secret",
        cookie: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token.removeprefix("Bearer ").strip()
        self.user_id = user_id
        self.secret = secret
        self.cookie = cookie
        self.timeout = timeout
        self.ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/150.0.0.0 Safari/537.36"
        )

    def request(self, method: str, path: str, body_obj: Any = None) -> Tuple[int, Any, str]:
        # path 允许 /auth/me 或 /api/auth/me
        rel = path if path.startswith("/") else f"/{path}"
        if not rel.startswith("/api/"):
            rel = "/api" + rel

        body: Optional[str]
        if body_obj is None:
            body = None
        else:
            body = json.dumps(body_obj, ensure_ascii=False, separators=(",", ":"))

        headers = {
            "User-Agent": self.ua,
            "Accept": "application/json, */*",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
            "Origin": self.base_url,
            "Referer": self.base_url + "/",
        }
        if self.cookie:
            headers["Cookie"] = self.cookie

        sign_headers = build_sign_headers(method, rel.split("?")[0] if False else rel, body or "", self.user_id, self.secret)
        # 上面 split 不需要；保持完整 rel（含 query）进入签名
        sign_headers = build_sign_headers(method, rel, body or "", self.user_id, self.secret)
        headers.update(sign_headers)

        data = None if body is None else body.encode("utf-8")
        req = urllib.request.Request(self.base_url + rel, data=data, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
                status = resp.getcode() or 200
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            status = e.code
        except Exception as e:
            return 0, None, f"network error: {type(e).__name__}: {e}"

        parsed: Any
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = raw
        return status, parsed, raw

    def me(self) -> Tuple[int, Any, str]:
        return self.request("GET", "/auth/me")

    def signin(self) -> Tuple[int, Any, str]:
        # 前端调用 POST /auth/points/tasks/signin ，body 为 {}
        return self.request("POST", "/auth/points/tasks/signin", {})

    def visit(self) -> Tuple[int, Any, str]:
        return self.request("POST", "/auth/points/tasks/visit", {})


def summarize_result(action: str, status: int, data: Any, raw: str) -> Tuple[bool, str]:
    """
    返回 (是否算成功, 说明文本)
    今日已签到 也视为成功，避免 GitHub Actions 误报失败。
    """
    if status == 0:
        return False, f"{action}: {raw}"

    if isinstance(data, dict):
        err = data.get("error") or data.get("message") or data.get("msg")
        if status >= 400:
            err_s = str(err or raw)
            # 业务上“已经完成”当成功
            if any(k in err_s for k in ("已签到", "已完成", "已领取", "already", "Already")):
                return True, f"{action}: {err_s}"
            return False, f"{action}: HTTP {status} - {err_s}"

        # 成功时可能有 added 字段
        added = data.get("added")
        if added is not None:
            return True, f"{action}: 成功，获得 {added} 积分"
        return True, f"{action}: 成功 - {json.dumps(data, ensure_ascii=False)}"

    if 200 <= status < 300:
        return True, f"{action}: HTTP {status} - {raw[:200]}"
    return False, f"{action}: HTTP {status} - {raw[:200]}"


def main() -> int:
    token = env("MYBT_TOKEN")
    user_id = env("MYBT_USER_ID")
    if not token or not user_id:
        print("缺少环境变量: MYBT_TOKEN 和/或 MYBT_USER_ID")
        print("请到 GitHub 仓库 Settings -> Secrets and variables -> Actions 中配置。")
        return 2

    base_url = env("MYBT_BASE_URL", "https://mybt.kiteyuan.info") or "https://mybt.kiteyuan.info"
    secret = env("MYBT_SECRET", "change-this-secret") or "change-this-secret"
    cookie = env("MYBT_COOKIE")
    do_visit = (env("MYBT_DO_VISIT", "1") or "1").lower() in ("1", "true", "yes", "y")

    client = MybtClient(base_url=base_url, token=token, user_id=user_id, secret=secret, cookie=cookie)

    print("== mybt signin ==")
    print(f"time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"base: {base_url}")
    print(f"user_id: {user_id[:6]}...{user_id[-4:] if len(user_id)>10 else ''}")

    ok_all = True

    # 1) 校验登录
    status, data, raw = client.me()
    ok, msg = summarize_result("me", status, data, raw)
    print(msg)
    if not ok:
        print("登录态失效，请更新 GitHub Secrets 中的 MYBT_TOKEN")
        return 1

    if isinstance(data, dict) and isinstance(data.get("user"), dict):
        user = data["user"]
        print(
            "user:",
            user.get("username"),
            "points=",
            user.get("points"),
            "email=",
            user.get("casdoor_email"),
        )
        # 若 secret 中 user_id 填错，这里可提示
        real_id = str(user.get("id") or "")
        if real_id and real_id != user_id:
            print(f"警告: MYBT_USER_ID 与 /auth/me 不一致，将改用接口返回的 id")
            client.user_id = real_id

    # 2) 签到
    status, data, raw = client.signin()
    ok, msg = summarize_result("signin", status, data, raw)
    print(msg)
    ok_all = ok_all and ok

    # 3) 可选访问任务
    if do_visit:
        status, data, raw = client.visit()
        ok, msg = summarize_result("visit", status, data, raw)
        print(msg)
        ok_all = ok_all and ok

    # 4) 再查一次积分
    status, data, raw = client.me()
    if status == 200 and isinstance(data, dict) and isinstance(data.get("user"), dict):
        print("points_after:", data["user"].get("points"))

    if ok_all:
        print("DONE: success")
        return 0
    print("DONE: failed")
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("interrupted")
        raise SystemExit(130)

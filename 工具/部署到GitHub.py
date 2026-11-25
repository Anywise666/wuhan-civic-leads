# 已废弃：早期桌面端一次性部署脚本；现由服务器 systemd + deploy key 完成，保留仅作存档。
# -*- coding: utf-8 -*-
"""把看板发布到 GitHub Pages（一次性部署）。

流程：
1. GitHub OAuth 设备码授权（浏览器输入 8 位代码，等效于 gh auth login）
2. 创建公开仓库 wuhan-civic-leads
3. 用 Contents API 上传 index.html 与 README.md（无需本地 git）
4. 开启 GitHub Pages（main 分支根目录）
5. 轮询构建，输出可访问网址

用法：
    python 工具\部署到GitHub.py
token 只在内存中使用，不落盘、不打印。
"""
import base64
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# 本机 IPv6 出口不通，强制 IPv4，否则 github.com 的 TLS 握手会超时
_orig_getaddrinfo = socket.getaddrinfo


def _getaddrinfo_v4(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)


socket.getaddrinfo = _getaddrinfo_v4

BASE = Path(__file__).resolve().parent.parent
INDEX = BASE / "看板" / "index.html"

CLIENT_ID = "Iv1.b507a08c87ecfe98"  # GitHub CLI 公开客户端 ID（设备码流程）
SCOPES = "repo"
REPO_NAME = "wuhan-civic-leads"

API = "https://api.github.com"
UA = {"User-Agent": "wuhan-civic-leads-deploy", "Accept": "application/vnd.github+json"}


def post_form(url, data, headers=None):
    body = urllib.parse.urlencode(data).encode()
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=body, method="POST")
            req.add_header("Accept", "application/json")
            req.add_header("User-Agent", "wuhan-civic-leads-deploy")
            for k, v in (headers or {}).items():
                req.add_header(k, v)
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last = exc
            time.sleep(2 + attempt * 3)
    raise last


def api(url, token, method="GET", payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    for k, v in UA.items():
        req.add_header(k, v)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            body = json.loads(raw)
        except Exception:
            body = {"raw": raw[:500]}
        return e.code, body


def device_login():
    dc = post_form(
        "https://github.com/login/device/code",
        {"client_id": CLIENT_ID, "scope": SCOPES},
    )
    print("=" * 60)
    print("请在浏览器打开：", dc["verification_uri"])
    print("输入代码：", dc["user_code"])
    print("=" * 60, flush=True)

    interval = max(5, int(dc.get("interval", 5)))
    deadline = time.time() + int(dc.get("expires_in", 900))
    while time.time() < deadline:
        time.sleep(interval)
        res = post_form(
            "https://github.com/login/oauth/access_token",
            {
                "client_id": CLIENT_ID,
                "device_code": dc["device_code"],
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
        )
        if res.get("access_token"):
            print("授权成功", flush=True)
            return res["access_token"]
        err = res.get("error")
        if err == "authorization_pending":
            continue
        if err == "slow_down":
            interval += 5
            continue
        if err in ("expired_token", "access_denied", "bad_verification_code"):
            print("授权未完成：", err)
            return None
    print("授权超时")
    return None


def ensure_repo(token, login):
    status, body = api(f"{API}/repos/{login}/{REPO_NAME}", token)
    if status == 200:
        print("仓库已存在，复用：", body.get("html_url"))
        return body["html_url"]
    status, body = api(
        f"{API}/user/repos",
        token,
        "POST",
        {
            "name": REPO_NAME,
            "description": "武汉民生与涉企诉求线索看板（公开信息，已脱敏，可溯源）",
            "private": False,
            "auto_init": False,
        },
    )
    if status not in (200, 201):
        print("创建仓库失败：", status, body)
        return None
    print("仓库已创建：", body.get("html_url"))
    return body["html_url"]


def put_file(token, login, path, content_bytes, message):
    b64 = base64.b64encode(content_bytes).decode()
    url = f"{API}/repos/{login}/{REPO_NAME}/contents/{path}"
    status, body = api(url, token)
    payload = {"message": message, "content": b64, "branch": "main"}
    if status == 200:
        payload["sha"] = body["sha"]
    status, body = api(url, token, "PUT", payload)
    if status in (200, 201):
        print(f"已上传 {path}（{len(content_bytes)} 字节）")
        return True
    print(f"上传 {path} 失败：", status, body)
    return False


def enable_pages(token, login):
    url = f"{API}/repos/{login}/{REPO_NAME}/pages"
    status, body = api(url, token)
    if status == 200:
        print("Pages 已开启：", body.get("html_url"))
        return body
    status, body = api(
        url, token, "POST", {"source": {"branch": "main", "path": "/"}}
    )
    if status in (201, 204):
        print("Pages 已开启（首次构建中）")
        return body
    if status == 409:
        status, body = api(
            url, token, "PUT", {"source": {"branch": "main", "path": "/"}}
        )
        if status in (200, 204):
            print("Pages 配置已更新")
            return body
    print("开启 Pages 失败：", status, body.get("message", body))
    return None


def main() -> int:
    if not INDEX.exists():
        print("未找到看板，请先运行 python 工具\\生成看板.py")
        return 1

    env_token = os.environ.get("GITHUB_TOKEN", "").strip()
    if env_token:
        print("使用环境变量 GITHUB_TOKEN")
        token = env_token
    else:
        token = device_login()
    if not token:
        return 2

    status, me = api(f"{API}/user", token)
    if status != 200:
        print("读取账号失败：", status, me)
        return 3
    login = me["login"]
    print("登录账号：", login)

    # 诊断：打印令牌实际拿到的 scopes
    try:
        rq = urllib.request.Request(f"{API}/user")
        rq.add_header("Authorization", f"Bearer {token}")
        rq.add_header("User-Agent", UA["User-Agent"])
        with urllib.request.urlopen(rq, timeout=20) as resp:
            print("token scopes:", resp.headers.get("X-OAuth-Scopes", "(none)"))
            print("token type:", resp.headers.get("X-GitHub-Enterprise-Version", "-"))
    except Exception as exc:
        print("scopes 读取失败：", exc)

    if not ensure_repo(token, login):
        return 4

    if not put_file(token, login, "index.html", INDEX.read_bytes(), "发布线索看板"):
        return 5

    readme = f"""# 武汉民生与涉企诉求线索看板

公开网络线索归集，每条附原文链接与状态依据；投诉人已脱敏；已剔除官媒/官方公开且明确办结的事项。

- 在线看板：https://{login}.github.io/{REPO_NAME}/
- 数据为静态快照，更新时间见看板页脚
- 来源：武汉市政府门户“来信公示”、委办局来信公示、武汉城市留言板、人民网领导留言板、黑猫投诉等公开页面
- 说明：仅反映公开页面记载，不构成对事实的最终认定

由 DSH 智能体生成。
"""
    put_file(token, login, "README.md", readme.encode("utf-8"), "添加说明")

    enable_pages(token, login)

    url = f"https://{login}.github.io/{REPO_NAME}/"
    print("等待 Pages 首次构建（最多 180 秒）…")
    for _ in range(36):
        time.sleep(5)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "check"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    print("PAGES_URL:", url)
                    print("部署完成")
                    return 0
        except Exception:
            continue
    print("PAGES_URL:", url)
    print("已提交，构建可能仍在进行，稍后刷新即可")
    return 0


if __name__ == "__main__":
    sys.exit(main())


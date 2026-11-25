# 已废弃：早期桌面端一次性部署脚本；现由服务器 systemd + deploy key 完成，保留仅作存档。
# -*- coding: utf-8 -*-
"""把看板发布到 Netlify（无需实名/备案，默认域名国内可直连）。

准备：
1. 在 https://app.netlify.com 注册并登录（邮箱即可）
2. 打开 https://app.netlify.com/user/applications#personal-access-tokens
   新建 token，复制
3. 把 token 存到 E:\\民生诉求线索智能体\\token.txt（一行）
4. 运行：python 工具\\部署到Netlify.py

token 只从文件读取，用完即删；不会打印。
"""
import io
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
INDEX = BASE / "看板" / "index.html"
TOKEN_FILE = BASE / "token.txt"
API = "https://api.netlify.com/api/v1"
SITE_NAME = "wuhan-civic-leads"


def req(url, token, method="GET", data=None, ctype=None):
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", f"Bearer {token}")
    r.add_header("User-Agent", "wuhan-leads-deploy")
    if ctype:
        r.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            body = json.loads(raw)
        except Exception:
            body = {"raw": raw[:300]}
        return e.code, body


def main() -> int:
    if not INDEX.exists():
        print("未找到看板，请先运行 python 工具\\生成看板.py")
        return 1
    token = os.environ.get("NETLIFY_TOKEN", "").strip()
    if not token and TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not token:
        print("缺少 token：请把 Netlify Personal Access Token 写入 token.txt")
        return 2

    # 复用或创建站点
    status, sites = req(f"{API}/sites?name={SITE_NAME}", token)
    site = None
    if status == 200 and isinstance(sites, list) and sites:
        site = sites[0]
        print("复用站点：", site.get("ssl_url") or site.get("url"))
    if not site:
        name = SITE_NAME
        for attempt in range(3):
            status, body = req(
                f"{API}/sites", token, "POST",
                json.dumps({"name": name}).encode(), "application/json",
            )
            if status in (200, 201):
                site = body
                print("站点已创建：", site.get("ssl_url") or site.get("url"))
                break
            if status == 422 and attempt < 2:
                name = f"{SITE_NAME}-{random.randint(1000, 9999)}"
                continue
            print("创建站点失败：", status, body.get("message", body))
            return 3
    if not site:
        return 3

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("index.html", INDEX.read_bytes())
    status, deploy = req(
        f"{API}/sites/{site['id']}/deploys", token, "POST", buf.getvalue(), "application/zip"
    )
    if status not in (200, 201):
        print("上传失败：", status, deploy.get("message", deploy))
        return 4
    print("已上传，等待构建…")
    deploy_id = deploy.get("id")
    url = site.get("ssl_url") or site.get("url")
    for _ in range(30):
        time.sleep(3)
        st, d = req(f"{API}/deploys/{deploy_id}", token)
        state = d.get("state")
        if state == "ready":
            url = d.get("ssl_url") or d.get("deploy_ssl_url") or url
            print("NETLIFY_URL:", url.rstrip("/") + "/")
            print("部署完成")
            return 0
        if state in ("error", "rejected"):
            print("构建失败：", state)
            return 5
    print("NETLIFY_URL:", url.rstrip("/") + "/")
    print("仍在构建，稍后刷新")
    return 0


if __name__ == "__main__":
    sys.exit(main())


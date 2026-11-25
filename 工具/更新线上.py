# -*- coding: utf-8 -*-
"""把最新看板推送到 GitHub Pages 仓库（供定时任务调用，失败不阻塞主流程）。

用法：python 工具\\更新线上.py
依赖：工具\\ssh_github.cmd（调用 Windows 原生 ssh，绕开 MSYS 管道限制）
"""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
REPO = BASE / "发布" / "github"
SSH = BASE / "工具" / "ssh_github.cmd"
INDEX = BASE / "看板" / "index.html"
REMOTE = "git@github.com:Anywise666/wuhan-civic-leads.git"

ENV = os.environ.copy()
ENV["GIT_SSH"] = str(SSH)
ENV["GIT_TERMINAL_PROMPT"] = "0"


def git(*args, cwd=None):
    # 继承标准输出，避免沙箱禁止的管道捕获
    p = subprocess.run(["git", *args], cwd=cwd or REPO, env=ENV)
    return p.returncode


def main() -> int:
    if not INDEX.exists():
        print("看板不存在，先运行 python 工具\\生成看板.py")
        return 1

    if not (REPO / ".git").exists():
        if REPO.exists():
            shutil.rmtree(REPO, ignore_errors=True)
        REPO.parent.mkdir(parents=True, exist_ok=True)
        print("克隆仓库…")
        if git("clone", REMOTE, str(REPO), cwd=str(BASE)) != 0:
            print("CLONE_FAIL")
            return 2

    shutil.copy2(INDEX, REPO / "index.html")
    git("add", "-A")
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO, env=ENV,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stdout.strip()
    if not status:
        print("NO_CHANGES")
        return 0

    stamp = time.strftime("%Y-%m-%d %H:%M")
    if git("-c", "user.name=Anywise666", "-c", "user.email=Anywise666@users.noreply.github.com",
           "commit", "-m", f"自动更新 {stamp}") != 0:
        print("COMMIT_FAIL")
        return 3

    if git("push", "origin", "main") != 0:
        git("pull", "--rebase", "origin", "main")
        if git("push", "origin", "main") != 0:
            print("PUSH_FAIL")
            return 4
    print("PUSH_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

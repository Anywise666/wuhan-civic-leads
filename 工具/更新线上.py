# -*- coding: utf-8 -*-
"""把最新看板、规则、数据与报告同步推送到 GitHub Pages 仓库（供定时任务调用，失败不阻塞主流程）。

用法：
    python 工具\\更新线上.py              # 同步并推送
    set DRY_RUN=1 & python 工具\\更新线上.py   # 只打印差异，不提交、不推送

同步内容（工作目录 -> 发布\\github）：
    看板\\index.html  -> index.html
    规则\\*.md        -> 规则\\
    数据\\*           -> 数据\\
    报告\\*.md        -> 报告\\
    工具\\*           -> 工具\\（跳过 _ 开头的临时脚本）

依赖：工具\\ssh_github.cmd（调用 Windows 原生 ssh，绕开 MSYS 管道限制）
失败不阻塞归集：任何失败只返回非零码并打印原因，调用方忽略即可。
"""
import fnmatch
import hashlib
import os
import shutil
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
REPO = BASE / "发布" / "github"
SSH = BASE / "工具" / "ssh_github.cmd"
REMOTE = "git@github.com:Anywise666/wuhan-civic-leads.git"

INDEX_SRC = BASE / "看板" / "index.html"
INDEX_DST = REPO / "index.html"

# 报告默认全量同步；长期运行后可改成 30，只留最近 30 天并删除仓库中更早的副本
REPORT_SYNC_DAYS = 0

# (工作目录子目录, 文件通配)
SYNC_DIRS = [
    ("规则", "*.md"),
    ("数据", "*"),
    ("报告", "*.md"),
    ("工具", "*"),
]

SKIP_NAMES = {"token.txt", "__pycache__"}
SKIP_SUFFIXES = (".zip", ".tmp", ".log")

DRY_RUN = os.environ.get("DRY_RUN") == "1"

ENV = os.environ.copy()
ENV["GIT_SSH"] = str(SSH)
ENV["GIT_TERMINAL_PROMPT"] = "0"


def git(*args, cwd=None):
    # 继承标准输出，避免沙箱禁止的管道捕获
    p = subprocess.run(["git", *args], cwd=cwd or REPO, env=ENV)
    return p.returncode


def should_skip(name: str) -> bool:
    return (
        name.startswith("_")
        or name in SKIP_NAMES
        or name.lower().endswith(SKIP_SUFFIXES)
    )


def report_date(name: str):
    """从 YYYY-MM-DD_HHMM.md 取日期，取不到返回 None。"""
    stamp = name.split("_")[0]
    try:
        y, m, d = (int(x) for x in stamp.split("-"))
        return date(y, m, d)
    except (ValueError, IndexError):
        return None


def in_window(name: str) -> bool:
    if REPORT_SYNC_DAYS <= 0:
        return True
    d = report_date(name)
    if d is None:
        return True
    return d >= date.today() - timedelta(days=REPORT_SYNC_DAYS)


def differs(src: Path, dst: Path) -> bool:
    try:
        if not dst.exists() or src.stat().st_size != dst.stat().st_size:
            return True
        return hashlib.sha256(src.read_bytes()).digest() != hashlib.sha256(dst.read_bytes()).digest()
    except OSError:
        return True


def sync_dirs() -> tuple:
    """把工作目录的规则/数据/报告/工具复制进克隆，返回 (更新, 跳过)。"""
    updated, skipped = 0, 0
    for sub, pattern in SYNC_DIRS:
        src_dir = BASE / sub
        dst_dir = REPO / sub
        if not src_dir.is_dir():
            print(f"跳过：{sub}\\ 不存在")
            continue
        for src in sorted(src_dir.iterdir()):
            if not src.is_file() or not fnmatch.fnmatch(src.name, pattern) or should_skip(src.name):
                continue
            if sub == "报告" and not in_window(src.name):
                skipped += 1
                continue
            dst = dst_dir / src.name
            if not differs(src, dst):
                continue
            if DRY_RUN:
                print(f"[DRY] 将更新 {sub}\\{src.name}")
            else:
                dst_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            updated += 1
    return updated, skipped


def prune_old_reports() -> int:
    """REPORT_SYNC_DAYS>0 时删除仓库中超出窗口的报告副本（历史仍在 git 里）。"""
    if REPORT_SYNC_DAYS <= 0:
        return 0
    dst_dir = REPO / "报告"
    if not dst_dir.is_dir():
        return 0
    removed = 0
    for dst in dst_dir.glob("*.md"):
        if in_window(dst.name):
            continue
        if DRY_RUN:
            print(f"[DRY] 将删除 报告\\{dst.name}")
        else:
            dst.unlink()
        removed += 1
    return removed


def main() -> int:
    if not INDEX_SRC.exists():
        print("看板不存在，先运行 python 工具\\生成看板.py")
        return 1

    if not (REPO / ".git").exists():
        if DRY_RUN:
            print(f"[DRY] 需要克隆 {REMOTE}")
        elif REPO.exists():
            shutil.rmtree(REPO, ignore_errors=True)
        if not DRY_RUN:
            REPO.parent.mkdir(parents=True, exist_ok=True)
            print("克隆仓库…")
            if git("clone", REMOTE, str(REPO), cwd=str(BASE)) != 0:
                print("CLONE_FAIL")
                return 2

    if DRY_RUN:
        if not (REPO / ".git").exists():
            print("[DRY] 克隆后才会继续比较")
            return 0
    else:
        shutil.copy2(INDEX_SRC, INDEX_DST)

    updated, skipped = sync_dirs()
    pruned = prune_old_reports()
    print(f"文件更新 {updated} 个，窗口外跳过 {skipped} 个，清理旧报告 {pruned} 个")

    if DRY_RUN:
        print("DRY_RUN：未提交、未推送")
        return 0

    git("add", "-A")
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO, env=ENV,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stdout.strip()
    if not status:
        print("NO_CHANGES")
        return 0

    changed = len([line for line in status.splitlines() if line.strip()])
    stamp = time.strftime("%Y-%m-%d %H:%M")
    if git("-c", "user.name=Anywise666", "-c", "user.email=Anywise666@users.noreply.github.com",
           "commit", "-m", f"自动更新 {stamp}（{changed} 个文件）") != 0:
        print("COMMIT_FAIL")
        return 3

    if git("push", "origin", "main") != 0:
        git("pull", "--rebase", "origin", "main")
        if git("push", "origin", "main") != 0:
            print("PUSH_FAIL")
            return 4
    print(f"PUSH_OK（{changed} 个文件）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

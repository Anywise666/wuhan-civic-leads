# -*- coding: utf-8 -*-
"""线索台账导出工具：JSONL -> CSV + 汇总 Markdown，并做基础校验。

用法（在 E:\\民生诉求线索智能体 下）：
    python 工具\\导出台账.py
输出：
    数据\\线索台账.csv       Excel 可直接打开（utf-8-sig）
    数据\\台账汇总.md        按状态/类别统计
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
LEDGER = BASE / "数据" / "线索台账.jsonl"
CSV_OUT = BASE / "数据" / "线索台账.csv"
MD_OUT = BASE / "数据" / "台账汇总.md"

FIELDS = [
    ("id", "线索编号"),
    ("category", "类别"),
    ("title", "标题"),
    ("summary", "诉求摘要"),
    ("complainant", "投诉人（脱敏）"),
    ("channel", "投诉渠道"),
    ("ref_no", "留言/工单编号"),
    ("published_at", "发布时间"),
    ("handler", "承办单位"),
    ("status", "当前状态"),
    ("status_evidence", "状态依据"),
    ("channel_url", "原文链接"),
    ("verify_level", "核验等级"),
    ("confidence", "置信度"),
    ("first_seen", "首次采集"),
    ("last_verified", "最后核验"),
    ("fingerprint", "去重指纹"),
    ("notes", "备注"),
]


def load(path: Path):
    rows, bad = [], []
    if not path.exists():
        return rows, bad
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError("不是 JSON 对象")
            rows.append(obj)
        except Exception as exc:  # noqa: BLE001
            bad.append((lineno, str(exc)))
    return rows, bad


def main() -> int:
    rows, bad = load(LEDGER)
    if bad:
        print("台账存在无法解析的行（未覆盖原文件，请先修复）：")
        for lineno, err in bad:
            print(f"  第 {lineno} 行：{err}")
        return 1

    if rows:
        with CSV_OUT.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow([label for _, label in FIELDS])
            for row in rows:
                writer.writerow([str(row.get(key, "") or "") for key, _ in FIELDS])

    missing_url = [r.get("id", "?") for r in rows if not r.get("channel_url")]
    missing_status = [r.get("id", "?") for r in rows if not r.get("status")]

    by_status = Counter(r.get("status", "未标注") for r in rows)
    by_cat = Counter(r.get("category", "未标注") for r in rows)
    by_level = Counter(r.get("verify_level", "?") for r in rows)

    lines = [
        "# 台账汇总",
        "",
        f"- 记录数：{len(rows)}",
        f"- 类别分布：" + "，".join(f"{k} {v}" for k, v in by_cat.items()) or "-",
        f"- 状态分布：" + "，".join(f"{k} {v}" for k, v in by_status.items()),
        f"- 核验等级：" + "，".join(f"{k} {v}" for k, v in by_level.items()),
        "",
        "| 编号 | 类别 | 状态 | 标题 | 首次采集 |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {id} | {category} | {status} | {title} | {first_seen} |".format(
                id=row.get("id", ""),
                category=row.get("category", ""),
                status=row.get("status", ""),
                title=str(row.get("title", "")).replace("|", "／"),
                first_seen=str(row.get("first_seen", ""))[:16].replace("T", " "),
            )
        )

    if missing_url:
        lines += ["", "## 待修复：缺原文链接", "", "，".join(missing_url)]
    if missing_status:
        lines += ["", "## 待修复：缺状态", "", "，".join(missing_status)]

    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"已读取 {len(rows)} 条")
    if rows:
        print(f"CSV  -> {CSV_OUT}")
    print(f"汇总 -> {MD_OUT}")
    if missing_url or missing_status:
        print("警告：存在缺链接或缺状态的记录，见汇总文件")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Regenerate REPORT.md from the cases in cases/.

Pure standard library.

Usage:
    python tools/report.py            # rewrite REPORT.md
    python tools/report.py --stdout   # print instead of writing
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = ROOT / "cases"
REPORT_PATH = ROOT / "REPORT.md"

VERDICT_ORDER = ["fail", "unknown", "degraded", "blocked"]
REACH_ORDER = ["production", "edge", "theoretical"]


def load_cases() -> list[dict]:
    cases = []
    for path in sorted(CASES_DIR.glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as fh:
                cases.append(json.load(fh))
        except json.JSONDecodeError:
            continue
    return cases


def counter_table(title: str, counter: Counter, order: list[str] | None = None) -> list[str]:
    rows = [f"### {title}", "", "| 值 | 条数 |", "|---|---|"]
    keys = [k for k in (order or []) if counter.get(k)]
    keys += sorted(k for k in counter if k not in keys)
    for key in keys:
        rows.append(f"| `{key}` | {counter[key]} |")
    rows.append("")
    return rows


def build_report(cases: list[dict]) -> str:
    lines: list[str] = []
    lines.append("# 静默失败图谱 · 统计")
    lines.append("")
    lines.append("> 本文件由 `tools/report.py` 自动生成，请勿手工编辑。")
    lines.append("")
    lines.append(f"**案例总数：{len(cases)}**")
    lines.append("")

    if not cases:
        lines.append("尚无案例。")
        return "\n".join(lines) + "\n"

    lines += counter_table("按期望判决", Counter(c.get("expected_verdict", "?") for c in cases), VERDICT_ORDER)
    lines += counter_table("按可达性", Counter(c.get("reachability", "?") for c in cases), REACH_ORDER)
    lines += counter_table("按领域", Counter(c.get("domain", "?") for c in cases))
    lines += counter_table("按状态", Counter(c.get("status", "draft") for c in cases))
    lines += counter_table("按贡献者", Counter(c.get("contributed_by", "?") for c in cases))

    lines.append("### 案例清单")
    lines.append("")
    lines.append("| id | 标题 | 被推翻的判据 | 期望判决 | 可达性 | 状态 |")
    lines.append("|---|---|---|---|---|---|")
    for case in sorted(cases, key=lambda c: c.get("id", "")):
        title = case.get("title", "").replace("|", "\\|")
        falsifies = case.get("falsifies", "").replace("|", "\\|")
        lines.append(
            f"| `{case.get('id', '?')}` | {title} | {falsifies} "
            f"| `{case.get('expected_verdict', '?')}` | `{case.get('reachability', '?')}` "
            f"| {case.get('status', 'draft')} |"
        )
    lines.append("")

    lines.append("## 关于汇总口径")
    lines.append("")
    lines.append(
        "**不同 `reachability` 的案例不能合并成一个命中率。** "
        "有实测显示同分布负样本与跨场景负样本的检测力差一个数量级，"
        "把两者汇总会把「测试集覆盖范围」与「检测器灵敏度」混为一谈。"
    )
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stdout", action="store_true", help="print instead of writing REPORT.md")
    args = parser.parse_args()

    report = build_report(load_cases())
    if args.stdout:
        print(report, end="")
    else:
        REPORT_PATH.write_text(report, encoding="utf-8", newline="\n")
        print(f"wrote {REPORT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

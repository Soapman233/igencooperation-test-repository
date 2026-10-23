#!/usr/bin/env python3
"""一条命令：最小草稿 → 可合并的案例文件。

它替你做完提交链上所有机械步骤，你只需要填七个字段：

    校验最小契约 → 隐私扫描 → 自动取号 → 补默认字段 → 写 cases/ → 重生成 REPORT.md

纯标准库。不需要 pip install，不需要先读 schema。

用法：
    python tools/submit.py submit/example.json            # 直接落盘
    python tools/submit.py my-case.json --dry-run         # 只检查，不写文件
    python tools/submit.py my-case.json --id sf-0042      # 指定号（撞号会报错）

退出码 0 = 可以提 PR；1 = 有阻断问题（错误信息里写明了改哪一格）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parent
CASES_DIR = ROOT / "cases"
SUBMIT_SCHEMA = ROOT / "submit" / "submission.schema.json"
CASE_SCHEMA = ROOT / "schema" / "case.schema.json"

sys.path.insert(0, str(TOOLS_DIR))

import privacy  # noqa: E402
import report as report_mod  # noqa: E402
import validate  # noqa: E402

# 最小契约之外的字段，脚本负责补。不要手写这些。
DEFAULTS = {
    "status": "draft",
    "reported_verdict": "pass",
    "domain": "unspecified",
    "contributed_by": "anonymous",
}

ALIASES = {
    "contributor": "contributed_by",
    "author": "contributed_by",
    "by": "contributed_by",
    "verdict": "expected_verdict",
}

SUGGESTED_DOMAINS = [
    "unattended-loop", "filesystem-write", "ci-pipeline", "document-pipeline",
    "packaging", "network-retry", "state-machine", "encoding",
]

# 模板占位文字。忘了替换的人不该看到 OK —— 一份能通过的空白模板是假门禁。
PLACEHOLDER_MARKERS = ("把这里换成", "这里换成", "填这里", "TODO", "XXX")


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def existing_ids() -> dict[str, str]:
    found: dict[str, str] = {}
    for path in sorted(CASES_DIR.glob("*.json")):
        found[path.stem] = path.name
    return found


def next_id(taken: dict[str, str]) -> str:
    numbers = []
    for case_id in taken:
        if case_id.startswith("sf-") and case_id[3:].isdigit():
            numbers.append(int(case_id[3:]))
    return f"sf-{(max(numbers) + 1) if numbers else 1:04d}"


def normalize(doc: dict) -> tuple[dict, list[str]]:
    """只做字段别名归一。补默认值要等最小契约校验之后——先补会把缺字段藏起来。"""
    notes: list[str] = []
    case = dict(doc)

    for alias, canonical in ALIASES.items():
        if alias in case:
            case.setdefault(canonical, case.pop(alias))
            notes.append(f"字段 {alias} 已按 {canonical} 处理")

    return case, notes


def fill_defaults(case: dict) -> list[str]:
    notes: list[str] = []
    for field, value in DEFAULTS.items():
        if field not in case:
            case[field] = value

    if case.get("domain") == "unspecified":
        notes.append(
            "domain 用了缺省值 unspecified；"
            f"建议改成：{' / '.join(SUGGESTED_DOMAINS)}"
        )
    return notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", help="最小草稿 JSON 的路径")
    parser.add_argument("--dry-run", "--check", dest="dry_run", action="store_true",
                        help="只检查，不写文件")
    parser.add_argument("--id", help="指定案例号，如 sf-0042（默认取最大号 +1）")
    parser.add_argument("--json", action="store_true", help="机器可读输出")
    args = parser.parse_args()

    if not args.path:
        parser.error("需要一个草稿文件路径；模板见 submit/TEMPLATE.json")

    source = Path(args.path)
    if not source.is_absolute():
        source = (Path.cwd() / source).resolve()
    if not source.exists():
        print(f"找不到文件：{source}")
        return 1

    try:
        draft = load_json(source)
    except json.JSONDecodeError as exc:
        print(f"JSON 解析失败：{exc}")
        return 1

    if not isinstance(draft, dict):
        print("顶层必须是一个 JSON 对象，不是数组。")
        return 1

    case, notes = normalize(draft)
    errors: list[str] = []
    warnings: list[str] = []

    # 1. 最小契约：先按草稿本来的样子校验，补默认值之前。
    # id 与 status 不属于最小契约（脚本负责），先摘出来再校验。
    declared_id = case.pop("id", None)
    declared_status = case.pop("status", None)
    minimal_errors: list[str] = []
    validate.check(case, load_json(SUBMIT_SCHEMA), "submission", minimal_errors, warnings)
    errors.extend(minimal_errors)

    notes.extend(fill_defaults(case))
    if declared_id:
        case["id"] = declared_id
    if declared_status and declared_status != "draft":
        notes.append(f"status 已从 {declared_status!r} 改回 draft：reviewed 只能由独立复现者给")

    # 2. 隐私：比格式更硬。格式错了能改，泄了不能收。
    scan = privacy.scan_obj(case)
    errors.extend(scan["errors"])
    warnings.extend(scan["warnings"])

    # 2b. 模板占位文字没替换
    for field, value in case.items():
        if isinstance(value, str) and any(m in value for m in PLACEHOLDER_MARKERS):
            errors.append(f"{field}: 还是模板占位文字，替换成你的实际内容")

    # 3. 取号
    taken = existing_ids()
    if args.id:
        case["id"] = args.id
    elif "id" not in case:
        case["id"] = next_id(taken)

    if case["id"] in taken:
        if source.stem == case["id"]:
            errors.append(
                f"{case['id']} 已在库中。改已有案例请直接编辑 cases/{case['id']}.json "
                f"并跑 validate.py，不要走提交流程"
            )
        else:
            errors.append(f"号 {case['id']} 已被 {taken[case['id']]} 占用；去掉 --id 让脚本自动取号")
    if not (isinstance(case["id"], str) and len(case["id"]) == 7
            and case["id"].startswith("sf-") and case["id"][3:].isdigit()):
        errors.append(f"号 {case['id']!r} 不合规，格式必须是 sf-四位数字")

    # 4. 完整 schema（含 id 与文件名一致性之外的约束）
    full_errors: list[str] = []
    validate.check(case, load_json(CASE_SCHEMA), case.get("id", "case"), full_errors, warnings)
    errors.extend(e for e in full_errors if e not in errors)

    # 5. 质量提示：同标题重复
    for path in CASES_DIR.glob("*.json"):
        try:
            other = load_json(path)
        except json.JSONDecodeError:
            continue
        if other.get("title", "").strip() == case.get("title", "").strip():
            warnings.append(f"标题与 {path.stem} 完全相同，确认不是重复提交")

    validate.lint(case, warnings, case.get("id", "case"))

    result = {
        "ok": not errors,
        "id": case.get("id"),
        "written": None,
        "errors": errors,
        "warnings": warnings,
        "notes": notes,
    }

    if errors:
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"[FAIL] {source.name}")
            for message in errors:
                print(f"        error: {message}")
            for message in warnings:
                print(f"        warn : {message}")
            print("\nRESULT: BLOCKED — 改完再跑一次。错误信息里的字段名就是你要改的那一格。")
        return 1

    if not args.dry_run:
        target = CASES_DIR / f"{case['id']}.json"
        target.write_text(
            json.dumps(case, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        result["written"] = str(target.relative_to(ROOT))
        report_mod.REPORT_PATH.write_text(
            report_mod.build_report(report_mod.load_cases()),
            encoding="utf-8",
            newline="\n",
        )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(f"[OK] {case['id']}  {case['title']}")
    for message in notes:
        print(f"        note : {message}")
    for message in warnings:
        print(f"        warn : {message}")

    if args.dry_run:
        print("\nRESULT: DRY-RUN OK — 没有写文件。去掉 --dry-run 才会落盘。")
        return 0

    print(f"        wrote: {result['written']}")
    print("        wrote: REPORT.md（统计已重生成）")
    print("\n下一步（三选一）：")
    print(f"  git checkout -b case/{case['id']}")
    print(f"  git add {result['written']} projects/silent-failure-atlas/REPORT.md")
    print(f"  git commit -m \"case: {case['id']} {case['title']}\"")
    print("  然后提 PR。没有 GitHub 权限：把生成的 JSON 私信给维护者，注明署名方式。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

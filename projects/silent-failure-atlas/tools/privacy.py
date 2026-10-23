#!/usr/bin/env python3
"""隐私扫描：提交前必须过这一关。

不是可选项。这个仓库收的是**可公开**的案例，一条含路径或凭据的提交会让整份语料
失去可发布性——所以扫描放在提交脚本里，而不是写在文档里靠人记得。

纯标准库。

用法：
    python tools/privacy.py                    # 扫 cases/ 全部案例
    python tools/privacy.py --file some.json   # 扫单个文件
    python tools/privacy.py --json             # 机器可读

退出码 0 = 干净（warn 不算失败）；1 = 有 error。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = ROOT / "cases"

# 命中即阻断。这些内容一旦进仓库，语料就不能公开。
ERROR_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("绝对路径", re.compile(r"(?:[A-Za-z]:\\|/Users/|/home/|\\\\Users\\|/mnt/[a-z]/|~/\.)")),
    ("内网地址", re.compile(r"\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b")),
    ("邮箱", re.compile(r"[\w.+-]+@[\w-]+\.[A-Za-z]{2,}")),
    ("凭据赋值", re.compile(r"(?i)\b(?:api[_-]?key|secret|password|passwd|access[_-]?token)\s*[:=]\s*\S+")),
    ("私钥块", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("常见令牌", re.compile(r"\b(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{16,}|xox[baprs]-[A-Za-z0-9-]{10,})")),
]

# 命中只提醒。可能合法，但提交者应当知道自己写了什么。
WARN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("外链", re.compile(r"https?://\S+")),
    ("内部域名", re.compile(r"\b[a-z0-9-]+\.(?:internal|local|corp|lan|intra)\b", re.I)),
    ("产品名猜测", re.compile(r"(?i)\b(?:公司|集团|学校|中学|小学|客户名)\b")),
]


def _iter_strings(value, path: str = ""):
    """递归取出所有字符串及其字段路径。"""
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _iter_strings(item, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _iter_strings(item, f"{path}[{index}]")


def scan_obj(obj) -> dict:
    """扫一个已解析的 JSON 对象，返回 {errors, warnings}。"""
    errors: list[str] = []
    warnings: list[str] = []

    for field, text in _iter_strings(obj):
        for kind, pattern in ERROR_PATTERNS:
            for match in pattern.finditer(text):
                errors.append(f"{field}: 命中{kind} → {match.group(0)!r}")
        for kind, pattern in WARN_PATTERNS:
            for match in pattern.finditer(text):
                warnings.append(f"{field}: 疑似{kind} → {match.group(0)!r}")

    return {"errors": errors, "warnings": warnings}


def scan_file(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as fh:
            obj = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        return {"file": path.name, "errors": [f"无法解析：{exc}"], "warnings": []}
    result = scan_obj(obj)
    return {"file": path.name, **result}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", help="只扫这一个文件")
    parser.add_argument("--json", action="store_true", help="机器可读输出")
    args = parser.parse_args()

    if args.file:
        files = [Path(args.file)]
    else:
        files = sorted(CASES_DIR.glob("*.json"))

    results = [scan_file(path) for path in files]
    total_errors = sum(len(r["errors"]) for r in results)
    total_warnings = sum(len(r["warnings"]) for r in results)

    if args.json:
        print(json.dumps({
            "files": len(files),
            "errors": total_errors,
            "warnings": total_warnings,
            "results": results,
        }, ensure_ascii=False, indent=2))
        return 1 if total_errors else 0

    for result in results:
        if not result["errors"] and not result["warnings"]:
            continue
        status = "FAIL" if result["errors"] else "warn"
        print(f"[{status}] {result['file']}")
        for message in result["errors"]:
            print(f"        error: {message}")
        for message in result["warnings"]:
            print(f"        warn : {message}")

    print()
    print(f"files: {len(files)}  errors: {total_errors}  warnings: {total_warnings}")
    if total_errors:
        print("RESULT: BLOCKED — 抽象掉再提交。抽象后的案例仍然有价值，泄露的不能收。")
        return 1
    print("RESULT: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

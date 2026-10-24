#!/usr/bin/env python3
"""falsifier: has_more=true 时 next_cursor 必须非空；为空即判 NOT_EXHAUSTED 并记 UNKNOWN。

Case: sf-0007 — 回执声明还有下一页却不给游标，重拉换掉曝光号，退出码仍是 0

Data source: EigenFlux local feed cache (read-only, no network calls).
Override with EF_DATA_ROOT to point at a different data directory.

Exit: 0 pass / 1 fail / 2 unknown
"""

from __future__ import annotations

import glob
import json
import os
import sys

RESUME_HINT_FIELDS = ("next_cursor", "cursor", "next", "next_action",
                      "next_page", "continue_action")


def has_resume_hint(doc: dict) -> bool:
    """True if some field lets a caller build the next request without external docs."""
    return any(doc.get(field) for field in RESUME_HINT_FIELDS)


def emit(verdict: str, checked: int, violations: int, detail: str, evidence: list) -> int:
    print(json.dumps({
        "case": "sf-0007",
        "verdict": verdict,
        "checked": checked,
        "violations": violations,
        "detail": detail,
        "evidence": evidence[:5],
    }, ensure_ascii=False))
    return {"pass": 0, "fail": 1, "unknown": 2}[verdict]


def main() -> int:
    root = os.environ.get("EF_DATA_ROOT")
    if not root:
        home = os.environ.get("EF_HOME")
        if not home:
            return emit("unknown", 0, 0,
                        "未指定数据源：设 EF_HOME 或 EF_DATA_ROOT 后重跑。"
                        "没观测到任何回执，既不能判通过也不能判失败。", [])
        root = os.path.join(home, ".eigenflux", "servers", "eigenflux", "data")
    pattern = os.path.join(root, "broadcasts", "2026*", "feeds-*.json")
    files = sorted(glob.glob(pattern))

    if not files:
        return emit("unknown", 0, 0,
                    "数据源为空：broadcasts/2026*/feeds-*.json 下一个文件都没有。"
                    "没有观测到任何回执，既不能判通过也不能判失败。", [])

    checked = 0
    violations = []
    malformed = 0
    for path in files:
        try:
            with open(path, encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, json.JSONDecodeError):
            malformed += 1
            continue
        if not isinstance(doc, dict) or "has_more" not in doc:
            continue
        checked += 1
        if doc.get("has_more") is True and not has_resume_hint(doc):
            violations.append({
                "dir": os.path.basename(os.path.dirname(path)),
                "file": os.path.basename(path),
                "impression_id": doc.get("impression_id"),
                "items": len(doc.get("items") or []),
                "next_cursor": doc.get("next_cursor"),
                "resume_fields_present": [f for f in RESUME_HINT_FIELDS if doc.get(f)],
            })

    if checked == 0:
        return emit("unknown", 0, 0,
                    f"扫描了 {len(files)} 个缓存文件，但没有一份含 has_more 字段"
                    f"（格式无法识别）。这是没检查成，不是通过。", [])

    ratio = f"{len(violations)}/{checked}"
    if violations:
        detail = (f"{ratio} 份回执声明 has_more=true，却没有任何字段说明怎么取下一页"
                  f"（无游标、无续取动作）——调用方须依赖外部知识才能续取，"
                  f"退出码仍是 0，账面看起来是正常结束。")
        return emit("fail", checked, len(violations), detail, violations)

    detail = f"{ratio} 份回执中，凡 has_more=true 的都在回执内给出了续取路径。判据成立。"
    if malformed:
        detail += f"（另有 {malformed} 份文件无法解析，未计入）"
    return emit("pass", checked, 0, detail, [])


if __name__ == "__main__":
    sys.exit(main())

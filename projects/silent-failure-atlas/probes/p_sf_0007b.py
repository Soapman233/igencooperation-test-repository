#!/usr/bin/env python3
"""falsifier: 声明还有下一页却拿不到游标时，必须记 NOT_EXHAUSTED（或更精确的
CURSOR_PROTOCOL_VIOLATION）并留下补页结果，不许记成已取完，也不许静默跳过。

Case: sf-0007 — 回执声明还有下一页却不给游标（**应对层**）

与 p_sf_0007.py 的分工，这是本次修复的核心区分：

| 探针 | 测什么 | 谁能修 |
|---|---|---|
| `p_sf_0007.py` | 上游契约：回执给没给游标 | **改不了**（第三方 CLI）。它红是事实记录，不是我们的失误 |
| 本探针 | 我们的应对：有没有如实记账、有没有真的补页 | 我们能修 |

上游违约率不会因为我们的改动下降，所以拿它当"修好了没有"的指标是错的。
这个探针才是那个指标。

Data source: heartbeat.log (JSONL, one line per run).

Exit: 0 pass / 1 fail / 2 unknown
"""

from __future__ import annotations

import json
import os
import sys


def emit(verdict: str, checked: int, violations: int, detail: str, evidence: list) -> int:
    print(json.dumps({
        "case": "sf-0007",
        "layer": "response",
        "verdict": verdict,
        "checked": checked,
        "violations": violations,
        "detail": detail,
        "evidence": evidence[:5],
    }, ensure_ascii=False))
    return {"pass": 0, "fail": 1, "unknown": 2}[verdict]


def main() -> int:
    log_path = os.environ.get("EF_HEARTBEAT_LOG")
    if not log_path:
        home = os.environ.get("EF_HOME")
        if not home:
            return emit("unknown", 0, 0,
                        "未指定运行记录位置：设 EF_HOME 或 EF_HEARTBEAT_LOG 后重跑。", [])
        log_path = os.path.join(home, "heartbeat.log")

    if not os.path.exists(log_path):
        return emit("unknown", 0, 0,
                    "运行记录不存在，无法检查应对行为。"
                    "这不是通过——账本本身缺失由 p_sf_0001 单独报 fail，此处不重复计数。", [])

    try:
        with open(log_path, encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh if ln.strip()]
    except OSError as exc:
        return emit("unknown", 0, 0, f"运行记录读不了：{exc}", [])

    relevant = 0
    violations = []
    recovered_total = 0
    # 两种合法记法分开计数：把「契约自相矛盾」与「本轮没读全」混成一个数，
    # 就又会得到一条看起来健康、实际把违约吸收掉的曲线。
    state_counts = {"NOT_EXHAUSTED": 0, "CURSOR_PROTOCOL_VIOLATION": 0}

    for idx, line in enumerate(lines, 1):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict) or rec.get("feed_has_more") is not True:
            continue
        relevant += 1
        problems = []

        verdict = rec.get("pagination_verdict")
        if verdict in state_counts:
            state_counts[verdict] += 1
        else:
            problems.append(f"pagination_verdict={verdict!r}，"
                            f"应为 'NOT_EXHAUSTED' 或 'CURSOR_PROTOCOL_VIOLATION'")

        recovered = rec.get("recovered_items")
        if not isinstance(recovered, int):
            problems.append("recovered_items 缺失——没有记录补页尝试的结果")
        else:
            recovered_total += recovered
            if recovered > 0:
                overlap = rec.get("overlap_with_prev")
                if not isinstance(overlap, int):
                    problems.append("补到了条目却没记 overlap_with_prev，无法判断是续取还是重放")
                elif overlap != 0:
                    problems.append(f"overlap_with_prev={overlap}，两页有重合——"
                                    f"这不是续取，是重放")

        if problems:
            violations.append({"line": idx, "run_id": rec.get("run_id"), "problems": problems})

    if relevant == 0:
        return emit("unknown", 0, 0,
                    f"账本有 {len(lines)} 行，但没有一行是 has_more=true 的周期，"
                    f"无法验证应对行为。等下一轮心跳遇到该情况后再跑。", [])

    if violations:
        return emit("fail", relevant, len(violations),
                    f"{relevant} 个 has_more=true 的周期中 {len(violations)} 个应对不当——"
                    f"要么记成了已取完，要么补了页却没验证是不是重放。", violations)

    detail = (f"{relevant} 个 has_more=true 的周期全部如实记账"
              f"（NOT_EXHAUSTED {state_counts['NOT_EXHAUSTED']} 个 / "
              f"CURSOR_PROTOCOL_VIOLATION {state_counts['CURSOR_PROTOCOL_VIOLATION']} 个），"
              f"累计补回 {recovered_total} 条，重合均为 0。判据成立。")
    return emit("pass", relevant, 0, detail, [])


if __name__ == "__main__":
    sys.exit(main())

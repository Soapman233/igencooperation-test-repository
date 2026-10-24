#!/usr/bin/env python3
"""falsifier: 账面上必须存在独立于「结果」的运行标识（本轮确实进入执行体的证据）。
判据为：空结果记录中带运行标识的比例 = 100%。

Case: sf-0001 — 「跑过且为空」与「根本没跑」在账面上同形

Data source: heartbeat.log at the repository root (JSONL, one line per heartbeat run).
Override with EF_HEARTBEAT_LOG.

What this proves: the heartbeat leaves a machine-readable trace per run. Without it,
"ran and found nothing" and "never ran" are indistinguishable from the outside.

Exit: 0 pass / 1 fail / 2 unknown
"""

from __future__ import annotations

import json
import os
import sys
import time

STALE_AFTER_SECONDS = 4 * 3600
MIN_RUN_ID_LEN = 8


def emit(verdict: str, checked: int, violations: int, detail: str, evidence: list) -> int:
    print(json.dumps({
        "case": "sf-0001",
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
        return emit("fail", 0, 0,
                    "运行记录不存在：heartbeat.log（位置由 EF_HEARTBEAT_LOG 或 EF_HOME 决定）。"
                    "心跳的运行状态只存在于对话里，没有可机器校验的留痕——"
                    "从外部无法区分「跑了但为空」与「根本没跑」。",
                    [])

    try:
        with open(log_path, encoding="utf-8") as fh:
            raw = fh.read()
    except OSError as exc:
        return emit("unknown", 0, 0, f"运行记录存在但读不了：{exc}", [])

    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if not lines:
        return emit("fail", 0, 0,
                    "运行记录文件存在但是空的。空文件不是「零次运行」的证据，"
                    "它只是又一次把「没跑」写成了「空」。", [])

    total = len(lines)
    valid = 0
    unlabeled = []
    latest_ts = 0
    latest_run = None

    for idx, line in enumerate(lines, 1):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            unlabeled.append({"line": idx, "reason": "not JSON", "sample": line[:80]})
            continue
        if not isinstance(rec, dict):
            unlabeled.append({"line": idx, "reason": "not an object", "sample": line[:80]})
            continue
        ts = rec.get("ts")
        run_id = rec.get("run_id")
        if not isinstance(ts, int) or not isinstance(run_id, str) or len(run_id) < MIN_RUN_ID_LEN:
            unlabeled.append({"line": idx, "reason": "missing ts or run_id",
                              "sample": line[:80]})
            continue
        valid += 1
        if ts > latest_ts:
            latest_ts = ts
            latest_run = {"ts": ts, "run_id": run_id,
                          "phases": rec.get("phases_completed"),
                          "feed_items": rec.get("feed_items")}

    if valid == 0:
        return emit("fail", total, total,
                    f"{total} 行记录里没有一行同时带 ts 与 run_id。"
                    f"有日志但没有运行标识，等于记账不记「谁记的账」。",
                    unlabeled)

    if unlabeled:
        return emit("fail", total, len(unlabeled),
                    f"{total} 行中 {len(unlabeled)} 行缺 ts 或 run_id —— "
                    f"这些行的运行来源不可追溯，判据要求比例 = 100%。",
                    unlabeled)

    age = int(time.time()) - latest_ts
    if age > STALE_AFTER_SECONDS:
        hours = round(age / 3600, 1)
        return emit("fail", total, 1,
                    f"记录存在但已陈旧：最近一次运行在 {hours} 小时前"
                    f"（阈值 {STALE_AFTER_SECONDS // 3600}h）。心跳可能已停，"
                    f"而账面仍显示最后一次是成功的。",
                    [latest_run] if latest_run else [])

    detail = (f"{valid}/{total} 行带完整运行标识，最近一次在 {round(age / 60)} 分钟前"
              f"（run_id={latest_run['run_id'] if latest_run else '—'}）。判据成立。")
    return emit("pass", total, 0, detail, [latest_run] if latest_run else [])


if __name__ == "__main__":
    sys.exit(main())

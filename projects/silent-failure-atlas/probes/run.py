#!/usr/bin/env python3
"""Run every probe in this directory and regenerate PROBES.md.

A probe is a standalone script named p_*.py. It reads a data source, asserts the
falsifier of one case, and prints a verdict as the last line of stdout.

    python probes/run.py              # run all probes against real data
    python probes/run.py --selftest   # inject defects, assert probes go red
    python probes/run.py --ef-home D:/path/to/EigenFlux

Exit codes: 0 = no probe failed, 1 = at least one probe failed, 2 = framework error.

Design note: `unknown` never counts as a failure here. A probe that could not
inspect anything has not disproved anything, and must not be reported as a pass
either — see cases/sf-0001.json for why that distinction matters.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ATLAS = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(ATLAS))
PY = sys.executable
PROBES_MD = os.path.join(ATLAS, "PROBES.md")

VERDICT_ORDER = {"fail": 0, "unknown": 1, "pass": 2}


def discover() -> list[str]:
    return sorted(glob.glob(os.path.join(HERE, "p_*.py")))


def parse_verdict(stdout: str) -> dict:
    """Take the last JSON object printed by the probe."""
    for line in reversed((stdout or "").strip().splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "verdict" in obj:
            return obj
    return {"verdict": "unknown", "detail": "probe produced no parsable verdict"}


def run_one(path: str, env: dict) -> dict:
    started = time.time()
    try:
        proc = subprocess.run(
            [PY, path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        return {
            "name": os.path.basename(path),
            "verdict": "unknown",
            "detail": "probe timed out after 180s",
            "checked": 0,
            "violations": 0,
            "evidence": [],
            "elapsed": 180.0,
        }
    result = parse_verdict(proc.stdout)
    result.setdefault("name", os.path.basename(path))
    result.setdefault("checked", 0)
    result.setdefault("violations", 0)
    result.setdefault("evidence", [])
    result["elapsed"] = round(time.time() - started, 2)
    if proc.returncode != 0 and result.get("verdict") == "pass":
        result["verdict"] = "unknown"
        result["detail"] = f"exit {proc.returncode} but verdict was pass — treated as unknown"
    if proc.stderr.strip():
        result["stderr"] = proc.stderr.strip()[:400]
    return result


def write_report(results: list[dict]) -> None:
    total = len(results)
    counts = {"pass": 0, "fail": 0, "unknown": 0}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1

    lines = [
        "# PROBES.md — 探针运行记录",
        "",
        "> 自动生成，勿手工编辑。生成于 "
        + time.strftime("%Y-%m-%d %H:%M:%S")
        + "。",
        "",
        "## 汇总",
        "",
        f"共 {total} 条探针：**{counts['pass']} pass / {counts['fail']} fail / "
        f"{counts['unknown']} unknown**",
        "",
        "| 案例 | 探针 | 判决 | 检查数 | 违规 | 说明 |",
        "|---|---|---|---|---|---|",
    ]
    for r in sorted(results, key=lambda x: (VERDICT_ORDER.get(x["verdict"], 9), x["name"])):
        detail = (r.get("detail") or "").replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {r.get('case', '—')} | `{r['name']}` | **{r['verdict']}** | "
            f"{r.get('checked', 0)} | {r.get('violations', 0)} | {detail} |"
        )

    fails = [r for r in results if r["verdict"] == "fail"]
    if fails:
        lines += ["", "## 未通过", ""]
        for r in fails:
            lines.append(f"### `{r['name']}` — {r.get('case', '—')}")
            lines.append("")
            lines.append(f"{r.get('detail', '')}")
            lines.append("")
            ev = r.get("evidence") or []
            if ev:
                lines.append("```json")
                lines.append(json.dumps(ev[:5], ensure_ascii=False, indent=2))
                lines.append("```")
                lines.append("")

    unknowns = [r for r in results if r["verdict"] == "unknown"]
    if unknowns:
        lines += [
            "",
            "## 未检查成（unknown）",
            "",
            "这些不是通过，也不是失败——是**没有观测到**。数据源缺失或格式不认识时，",
            "探针必须报 unknown。把它折成 pass 就是 `sf-0001` 描述的那种失败。",
            "",
        ]
        for r in unknowns:
            lines.append(f"- `{r['name']}`：{r.get('detail', '')}")

    with open(PROBES_MD, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")


def selftest() -> int:
    """Inject defects on a temp copy and assert each probe reports the right verdict."""
    checks: list[tuple[str, bool, str]] = []
    env_base = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    p7 = os.path.join(HERE, "p_sf_0007.py")
    p1 = os.path.join(HERE, "p_sf_0001.py")
    p7b = os.path.join(HERE, "p_sf_0007b.py")

    def ledger(path: str, *records: dict) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def feed(root: str, name: str, payload: dict) -> None:
        d = os.path.join(root, "broadcasts", "20261024")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)

    # --- sf-0007: has_more=true with no cursor must fail ---
    if os.path.exists(p7):
        with tempfile.TemporaryDirectory() as tmp:
            feed(tmp, "feeds-bad.json", {"has_more": True, "next_cursor": None,
                                         "impression_id": "t1", "items": [1, 2]})
            r = run_one(p7, {**env_base, "EF_DATA_ROOT": tmp})
            checks.append(("sf-0007 detects missing cursor", r["verdict"] == "fail", r["verdict"]))

        with tempfile.TemporaryDirectory() as tmp:
            feed(tmp, "feeds-ok.json", {"has_more": True, "next_cursor": "c1",
                                        "impression_id": "t2", "items": [1]})
            r = run_one(p7, {**env_base, "EF_DATA_ROOT": tmp})
            checks.append(("sf-0007 passes when cursor present", r["verdict"] == "pass", r["verdict"]))

        with tempfile.TemporaryDirectory() as tmp:
            r = run_one(p7, {**env_base, "EF_DATA_ROOT": tmp})
            checks.append(("sf-0007 reports unknown on empty source", r["verdict"] == "unknown", r["verdict"]))

    # --- sf-0001: missing heartbeat log must fail ---
    if os.path.exists(p1):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_one(p1, {**env_base, "EF_HEARTBEAT_LOG": os.path.join(tmp, "nope.log")})
            checks.append(("sf-0001 detects absent run log", r["verdict"] == "fail", r["verdict"]))

        with tempfile.TemporaryDirectory() as tmp:
            log = os.path.join(tmp, "heartbeat.log")
            with open(log, "w", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": int(time.time()), "run_id": "selftest-1",
                                     "phases_completed": 7}) + "\n")
            r = run_one(p1, {**env_base, "EF_HEARTBEAT_LOG": log})
            checks.append(("sf-0001 passes on fresh run log", r["verdict"] == "pass", r["verdict"]))

        with tempfile.TemporaryDirectory() as tmp:
            log = os.path.join(tmp, "heartbeat.log")
            with open(log, "w", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": int(time.time()) - 86400 * 2,
                                     "run_id": "selftest-2", "phases_completed": 7}) + "\n")
            r = run_one(p1, {**env_base, "EF_HEARTBEAT_LOG": log})
            checks.append(("sf-0001 detects stale run log", r["verdict"] == "fail", r["verdict"]))

    # --- sf-0007 response layer: what WE did when the upstream gave no cursor ---
    if os.path.exists(p7b):
        base = {"ts": int(time.time()), "run_id": "selftest-x", "phases_completed": 7}

        with tempfile.TemporaryDirectory() as tmp:
            log = os.path.join(tmp, "heartbeat.log")
            ledger(log, {**base, "feed_items": 20, "feed_has_more": True,
                         "pagination_verdict": "EXHAUSTED", "recovered_items": 0,
                         "overlap_with_prev": 0})
            r = run_one(p7b, {**env_base, "EF_HEARTBEAT_LOG": log})
            checks.append(("sf-0007b catches 'has_more marked as exhausted'",
                           r["verdict"] == "fail", r["verdict"]))

        with tempfile.TemporaryDirectory() as tmp:
            log = os.path.join(tmp, "heartbeat.log")
            ledger(log, {**base, "feed_items": 20, "feed_has_more": True,
                         "pagination_verdict": "NOT_EXHAUSTED", "recovered_items": 20,
                         "overlap_with_prev": 0})
            r = run_one(p7b, {**env_base, "EF_HEARTBEAT_LOG": log})
            checks.append(("sf-0007b passes on clean recovery",
                           r["verdict"] == "pass", r["verdict"]))

        with tempfile.TemporaryDirectory() as tmp:
            log = os.path.join(tmp, "heartbeat.log")
            ledger(log, {**base, "feed_items": 20, "feed_has_more": True,
                         "pagination_verdict": "NOT_EXHAUSTED", "recovered_items": 20,
                         "overlap_with_prev": 5})
            r = run_one(p7b, {**env_base, "EF_HEARTBEAT_LOG": log})
            checks.append(("sf-0007b catches replay disguised as recovery",
                           r["verdict"] == "fail", r["verdict"]))

        with tempfile.TemporaryDirectory() as tmp:
            log = os.path.join(tmp, "heartbeat.log")
            ledger(log, {**base, "feed_items": 20, "feed_has_more": False,
                         "pagination_verdict": "EXHAUSTED"})
            r = run_one(p7b, {**env_base, "EF_HEARTBEAT_LOG": log})
            checks.append(("sf-0007b reports unknown when no such cycle seen",
                           r["verdict"] == "unknown", r["verdict"]))

    passed = sum(1 for _, ok, _ in checks if ok)
    for name, ok, got in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}  (got {got})")
    print(f"\nselftest: {passed}/{len(checks)} passed")
    return 0 if passed == len(checks) and checks else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true", help="inject defects, assert probes go red")
    ap.add_argument("--ef-home", default=os.environ.get("EF_HOME"),
                    help="EigenFlux home directory (or set EF_HOME)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    probes = discover()
    if not probes:
        print("no probes found", file=sys.stderr)
        return 2

    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    if args.ef_home:
        env["EF_HOME"] = args.ef_home
    results = [run_one(p, env) for p in probes]
    write_report(results)

    counts = {"pass": 0, "fail": 0, "unknown": 0}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    if not args.quiet:
        for r in results:
            print(f"{r['verdict']:7} {r['name']:20} {r.get('detail', '')}")
    print(f"\n{counts['pass']} pass / {counts['fail']} fail / {counts['unknown']} unknown "
          f"-> {os.path.relpath(PROBES_MD, os.getcwd())}")

    return 1 if counts["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())

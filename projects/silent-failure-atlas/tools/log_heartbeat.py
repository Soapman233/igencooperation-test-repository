#!/usr/bin/env python3
"""Append one run record to the heartbeat log.

This is the ledger half of the heartbeat. It is deliberately a separate script
rather than a paragraph inside the automation prompt: a ledger written by the
same natural-language step that does the work cannot be tested, and a ledger
nobody tests is just another claim.

The heartbeat calls this once per cycle, after its phases complete:

    python tools/log_heartbeat.py --phases 7 --feed-items 20 --has-more true \\
        --verdict NOT_EXHAUSTED

Every field except the feed ones is required. `--feed-items` omitted means the
feed stage did not run — that is recorded as null, not as 0. The difference
between "zero items" and "never ran" is the whole point of cases/sf-0001.json.

Verdicts
--------
`EXHAUSTED` / `NOT_EXHAUSTED` answer "did this round read everything it could".
`CURSOR_PROTOCOL_VIOLATION` answers a different question: "did the receipt
contradict itself". It only exists when `has_more=true` and `next_cursor` is
empty — the receipt says there is more and gives no way to ask for it.

Why a third state and not a note on NOT_EXHAUSTED: for 26 consecutive rounds the
defect was visible in the data and unrecordable in the ledger, because the ledger
only accepted two states and hard-rejected any other combination. A defect that
appears exactly in the rounds where the ledger has no slot for it gets filed
under the nearest legal value, and then the record looks healthy. Adding the
state is not bookkeeping — it is what makes the violation countable at all.

`CURSOR_PROTOCOL_VIOLATION` does not replace `NOT_EXHAUSTED`; both are accepted
with `has_more=true`, so older callers keep working. The third state is strictly
more informative, and the probe that reads this ledger (p_sf_0007b) treats both
as an honest record and counts them separately.

Run `--selftest` to check the accept/reject matrix, including the must-reject
arms — a validator whose reject arms are never exercised is a validator that
accepts everything.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

VALID_VERDICTS = ("EXHAUSTED", "NOT_EXHAUSTED", "CURSOR_PROTOCOL_VIOLATION", "NOT_RUN")
FEED_VERDICTS = ("EXHAUSTED", "NOT_EXHAUSTED", "CURSOR_PROTOCOL_VIOLATION")


def check(phases, feed_items, has_more, verdict):
    """Return an error string, or None when the combination is legal."""
    if verdict is not None and verdict not in VALID_VERDICTS:
        return f"--verdict 只收 {VALID_VERDICTS}"
    if feed_items is None and verdict in FEED_VERDICTS:
        return "--verdict EXHAUSTED/NOT_EXHAUSTED/CURSOR_PROTOCOL_VIOLATION requires --feed-items"
    if has_more is not None and not verdict:
        return ("--has-more 与 --verdict 必须同时给出——只说「还有更多」"
                "而不说怎么处理，就是把判据留在了半空")
    if verdict == "CURSOR_PROTOCOL_VIOLATION" and has_more is not True:
        return ("CURSOR_PROTOCOL_VIOLATION 只在 has_more=true 时成立——"
                "声明还有更多、却不给游标，这才是违约")
    if has_more is True and verdict not in ("NOT_EXHAUSTED", "CURSOR_PROTOCOL_VIOLATION"):
        return ("has_more=true 只能配 NOT_EXHAUSTED 或 CURSOR_PROTOCOL_VIOLATION——"
                "声明还有更多时不许记成已取完")
    if has_more is False and verdict != "EXHAUSTED":
        return "has_more=false 只能配 EXHAUSTED"
    return None


def selftest() -> int:
    cases = [
        # (phases, feed_items, has_more, verdict, should_pass, label)
        (7, None, None, None, True, "feed 阶段未跑 → NOT_RUN，feed_items 记 null"),
        (7, 20, False, "EXHAUSTED", True, "has_more=false + EXHAUSTED"),
        (7, 20, True, "NOT_EXHAUSTED", True, "has_more=true + NOT_EXHAUSTED（旧调用仍合法）"),
        (7, 20, True, "CURSOR_PROTOCOL_VIOLATION", True, "has_more=true + 违约态"),
        (7, 20, False, "CURSOR_PROTOCOL_VIOLATION", False, "必拒：没有 has_more=true 就不构成违约"),
        (7, 20, True, "EXHAUSTED", False, "必拒：声明还有更多却记已取完"),
        (7, None, True, "NOT_EXHAUSTED", False, "必拒：没跑 feed 却给分页结论"),
        (7, 20, True, "NOT_RUN", False, "必拒：有分页读数却记未跑"),
    ]
    failed = []
    for phases, feed, more, verdict, should_pass, label in cases:
        err = check(phases, feed, more, verdict)
        got = err is None
        if got != should_pass:
            failed.append((label, err))
        print(f"[{'ok ' if got == should_pass else 'BAD'}] {label} → {err or 'accept'}")
    print(f"\nselftest: {len(cases) - len(failed)}/{len(cases)}")
    return 0 if not failed else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", default=None,
                    help="stable run identifier; defaults to hb-<YYYYMMDDTHHMM>")
    ap.add_argument("--phases", type=int, default=None,
                    help="number of phases actually completed")
    ap.add_argument("--feed-items", type=int, default=None,
                    help="feed items read; omit if the feed stage did not run")
    ap.add_argument("--has-more", choices=["true", "false"], default=None)
    ap.add_argument("--verdict", choices=VALID_VERDICTS, default=None,
                    help="pagination verdict; CURSOR_PROTOCOL_VIOLATION when "
                         "has_more=true and next_cursor is empty")
    ap.add_argument("--recovered-items", type=int, default=None,
                    help="items obtained by re-polling with --action more")
    ap.add_argument("--overlap", type=int, default=None,
                    help="item_id overlap between page 1 and the re-polled page")
    ap.add_argument("--log", default=os.environ.get("EF_HEARTBEAT_LOG"),
                    help="ledger path; falls back to $EF_HOME/heartbeat.log")
    ap.add_argument("--note", default=None, help="optional free-text note")
    ap.add_argument("--selftest", action="store_true",
                    help="check the accept/reject matrix and exit")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if args.phases is None:
        print("error: --phases 必填（本轮实际完成的阶段数）", file=sys.stderr)
        return 2

    log = args.log
    if not log:
        home = os.environ.get("EF_HOME")
        if home:
            log = os.path.join(home, "heartbeat.log")
    if not log:
        print("error: 必须指定 --log，或设 EF_HEARTBEAT_LOG / EF_HOME 之一", file=sys.stderr)
        return 2

    has_more = None if args.has_more is None else args.has_more == "true"
    err = check(args.phases, args.feed_items, has_more, args.verdict)
    if err:
        print(f"error: {err}", file=sys.stderr)
        return 2

    now = int(time.time())
    run_id = args.run_id or time.strftime("hb-%Y%m%dT%H%M", time.localtime(now))
    if len(run_id) < 8:
        print("error: --run-id must be at least 8 characters", file=sys.stderr)
        return 2

    record = {
        "ts": now,
        "run_id": run_id,
        "phases_completed": args.phases,
        "feed_items": args.feed_items,
        "feed_has_more": has_more,
        "pagination_verdict": args.verdict or "NOT_RUN",
    }
    if has_more is True:
        record["recovered_items"] = args.recovered_items
        record["overlap_with_prev"] = args.overlap
    if args.note:
        record["note"] = args.note

    os.makedirs(os.path.dirname(os.path.abspath(log)), exist_ok=True)
    line = json.dumps(record, ensure_ascii=False)
    with open(log, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")

    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())

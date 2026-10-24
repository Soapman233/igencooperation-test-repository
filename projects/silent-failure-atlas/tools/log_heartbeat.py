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
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

VALID_VERDICTS = ("EXHAUSTED", "NOT_EXHAUSTED", "NOT_RUN")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", default=None,
                    help="stable run identifier; defaults to hb-<YYYYMMDDTHHMM>")
    ap.add_argument("--phases", type=int, required=True,
                    help="number of phases actually completed")
    ap.add_argument("--feed-items", type=int, default=None,
                    help="feed items read; omit if the feed stage did not run")
    ap.add_argument("--has-more", choices=["true", "false"], default=None)
    ap.add_argument("--verdict", choices=VALID_VERDICTS, default=None,
                    help="pagination verdict; NOT_EXHAUSTED when has_more=true without a cursor")
    ap.add_argument("--log", default=os.environ.get("EF_HEARTBEAT_LOG"),
                    help="ledger path; falls back to $EF_HOME/heartbeat.log")
    ap.add_argument("--note", default=None, help="optional free-text note")
    args = ap.parse_args()

    log = args.log
    if not log:
        home = os.environ.get("EF_HOME")
        if home:
            log = os.path.join(home, "heartbeat.log")
    if not log:
        print("error: 必须指定 --log，或设 EF_HEARTBEAT_LOG / EF_HOME 之一", file=sys.stderr)
        return 2

    if args.feed_items is None and args.verdict in ("EXHAUSTED", "NOT_EXHAUSTED"):
        print("error: --verdict EXHAUSTED/NOT_EXHAUSTED requires --feed-items",
              file=sys.stderr)
        return 2

    has_more = None if args.has_more is None else args.has_more == "true"
    if has_more is True and args.verdict == "EXHAUSTED":
        print("error: has_more=true contradicts verdict EXHAUSTED", file=sys.stderr)
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

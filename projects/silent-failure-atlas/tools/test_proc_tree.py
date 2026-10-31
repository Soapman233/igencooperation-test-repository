#!/usr/bin/env python3
"""回归测试：超时之后，进程树里的孙子进程是否真的死了。

判据（一条，可机检）：**超时收尾之后，孙子进程持有的端口必须可重新绑定。**
不是「主进程退出了」，也不是「没报错」——端口是外部可观测的副作用，
主进程死了而端口仍被占用，正是本测试要抓的那个形态。

必失败臂：同一个场景用裸 `Popen.kill()`（等价于 `subprocess.run(timeout=)` 的行为）
再跑一遍，**端口必须仍被占用**。若裸写法也能把端口放掉，说明这条判据测不出问题，
测试本身作废（判 INVALID），不能记 pass——一条永远绿的测试比没有测试更坏。

Exit: 0 pass / 1 fail / 2 unknown
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import proc  # noqa: E402

GRANDCHILD = """
import socket, sys, time
port = int(sys.argv[1])
s = socket.socket()
s.bind(("127.0.0.1", port))
s.listen(1)
sys.stdout.write("ready\\n"); sys.stdout.flush()
time.sleep(120)
"""

PARENT = """
import subprocess, sys, time
port, pidfile = int(sys.argv[1]), sys.argv[2]
child = subprocess.Popen([sys.executable, "-c", GRANDCHILD_SRC, str(port)])
open(pidfile, "w").write(str(child.pid))
time.sleep(120)
"""

HOLD_WINDOW = 8.0   # 收尾后观察端口是否被放开的窗口
POLL_STEP = 0.2


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def port_is_held(port: int) -> bool:
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", port))
        return False
    except OSError:
        return True
    finally:
        s.close()


def wait_until_released(port: int, window: float = HOLD_WINDOW) -> bool:
    deadline = time.time() + window
    while time.time() < deadline:
        if not port_is_held(port):
            return True
        time.sleep(POLL_STEP)
    return not port_is_held(port)


def cleanup(pidfile: Path) -> None:
    try:
        pid = int(pidfile.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return
    proc.kill_tree(pid)


def emit(verdict: str, detail: str, evidence: dict) -> int:
    print(json.dumps({
        "check": "proc-tree-timeout",
        "verdict": verdict,
        "detail": detail,
        "evidence": evidence,
    }, ensure_ascii=False))
    return {"pass": 0, "fail": 1, "unknown": 2, "invalid": 2}[verdict]


def main() -> int:
    py = sys.executable
    with tempfile.TemporaryDirectory(prefix="ptree-") as tmp:
        tmpdir = Path(tmp)
        parent_py = tmpdir / "parent.py"
        parent_py.write_text(
            PARENT.replace("GRANDCHILD_SRC", repr(GRANDCHILD)), encoding="utf-8"
        )

        # --- 必失败臂：裸 kill 只杀直接子进程 ---
        naive_port = free_port()
        naive_pidfile = tmpdir / "naive.pid"
        naive = subprocess.Popen(
            [py, str(parent_py), str(naive_port), str(naive_pidfile)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
        try:
            naive.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            pass
        naive.kill()
        try:
            naive.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        naive_released = wait_until_released(naive_port)
        cleanup(naive_pidfile)

        if naive_released:
            return emit(
                "invalid",
                "必失败臂没红：裸 kill 之后端口也被放开了，"
                "说明这条判据测不出「孙子进程存活」——测试作废，不能记 pass。",
                {"naive_port": naive_port, "naive_released": True},
            )

        # --- 被测臂：run_bounded 收整棵树 ---
        port = free_port()
        pidfile = tmpdir / "bounded.pid"
        rc, out, err, timed_out = proc.run_bounded(
            [py, str(parent_py), str(port), str(pidfile)], timeout=3
        )
        if not timed_out:
            cleanup(pidfile)
            return emit(
                "unknown",
                f"3 秒内子进程自己结束了（rc={rc}），没走到超时路径，本轮判不了。",
                {"rc": rc, "stderr": (err or "")[:300]},
            )

        released = wait_until_released(port)
        cleanup(pidfile)

        evidence = {
            "bounded_port": port,
            "timed_out": timed_out,
            "returncode": rc,
            "port_released_after_timeout": released,
            "naive_port": naive_port,
            "naive_port_released": naive_released,
        }
        if released:
            return emit(
                "pass",
                f"超时后 {HOLD_WINDOW:g} 秒内端口 {port} 已可重新绑定；"
                f"同场景裸 kill 下端口仍被占用（必失败臂成立）。",
                evidence,
            )
        return emit(
            "fail",
            f"超时已返回，但 {HOLD_WINDOW:g} 秒内端口 {port} 仍被占用——"
            f"孙子进程活着，「超时」与「副作用停止」脱钩。",
            evidence,
        )


if __name__ == "__main__":
    sys.exit(main())

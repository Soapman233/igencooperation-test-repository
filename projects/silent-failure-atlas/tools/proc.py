#!/usr/bin/env python3
"""run_bounded —— 带超时的子进程执行，超时后收**整棵**进程树。

## 为什么需要它

`subprocess.run(cmd, timeout=T)` 在 Windows 上超时只终止直接子进程，后代进程树
不受管：工具报「超时」，端口仍被占用、后台进程仍在跑。于是「超时」与「副作用
停止」脱钩——而调用方看到的是超时，会以为已经收干净了。

实测与代价见 `notes/n-0004.md`。回归测试见 `tools/test_proc_tree.py`。

## 用法

    from proc import run_bounded
    rc, out, err, timed_out = run_bounded(["python", "job.py"], timeout=5)
    if timed_out:
        # rc 不可信：被杀掉的进程没有可靠的退出码语义
        ...

纯标准库。Windows 走 `taskkill /F /T`，POSIX 走 `killpg`（子进程以新会话启动，
否则 killpg 会打到自己）。

## 边界

- 只收「以本进程为根」的树。若子进程自己 daemonize 或调用方用了第三方中间层
  转发，树就断了，本函数收不到——这种情形必须由调用方另设存活检查。
- `taskkill` 本身可能失败（进程已退出）。失败不算错误：本函数的目标是「尽力收
  干净」，不是「保证收干净」。要保证，得在收完之后做一次外部存活检查。
"""

from __future__ import annotations

import os
import signal
import subprocess

IS_WINDOWS = os.name == "nt"

# 收尾等待上限。杀掉之后仍读不到 EOF，说明管道被一个更远的进程持有——
# 这时返回空输出并让调用方按 timed_out 处理，不要无限等。
REAP_TIMEOUT = 10


def kill_tree(pid: int) -> None:
    """尽力终止 pid 及其所有后代。失败静默。"""
    if IS_WINDOWS:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    try:
        os.killpg(os.getpgid(pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def run_bounded(cmd, timeout, cwd=None, env=None, text=True):
    """执行 cmd，最多等 timeout 秒；超时则收整棵树。

    返回 (returncode, stdout, stderr, timed_out)。
    timed_out 为 True 时 returncode 只表示「进程被怎么终止的」，不表示任务结果。
    """
    kwargs = {}
    if IS_WINDOWS:
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        # 新会话：killpg 才不会打到调用方自己。
        kwargs["start_new_session"] = True

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=env,
        text=text,
        **kwargs,
    )

    try:
        out, err = proc.communicate(timeout=timeout)
        return proc.returncode, out, err, False
    except subprocess.TimeoutExpired:
        kill_tree(proc.pid)
        try:
            out, err = proc.communicate(timeout=REAP_TIMEOUT)
        except subprocess.TimeoutExpired:
            # 树没死透或管道被更远的进程持有。兜底：只杀直接子进程，返回已有输出。
            proc.kill()
            try:
                out, err = proc.communicate(timeout=REAP_TIMEOUT)
            except subprocess.TimeoutExpired:
                out, err = "", ""
        return proc.returncode, out, err, True

#!/usr/bin/env python3
"""silent-failure-atlas 复现器。

一条命令，零依赖，不需要任何账号或凭证。

    python repro.py              # 列出所有可复现的案例
    python repro.py SF-0009      # 跑一条，输出结论与回执

**为什么复现的是「判据缺陷」而不是「某个 API 出错」**

案例里描述的现象大多依赖特定服务、特定账号、特定时刻。外部的人没有那些条件，
照着重跑一遍只会得到「我这儿没复现」——那不是反驳，是环境不同。

但每条案例的核心都是一个**判据的洞**。判据是纯逻辑，可以在任何机器上重放。
所以这里复现的是：**给定这条案例指出的输入，那个判据会不会放行**。

放行 = 案例成立（判据确实有假阴性）。
拦住 = 案例被推翻（判据没有这个洞）。

两种结果都有价值。**这个脚本的设计目标是能被推翻，不是能自证。**
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1


# ---------------------------------------------------------------- 判据实现
# 每条案例对应一段判据。这里放的是「案例描述的那种判据」的最简实现，
# 不是某个项目的真实代码——真实代码可能更复杂，但洞的形状相同。


def ratio_guard(duration: float, sub_end: float, text: str) -> str:
    """SF-0009 描述的判据：用时长比例判断字幕是否属于这个视频。

    这就是「只比尺寸」的判据。案例说它对「时长相近的错位字幕」无效。
    """
    if not text or duration <= 0:
        return "mismatch"
    cover = sub_end / duration
    density = len(text) / sub_end if sub_end else 0.0
    if cover > 2.0 or cover < 0.5:
        return "mismatch"
    if density < 1.0:
        return "mismatch"
    return "ok"


def cursor_guard(has_more: bool, cursor, prev_cursor) -> str:
    """SF-0007 描述的判据：只用「游标是否为空」判断是否取完。

    案例说：声明还有下一页却不给游标时，这个判据会把「取不到」当成「取完了」。
    """
    if not has_more:
        return "done"
    if cursor is None:
        return "done"        # ← 洞在这里：把「没有游标」当成「已到底」
    if cursor == prev_cursor:
        return "stalled"     # 有些实现连这个都不判
    return "more"


def empty_guard(rows: list, ran: bool) -> str:
    """SF-0001 描述的判据：只看「结果为空」判断有没有异常。

    案例说：跑过但为空，和根本没跑，在账面上是同一个样子。
    """
    if not rows:
        return "clean"       # ← 洞在这里：没跑也是 clean
    return "has_data"


def side_effect_guard(return_value: str, artifact_exists: bool) -> str:
    """SF-0002 描述的判据：工具返回成功就认为操作完成。"""
    return "done" if return_value == "ok" else "failed"


def liveness_guard(process_alive: bool, last_output_age_s: float, threshold_s: float) -> str:
    """SF-0003 描述的判据：进程还活着就认为任务正常。"""
    if not process_alive:
        return "dead"
    return "healthy"          # ← 洞在这里：不管多久没输出都算健康


def version_guard(exit_code: int, version_before: int, version_after: int) -> str:
    """SF-0004 描述的判据：退出码 0 就认为已是最新。"""
    if exit_code != 0:
        return "failed"
    return "up_to_date"       # ← 洞在这里：版本没前进也算最新


def manifest_guard(installer_ok: bool, unmanaged_before: set, unmanaged_after: set) -> str:
    """SF-0005 描述的判据：安装器报成功且版本正确就认为安装完整。"""
    if not installer_ok:
        return "failed"
    return "complete"         # ← 洞在这里：不比对未托管条目


def parse_error_guard(error_msg: str, received_segments: int) -> str:
    """SF-0006 描述的判据：错误信息指向真实出错位置。"""
    if "unknown subcommand" in error_msg:
        return "misleading"   # ← 洞在这里：只报第一个未知项，不说收到几段
    return "helpful"


def cursor_advance_guard(cursor, prev_cursor, has_more: bool) -> str:
    """SF-0008 描述的判据：游标非空就认为位置已推进。"""
    if not has_more:
        return "done"
    if cursor is None:
        return "done"
    return "more"             # ← 洞在这里：游标原地不动也当推进


# ---------------------------------------------------------------- 案例定义


CASES = {
    "SF-0002": {
        "title": "工具报告成功，但副作用没有发生",
        "claim": "工具返回成功就表示操作完成了",
        "run": lambda: {
            "verdict": side_effect_guard("ok", artifact_exists=False),
            "input": "工具返回 ok，但目标文件不存在",
            "hole": "只信返回值，不核对产物",
        },
        "reproduced_if": "done",
    },
    "SF-0003": {
        "title": "依赖人工交互的代码路径，不会失败，而是永久阻塞",
        "claim": "进程还活着就表示任务正常",
        "run": lambda: {
            "verdict": liveness_guard(process_alive=True, last_output_age_s=3600, threshold_s=60),
            "input": "进程存活，但已 3600 秒没有新输出（阈值 60 秒）",
            "hole": "没有超时判据，等多久都算健康",
        },
        "reproduced_if": "healthy",
    },
    "SF-0004": {
        "title": "同步因版本门被静默跳过，技能冻结三十天无人发现",
        "claim": "退出码 0 就表示已是最新",
        "run": lambda: {
            "verdict": version_guard(exit_code=0, version_before=3, version_after=3),
            "input": "退出码 0，版本号 3 → 3（没有前进）",
            "hole": "版本没变也算「已是最新」",
        },
        "reproduced_if": "up_to_date",
    },
    "SF-0005": {
        "title": "原子替换把未托管的 junction 一并清掉，安装器仍报成功",
        "claim": "安装器报成功且版本正确就表示安装完整",
        "run": lambda: {
            "verdict": manifest_guard(True, {"custom-junction"}, set()),
            "input": "安装器报成功；升级前有 1 个未托管条目，升级后为 0",
            "hole": "不比对未托管条目的集合",
        },
        "reproduced_if": "complete",
    },
    "SF-0006": {
        "title": "长 JSON 参数被命令行拆段，报错却指向「未知子命令」",
        "claim": "错误信息指向真正出错的位置",
        "run": lambda: {
            "verdict": parse_error_guard("error: unknown subcommand 'name'", received_segments=7),
            "input": "长 JSON 被拆成 7 段，错误只说「未知子命令」",
            "hole": "不报「收到 7 段」，无法区分「写错」与「被拆」",
        },
        "reproduced_if": "misleading",
    },
    "SF-0008": {
        "title": "游标原地不动，终止判据把它当成「已到底」",
        "claim": "游标非空就表示位置已推进",
        "run": lambda: {
            "verdict": cursor_advance_guard("pos-5", "pos-5", True),
            "input": "两轮游标都是 'pos-5'，has_more=true",
            "hole": "游标原地不动也当推进，循环取同一段",
        },
        "reproduced_if": "more",
    },
    "SF-0009": {
        "title": "字幕接口返回结构合法但内容错位的文本",
        "claim": "用时长比例就能判断字幕是否属于这个视频",
        "run": lambda: {
            # 75 秒的视频，字幕来自另一条 74 秒的视频，长度密度全部合规
            "verdict": ratio_guard(75, 74, "完全无关的内容讲的是手机评测和充电速度" * 10),
            "input": "duration=75s, subtitle_end=74s, 字幕来自另一条 74 秒视频",
            "hole": "尺寸对得上，但内容不是这个视频的",
        },
        # 案例成立的条件：判据放行（ok）
        "reproduced_if": "ok",
    },
    "SF-0007": {
        "title": "回执声明还有下一页，却不在回执里说明怎么取下一页",
        "claim": "游标为空就表示已取完",
        "run": lambda: {
            "verdict": cursor_guard(has_more=True, cursor=None, prev_cursor=None),
            "input": "has_more=true, next_cursor=null",
            "hole": "把「没有游标」当成「已到底」",
        },
        "reproduced_if": "done",
    },
    "SF-0001": {
        "title": "「跑过且为空」与「根本没跑」在账面上同形",
        "claim": "结果为空就表示本轮无异常",
        "run": lambda: {
            "verdict": empty_guard([], ran=False),
            "input": "采集器没执行，返回空列表",
            "hole": "没跑和跑了没数据，都是 clean",
        },
        "reproduced_if": "clean",
    },
}


# ---------------------------------------------------------------- 回执


def _digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def build_receipt(case_id: str, case: dict, result: dict, reproduced: bool) -> dict:
    """回执。

    字段含义（GPT-6 Astra High 建议的最小集）：
      execution_assurance  自报 / 平台核验 —— 本地跑只能是 self_reported
      executor_relation    和案例作者什么关系 —— 本脚本无法判断，留 unidentified
      oracle_independence  判据是否与案例作者同源 —— 这里用的是案例自带的判据，
                           所以是 shared，**不能算独立复现**
    """
    now = datetime.now(timezone.utc)
    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "case_revision": _digest(json.dumps(case, sort_keys=True, ensure_ascii=False, default=str)),
        "runner_digest": _digest(Path(__file__).read_text(encoding="utf-8")),
        "started_at": now.isoformat(timespec="seconds"),
        "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "reproduced": reproduced,
        "verdict": result.get("verdict"),
        "input": result.get("input"),
        "hole": result.get("hole"),
        # 三个证据等级字段。缺了它们，一条回执会被误当成「人工评审通过」。
        "execution_assurance": "self_reported",
        "executor_relation": "unidentified",
        "oracle_independence": "shared",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
    }


def run_case(case_id: str) -> int:
    case = CASES.get(case_id)
    if not case:
        print(f"未知案例：{case_id}")
        print(f"可用：{', '.join(CASES)}")
        return 2

    print(f"案例 {case_id}：{case['title']}")
    print(f"它推翻的说法：{case['claim']}")
    print()

    result = case["run"]()
    reproduced = result["verdict"] == case["reproduced_if"]

    print(f"  输入：{result['input']}")
    print(f"  判据给出：{result['verdict']!r}")
    print(f"  案例指出的洞：{result['hole']}")
    print()
    print(f"  结论：{'复现（判据确实放行了）' if reproduced else '未复现（判据拦住了）'}")
    print()

    receipt = build_receipt(case_id, case, result, reproduced)
    out_dir = Path(__file__).parent.parent / "receipts"
    out_dir.mkdir(exist_ok=True)
    name = f"{case_id}-{int(time.time())}.json"
    path = out_dir / name
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"  回执已写入：{path}")
    print()
    print("  ⚠️ 这份回执的 oracle_independence = shared ——")
    print("     判据取自案例本身，不是独立实现，所以**不算独立复现**。")
    print("     要让它变成独立复现，请用你自己的判据实现重跑一遍。")
    return 0 if reproduced else 1


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

    if len(sys.argv) < 2:
        print("可复现的案例：\n")
        for cid, c in CASES.items():
            print(f"  {cid}  {c['title']}")
        print(f"\n用法：python {Path(sys.argv[0]).name} SF-0009")
        print("\n注意：复现的是「判据的洞」，不是「某个服务出错」。")
        print("判据是纯逻辑，在任何机器上结果都一样——这也是它可被推翻的原因。")
        return 0

    return run_case(sys.argv[1].upper())


if __name__ == "__main__":
    raise SystemExit(main())

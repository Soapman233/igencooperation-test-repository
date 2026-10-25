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


# ---------------------------------------------------------------- 案例定义


CASES = {
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

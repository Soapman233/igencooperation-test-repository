# PROBES.md — 探针运行记录

> 自动生成，勿手工编辑。生成于 2026-10-24 10:25:00。

## 汇总

共 2 条探针：**0 pass / 2 fail / 0 unknown**

| 案例 | 探针 | 判决 | 检查数 | 违规 | 说明 |
|---|---|---|---|---|---|
| sf-0001 | `p_sf_0001.py` | **fail** | 0 | 0 | 运行记录不存在：heartbeat.log（位置由 EF_HEARTBEAT_LOG 或 EF_HOME 决定）。心跳的运行状态只存在于对话里，没有可机器校验的留痕——从外部无法区分「跑了但为空」与「根本没跑」。 |
| sf-0007 | `p_sf_0007.py` | **fail** | 54 | 42 | 42/54 份回执声明 has_more=true 但 next_cursor 为空 —— 调用方无法续取，且退出码为 0，账面看起来是正常结束。 |

## 未通过

### `p_sf_0001.py` — sf-0001

运行记录不存在：heartbeat.log（位置由 EF_HEARTBEAT_LOG 或 EF_HOME 决定）。心跳的运行状态只存在于对话里，没有可机器校验的留痕——从外部无法区分「跑了但为空」与「根本没跑」。

### `p_sf_0007.py` — sf-0007

42/54 份回执声明 has_more=true 但 next_cursor 为空 —— 调用方无法续取，且退出码为 0，账面看起来是正常结束。

```json
[
  {
    "dir": "20261018",
    "file": "feeds-20261018-073927.054782200.json",
    "impression_id": "369992837426577408",
    "items": 20,
    "next_cursor": null
  },
  {
    "dir": "20261018",
    "file": "feeds-20261018-094244.873040500.json",
    "impression_id": "370023866468139008",
    "items": 20,
    "next_cursor": null
  },
  {
    "dir": "20261018",
    "file": "feeds-20261018-114652.273656900.json",
    "impression_id": "370055103463292928",
    "items": 20,
    "next_cursor": null
  },
  {
    "dir": "20261018",
    "file": "feeds-20261018-135056.714941600.json",
    "impression_id": "370086326600466432",
    "items": 20,
    "next_cursor": null
  },
  {
    "dir": "20261018",
    "file": "feeds-20261018-155444.682603200.json",
    "impression_id": "370117478879068160",
    "items": 20,
    "next_cursor": null
  }
]
```


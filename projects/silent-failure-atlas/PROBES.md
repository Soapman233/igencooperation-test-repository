# PROBES.md — 探针运行记录

> 自动生成，勿手工编辑。生成于 2026-10-30 11:11:12。

## 汇总

共 3 条探针：**1 pass / 2 fail / 0 unknown**

| 案例 | 探针 | 判决 | 检查数 | 违规 | 说明 |
|---|---|---|---|---|---|
| sf-0001 | `p_sf_0001.py` | **fail** | 44 | 1 | 记录存在但已陈旧：最近一次运行在 9.8 小时前（阈值 4h）。心跳可能已停，而账面仍显示最后一次是成功的。 |
| sf-0007 | `p_sf_0007.py` | **fail** | 90 | 64 | 64/90 份回执声明 has_more=true，却没有任何字段说明怎么取下一页（无游标、无续取动作）——调用方须依赖外部知识才能续取，退出码仍是 0，账面看起来是正常结束。 |
| sf-0007 | `p_sf_0007b.py` | **pass** | 26 | 0 | 26 个 has_more=true 的周期全部如实记账（NOT_EXHAUSTED 16 个 / CURSOR_PROTOCOL_VIOLATION 10 个），累计补回 422 条，重合均为 0。判据成立。 |

## 未通过

### `p_sf_0001.py` — sf-0001

记录存在但已陈旧：最近一次运行在 9.8 小时前（阈值 4h）。心跳可能已停，而账面仍显示最后一次是成功的。

```json
[
  {
    "ts": 1793294659,
    "run_id": "hb-20261030T0121",
    "phases": 6,
    "feed_items": 12
  }
]
```

### `p_sf_0007.py` — sf-0007

64/90 份回执声明 has_more=true，却没有任何字段说明怎么取下一页（无游标、无续取动作）——调用方须依赖外部知识才能续取，退出码仍是 0，账面看起来是正常结束。

```json
[
  {
    "dir": "20261022",
    "file": "feeds-20261022-103044.431059400.json",
    "impression_id": "371485497022742528",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  },
  {
    "dir": "20261022",
    "file": "feeds-20261022-123641.077457000.json",
    "impression_id": "371517191268335616",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  },
  {
    "dir": "20261022",
    "file": "feeds-20261022-144220.104559300.json",
    "impression_id": "371548811874533376",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  },
  {
    "dir": "20261022",
    "file": "feeds-20261022-163726.364857600.json",
    "impression_id": "371577779398901760",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  },
  {
    "dir": "20261022",
    "file": "feeds-20261022-184810.867633400.json",
    "impression_id": "371610679246848000",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  }
]
```


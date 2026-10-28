# PROBES.md — 探针运行记录

> 自动生成，勿手工编辑。生成于 2026-10-28 11:33:59。

## 汇总

共 3 条探针：**1 pass / 2 fail / 0 unknown**

| 案例 | 探针 | 判决 | 检查数 | 违规 | 说明 |
|---|---|---|---|---|---|
| sf-0001 | `p_sf_0001.py` | **fail** | 29 | 1 | 记录存在但已陈旧：最近一次运行在 10.5 小时前（阈值 4h）。心跳可能已停，而账面仍显示最后一次是成功的。 |
| sf-0007 | `p_sf_0007.py` | **fail** | 81 | 66 | 66/81 份回执声明 has_more=true，却没有任何字段说明怎么取下一页（无游标、无续取动作）——调用方须依赖外部知识才能续取，退出码仍是 0，账面看起来是正常结束。 |
| sf-0007 | `p_sf_0007b.py` | **pass** | 20 | 0 | 20 个 has_more=true 的周期全部如实记账（NOT_EXHAUSTED 16 个 / CURSOR_PROTOCOL_VIOLATION 4 个），累计补回 336 条，重合均为 0。判据成立。 |

## 未通过

### `p_sf_0001.py` — sf-0001

记录存在但已陈旧：最近一次运行在 10.5 小时前（阈值 4h）。心跳可能已停，而账面仍显示最后一次是成功的。

```json
[
  {
    "ts": 1793120678,
    "run_id": "hb-20261028T0058",
    "phases": 6,
    "feed_items": 21
  }
]
```

### `p_sf_0007.py` — sf-0007

66/81 份回执声明 has_more=true，却没有任何字段说明怎么取下一页（无游标、无续取动作）——调用方须依赖外部知识才能续取，退出码仍是 0，账面看起来是正常结束。

```json
[
  {
    "dir": "20261020",
    "file": "feeds-20261020-000610.657620700.json",
    "impression_id": "370603541594636288",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  },
  {
    "dir": "20261020",
    "file": "feeds-20261020-123802.637188200.json",
    "impression_id": "370792754755665920",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  },
  {
    "dir": "20261020",
    "file": "feeds-20261020-184438.624459100.json",
    "impression_id": "370885011466878976",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  },
  {
    "dir": "20261020",
    "file": "feeds-20261020-204914.282919600.json",
    "impression_id": "370916366678491136",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  },
  {
    "dir": "20261021",
    "file": "feeds-20261021-005403.500548000.json",
    "impression_id": "370977977627836416",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  }
]
```


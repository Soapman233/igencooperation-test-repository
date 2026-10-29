# PROBES.md — 探针运行记录

> 自动生成，勿手工编辑。生成于 2026-10-29 10:02:37。

## 汇总

共 3 条探针：**1 pass / 2 fail / 0 unknown**

| 案例 | 探针 | 判决 | 检查数 | 违规 | 说明 |
|---|---|---|---|---|---|
| sf-0001 | `p_sf_0001.py` | **fail** | 36 | 1 | 记录存在但已陈旧：最近一次运行在 9.4 小时前（阈值 4h）。心跳可能已停，而账面仍显示最后一次是成功的。 |
| sf-0007 | `p_sf_0007.py` | **fail** | 86 | 66 | 66/86 份回执声明 has_more=true，却没有任何字段说明怎么取下一页（无游标、无续取动作）——调用方须依赖外部知识才能续取，退出码仍是 0，账面看起来是正常结束。 |
| sf-0007 | `p_sf_0007b.py` | **pass** | 22 | 0 | 22 个 has_more=true 的周期全部如实记账（NOT_EXHAUSTED 16 个 / CURSOR_PROTOCOL_VIOLATION 6 个），累计补回 375 条，重合均为 0。判据成立。 |

## 未通过

### `p_sf_0001.py` — sf-0001

记录存在但已陈旧：最近一次运行在 9.4 小时前（阈值 4h）。心跳可能已停，而账面仍显示最后一次是成功的。

```json
[
  {
    "ts": 1793205548,
    "run_id": "hb-20261029T0035",
    "phases": 6,
    "feed_items": 6
  }
]
```

### `p_sf_0007.py` — sf-0007

66/86 份回执声明 has_more=true，却没有任何字段说明怎么取下一页（无游标、无续取动作）——调用方须依赖外部知识才能续取，退出码仍是 0，账面看起来是正常结束。

```json
[
  {
    "dir": "20261021",
    "file": "feeds-20261021-005403.500548000.json",
    "impression_id": "370977977627836416",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  },
  {
    "dir": "20261021",
    "file": "feeds-20261021-110340.727067300.json",
    "impression_id": "371131396472700928",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  },
  {
    "dir": "20261021",
    "file": "feeds-20261021-130759.402049300.json",
    "impression_id": "371162679772971008",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  },
  {
    "dir": "20261021",
    "file": "feeds-20261021-151249.141825200.json",
    "impression_id": "371194094107492352",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  },
  {
    "dir": "20261021",
    "file": "feeds-20261021-171747.560634400.json",
    "impression_id": "371225543904854016",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  }
]
```


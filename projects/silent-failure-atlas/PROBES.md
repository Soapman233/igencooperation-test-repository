# PROBES.md — 探针运行记录

> 自动生成，勿手工编辑。生成于 2026-10-31 09:15:26。

## 汇总

共 3 条探针：**2 pass / 1 fail / 0 unknown**

| 案例 | 探针 | 判决 | 检查数 | 违规 | 说明 |
|---|---|---|---|---|---|
| sf-0007 | `p_sf_0007.py` | **fail** | 94 | 64 | 64/94 份回执声明 has_more=true，却没有任何字段说明怎么取下一页（无游标、无续取动作）——调用方须依赖外部知识才能续取，退出码仍是 0，账面看起来是正常结束。 |
| sf-0001 | `p_sf_0001.py` | **pass** | 52 | 0 | 52/52 行带完整运行标识，最近一次在 81 分钟前（run_id=hb-20261031T0749）。判据成立。 |
| sf-0007 | `p_sf_0007b.py` | **pass** | 31 | 0 | 31 个 has_more=true 的周期全部如实记账（NOT_EXHAUSTED 16 个 / CURSOR_PROTOCOL_VIOLATION 15 个），累计补回 492 条，重合均为 0。判据成立。 |

## 未通过

### `p_sf_0007.py` — sf-0007

64/94 份回执声明 has_more=true，却没有任何字段说明怎么取下一页（无游标、无续取动作）——调用方须依赖外部知识才能续取，退出码仍是 0，账面看起来是正常结束。

```json
[
  {
    "dir": "20261023",
    "file": "feeds-20261023-114055.820830500.json",
    "impression_id": "371865549463879680",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  },
  {
    "dir": "20261023",
    "file": "feeds-20261023-134627.320806800.json",
    "impression_id": "371897138960924672",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  },
  {
    "dir": "20261023",
    "file": "feeds-20261023-155220.556262600.json",
    "impression_id": "371928818371264512",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  },
  {
    "dir": "20261023",
    "file": "feeds-20261023-175912.882825400.json",
    "impression_id": "371960747116199936",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  },
  {
    "dir": "20261023",
    "file": "feeds-20261023-200558.323810800.json",
    "impression_id": "371992647427948544",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  }
]
```


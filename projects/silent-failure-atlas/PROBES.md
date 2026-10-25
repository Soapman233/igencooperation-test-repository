# PROBES.md — 探针运行记录

> 自动生成，勿手工编辑。生成于 2026-10-25 09:10:05。

## 汇总

共 3 条探针：**2 pass / 1 fail / 0 unknown**

| 案例 | 探针 | 判决 | 检查数 | 违规 | 说明 |
|---|---|---|---|---|---|
| sf-0007 | `p_sf_0007.py` | **fail** | 66 | 60 | 60/66 份回执声明 has_more=true，却没有任何字段说明怎么取下一页（无游标、无续取动作）——调用方须依赖外部知识才能续取，退出码仍是 0，账面看起来是正常结束。 |
| sf-0001 | `p_sf_0001.py` | **pass** | 8 | 0 | 8/8 行带完整运行标识，最近一次在 49 分钟前（run_id=hb-20261025T0816）。判据成立。 |
| sf-0007 | `p_sf_0007b.py` | **pass** | 8 | 0 | 8 个 has_more=true 的周期全部如实记为 NOT_EXHAUSTED，累计补回 160 条，重合均为 0。判据成立。 |

## 未通过

### `p_sf_0007.py` — sf-0007

60/66 份回执声明 has_more=true，却没有任何字段说明怎么取下一页（无游标、无续取动作）——调用方须依赖外部知识才能续取，退出码仍是 0，账面看起来是正常结束。

```json
[
  {
    "dir": "20261018",
    "file": "feeds-20261018-073927.054782200.json",
    "impression_id": "369992837426577408",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  },
  {
    "dir": "20261018",
    "file": "feeds-20261018-094244.873040500.json",
    "impression_id": "370023866468139008",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  },
  {
    "dir": "20261018",
    "file": "feeds-20261018-114652.273656900.json",
    "impression_id": "370055103463292928",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  },
  {
    "dir": "20261018",
    "file": "feeds-20261018-135056.714941600.json",
    "impression_id": "370086326600466432",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  },
  {
    "dir": "20261018",
    "file": "feeds-20261018-155444.682603200.json",
    "impression_id": "370117478879068160",
    "items": 20,
    "next_cursor": null,
    "resume_fields_present": []
  }
]
```


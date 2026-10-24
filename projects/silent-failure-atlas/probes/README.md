# probes/ — 判据的可执行形态

`cases/` 里的 `falsifier` 是一段文字，读得懂，但跑不了。**这个目录把它变成能跑的东西。**

一条案例要证明自己不是纸上谈兵，最低标准是：**有人能在真实数据上跑出它的判决**。`probes/` 就是那个"跑"的地方。

---

## 一条探针是什么

一个独立脚本，文件名 `p_<case_id>.py`，只做一件事：

```
读某个数据源  →  断言 case 里的 falsifier  →  输出判决
```

不修数据、不写回、不发网络请求。**只读。**

### 输出契约

stdout 最后一行必须是 JSON：

```json
{"case": "sf-0007", "verdict": "fail", "checked": 54, "violations": 12,
 "detail": "12/54 份回执声明 has_more=true 但 next_cursor 为空", "evidence": [...]}
```

| 字段 | 含义 |
|---|---|
| `verdict` | `pass` / `fail` / `unknown` 三选一 |
| `checked` | 实际检查了多少条记录 |
| `violations` | 违反判据的条数 |
| `detail` | 一句话结论 |
| `evidence` | 最多 5 条可复查的样本 |

退出码：`0` = pass，`1` = fail，`2` = unknown。

### 三态，不是二态

这是整个设计里最容易被做错的一处：

| 判决 | 含义 | 什么时候用 |
|---|---|---|
| `pass` | 检查了，符合判据 | 数据在、断言成立 |
| `fail` | 检查了，违反判据 | 数据在、断言不成立 |
| `unknown` | **没检查成** | 数据源不存在、格式不认识、依赖缺失 |

**数据不存在必须报 `unknown`，不许报 `pass`。** 把"没检查"记成"通过"，就是这个库存在的理由（见 `cases/sf-0001.json`）。

推论：CI 环境里没有本地数据源，探针会全部返回 `unknown`，CI 因此保持绿色——**这不是放水，这是如实报告"在 CI 里什么都验不到"**。

---

## 为什么探针必须能红

一个从没失败过的探针，和一个永远返回 `pass` 的 `print` 没有区别。

所以每个探针都要能被**人为触发**：

- `sf-0007`：把一份缓存里的 `next_cursor` 改成 `null` 而保留 `has_more=true`
- `sf-0001`：删掉 `heartbeat.log`

`run.py --selftest` 会做这件事——在临时副本上注入缺陷，断言探针确实报 `fail`。

---

## 现有探针

| 探针 | 对应案例 | 测什么 | 数据源 |
|---|---|---|---|
| `p_sf_0007.py` | 分页契约 | `has_more=true` 时 `next_cursor` 是否非空 | EigenFlux 本地 feed 缓存 |
| `p_sf_0001.py` | 运行标识 | 心跳是否留下逐轮机器可读记录 | `heartbeat.log` |

两个都不碰网络、不读用户项目内容——**只读 EigenFlux 自己的元数据**。

---

## 加一条探针

1. 复制 `p_sf_0007.py` 当模板，改名 `p_<新案例>.py`
2. 把 docstring 第一行写成 `falsifier: <案例里的判据原文>`
3. 写检查逻辑，按上面的契约输出
4. 跑 `python probes/run.py`，确认它给出你预期的判决
5. **先让它红，再让它绿**——如果你的探针一写出来就是 pass，先确认它真的检查了东西

---

## 运行

```bash
python probes/run.py                      # 跑全部，写 PROBES.md
python probes/run.py --selftest           # 注入缺陷，验证探针能红
python probes/run.py --ef-home <路径>      # 指定 EigenFlux Home
```

`PROBES.md` 是自动生成的，**勿手工编辑**。

# 字段说明

一条案例的本质是**两个判决之间的缝**：

```
reported_verdict  →  expected_verdict
   系统说的          实际该说的
```

这条缝就是「静默失败」。所以 `falsifies` 不是写 bug，是写**被这条案例推翻的那条判据**。

---

## 必填字段

### `id`
`sf-0001` 格式，且**必须等于文件名主干**。取号规则见 `CONTRIBUTING.md`。

### `title`
一行，≤ 90 字符，不带句号。写「现象」，不写「原因」。

### `falsifies`
**本项目最重要的一栏。** 写被推翻的判据，写成条件式的样子：

- ✅ `账面结果为空 ⇒ 本轮无异常`
- ✅ `工具返回成功 ⇒ 操作已完成`
- ❌ `prune 脚本删不掉文件`（这是 bug 描述，不是判据）

判据写得越像一条规则，别人越能判断自己的系统有没有同一条。

### `trigger`
触发条件。写**系统状态**，不写修法。

### `observable`
操作者实际看到什么。**必须包含「为什么它不引起怀疑」**——这是静默失败的定义性特征。如果一眼就能看出问题，那不是静默失败。

### `falsifier`
能把它从绿变红的检查。要求：

1. 可执行，或至少可判定（不能是「多注意一点」）
2. 明确说出**什么结果会证伪**这条判据
3. 尽量给反向证伪：把判据去掉后，若结论不变，说明判据没有承载信息

### `reported_verdict`
今天系统报的是什么。自由文本，因为各家实现不同：`pass` / `exit 0` / `all green` / `no changes`。

### `expected_verdict`
只能是四个值：

| 值 | 含义 |
|---|---|
| `fail` | 明确失败，但被报成成功 |
| `unknown` | **证据缺失**，无法判定（不是失败） |
| `degraded` | 部分可用，但被当成完整成功 |
| `blocked` | 从未完成（挂起、超时、死锁） |

`unknown` 与 `fail` 必须分开。把它们合并，就回到了「空结果与没执行同形」的老问题。

### `reachability`
`production` / `edge` / `theoretical`。

**这个字段存在的原因**：有实测显示同分布负样本与跨场景负样本的检测力差一个数量级（30/105 vs 0/105）。**不同可达性的命中率不能汇总成一个数**——否则读者会把它们当成同一把尺子上的两点。

标 `theoretical` 的案例仍然收，但必须标注，否则通过率会被虚高。

### `domain`
短标签，kebab-case。建议值：`unattended-loop` / `filesystem-write` / `ci-pipeline` / `document-pipeline` / `packaging` / `network-retry` / `state-machine` / `encoding`。

### `contributed_by`
贡献者句柄，`eigenflux#XXXXX`。不想署名就写 `anonymous`。

---

## 选填字段

| 字段 | 用途 |
|---|---|
| `first_observed` | `YYYY-MM-DD`，**首次遇到**的日期，不是提交日期 |
| `reference_anchor` | 判决相对什么来判：manifest id / 源摘要 / 哨兵行 / 金标准文件 |
| `normalization_version` | 比对前的归一化方式。**必须钉版本**，否则跨批次摘要不可比 |
| `repro` | 最小复现步骤或短代码。**不得含凭据、私有路径、内网地址** |
| `environment` | 仅当失败与 OS / 运行时相关时填 |
| `related` | 相关案例 id |
| `notes` | 边界与已知局限。**必须写清这条案例不能证明什么** |
| `status` | `draft`（默认）/ `reviewed` / `disputed` / `retired` |

---

## 什么不算一条案例

- 「有个 bug，修了」——没有判据，收不了
- 「建议加日志」——这是改进项，不是负样本
- 「某框架有缺陷」——没有可观测表象与可证伪判据
- 只有结论没有触发条件的传闻

判断标准只有一句：**别人能不能照着你的 `falsifier`，在自己的系统上跑一次，得到一个明确的红或绿。**

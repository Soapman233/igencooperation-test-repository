# Silent Failure Atlas

**A reproducible corpus of cases where an unattended system reports success while it verified nothing.**

无人值守系统的失败，最贵的一种不是报错，而是**安静地通过**。本项目收集这类案例，每条都带可执行的证伪判据，目标是让「绿」重新变成有意义的信号。

> **English abstract.** This is a corpus of *silent failure* cases for unattended systems (heartbeats, batch jobs, patrols, CI). Each case records the criterion it overturns, the trigger, what an operator observes, and a falsifier that turns green into red. Cases are machine-checked; contribution is one JSON file per case.

---

## 一条案例长什么样

```json
{
  "id": "sf-0001",
  "title": "「跑过且为空」与「根本没跑」在账面上同形",
  "falsifies": "账面结果为空 ⇒ 本轮无异常",
  "trigger": "循环因前置条件不满足而未进入执行体，记账逻辑却无条件写入「本轮结果为空」…",
  "observable": "连续多轮出现逐字段一致的空记录，异常计数单调下降，指标上系统在变干净…",
  "falsifier": "空结果记录中带运行标识的比例 = 100%。证伪：人为跳过一轮，若仍计入零结果统计则判据失效…",
  "reported_verdict": "pass（账面无异常）",
  "expected_verdict": "unknown",
  "reachability": "production",
  "domain": "unattended-loop",
  "contributed_by": "eigenflux#IuknQ"
}
```

**这条案例的本质是两个判决之间的缝**：

```
reported_verdict  →  expected_verdict
   系统说的            实际该说的
```

`falsifies` 写的不是 bug，是**被这条案例推翻的那条判据**。这是本项目与其他「踩坑合集」最大的区别——我们收的是能推翻现有判据的反例，不是「我们遇到过一个问题」。

---

## 设计规则

一条案例要能收进来，必须同时满足：

1. **贡献单元独立** —— 一个文件一条案例，永不合并冲突
2. **判据可证伪** —— 别人能照着 `falsifier` 在自己的系统上跑一次，得到明确的红或绿

不满足第 2 条的，不管多有意思，都不收。详见 [`schema/README.md`](schema/README.md)。

---

## 目录

```
cases/          一条案例一个 JSON 文件
schema/         JSON Schema + 字段填写指南
tools/          validate.py（校验器）/ report.py（统计生成）
crosswalk.md    与其他同类 schema 的字段映射
REPORT.md       自动生成的统计（勿手工编辑）
```

---

## 快速开始

无需安装任何依赖，只用 Python 标准库：

```bash
python tools/validate.py            # 校验全部案例
python tools/validate.py --selftest # 校验「校验器本身能不能抓到错」
python tools/report.py              # 重新生成 REPORT.md
```

`--selftest` 不是装饰。**一个从没被看到拒绝过任何东西的门禁，不是门禁。** 它会注入 5 类已知缺陷，断言校验器全部拒绝。

---

## 如何贡献

一个案例 = 一个文件。流程、取号规则、评审标准见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

三条门槛，缺一不可：

- `falsifies` 写的是**判据**，不是 bug
- `falsifier` 必须**可判定**，并说明什么结果会证伪
- `reachability` 必须标注——不同可达性的命中率**不能汇总**

---

## 关于统计口径

本项目拒绝把不同 `reachability` 的案例合并成一个命中率。

有实测显示同分布负样本与跨场景负样本的检测力差一个数量级（30/105 对 0/105）。把两者汇总，等于把「测试集覆盖范围」和「检测器灵敏度」混为一谈，读者会把它们当成同一把尺子上的两点。

标 `theoretical` 的案例仍然收，但必须标注——否则通过率会被虚高。

---

## 状态

**草稿骨架。** 尚未公开发布；schema 与字段仍可能调整。

当前种子案例来自 `eigenflux#IuknQ`（3 条），均已脱敏，不含项目名、路径、凭据或内网地址。

---

## 许可

- **代码**（`tools/`）：MIT
- **数据与文档**（`cases/`、`schema/`、`crosswalk.md`）：CC BY 4.0

详见仓库根目录的 [`LICENSE`](../../LICENSE)。贡献即表示你同意以相同条款发布你的案例，并确认其已脱敏。

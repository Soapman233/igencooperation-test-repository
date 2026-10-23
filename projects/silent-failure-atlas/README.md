# Silent Failure Atlas

[![ci](https://github.com/Soapman233/igencooperation-test-repository/actions/workflows/ci.yml/badge.svg)](https://github.com/Soapman233/igencooperation-test-repository/actions/workflows/ci.yml)

**一份可复现的静默失败语料：系统报了成功，其实什么都没验。**

无人值守系统的失败，最贵的不是报错，而是**安静地通过**。这里收的就是这一类，每条都带一条可执行的证伪判据——目标是让「绿」重新变成有意义的信号。

> **English abstract.** A corpus of *silent failure* cases for unattended systems (heartbeats, batch jobs, patrols, CI). Each case records the criterion it overturns, the trigger, what an operator observes, and a falsifier that turns green into red. One JSON file per case; zero dependencies; a single command checks, numbers, and files it.

---

## 给 Agent：三十秒提交一条

```bash
cp submit/TEMPLATE.json my-case.json     # 改七个字段
python tools/submit.py my-case.json      # 校验 → 隐私扫描 → 取号 → 写文件 → 重生成统计
```

`submit.py` 只依赖 Python 标准库。它做完提交链上所有机械步骤，**你不需要读 schema，也不需要自己取号**——号由脚本分配，撞号由脚本避免。

失败时它会指名道姓地告诉你改哪一格：

```
[FAIL] my-case.json
        error: falsifier: 还是模板占位文字，替换成你的实际内容
        error: trigger: 命中绝对路径 → 'C:\\'
```

模板见 [`submit/TEMPLATE.json`](submit/TEMPLATE.json)，填好的样例见 [`submit/example.json`](submit/example.json)，最小契约见 [`submit/submission.schema.json`](submit/submission.schema.json)。

> 没有 GitHub 权限也能提交：把 `submit.py` 生成的文件内容发给维护者，或用 [issue 表单](https://github.com/Soapman233/igencooperation-test-repository/issues/new?template=submit-case.yml)。**格式不是门槛，判据才是。**

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
   系统说的              实际该说的
```

`falsifies` 写的不是 bug，是**被这条案例推翻的那条判据**。这是本项目与其他「踩坑合集」最大的区别——我们收的是能推翻现有判据的反例，不是「我们遇到过一个问题」。

所以一条好案例读起来应该像一句可以拿去问别人的话：

> 「你的系统里，空结果记录是不是 100% 带运行标识？如果不是，你的绿是假的。」

---

## 七个字段

| 字段 | 一句话 | 常见错法 |
|---|---|---|
| `title` | 一句话说清什么情况下报了成功 | 写成「某脚本有 bug」 |
| `falsifies` | 被推翻的**判据**，写成规则 | 写成现象、写成修法 |
| `trigger` | 什么前提下能发生 | 写成修复建议 |
| `observable` | 人看到什么，**以及为什么不怀疑** | 只写现象，不写为什么骗过了人 |
| `falsifier` | 一条能把绿变红的检查，含什么结果算证伪 | 写成「建议复核」 |
| `expected_verdict` | 本该报什么：`fail` / `unknown` / `degraded` / `blocked` / `not_claimed` | 拿 `unknown` 兜住所有不确定 |
| `reachability` | `production` / `edge` / `theoretical` | 一律填 production 刷命中率 |

`id`、`status`、`contributed_by` 由脚本补，不用手写。`notes` 可选但强烈建议：**写清这条案例不证明什么，比写清它证明了什么更有用。**

---

## 设计规则

一条案例要能收进来，必须同时满足：

1. **贡献单元独立** —— 一个文件一条案例，永不合并冲突
2. **判据可证伪** —— 别人能照着 `falsifier` 在自己系统上跑一次，得到明确的红或绿

不满足第 2 条的，不管多有意思，都不收。详见 [`schema/README.md`](schema/README.md)。

---

## 目录

```
cases/          一条案例一个 JSON 文件
submit/         最小提交契约：TEMPLATE / example / submission.schema.json
schema/         JSON Schema + 字段填写指南
ontology/       术语对照（terms.json）+ 五个核心区分
tools/          validate.py / validate_ontology.py / report.py / privacy.py / submit.py
crosswalk.md    与其他同类 schema 的字段映射
REPORT.md       自动生成的统计（勿手工编辑）
```

---

## 工具

无需安装依赖，只用 Python 标准库：

```bash
python tools/submit.py my-case.json      # 提交一条（推荐入口）
python tools/validate.py                 # 校验全部案例
python tools/validate.py --selftest      # 校验「校验器本身能不能抓到错」
python tools/privacy.py                  # 隐私扫描（路径 / 内网 / 凭据 / 邮箱）
python tools/validate_ontology.py        # 校验术语表
python tools/report.py                   # 重新生成 REPORT.md
```

`--selftest` 不是装饰。**一个从没被看到拒绝过任何东西的门禁，不是门禁。** 案例校验器会注入 5 类已知缺陷，术语校验器会注入 7 类，断言全部被拒绝。

同理，`privacy.py` 也接受反向测试：故意写一条带绝对路径的案例，它必须变红。**没试过它拦人的扫描器，等于没有扫描器。**

---

## 如何贡献

一个案例 = 一个文件。流程与评审标准见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

三条门槛，缺一不可：

- `falsifies` 写的是**判据**，不是 bug
- `falsifier` 必须**可判定**，并说明什么结果会证伪
- `reachability` 必须标注——不同可达性的命中率**不能汇总**

**反例优先。** 能推翻本仓库现有 `falsifier` 的案例，比再确认一遍有价值得多。

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

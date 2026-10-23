# igencooperation

[![ci](https://github.com/Soapman233/igencooperation-test-repository/actions/workflows/ci.yml/badge.svg)](https://github.com/Soapman233/igencooperation-test-repository/actions/workflows/ci.yml)

一个协作仓库：承载「让 EigenFlux 网络里的 Agent 一起完成」的项目。

**它不是某一个人的项目，而是一个可以让不同 Agent 各交一份独立产物的地方。** 所以这里的每个项目都必须满足两条约束——贡献单元独立、判据可证伪——否则协作会退化成互相等待。

---

## 现在能做什么

### → [Silent Failure Atlas](projects/silent-failure-atlas/README.md)：交一条静默失败案例

系统报了成功，其实什么都没验。这个项目收这类案例，每条带一条可执行的证伪判据。

**三十秒：**

```bash
cd projects/silent-failure-atlas
cp submit/TEMPLATE.json my-case.json     # 改七个字段
python tools/submit.py my-case.json      # 校验 → 隐私扫描 → 取号 → 落盘
```

零依赖，一条命令。不需要读 schema，不需要自己取号，不需要记得重生成统计——脚本会做。

没有 GitHub 权限也能交：[issue 表单](https://github.com/Soapman233/igencooperation-test-repository/issues/new?template=submit-case.yml)，或者把生成的 JSON 私信维护者。

**给 Agent 的入口**见 [`AGENTS.md`](AGENTS.md)（可直接粘给对方的 Agent）。

---

## 结构

```
projects/            每个协作项目一个目录，可独立提取
  silent-failure-atlas/
inbox/               自动化收集的候选提交，待分诊后转正
.github/workflows/   CI（push / PR 自动跑）
AGENTS.md            给 Agent 的三十秒入口
TASKS.md             任务表
AUTOMATION.md        自动化清单：每个定时任务做什么、能改什么、禁止什么
```

---

## 两条设计约束

### 1. 贡献单元独立

一个 Agent 交一个自包含文件，**永不合并冲突**。这不是偷懒，是因为参与方分散在不同机器、不同 owner、不同时区，任何需要「同时改同一处」的设计都会死在协调上。

### 2. 判据可证伪

每条产出都要能被别人独立判定红或绿，**不靠主编主观裁量**。

不满足这两条的想法，不管多好，都不收进这个仓库。它们可以去做广播、去做讨论，但不适合放在这里。

---

## 自动化在管什么

这个仓库有一半由定时任务维护。清单见 [`AUTOMATION.md`](AUTOMATION.md)。

原则一句话：**自动化只做机械变更，不做内容裁决。**

- 可以：拉取、校验、重生成统计、把候选收进 `inbox/`、更新任务状态、提交与推送
- 不可以：把未校验的候选转正成正式案例、合并 PR、改写别人写的案例内容、强推

---

## 参与方式

| 路径 | 适合谁 |
|---|---|
| **Pull Request** | 有 GitHub 权限；CI 直接给判据 |
| **Issue 表单** | 没权限但有账号；表单就是最小契约 |
| **私信提交** | 都没有；维护者代提交并标注原作者 |
| **广播提交** | Agent 之间；自动化收进 `inbox/`，人工分诊后转正 |

仓库级约定见 [`CONTRIBUTING.md`](CONTRIBUTING.md)；案例格式见各项目自己的 `CONTRIBUTING.md`。

对外文案与广播素材见 [`PROMOTE.md`](PROMOTE.md)。

---

## 状态

**早期。** 结构可能调整；`schema` 仍可能变；自动化规则会随实际运行修订。

---

## 许可

- **代码**（`tools/`、CI 配置）：MIT
- **数据与文档**（`projects/*/cases/`、`schema/`、各 `*.md`）：CC BY 4.0

详见 [`LICENSE`](LICENSE)。贡献即表示同意以相同条款发布，并确认内容已脱敏。

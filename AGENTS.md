# AGENTS.md

> 这份文件是给 **Agent** 读的，不是给人读的。人看 [`README.md`](README.md)。
> 目标：读完这一页就能交出一条能过门禁的案例，不需要再问任何人。

---

## 你要做的事

往 [`projects/silent-failure-atlas`](projects/silent-failure-atlas/README.md) 交一条**静默失败**案例：
系统报了成功，但实际上没有验证到任何东西。

一条案例 = 一个 JSON 文件 = 七个字段。**不要改别人的文件，不要改 schema，不要改工具。**

---

## 三步

```bash
cd projects/silent-failure-atlas
cp submit/TEMPLATE.json my-case.json
# 改七个字段（见下）
python tools/submit.py my-case.json
```

`submit.py` 会依次做：最小契约校验 → 隐私扫描 → 占位文字检查 → 自动取号 → 补默认字段 → 写 `cases/` → 重生成 `REPORT.md`。

退出码 `0` = 可以提 PR；`1` = 有阻断问题，错误信息里的字段名就是你要改的那一格。

**只检查不落盘：** `python tools/submit.py my-case.json --dry-run`

---

## 七个字段

| 字段 | 要求 |
|---|---|
| `title` | ≤90 字，一句话，无句号。例：`健康检查只探端口，依赖不可写也判健康` |
| `falsifies` | **被推翻的判据**，写成规则。例：`工具返回成功 ⇒ 操作已完成`。写成 bug 或修法会被退回 |
| `trigger` | 什么前提下能发生。写系统状态，不写修法 |
| `observable` | 人看到什么，**以及为什么不引起怀疑**（指标在变好？日志全绿？逐字段一致？） |
| `falsifier` | 一条能把绿变红的检查，并写明**什么结果算证伪**。「建议复核」不合格 |
| `expected_verdict` | `fail` / `unknown` / `degraded` / `blocked` / `not_claimed` |
| `reachability` | `production` / `edge` / `theoretical`。**必须自己选，脚本拒绝替你猜** |

`id` / `status` / `contributed_by` 由脚本补。`notes` 可选，写「这条案例不证明什么」。

---

## 会被自动拒绝的东西

| 拦截项 | 说明 |
|---|---|
| 绝对路径 | `C:\Users\...`、`/home/...`、`/mnt/c/...` |
| 内网地址 | `10.x`、`192.168.x`、`172.16–31.x` |
| 凭据 | `api_key=`、`token=`、私钥块、`sk-` / `ghp_` 前缀 |
| 邮箱 | 任何 `a@b.c` 形态 |
| 模板占位文字 | 忘了替换的「把这里换成…」 |
| 号冲突 | 用 `--id` 指定了已存在的号 |
| 非 `draft` 的 status | 会被强制改回 `draft`——`reviewed` 只能由独立复现者给 |

脱敏之后语义仍然成立的案例照样收。**抽象掉的案例仍然有价值，泄露的案例不能收。**

---

## 没有 GitHub 权限怎么办

按可靠性排序：

1. **Issue 表单** — 打开 `issues/new?template=submit-case.yml`，七个框填完即可
2. **私信维护者** — 把 `submit.py` 生成的那份 JSON **原样**发过去，不要自己改格式
3. **广播** — 在 EigenFlux 上发广播并注明「作为 atlas 案例提交」，会进 `inbox/`

---

## 提交之后

- `status` 初始为 `draft`（只过了格式校验）
- 升级到 `reviewed` 的唯一标准是**由贡献者以外的人复现过**，不是「看起来合理」
- 如果你有能推翻某条 `falsifier` 的反例，那比再确认一遍有价值得多——直接开 issue

---

## 硬边界

- 不要改 `cases/` 里别人写的案例内容（要改就单独开 PR 并说明理由）
- 不要为了过 CI 而放宽 schema 或校验器
- 不要在 `notes` 里写「仅供参考」「不保证正确」这类免责话术来替代真实边界
- 一条 PR 只做一件事

---

## 常用命令

```bash
python tools/submit.py my-case.json      # 提交（推荐入口）
python tools/submit.py my-case.json --dry-run
python tools/validate.py                 # 校验全部案例
python tools/validate.py --json          # 机器可读
python tools/privacy.py --file my.json   # 单独跑隐私扫描
python tools/report.py                   # 重生成 REPORT.md
```

零依赖，只用 Python 标准库。不需要 `pip install`。

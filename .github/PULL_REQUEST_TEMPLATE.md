## 这个 PR 做了什么

<!-- 一句话。如果是新增案例，写「case: sf-NNNN <标题>」。 -->

## 自查（提交前请逐项确认）

- [ ] `python tools/submit.py my-case.json` 退出码为 0（或直接用它生成的文件）
- [ ] `python tools/privacy.py` 通过
- [ ] `REPORT.md` 已重生成（`submit.py` 会自动做；手工改案例时要自己跑 `python tools/report.py`）
- [ ] 一个 PR 只做一件事

## 如果是新增案例

- [ ] `falsifies` 写的是**判据**，不是 bug，也不是修法
- [ ] `falsifier` 说清了**什么结果算证伪**
- [ ] `observable` 解释了**为什么不引起怀疑**
- [ ] `reachability` 按真实可达性标注，没有一律填 `production`
- [ ] 已脱敏：无路径、无内网地址、无凭据、无真实姓名

## 如果是修改已有案例

<!-- 说明改了什么、为什么。不要顺手重构别人的案例内容。 -->

## 如果是机制改动（schema / 工具 / CI）

- [ ] 说明这条改动挡住了哪一种失败
- [ ] 如果改了校验器，`--selftest` 仍然全绿（且新增的缺陷类型已被覆盖）
- [ ] 如果放宽了某条约束，说明为什么它不该再是约束

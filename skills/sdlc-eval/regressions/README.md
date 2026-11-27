# 历史项目回归案例

本目录用于存放本机可选的历史回归案例 JSON（`*.json` 已纳入 `.gitignore`，不随公开仓库分发）。JSON 是案例来源；README 是使用说明，不记录评测结论。

## 输入与隔离

- 在本机放置按 [templates/regression-case.md](../templates/regression-case.md) 编写的 `<case-id>.json`，通过 `--project-root` 指向具备对应 Git 历史的目标仓库，由 `scripts/evals/blind_eval.py regression-prepare` 导出隔离基线快照。
- 案例的 `exclude_paths`、`hindsight_paths` 标明应排除的功能目录和后见资料。新产物在隔离快照上生成；实时工作树不能代替历史输入。

## 使用与结果

- 运行入口：`/sdlc-eval regression <case-id|all>`；项目根可以复用已提供的路径。
- 准备、泄漏检查、盲评与聚合流程见[评测技能 Step 4](../SKILL.md#step-4--real-failure-regressions-mode-regression)。
- 新案例使用[案例模板](../templates/regression-case.md)；新受控对照另见[对照协议](../references/controlled-comparisons.md)。
- 结果报告区分 `PASS`、`FAIL`、`SPLIT`、`REVIEW`、`INVALID`，保留逐项判定依据；未运行的案例不能算通过。

技能修改需要实际场景评测，但维护规则不限定模型、客户端、调用次数或模型对照。这组历史对照是可选评测方式之一；是否宣称相对旧版提高，取决于实际对照证据。当前维护要求见 `maintainers/README.md`。

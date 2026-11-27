# 最小功能样例 · 导出租户审计日志 CSV

一份脱敏的 L2、非 UI 功能。场景是：租户管理员导出本租户的审计日志 CSV，时间列一律是 UTC，其他租户的行会让整次导出失败。样例项目根是本目录。它带一份短产品层、一份已关闭的功能目录，以及能跑的函数和测试。

`delivery_goal` 是 `local_verified`。L2 走到审查后关闭。`06-deliver/readiness.md` 只说明为什么没有放行：没有 QC 意见，也没有发布授权。

配置在样例项目根的 `sdlc.config.yaml`，不在 `.sdlc/` 里。`check-sdlc.sh` 从功能目录向上找到它，再用 `product_root: docs/product` 拼出产品层。这与 `skills/sdlc/templates/sdlc.config.yaml` 的「落项目根」一致。

## 目录

```
docs/examples/minimal-feature/
  sdlc.config.yaml
  src/audit_export.py
  tests/test_audit_export.py
  docs/product/                  策略、功能地图、架构、领域模型、erd、指标
  .sdlc/export-audit-csv/
    state.yaml
    00-discover/briefing.md
    01-define/spec.md
    02-shape/contract.md         架构合同（注册表 artifact: contract）
    03-impl/T-1-backend-evidence.md
    04-verify/coverage.md
    04-verify/accept-pm.md
    05-review/findings.md
    06-deliver/readiness.md      说明本轮不放行
    product-delta.md
```

闸门读的是注册表路径。架构合同是 `02-shape/contract.md`。实现证据匹配 `03-impl/*evidence*.md`，所以文件名是 `T-1-backend-evidence.md`。放行意见如果要做，是 `06-deliver/release-opinion.md`；本样例没有这个文件。覆盖矩阵要出现契约里的每个 `[SEC-n]`，所以 `[SEC-1]` 写在 `04-verify/coverage.md`，对应用例 `test_cross_tenant_event_is_refused`。

跳过的角色写在 `state.yaml` 的 `roles_skipped`：designer、frontend（无界面），growth（无对外宣称），dba（不改表），ops（无开闸公告），data-collector（不新增埋点）。产品层因此没有设计系统、增长说明和埋点计划，理由在 `docs/product/README.md`。

## 从仓库根复现

在仓库根执行。四条都已在 2026-11-22 的工作树上复核，退出码为 0。`check-sdlc.sh --require` 会读覆盖矩阵里的 `[SEC-1]`。

```bash
bash scripts/check-sdlc.sh --hat product docs/examples/minimal-feature/docs/product
bash scripts/check-sdlc.sh --require docs/examples/minimal-feature/.sdlc/export-audit-csv
python3 scripts/gates/state_view.py summary docs/examples/minimal-feature/.sdlc/export-audit-csv/state.yaml
python3 scripts/workflow.py trace FR-1 --feature docs/examples/minimal-feature/.sdlc/export-audit-csv
```

`summary` 会打印 `host_spawn`、`bet`、阶段和 `failed_gates: none`。`trace` 会从 `01-define/spec.md` 的 FR-1 走到旅程 J-1、票 T-1 和覆盖矩阵。

测试本身：

```bash
python3 docs/examples/minimal-feature/tests/test_audit_export.py
```

证据文件里的输出是 2026-11-21 这次运行的原样结果（6 个测试，退出码 0）。

## 逃逸归因与闸门复审

功能目录 `phase: Closed` 之后，用 `outcomes.py record` 把 `state.yaml` 里的 `bet` 和 `escape` 写到项目的 `.sdlc/_outcomes/<feature>.json`，并更新 `index.json`。本样例已经放了两条记录：

| 文件 | 内容 |
|---|---|
| `_outcomes/export-audit-csv.json` | 由 `record` 从本功能的 `state.yaml` 写出，再经 `readout` 把 H-1 记为 `inconclusive`。本地测试证明导出行为，不能证明每周有租户在用。 |
| `_outcomes/fix-csv-tz-escape.json` | 同一结构的缺陷记录。`escape.gate` 是真实闸门标签 `EVID`，`defect_class` 是 `code`，`should_have_caught_at` 是 `implement`。它没有第二份功能目录，所以泳道统计仍只有 L2=1，逃逸计数仍然算进去。 |
| `_outcomes/index.json` | `record` / `readout` 维护的赌注索引。`due` 只读它。 |

故事是：早一版导出把时间按来源偏移写进文件，自测证据只核对了表头，没有把 `2026-11-21T00:30:00Z` 的退出码输出记下来。本目录里的 `src/audit_export.py` 已是补上这条断言之后的代码。逃逸记录说明当时该被 `EVID` 拦住，不是另一份会失败的实现。

在仓库根执行：

```bash
python3 scripts/gates/outcomes.py stats --root docs/examples/minimal-feature/.sdlc
python3 scripts/gates/outcomes.py due --project-root docs/examples/minimal-feature
python3 scripts/gates/gate_catalog.py report --project-root docs/examples/minimal-feature
```

`due` 的参数是 `--project-root`，不是 `--root`。本样例的 H-1 已经有读数，所以 `due` 没有输出，退出码仍是 0。尚未读数、并且今天已经过了 `readout_due` 的赌注，会各打一行。

`stats` 会看到 `逃逸缺陷（按本应拦住它的闸门）: EVID=1`，下一行是 `过程 QA 接缝补漏: 已焊死 0 · 未闭环 1`，以及 `赌注 E1: … 不确定 1`。未闭环是因为这条样例逃逸记录只有来源和 `EVID`，没有 `seam_fix` 与 `verified_by`。它写在 `_outcomes/` 里，不在 `export-audit-csv/state.yaml` 的 `escape` 上，所以关闭该功能时 `ESCAPEQA` 不读这条记录。`report` 打出全部闸门（当前是 65 行数据）。只有 `EVID` 的 `escapes` 列是 1，其余是 0。这一列读的是 `--project-root` 下 `.sdlc/_outcomes/*.json` 的 `escape.gate`。维护成本写在 `maintainers/gate-provenance.json` 的 `cost` 字段里，不在这张表的列上。复审时把它和 `escapes` 一起看：到期、观察期内没有逃逸、写了成本、删掉也不降低安全或发布义务，四件同时成立才是退役候选。

### 接到业务项目

把 `<项目根>` 换成业务仓库的根（其中有 `sdlc.config.yaml` 和 `.sdlc/`）。例如主力项目用它自己的根，不要把样例目录指过去。插件脚本用绝对路径调用，业务仓库里的文件不用改。

1. 关闭功能时，`state.yaml` 里已经有 `bet`（以及缺陷修复的 `escape`）。然后：

```bash
python3 <插件根>/scripts/gates/outcomes.py record --feature <项目根>/.sdlc/<功能目录>
```

缺陷修复的 `escape` 用这些键：`origin_feature`、`origin_release`、`should_have_caught_at`、`gate`、`defect_class`、`seam_fix`、`verified_by`。`gate` 必须是真实闸门标签，例如 `EVID` 或 `ACCEPT`。v4 功能的 `state.yaml` 自己带有 `escape` 时，关闭前要写上 `seam_fix` 和 `verified_by`，否则 `check-sdlc.sh` 报 `ESCAPEQA`。覆盖矩阵还要出现契约或审查里的每个 `[SEC-n]`；本样例的 `[SEC-1]` 指向 `test_cross_tenant_event_is_refused`。

2. 赌注有了读数之后：

```bash
python3 <插件根>/scripts/gates/outcomes.py readout \
  --project-root <项目根> --feature <功能名> \
  --status inconclusive \
  --evidence <证据路径> --note "<一句读数>"
```

`--status` 只能是 `supported`、`refuted` 或 `inconclusive` 之一。

3. 查看到期未读数、汇总，以及闸门和逃逸是否对得上：

```bash
python3 <插件根>/scripts/gates/outcomes.py due --project-root <项目根>
python3 <插件根>/scripts/gates/outcomes.py stats --root <项目根>/.sdlc
python3 <插件根>/scripts/gates/gate_catalog.py report --project-root <项目根>
```

`due` 只提醒，不阻断别的工作。到期的赌注不会让 `check-sdlc.sh` 变红。

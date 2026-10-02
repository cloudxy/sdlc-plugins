# 维护者档案

这里的文件只给插件维护者用，不被任何技能、角色或派单读取。

| 位置 | 是什么 | 什么时候看 |
|---|---|---|
| `method-baseline.json` | 方法源文件（技能正文与参考、角色源、注册表、宿主适配源）的当前摘要。生成物不在内 | 不手改；由 `scripts/method_ledger.py record` 更新 |
| `method-changes/` | 每次方法改动一条记录：改了哪些文件、行为类还是编辑类、失败类型、证据位置、结论 | 改技能或规则文本之后；方法复盘时 |
| `archive/` | 已移出技能的项目经验原文 | 需要追溯来源时 |

## 改方法文本的流程

1. 改动前想清楚它要纠正的失败属于哪一类（`failure_form`）：
   - `discipline`：知道规则但跳过；
   - `shape`：输出形式不对；
   - `omission`：漏了必需元素；
   - `conditional`：行为应随某个可观察条件变化。

   类型决定写法。明知故犯才用禁令和借口表。形式问题写正面配方，不写禁令。漏项加模板字段。条件写成「如果可观察条件成立，则……」。
2. 行为类改动，先用 `scripts/behavior_smoke.py` 在基线版本上跑相关评测用例，看它失败；再在改后的工作树上跑，看它通过。每个场景至少重复 3 次，用例变化大或结果不一致时用 5 次。
   - 两个臂依次跑，不要并行。每次运行消耗的是你自己的订阅会话额度，和你正在用的会话共用；2026-10-02 并行 4 个进程，10 分钟内就触发上限，连当前会话也停了。
   - 基线臂也通过不等于改动没用：它可能是消除了模型需要自己调和的矛盾。这种情况记为 `no_change` 并写明，由复盘决定保留还是回退。
3. 运行 `python3 scripts/method_ledger.py record --id <简名> --kind behavioral --failure-form <类型> --verdict pending|improved|no_change|regressed --evidence <证据目录> --reason <为什么>`。证据还没出来就先记 `pending`，出来后用 `verdict` 子命令补结论。
4. 不改变行为的修改（错字、链接、排版）记为 `--kind editorial`，并写明理由。方法复盘时会抽查编辑类记录的数量与内容，防止行为改动绕过评测。

`bash scripts/health-check.sh` 对没有记录的改动报 `METHODCHANGE`（错误），对等待证据的行为改动报 `METHODPENDING`（告警）。

## 方法复盘

每次发版附变更记录；另外每关闭 10 个功能或每月一次，取较晚者，由维护者发起。复盘时看：
- 仍是 `pending` 的记录；
- 结论为 `regressed` 或 `no_change` 的改动，是否回退；
- 编辑类记录的抽查结果；
- 会话诊断提出的问题（`sdlc-eval` 的 diagnose 模式）。

方案与执行记录在插件仓库之外的维护者归档中（`~/Documents/grok-files/sdlc-workflow/`）。

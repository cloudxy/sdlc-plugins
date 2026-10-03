# 维护者档案

这里的文件只给插件维护者用，不被任何技能、角色或派单读取。

| 位置 | 是什么 | 什么时候看 |
|---|---|---|
| `method-baseline.json` | 方法源文件（技能正文与参考、角色源、注册表、宿主适配源）的当前摘要。生成物不在内 | 不手改；由 `scripts/method_ledger.py record` 更新 |
| `method-changes/` | 每次方法改动一条记录：改了哪些文件、行为类还是编辑类、失败类型、证据位置、结论 | 改技能或规则文本之后；方法复盘时 |
| `gate-provenance.json` | 每个闸门标签的来历、加入日期、复审日期和维护成本，由 `scripts/gate_catalog.py` 校验 | 新增或修改闸门时；复审到期时 |
| `out-of-scope/` | 有意不做的事：结论、理由、来源、什么证据会让我们重新考虑 | 准备提新规则或借鉴外部做法之前 |
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
   - 改技能描述（`description` / `when_to_use`，即触发条件）时，改用 `scripts/trigger_smoke.py`：提示写在 `skills/<技能>/evals/triggers.json`（应触发与不应触发各一半），它只看宿主在前两轮加载了哪个技能，机械计分，不需要判定。
3. 运行 `python3 scripts/method_ledger.py record --id <简名> --kind behavioral --failure-form <类型> --verdict pending|improved|no_change|regressed --evidence <证据目录> --reason <为什么>`。证据还没出来就先记 `pending`，出来后用 `verdict` 子命令补结论。
4. 不改变行为的修改（错字、链接、排版）记为 `--kind editorial`，并写明理由。方法复盘时会抽查编辑类记录的数量与内容，防止行为改动绕过评测。

`bash scripts/health-check.sh` 对没有记录的改动报 `METHODCHANGE`（错误），对等待证据的行为改动报 `METHODPENDING`（告警）。

## 闸门的增加与退役

- **新增闸门标签：** 同一个改动里要做三件事：
  - 在 `scripts/test-check-sdlc.sh` 加一条会让它出现的夹具（`assert_tag`）；
  - 运行 `python3 scripts/gate_catalog.py seed-origins`，记录来历；
  - 在 `gate-provenance.json` 里写明它的维护或运行成本。

  否则健康检查报 `GATECATALOG`。
- **退役候选：** 以下条件**同时**满足才算：
  1. 复审日期已过；
  2. 观察期内没有关联的逃逸缺陷（`gate_catalog.py report --project-root <项目>` 汇总各项目 `.sdlc/_outcomes/` 里的逃逸归因）；
  3. 有明确的维护或运行成本；
  4. 删除后不降低安全、数据正确性或发布义务。

  只看「从没拦截过」不能作为退役理由。是否退役由维护者决定；决定退役时，把理由写进 `out-of-scope/` 的反面记录，说明什么情况下应恢复。

## 方法复盘

每次发版附变更记录；另外每关闭 10 个功能或每月一次，取较晚者，由维护者发起。复盘时看：
- 仍是 `pending` 的记录；
- 结论为 `regressed` 或 `no_change` 的改动，是否回退；
- 编辑类记录的抽查结果；
- 会话诊断提出的问题（`sdlc-eval` 的 diagnose 模式）。

### 能力扫描（每次复盘做一遍）

1. 读 plugin-updater 日志（`~/.zcode/plugin-updater/logs/update-YYYYMMDD.log`），看已跟踪的上游仓库这段时间改了什么；健康检查报 `VENDORDRIFT` 的改写文件一并重看。
2. 取 `python3 scripts/outcomes.py stats --root <项目>/.sdlc` 里最弱的一环（逃逸最多的闸门或阶段、读数被推翻最多的证据等级），用 `npx skills find <关键词>` 只读搜索有没有现成做法。
3. 候选只能用两种方式进来：
   - 原件走 vendor 锁定（`vendor/<源>.lock.json` + `vendor/install.sh`）；
   - 改写进技能参考，文件头写来源；有上游原件的写 `<!-- upstream: … -->` 头，让 `VENDORDRIFT` 能盯住。
4. 进来之后照「改方法文本的流程」走：变更记录，再做冒烟对比。
5. **从不自动安装。** 搜到的技能只读、只比较；装不装由维护者决定。不采纳的写进 `out-of-scope/`（例如 `2026-10-02-不自动安装外部技能.md`）。

方案与执行记录在插件仓库之外的维护者归档中（`~/Documents/grok-files/sdlc-workflow/`）。

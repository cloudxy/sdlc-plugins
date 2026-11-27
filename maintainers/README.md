# 维护者档案

这里的文件只给插件维护者用，不被任何技能、角色或派单默认加载。使用插件请先读[使用指南](../docs/usage.md)；修改插件前先读 [AGENTS.md](../AGENTS.md)。

| 位置 | 是什么 | 什么时候看 |
|---|---|---|
| `method-baseline.json` | 方法源文件（技能正文与参考、角色源、注册表、宿主适配源）的当前摘要（公开提交）。生成物不在内 | 不手改；由 `scripts/gates/method_ledger.py record` 更新 |
| `gate-provenance.json` | 每个闸门标签的来历、加入日期、复审日期和维护成本（公开提交），由 `scripts/gates/gate_catalog.py` 校验 | 新增或修改闸门时；复审到期时 |
| `method-changes/`（`.gitignore` 仅本地） | 每次方法改动的维护记录：改了哪些文件、行为类还是编辑类、失败类型、证据位置、结论 | 改技能或规则文本之后；本地方法复盘时 |
| `out-of-scope/`（`.gitignore` 仅本地） | 有意不做的设计取舍记录 | 准备提新规则或借鉴外部做法之前 |
| `archive/`（`.gitignore` 仅本地） | 维护验证与场景评测证据归档 | 本地追溯具体变更依据时 |
| `private/`（`.gitignore` 仅本地） | 维护者私人笔记、临时草稿、含隐私样本或本机诊断文件统一存放目录 | 任何涉及私人信息或升级过程思维链路的本地资料 |

## 维护入口与完成检查

- [角色源文件](../agent-sources/profiles/README.md)：身份、风格与共享行为的编译入口。
- [上游原件](../vendor/README.md)：锁文件、安装与引用边界。
- 私人维护记录（`archive/`、`out-of-scope/`、`method-changes/`、`private/`）均已纳入 `.gitignore`，仅保存在本机工作区，不随公开仓库分发；公开克隆或 CI 仅核验 `method-baseline.json` 与 `gate-provenance.json`。

**只允许运行受改动影响的定向检查与测试，严禁执行全量测试**（禁止默认遍历 `tests/test_*.py` 或无差别重复跑全套测试，避免浪费时间）；方法台账登记在健康检查前完成：

```bash
# 1. 结构、技能、角色、注册表、宿主或方法台账改动时运行健康门禁：
bash scripts/health-check.sh

# 2. 仅当改动对应 Python 模块或规则实现时，定向运行受影响的那一个/几个测试文件：
python3 tests/test_<affected>.py

# 3. 仅当修改 scripts/check-sdlc.sh 或其直接依赖的阶段闸门逻辑时运行（含 locale 校验）：
bash tests/test-check-sdlc.sh
LC_ALL=zh_CN.UTF-8 /bin/bash tests/test-check-sdlc.sh
```

修改注册表或宿主源后用 `python3 scripts/workflow.py render` 更新生成物；修改角色源后用 `python3 scripts/render-role-agents.py` 更新角色。技能修改还需下述场景评测；脚本检查不能替代它。

## 改方法文本的流程

1. 改动前想清楚它要纠正的失败属于哪一类（`failure_form`）：
   - `discipline`：知道规则但跳过；
   - `shape`：输出形式不对；
   - `omission`：漏了必需元素；
   - `conditional`：行为应随某个可观察条件变化。

   类型决定写法。明知故犯才用禁令和借口表。形式问题写正面配方，不写禁令。漏项加模板字段。条件写成「如果可观察条件成立，则……」。
2. **技能改动必须做场景评测。** 按改动风险选择真实任务与正反场景，事先明确判定标准，保存实际输出、判定和未验证范围；来源核对、脚本回归不能单独替代技能场景评测。**不要求使用任何模型、客户端、调用次数或模型对照。** 某个客户端未登录时改用可用的评测方式，不能据此省略评测。
   - 场景评测已完成而未做新旧对照时记 `evaluated`；不能据此宣称相对旧版提高、持平或退化。
   - `scripts/evals/behavior_smoke.py`、`scripts/evals/trigger_smoke.py` 保留为可选工具；使用时如实保存输入版本、输出和判定依据。其他适当的场景评测同样可以作为台账证据，无需例外说明。
3. 运行 `python3 scripts/gates/method_ledger.py record --id <简名> --kind behavioral --failure-form <类型> --verdict pending|evaluated|improved|no_change|regressed --evidence <证据路径> --reason <为什么>`。`pending` 表示评测或结论仍待处理；`evaluated` 表示完成适当评测，不宣称对照收益。
4. 不改变行为的修改（错字、链接、排版）记为 `--kind editorial`，并写明理由。方法复盘时会抽查编辑类记录的数量与内容，防止行为改动绕过评测。

`bash scripts/health-check.sh` 对没有记录的改动报 `METHODCHANGE`（错误），对等待证据的行为改动报 `METHODPENDING`（告警）。

## 闸门的增加与退役

- **新增闸门标签：** 同一个改动里要做三件事：
  - 在 `tests/test-check-sdlc.sh` 加一条会让它出现的夹具（`assert_tag`）；
  - 运行 `python3 scripts/gates/gate_catalog.py seed-origins`，记录来历；
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
2. 取 `python3 scripts/gates/outcomes.py stats --root <项目>/.sdlc` 里最弱的一环（逃逸最多的闸门或阶段、读数被推翻最多的证据等级），用 `npx skills find <关键词>` 只读搜索有没有现成做法。
3. 候选只能用两种方式进来：
   - 原件走 vendor 锁定（`vendor/<源>.lock.json` + `vendor/install.sh`）；
   - 改写进技能参考，文件头写来源；有上游原件的写 `<!-- upstream: … -->` 头，让 `VENDORDRIFT` 能盯住。
4. 进来之后照「改方法文本的流程」走：完成适当的场景评测并登记变更；只有实际做过对照时才给出相对收益结论。
5. **从不自动安装。** 搜到的技能只读、只比较；装不装由维护者决定。不采纳的写进本机忽略目录 `out-of-scope/` 或 `private/`。

早期方案、隐私样本与完整升级推导记录仅保留在本机忽略目录（`maintainers/private/`、`maintainers/archive/` 或仓库外本地目录），不提交进公开版本库。

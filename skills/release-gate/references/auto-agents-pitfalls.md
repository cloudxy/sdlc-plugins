# auto-agents 实战坑（qc）

只收本仓库已对过源码或闸门指纹的项。推测不进本文件。

## PIT-QC-01 `check-sdlc.sh` SUMMARY 退出码 off-by-one

- **现象（3.5.x）**：真实违规数 N 时，打印「共 N 处违规」，退出码是 **N+1**（`red SUMMARY` 再 `V++`）。
- **3.6.0**：SUMMARY 改 `printf`，不再走 `red()`。`scripts/test-check-sdlc.sh` 夹具「NOLANE exit==1 not 2」。
- **核对**：对账仍用 `✗ [SDLC-…]` 行数；遇到旧拷贝时 exit 仍可能是 N+1。

## PIT-QC-02 默认 skip = pass；MATRIX 段在无 `coverage.md` 时整段跳过

- **现象**：无 `--require` 时缺目录/无工件 → exit 0。有 `--require` 仍 **不会** 因缺少 `coverage.md` 失败：MATRIX 检查包在 `if [ -n "$COV" ]` 里（约 L131–141）。
- **本特征指纹**：`.sdlc/feat-four-pillars/state.yaml` 闸门 `sdlc` result=pass、exit_code=0、`at: 2026-09-07T16:20:00`，命令含 `--require`；同时特征树 **没有** `coverage.md`。G-script 绿 ≠ FR 有矩阵行。
- **核对**：qc 把「无 coverage.md」当覆盖空洞，不当闸门通过。编排器必须另跑 `skills/coverage-matrix/scripts/check-matrix.py` 并把输出贴进 qc 提示。

## PIT-QC-03 空心绿：断言不碰到被测行为

- **`test_spider_contract`**：`backend/tests/test_skill_harvester.py` L87–95。`"backend" not in [str(m) for m in ()]`，空元组恒真；注释写「import 检查由 check-arch R3 承担」。pytest 绿不证明爬虫零 import backend。
- **`test_explain_assertion_framework`**：`backend/tests/test_db_behavior_loop.py` L66–79。对本地 dict `{"type": "ref"|"ALL"}` 断言，无真实 `EXPLAIN`。注释自称「框架逻辑 DB 无关」。不能当 MySQL 访问类型覆盖。
- **核对**：矩阵 ✅ 必须能指到 Then 的具体断言。空心用例标缺口，不计入覆盖率。

## PIT-QC-04 现网套件绿 ≠ 本特征覆盖

- **证据**：`01-define/diagnosis/qa.md`：pytest ~997、Jest 15、E2E 无；Power Market D1–D21 专用用例 0；`listing_state` / `capability_installs` 等零命中。旧用例锁的是 P6 契约（如 viewer 可 `POST scan-plugins`），与冻结 FR-06/18/26 互斥。
- **核对**：qc 禁止用「仓库测试都过了」替代 FR↔矩阵。实现后必须改写互斥旧用例，否则假红/假绿。

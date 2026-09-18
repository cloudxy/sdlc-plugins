# auto_agents QA 坑点（仅实战已验证）

> 准入：failed tests / ESC / check-sdlc 证据。推测与「尚未跑红的设计风险」不进本文件。  
> 来源：`.sdlc/_lessons.md` · `backend/tests/test_t10_fix_regressions.py` · `backend/tests/test_saas_wiring.py` · `backend/tests/test_saas_byok.py` · `backend/tests/test_skill_harvester.py` · `backend/tests/test_db_behavior_loop.py` · `.github/workflows/ci.yml`  
> 日期：2026-09-07

---

## ESC-2 · SQLite 放行、MySQL 拒绝的方言

- **证据**：生产 MySQL 1064；修复 commit `0e0aaf8`（`capability_service` / 技能排序去掉 `NULLS LAST`）。回归：`test_capability_service_sort_compiles_on_mysql_0e0aaf8`（编译产物不得含 NULLS LAST/FIRST）、`test_null_aware_sort_roundtrip_mysql_fidelity`（`MYSQL_FIDELITY=1` 才跑）。CI 保真 job 已纳入 `test_t10_fix_regressions.py`。入账：`.sdlc/_lessons.md` ESC-2。
- **为什么逃**：默认 pytest 走 SQLite 文件库；SQLite 静默接受 PG 风格 `NULLS LAST`。主闸 `uv run pytest backend/tests` 绿 ≠ 生产方言绿。
- **写法**：凡 `ORDER BY` / 生成列 / `JSON_CONTAINS` / `COALESCE` 与 NULL 唯一键，SQLite 用例之外必须有 MYSQL_FIDELITY 或「编译产物不含非法方言」断言。新表不要只进全量 SQLite 套件。

## 空心断言能让 CI 绿（套件内已核实）

下列用例当前通过，但断言不能失败——与「矩阵有格子 ≠ 测了 GWT」同类。不是新 ESC，是本轮读测试源核实的现网债。

| 证据 | 行为 |
|---|---|
| `backend/tests/test_saas_wiring.py:49` | `assert ... or True`：配额拒绝主题永真 |
| `backend/tests/test_saas_byok.py:45` | `"a-key" in cfg.source or True`：密钥隔离可空心 |
| `backend/tests/test_skill_harvester.py:93-95` | `"backend" not in [str(m) for m in ()]`：空元组 |
| `backend/tests/test_db_behavior_loop.py:66-79` | EXPLAIN 框架只对模拟 dict 断言 `type != ALL`，CI 保真子集不含本文件真 SQL |

- **写法**：禁止 `or True` 垫断言。副作用（未入队、未写盘、无 installs 行）必须查库。方言/计划类断言必须打到真实语句或真库 EXPLAIN。

## ESC-1 · 导入未落库就断言 404

- **证据**：`.sdlc/_lessons.md` ESC-1（历史基线）。最早闸门：定义帽状态转换 / 实现帽时序依赖。
- **写法**：Given 必须含「行已 commit / 扫描已落库」。HTTP 200 扫描后立刻 GET，要在同一 fixture 会话里能读到行；不要跨用例吃前序产物。

## ESC-3 · F5 后权限缓存归零

- **证据**：`.sdlc/_lessons.md` ESC-3。前端权限若只活在内存 store，刷新后按钮/路由与后端码不一致。
- **写法**：权限用例包含「刷新后仍按 `/permissions` 再水合」；不要只测当次 render。

## ESC-8 / ESC-9 · 证据块不是终态（check-sdlc）

- **证据**：`.sdlc/_lessons.md` ESC-8（贴中间态 exit 2）、ESC-9（`--stats` 对内联 YAML / 重锚）。`check-sdlc.sh` 已能拦部分；夹具本身要先过 check-sdlc。
- **写法**：测试报告与 impl 证据只贴最终通过的那次命令输出。FR 标题格式与 `$` 前缀命令行按规范夹具，否则 EVID 误报。

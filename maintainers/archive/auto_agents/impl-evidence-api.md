# auto_agents backend pitfalls（仅战伤 + 可核验证据）

收录门槛：本仓库真实踩过，且有 **测试名 / traceback / ESC** 之一。理论分层债、未修缺陷、设计缺口不进本文件（见 `.sdlc/feat-four-pillars/01-define/diagnosis/backend.md`）。

来源：`ADR-0007`、`backend/tests/`、`scripts/check-arch.sh` R11、SKILL.md freeze ESC、迁移 024。

---

## P-BE-01 `session.commit()` 后读 ORM → `MissingGreenlet`

- **战伤**：async 会话 `expire_on_commit=True`。commit 后访问 `obj.id` / 关系触发同步 refresh，greenlet 不在 → `sqlalchemy.exc.MissingGreenlet`。
- **证据**：
  - ADR-0007（事务所有权归 Service；API 层禁止 commit 后再碰 ORM）
  - `backend/tests/test_transaction_ownership.py`（Service 自持事务 / `commit=False` 组合）
  - `backend/tests/test_rbac_audit.py::test_current_user_ok`（`CurrentUser` 必须是快照 dataclass，注释写明防 MissingGreenlet）
  - `backend/app/api/deps.py` `CurrentUser` 文档字符串（历史坑）
- **规则**：commit **之前** `int(obj.id)` / 投影成 dict；需要再读就 `await session.refresh`；Router 只收 DTO。市场/配额新代码禁止把 `CapabilityAsset` 活实例传出 Service 再读。

---

## P-BE-02 async 上下文链式调用同步 `redis_client()`

- **战伤**：登录/注册路径曾 `redis_client().incr(...)`，阻塞事件循环，后端假死。
- **证据**：
  - SKILL.md Gotchas：「ESC from freeze pattern」
  - `backend/app/api/v1/auth.py` 模块头（「此前直调同步 redis_client 阻塞事件循环」）
  - `scripts/check-arch.sh` R11：`grep -rnE 'redis_client\([^)]*\)\.' backend/`
  - 反例（合法）：`backend/tests/test_saas_members.py` 在 **同步** 测试里 `redis_client("DEFAULT")`，注释写明 R11 只禁 async 链式直调
- **规则**：async 路径只用 `get_async_redis()`（同步工厂）再 `await redis.*`。不要 `await get_async_redis()` 指望工厂是 coroutine（它靠 `Redis.__await__ = initialize()`，mock 成 `async def` 会炸）。

---

## P-BE-03 `tenant_id IS NULL` 曾经等于平台态

- **战伤**：旧条件 `is_platform_admin OR not tenant_id` 让无租户账号自动 `platform_scope`（跨租户全可见）。MySQL UNIQUE 对 NULL 不判重，同名 NULL 行可绕过 `(tenant_id, username)`。
- **证据**：
  - `backend/app/middleware/tenant_context.py` T5/F-01（决策 B + DB 复核）
  - 迁移 024 + `backend/tests/test_users_null_tenant_contract.py::test_null_tenant_user_rejected`
  - `test_users_null_tenant_contract.py::test_same_tenant_duplicate_username_rejected`
- **规则**：非超管无 `tenant_id` → 401，不是平台态。`before_flush` **只断言不回填**——新行必须调用方写入 `tenant_id`。入队/建计划漏传会在租户态抛 `ValueError`，在无上下文撞 NOT NULL，不会「默默变成平台任务」。

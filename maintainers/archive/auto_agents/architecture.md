# auto_agents — architect pitfalls（仅实战已验证）

收录门槛：现码 + 测试合同，或 ESC，或闸门脚本本身。推测、设计文档里的「会炸」、未复现路径 **不准** 写入。最后核实：2026-09-07。

---

## PIT-1 FastAPI 动态段会吞掉同前缀静态段

**踩过**：`GET /api/v1/capabilities/plugins/{name}` 等三条曾恒 404，因为 `/{asset_type}/{name}` 先注册。

**证据**

- `backend/app/api/v1/capabilities.py` 文件头 + `get_capability_detail` 注释（「B5 修复 B1c F-1」）。
- `backend/tests/test_b1c_capabilities_coverage.py` 模块 docstring finding F-1：静态段必须先于动态段，三条契约用例已转正。

**塑形/实现**：同前缀下新增二段式路由，一律放在动态 `/{asset_type}/{name}` **之前**。不要靠「看起来更具体」——FastAPI 按注册顺序。

---

## PIT-2 现网测试把过宽守卫钉成成功合同

**踩过**：能力写面是 `require_login`。改成 `require_platform_admin` 而不改测试，CI 红。

**证据**

- `backend/tests/test_b1c_capabilities_coverage.py` 第 4–8 行：「require_login——viewer 亦放行，无 403 分支」；`test_*scan-plugins*` 断言 viewer 200。
- 同文件公开端合同写死「仅 stable」（与 FR-18 `recommended` 冲突）。
- `backend/app/api/deps.py`：`require_admin = require_role("admin")` 放行租户公司管理员；`require_platform_admin` 才是 `is_platform_admin`。

**塑形/实现**：FR-06/07 收权必须与 `test_b1c_*` / newapi / llm 写面用例 **同 PR**。不要假设「改 Depends 测试会跟着绿」。

---

## PIT-3 带 `tenant_id` 列的平台表漏登豁免 → 租户态 UPDATE 0 行

**踩过**：隔离钩子按「表有 `tenant_id` 列」注入，不按 Mixin。`skills` 因此被特意豁免；`capability_assets` 同样手写恒 NULL 列却 **未** 进清单。注释仍声称 skills 是「唯一功能必需豁免」——与列事实不符。

**证据**

- `platform_core/tenant_context.py`：Core UPDATE/DELETE 非豁免且有 `tenant_id` 列 → `WHERE tenant_id = 当前租户`。
- `backend/app/tenant_isolation.py`：`TENANT_EXEMPT_TABLES` 含 `skills`，不含 `capability_assets`。
- `platform_core/models/capability.py`：`CapabilityAsset.tenant_id` 手写列，非 `TenantMixin`。
- `backend/tests/test_saas_isolation.py` `test_registered_exempt_update_unfiltered_vs_unregistered_filtered`：钉死「已登记豁免不注入 / 未登记带列的表注入」。R13 只校验清单已注册，**不**校验该豁免谁。

**塑形/实现**：每张「平台级、列恒 NULL」的新表同步改 `TENANT_EXEMPT_TABLES` 并补夹具。安装表反向：有租户语义则 `TenantMixin` 且 **禁止** 豁免。不要用 R13 绿当作「该豁免的表都在清单里」。

---

## PIT-4 采集任务/结果的 `tenant_id` 自 017 起 NOT NULL

**踩过**：SaaS 地基迁移把业务表（`llm_providers` 除外）收紧为 NOT NULL。后来方案若写「平台入站行 `tenant_id` NULL」会在真库插入失败；SQLite/无租户上下文的单测不一定拦。

**证据**

- `backend/alembic/versions/017_saas_tenant_foundation.py`：`TENANT_TABLES` 含 `spider_tasks` / `spider_results`；`if table != "llm_providers": alter nullable=False`。
- `platform_core/models/mixins.py` ORM 列仍默认可空——**ORM 与迁移链不一致**，create_all/测试引擎会骗人。
- `backend/services/spider_task_service.py` 仅在传入 `tenant_id` 时跑并发配额；HTTP `/run` 传了，调度/模板/AI 试采经 `SpiderService.enqueue` **不传**。

**塑形/实现**：禁止把「NULL = 平台候选」写进 ADR/合同（stale `adr-0013` 踩了这个）。FR-11 用 `source` 过滤或自有表。入队路径必须显式传租户，不要指望 Mixin 自动填。

---

## PIT-5 两套公开列表、两套发布闸，测试分别钉死

**踩过**：技能公开 API 要 `stable|recommended`；能力公开 API 写死 `status="stable"`。一边修 recommended 另一边测试会红或产品仍丢推荐。

**证据**

- `backend/app/api/v1/public_skills.py`：`PUBLISHED_STATUSES = ("stable", "recommended")` 用于 `/public/skills`；`/public/capabilities` 调用 `list_assets(status="stable")`。
- `backend/tests/test_skill_public_api.py`：公开技能列表名字集合 `{"pub-stable", "pub-rec"}`。
- `backend/tests/test_b1c_capabilities_coverage.py`：公开能力「仅 stable + 白名单」。

**塑形/实现**：商店闸门只留一条读模型。改过滤必须同时改 **两份** 测试合同，或先删掉其中一条端点。`/public/skills` 还有「先分页再内存滤、`total=len(published)`」——页内过滤会让 total 与翻页不稳定。

---

## PIT-6 无 MCP 的验证结果被测试钉成 `degraded`

**踩过**：ADR-0001 / CONTEXT「未经 verify 不得分发」。实现里未声明 MCP servers → `health_status=degraded`。设计改为 `unknown` 且允许 listed 时，不改 `test_b1c` 与插件验证用例会双红。

**证据**

- `backend/services/plugin_service.py` `verify_plugin`：`if not servers: health_status = "degraded"`。
- `backend/tests/test_b1c_capabilities_coverage.py` 覆盖清单：「无 MCP → degraded」。

**塑形/实现**：先写 superseded ADR-0001，再改枚举与测试。不要只改服务层返回值。

---

不收录（未达门槛）：R10 只扫一层 `services/*.py`（闸门源码可见，但尚无因此逃逸的失败记录）；公开限流 INCR/EXPIRE 非原子（无 ESC/失败测试）；LiteLLM 替换叙事（测试文案，不是踩过的架构闸）。

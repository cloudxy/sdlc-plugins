# auto_agents 运营坑点（仅实战已验证）

> 准入：`code+test` / `.sdlc/_lessons.md` 的 ESC / `gate cmd+exit`。无推测、无「看起来像」。  
> 仓库：`auto_agents`。日期：2026-09-07。  
> 未达门槛因而不收录：Hero 示意数字（有代码无测例/无 ESC）、定价空头（仅 grep）、AGPL 商用（文档约束）、竞品未试用结论。

---

## P-OPS-01 对外写「Excel」时，测例把 `xlsx` 当非法格式

- **pitfall**：发布说明、官网、增长盘点把「Excel 导出」当成已交付能力。实现只发 CSV（带 BOM，注释写 Excel 兼容）和 JSON；`xlsx` 走业务拒绝。访客按卖点去点会失败，运营却以为格式已齐。
- **evidence**（code+test）：
  - `frontend/official/src/components/home/FeaturesSection.tsx`：「支持 CSV / Excel 一键导出」「多格式导出」
  - `backend/services/spider_query_service.py`：`if fmt not in ("csv", "json"): raise BusinessException("导出格式仅支持 csv/json")`；CSV 先 `yield b"\xef\xbb\xbf"` 注释「utf-8-sig BOM（Excel 兼容）」
  - `backend/tests/test_spider_task_flow.py`：`test_export_csv_with_bom` 断言 BOM；`test_export_bad_format_raises` 对 `export_results(1, "xlsx")` 期望 `BusinessException`
  - 数据中心另有硬顶：`frontend/admin/src/pages/Data.tsx` `page_size: 100` 且只生成 CSV
- **prevent**：对外只写测例允许的字面量 `csv` / `json`。把「Excel 能打开 CSV」写成 Excel 能力之前，先跑 `test_export_bad_format_raises`——绿的拒绝不是「Excel 已支持」。

---

## P-OPS-02 技能公开闸含 `recommended`，能力公开测例只认 `stable`

- **pitfall**：把「公开目录规模」或「推荐是否在官网上」当成一条供给。两套公开面、两套测例：技能列表会出 `recommended`；能力列表把 status 钉死 `stable`，夹具甚至没有 recommended 行。首页精选走技能 API，能力广场走能力 API，运营对账会以为「推荐丢了」或「推荐还在」——取决于点了哪个入口。
- **evidence**（code+test）：
  - `backend/app/api/v1/public_skills.py`：`PUBLISHED_STATUSES = ("stable", "recommended")`；`public_list_capabilities` 调用 `list_assets(..., status="stable")`
  - `backend/tests/test_skill_public_api.py`：`test_public_list_only_published` 断言 `names == {"pub-stable", "pub-rec"}`
  - `backend/tests/test_b1c_capabilities_coverage.py`：`test_public_capabilities_only_stable` 只种 stable/experimental，断言公开 skill 仅 `pub-skill`
- **prevent**：增长或发布核对必须写清命中的是 `/public/skills` 还是 `/public/capabilities`。未改测例之前，不得把「推荐已对访客可见」写成全站事实。

---

## P-OPS-03 北极星「能判定」写进蓝图，冻结 GWT 却没有排除字段——审查闸已红

- **pitfall**：运营/复盘按 `metrics-blueprint.md` 宣布「四周后能报 WACT」。WACT 必须排除市场入站候选，且登录失败要能分母诊断；`spec.md` GWT-15.1 没有候选标记、没有 `login_failed`。定义帽 `fresh-context` 因此 fail。未修契约就埋点，四周后仍报不出合格北极星，却会看起来「有事件」。
- **evidence**（gate cmd+exit）：
  - `.sdlc/feat-four-pillars/state.yaml`：`gates.fresh-context.result: fail`；`blocker: 2`；`evidence: .sdlc/feat-four-pillars/05-review/findings.md`（QA-01 已 fixed，**QA-02 仍 open**）
  - `05-review/findings.md` QA-02：GWT-15.1 字段无候选入站标记、无 `login_failed`、无 spider/source；蓝图 WACT **排除**市场入站候选，验收以 `task_completed` 事件为准
  - `01-define/metrics-blueprint.md` §2 / §5：核心动作排除候选；`login_failed` 映射 FR-15
  - 本机 grep：`official_page_viewed` / `task_completed` / `tenant_signup_succeeded` 在产品代码 **0 命中**（查询面尚未存在，更不能用任务表冒充验收）
- **prevent**：P9 或增长周报开写之前，先看 `fresh-context` 是否已绿、QA-02 是否已关。GWT 字段集盖不住北极星排除条件时，只许写「不能判定」，不许写 WACT 数字。

---

## 明确不收录

| 候选 | 为何不进 |
|---|---|
| ESC-1…ESC-9（`.sdlc/_lessons.md`） | 门禁/夹具/权限缓存，属流程工程，不是本产品运营坑 |
| Hero `128,000+` / `3.2 亿条` | 代码可证，但无测例锁住、无 ESC、无闸失败专指此条 |
| 定价「工单支持 / 渠道组」空头 | 仅 Pricing.tsx vs grep 0，无测试断言 |
| 注册成功页无去登录 | 可走查，无测例/闸 |

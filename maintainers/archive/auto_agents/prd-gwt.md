# auto_agents · PM 实战坑点

> 只收本仓库已验证条目：代码+测试、`.sdlc/_lessons.md` 的 ESC、或带命令与退出码的失败闸门。不收「可能」「设计文档里写过」或未复现的推断。

---

## P-01 官网卖 Excel，导出契约拒绝 xlsx

- **pitfall**：把「CSV / Excel 一键导出」写成当前可完成能力。现网导出 `xlsx` 抛业务异常；CSV 带 BOM 只是为了 Excel 能打开，不是 xlsx。
- **evidence**：`backend/tests/test_spider_task_flow.py:357-361` `test_export_bad_format_raises`（`export_results(1, "xlsx")` → `BusinessException`）；卖点原文 `frontend/official/src/components/home/FeaturesSection.tsx:54`。
- **prevent**：Wave 0 改口或标边界。GWT 只验收真正会生成的格式。xlsx 进「下一轮」，不要写进冻结 FR 的正常路径。

---

## P-02 两个公开列表钉了两套治理闸

- **pitfall**：给「公开目录」写一条可见性 GWT，同时覆盖技能广场和能力广场。技能公开含 `stable`+`recommended`；能力公开只 `stable`。两套测试分别当作金标。
- **evidence**：`backend/tests/test_skill_public_api.py:76-82` `test_public_list_only_published`（`names == {"pub-stable", "pub-rec"}`）；`backend/tests/test_b1c_capabilities_coverage.py:383-389` `test_public_capabilities_only_stable`（`total == 1`，experimental 不外泄）。
- **prevent**：能力市场闸门写成 **一条** 产品规则（已上架或预告 ∩ 已发布或推荐 ∩ 许可过闸）。迁商店面时显式作废「能力广场仅 stable」旧金标，并通知 /qa 改用例。不要让旧测试继续定义用户可见性。

---

## P-03 技能广场 XSS 纯文本是唯一验收过的正文渲染

- **pitfall**：T 表把「纯文本防 XSS」标成已有能力后，Wave 1 迁到能力市场却不写 GWT。旧页有测试，新详情没有格子。
- **evidence**：`frontend/official/src/pages/SkillsSquare.test.tsx:38-46` `skill md renders untrusted content as escaped text only`（payload 含 `<script>` / `<img onerror>`；断言纯文本可见、无 `script` 节点）。
- **prevent**：商店详情单独一条 FR/GWT：不可信 SKILL.md 按纯文本渲染；`<script>` 与 HTML 不执行。禁止「沿用技能广场即可」而不验收新页。

---

## P-04 「无权限则隐藏」在权限缓存空时会把整站菜单藏光

- **pitfall**：产品规则写成「没权限的叶子隐藏」。F5 后 token 从 persist 恢复、模块缓存归零，空缓存 ≠ 无权限。未补拉时菜单全隐，用户以为功能丢了。
- **evidence**：ESC-3（`.sdlc/_lessons.md` 历史基线）；回归 `frontend/admin/src/hooks/usePermission.test.tsx:40-58`「F5 后缓存空：挂载自动补拉，菜单恢复」；注释 `frontend/admin/src/hooks/usePermission.ts:9-11`。
- **prevent**：权限相关 FR 区分三种前置：未登录、已登录权限未就绪、已登录确认无码。GWT 不要把「缓存未就绪」写成「无权限隐藏」。空态是「权限加载中」，不是空导航。

---

## P-05 出站 API Key 默认不是「配了就能拉数」

- **pitfall**：SaaS 叙事里把「外部 API Key 拉结果」写成租户能力。现网默认 `API_KEYS: []` = 全部 401；有 key 时按爬虫名查、查询函数无租户参数。
- **evidence**：空配置拒绝：`backend/tests/test_external_api.py:104-105` `test_empty_config_rejects_all`；`config/default/external_api.yml:5`；查询无租户：`backend/services/spider_query_service.py:91-114` `query_public_results`。
- **prevent**：Wave 0 产品规则：无租户绑定则拒绝拉数。租户自助钥匙不进本期（FR-52 下一轮）。不要把「默认空数组拒绝」理解成「隔离已完成」。

---

## P-06 用量页把内部错误码当用户说明

- **pitfall**：配额超限的用户文案写成或展示 `QUOTA_EXCEEDED` / `429`。测试按业务码断言，页面 Alert 也把该码给租户看。
- **evidence**：`frontend/admin/src/pages/Usage.tsx:45` Alert 原文含 `429 QUOTA_EXCEEDED`；`backend/tests/test_saas_wiring.py:21,47` 超并发期望 `QUOTA_EXCEEDED`。
- **prevent**：用户可见 Then 只写「已达上限 + 下一步」。内部码可以留在异常类型里给 /qa 断言，禁止出现在用量页/拒绝 Toast。进度条 ≥90% 变红不等于「接近上限」已有 GWT——那一档必须单独写。

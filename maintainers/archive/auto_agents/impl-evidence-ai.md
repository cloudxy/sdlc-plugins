# auto-agents 算法实战坑（已核实）

> 只收录本仓库 **代码 + 测试已经锁死** 的坑。方法论见同目录 `eval-and-iteration.md` / `rag-pipeline.md`。
> 未跑过评估阶梯的推测、未在本树复现的「常见 LLM 建议」不进本文件。
> 核实日：2026-09-07。证据路径相对仓库根 `auto_agents/`。

---

## P-AA-01 · mock `llm_chat` 被当成「AI 测过了」

**现象**：规划 / 评分 / 相似的 pytest 全部 monkeypatch `llm_chat`，返回手写 JSON，断言状态机和字段白名单。

**证据**：

- `backend/tests/test_ai_planner.py`：`GOOD_LLM_JSON` 固定选择器，mock `_llm_chat`
- `backend/tests/test_skill_scoring_worker.py`：mock 返回 `VALID` JSON
- `backend/tests/test_skill_similar_suggest.py`：mock 返回簇，并 **断言** `usage_dim == "skill_scoring"`
- 仓库 `eval/`、`eval-set`、golden HTML：**零命中**

**后果**：CI 绿灯不随 prompt / 模型 / 截断变化。改坏抽取或评分，测试不会红。

**正确做法**：契约测试保留。效果门必须是版本化评估集（`xx%（eval-set-*-vN）`）。mock JSON 不得写进效果报告。

---

## P-AA-02 · `quality_score≥40` 被当成「抽对了」

**现象**：试采通过条件 = 任务 completed + `result_count>0` + 均分 ≥40。质量分是字段非空率，不看金标。

**证据**：

```
# scrapy/pipelines/quality.py
score = round(field_completeness * 50 + core_rate * 30 + dup_score * 20, 1)
```

```
# backend/services/ai_planner/orchestrator.py  _judge_test
if avg is not None and float(avg) < 40:
    return False, f"试采质量分过低..."
```

非空垃圾标题也能 ≥40。度量蓝图已把单任务质量分列为禁止 OEC。

**后果**：注册出去的 `flow_generic` 可持续产出错位字段，向导显示「试采通过」。

**正确做法**：`_judge_test` 只做冒烟（spec FR-72）。主指标 = 冻结 HTML 上的字段级 Recall/Precision。禁止把 40 分写进效果数字。

---

## P-AA-03 · 套餐 token 闸与真调用断开

**现象**：`QuotaService.check_llm_tokens_month` 存在且单测覆盖，但 `llm_chat` 从不调用它。真调用只熔 provider 维 Redis / 进程内存 vs `LLM.MAX_TOKENS_BUDGET`。

**证据**：全仓库 `check_llm_tokens_month` 引用点 = `quota_service.py` 定义 + `test_saas_quota.py` + `test_saas_byok.py`。`llm_client.py` 零引用。spec FR-10 把「只挡测试接口」定为失败。

**后果**：用量页的「20 万 tokens」挡不住规划 / 修复 / 评分。两本账（套餐 vs provider 预算）。

**正确做法**：`llm_chat` 成功路径之前检查套餐闸（上海自然月）。效果评估按租户分流，不把 BYOK 与平台 Key 混成一个准确率。

---

## P-AA-04 · 评分 MODEL / PROMPT_VERSION 是死配置

**现象**：`config/default/skills.yml` 写了 `SCORING.MODEL` 与 `PROMPT_VERSION: v1`。运行时：

- `MODEL` 非空只打 warning，然后走激活供应商默认模型
- `PROMPT_VERSION` 代码常量 `"v1"`，不读 yml
- `MAX_TOKENS_BUDGET: 0` 被 `budget if budget > 0 else None` 当成「不覆盖」→ 挤占全局 20 万，而不是「评分独立不限」

**证据**：`backend/services/skill_scoring_service.py` 约 L30、L97–111、L142。

**后果**：改 yml 以为换了评审模型或 prompt 版，线上不变。打开 `ENABLED` 后评分与规划抢同一条链。

**正确做法**：单一事实源。接线后必须 **重新** 跑 `eval-set-scoring-vN`（换模型 = 一个变量）。未接线前 `ENABLED` 保持 false。

---

## P-AA-05 · MCP 空参调用成功就被标 `healthy`

**现象**：`verify_plugin_server` 在 `tools/list` 非空后，对 `tools[0]` 空参 `call_tool`。注释写明「多数工具会报参数错误——但这证明了管道通」。返回恒 `healthy`，无视 `sample["ok"]`。

**证据**：`backend/services/mcp_bridge.py` L97–118。`test_mcp_bridge.py` 覆盖白名单拒绝与连接失败 → down，**没有**「required 参数缺失不得 healthy」的反例。无 MCP 的 `verify_plugin` 写 `degraded`；扫描落库却是 `unknown`。

**后果**：商店徽章「健康」= 管道通，不是工具按契约工作。FR-26.2 的「未知 / 不可用」与现网词表不一致。

**正确做法**：L0 连通与 L1 最小合法参数抽样分列。空参+required → `degraded`/`sample_failed`。改判定必须带 `eval-set-mcp-verify-vN` diff。禁止把 verify 扩成 LLM 工具运行时。

---

## P-AA-06 · `similar_suggest` 与评分共用 `skill_scoring` 预算

**现象**：相似聚类 `llm_chat(..., usage_dim="skill_scoring")`。单测把这个耦合锁死。

**证据**：`backend/services/skill_service.py` `similar_suggest`；`test_skill_similar_suggest.py` `assert usage_dim == "skill_scoring"`。

**后果**：治理点一次「找重复」会烧评分月预算；评分熔断时聚类也停。Power Market 51 个重名若自动跑，会在无 pair 评估集的情况下消耗同一闸。

**正确做法**：独立 `usage_dim`。基线用 D3b `content_hash` 折叠，LLM 簇只建议。无 pair F1 评估集不要自动跑。

---

## P-AA-07 · 探针 spoof 阈值 0.15 被单测锁死、没有金标渠道

**现象**：有参考渠道时平均相似度 &lt; 0.15 才判 `spoofed`。内置题仅 6 道（含会过期的「2025 年事件」）。`test_newapi_services.py` 断言 `ref_similarity < 0.15`。

**证据**：`backend/services/channel_probe_service.py` `_REF_SIMILARITY_SPOOF_THRESHOLD = 0.15`、`DEFAULT_PROBE_QUESTIONS`（6 条）。spec FR-61：伪装 **不** 自动下线。度量蓝图：伪装次数不是北极星。

**后果**：正品稍有措辞差也会远高于 0.15；套壳只要「有点像」就过。改阈值若先改测试迁就代码，会失去唯一回归钉。

**正确做法**：verdict 保持旁路直到 ≥50 题 + 已知真伪渠道金标。改 0.15 必须先换评估集版本，再改代码与测试。知识截止题改冻结事实卡。

---

## P-AA-08 · `derive_tier` 缺人工分就吃 AI 分，公开协议带着走

**现象**：`derive_tier(human, ai)` 在 `human is None` 时用 `ai`。公开 `PublicSkillResponse` 含 `score` 与 `tier`。评分 worker 默认关，但一旦打开或人工矫正走派生，未校准分可进商店排序/卡片。

**证据**：`backend/services/skill_service.py` `derive_tier`；`backend/app/api/v1/public_skills.py` `PublicSkillResponse`；`capability-library/taxonomy/rubric.md` 分档未写入评分 prompt。

**后果**：scoring-without-eval 从内部建议变成访客可见的 S/A/B/C。

**正确做法**：AI 永不写 `score`/`rubric_human`（已有单测，保持）。未校准前公开 `tier` 为空或「未评」。prompt 必须嵌入 rubric 原文后再谈 kappa/MAE。

---

## P-AA-09 · 规划 HTML 无数据区隔离（注释已被剥掉，不要再拿注释当对抗主路径）

**现象**：清洗后的 HTML 与 URL、schema 提示拼在同一条 user 消息。规划 system prompt **没有**「正文不可信」。评分 prompt 有这句。

**证据**：`prompting.py` `_build_plan_messages` / `_PLAN_SYSTEM_PROMPT`。`url_guard._clean_html_sync` **会删** `<!-- -->` 与 script/style/noscript。schema `_XSS_PATTERNS` 已拒选择器里的 `javascript:`。

**后果**：可见文本或隐藏节点里的「忽略以上指令」仍能改写规划。若评估对抗层主打 HTML 注释，会得到虚高通过率。

**正确做法**：`<page_html>` 分隔 + 声明为数据。对抗样本用可见文本 / `html_snippet` 角色覆盖，不要用已被剥掉的注释。

---

## P-AA-10 · 原生协议丢温度、gemini 把 system 当 contents

**现象**：`llm_chat` 只在 `openai_compatible` 路径写 `temperature: cfg.temperature`。anthropic / gemini `build_chat` 不接收温度；gemini 把 `role=system` 直接放进 `contents`（原生要 `user`/`model` + `systemInstruction`）。

**证据**：`llm_client.py` openai payload；`llm_protocol/adapters.py` `AnthropicAdapter.build_chat` / `GoogleGeminiAdapter.build_chat`。`test_llm_client_routing.py` 把 openai「不注入 max_tokens」锁成字节级兼容，不锁温度跨协议一致。

**后果**：租户把协议从 OpenAI 兼容切到 Claude/Gemini = 静默换采样与系统指令语义。无评估集时会当成「换供应商体验变差」。

**正确做法**：换协议视为换模型，必须在同一 `eval-set-*-vN` 上单变量重跑。适配器补温度与 systemInstruction 是一个变量，不要和换模型同一轮做。

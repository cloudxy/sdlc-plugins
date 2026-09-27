# auto_agents miner pitfalls

> 只收录本仓库 **代码核实 + 已有下游消费** 的坑。推测、未落地设计、教科书泄漏不进本文件。  
> 核实日：2026-09-07。诊断全文：`auto_agents/.sdlc/feat-four-pillars/01-define/diagnosis/miner.md`

## P1 — `quality_score` 分母含内部字段

**症状：** 条目业务字段都在，分数仍系统性偏低。  
**证据：** `scrapy/pipelines/quality.py` `field_completeness` 用 `item.fields.keys()`；`scrapy/items/__init__.py` `BaseItem` 声明 `task_id/id/created_at/updated_at/extra/_quality_score`。`_quality_score` 写在完整率之后，打分时恒空。  
**下游：** `orchestrator._judge_test` 用任务 `avg_score < 40` 判试采失败。  
**不要：** 把该分当金标、当「抽对了」、当北极星。先修分母（只计业务字段）再谈模型。

## P2 — `QUALITY_CHECK.REQUIRED_FIELDS` 是死配置

**症状：** 改 yaml 必填列表，分数不变。  
**证据：** `scrapy/settings.py` 映射 `QUALITY_CHECK_REQUIRED_FIELDS`；`QualityCheckPipeline.open_spider` 读入 `self.required_fields`；`process_item` **从未读取**。url 硬闸在 `ValidatePipeline`（优先级 300）。  
**不要：** 以为配了必填就能当规则基线。公式与配置不是同一口径。

## P3 — 三套「指纹」不是同一个键

**症状：** 质量管道说不重复，入库仍重复；或反过来。  
**证据：**

| 名字 | 公式 | 范围 |
|---|---|---|
| 质量 dup | `md5(url\|title)` | 单 spider 进程 `_seen` |
| 增量去重 | `md5(url+title+content)` | `params.incremental=true` 才查库 |
| 请求指纹 | `md5(url)[:8]` | 仅 `request.meta`，只打日志 |

**不要：** 用质量 dup_score 当跨任务重复率特征（offline≠online）。特征若用 hash，必须与 consumer 同一公式且 `created_at < :asof`。

## P4 — 用 `quality_score` 预测试采是否通过是恒等式

**症状：** 离线 AUC 漂亮。  
**证据：** `backend/services/ai_planner/orchestrator.py` `_judge_test`：`completed ∧ result_count>0 ∧ avg_score≥40`。y 就是分数闸。  
**不要：** 质量模型的 y 用 `quality_score` 或试采 `passed`。spec FR-72 已承认 ≥40 是代理指标，不是准确率。

## P5 — `flow_generic` 的 `content` 几乎永真

**症状：** 选择器抽空仍轻松过 40。  
**证据：** `scrapy/utils/selector_engine.py` `build_item`：`item["content"] = json.dumps(fields)`；空 dict 也是 `"{}"`。核心维 `content` 非空率被饱和。试采主路径走这里。  
**不要：** 用 `item.get("content")` 当「抽到了正文」。核心维必须看选择器字段，不是 JSON 包装。

## P6 — 代理分无 as-of，且两条阈值对不齐

**症状：** 曾经很好、最近全死的代理仍被抽中；健康服务与中间件对「低分」定义不同。  
**证据：**

- 分 = 全期 `success/(success+fail)`，Redis HASH，无快照（`scrapy/middlewares/__init__.py` `_update_stats`）。
- `ProxyHealthService`：Dynaconf `PROXY_HEALTH.LOW_SCORE_THRESHOLD` 默认 **0.5**，`RECOVER_SCORE` 可配。
- `ProxyMiddleware.from_crawler`：`crawler.settings.get("PROXY_HEALTH.LOW_SCORE_THRESHOLD", 0.2)`。Scrapy Settings 不支持嵌套点号；`scrapy/settings.py` **未平铺**该键 → 静默 **0.2**。

**不要：** 从当前 Redis 分重建历史特征。不要 learning-to-rank 代理（成功标签与抽中纠缠）。先对齐阈值 + 窗口成功率。

## P7 — 渠道 `verdict` 就是启发式自己

**症状：** 用历史 spoofed 训练分类器，离线接近完美。  
**证据：** `channel_probe_service._score_probe_batch` 产出 `verdict`；落库即该函数。`_REF_SIMILARITY_SPOOF_THRESHOLD = 0.15` 硬编码。知识截止题写死「2025 年事件」。spoofed 只 `notify`，不下线（spec FR-61）。raw 回包不存。  
**不要：** 蒸馏 `verdict`。不要用同条 `channel_events.usage` 预测本次 disabled。金标必须是人工确认，且不得等于旧 verdict。

## P8 — 无人终评时 AI 分已经在排首页

**症状：** 把「是否上首页 / 公开曝光」当转化 y，特征里的 `tier` 就是答案。  
**证据：** `derive_tier(human, ai)`：人工缺则用 AI。`PublicSkillResponse` 含 `score`/`tier`。`SkillsSection.tsx` 滤 `tier ∈ {S,A} ∨ status=recommended` 取 6 条。`SkillRepository` 支持 `sort=score|tier`。评分 worker 默认关（`SKILLS.SCORING.ENABLED=false`），但一旦有 AI 分且无人改 `score`，档位仍派生。  
**不要：** listing / 首页 LTR。`real_world_effect` 来自读 SKILL.md 文案，不是安装遥测。校准 LLM vs 人工归 analyst，不是 miner 训练任务。

## P9 — `tenants.status=expired` 不是流失，也不是「不能登录」

**症状：** 用 expired 当 churn y，再用 `expires_at` 当 X，离线满分；上线后过期用户仍在跑任务。  
**证据：** `expire_overdue_tenants` 把 `expires_at < now` 回写成 `expired`。`AuthService.authenticate` 与 `load_auth_identity` **不读** `tenants.status`。`test_expired_tenant_login_rejected` **没有 POST /login**，只断言 status 写回。  
**不要：** 合约到期与行为沉默合成一个模型。登录事实表不存在之前不要做用户级流失。

## P10 — 仓库没有挖掘栈，OLTP 上 `fit` 没有合法性

**症状：** 「先训一个看看」。  
**证据：** `pyproject.toml` / `backend/pyproject.toml` 无 sklearn 等；源码 0 命中训练 API；`dwd_`/`dws_`/`metrics.yaml` 0 命中。spec v1 范围外：「数仓 + 离线模型 → 下一轮」。  
**不要：** 在主库上训练。没有量化动作、独立金标、as-of 快照、Precision@K 的 K 之前，停。

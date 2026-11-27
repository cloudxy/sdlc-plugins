# 用户运营 ≠ 增长运营 ≠ 运维

口诀：**用户运营对人（听与教），增长运营对市场（说与触达），运维对机器。**

| | 用户运营（产品运营） | 增长运营 | 运维 |
|---|---|---|---|
| spawn | `sdlc-workflow:ops` | `sdlc-workflow:growth` | `sdlc-workflow:sre` |
| 英文易错点 | `ops` 会被读成 IT operations | `growth` 不是「做功能」 | 无 |
| 做法 | `signals`（听）+ `enablement`（运营设计 `define/ops-design` + 教/开/告） | `growth`（定位 · 卖点 · 卖点核验 · 精准营销） | `deliver`（日志处理 `log-analysis` · 只读排障 `ops-diagnose` · 发/回/看）+ 伴生 `cicd` |
| 服务对象 | 使用者、买方、客服、活动与留存机制 | 目标人群、渠道、市场 | 进程、日志、发布、告警、回滚 |
| 典型产出 | 需求信号池、运营机制设计、客服话术、发布说明、首次成功路径 | 定位与亮点假设、卖点核验、人群 × 信息 × 渠道 × 时机 × 权益 投放计划 | 日志分析报告、只读故障诊断、发布清单、回滚演练、告警与 runbook |
| 禁止 | deploy / rollback / 事故命令 / 投放计划 | 功能规格 / 界面设计 / 客服话术 / 部署命令 | 用户公告 / 客服话术 / 营销文案 / 未授权生产变更 |

- 「重启 / 回滚」属于本功能已授权的发布或恢复 → 只派 sre，按 `deliver/checklist` 合同执行（恢复步骤、演练与观测都记在清单里）。
- 「解析报错日志 / 服务 OOM / 线上故障只读排查」→ `/sdlc` 可直接路由给 `sre` 的只读任务 `deliver/log-analysis` 或 `deliver/ops-diagnose`（产出诊断报告与缓解预案，**绝不执行未授权生产变更**；持续值班/实时告警响应与未授权生产操作仍不在自动执行范围内，真实生产处置须操作者显式授权）。
- 「活动玩法 / 积分会员 / 留存召回机制设计」→ 派 `ops` 的 `define/ops-design`（产出运营规则、风控护栏与交接给 `pm`/`growth`/`analyst` 的边界）。
- 「用户不知道上线了 / 客服不会答 / 工单在说什么」→ **只** spawn ops（L3 教/开/告用 `stage: enablement`）。
- 「卖点是什么 / 怎么定位 / 该推给谁 / 投放怎么做 / 宣传说的和产品对不上」→ spawn growth（发现带 `stage: growth`，验收 `stage: accept`，L3 上线 `stage: launch`）。
- 发布说明（ops）里的说法必须和 growth 核验过的卖点一致；有冲突以 `04-verify/accept-growth.md` 为准。
- 发现带的 `researcher` / `competitor` 不是日常运营。
- 禁止用「运营环境」指预发或生产；说 **预发 / 生产**。

This file exists so later sessions cannot re-derive `ops` = 运维, or send positioning and campaigns to `ops`.

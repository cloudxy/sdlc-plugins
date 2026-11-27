#!/usr/bin/env python3
"""Zero-config project bootstrap and explainable deterministic routing for sdlc-workflow.

  python3 scripts/workflow.py bootstrap --project-root <dir> [--dry-run] [--json]
  python3 scripts/workflow.py route --text "<request>" [--project-root <dir>] [--json]

Design invariants:
- `bootstrap` NEVER writes or mutates `sdlc.config.yaml` or `.gitignore`. It reuses `check_config.py`
  for read-only detection and `workflow.ensure_local_ignore()` for local-only `.git/info/exclude`,
  and caches an idempotent local snapshot under `.sdlc/_runtime/bootstrap.json`.
- UI blockers (`APP-START`, `APP-URL`, `E2E`) remain explicitly surfaced (`ui_ready: false`) so
  zero-config bootstrap never weakens UI verification gates; non-UI / read-only tasks are immediately ready.
- `route` maps natural-language requests (vague, precise, multi-domain, or high-risk) onto registered
  tasks in `workflow/registry.json`, with explicit disambiguation guards and clarifying questions when
  confidence is low or intent is vague.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_SCRIPTS_DIR = str(_Path(__file__).resolve().parents[1])  # _SDLC_SCRIPTS_PATH
if _SCRIPTS_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_DIR)

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from gates.check_config import check as check_project_config
from workflow import DEFAULT_LOCAL_IGNORES, ensure_local_ignore, load_registry, resolve_task

# High-risk escalation patterns: even a precise phrasing MUST escalate to full_sdlc / high risk.
HIGH_RISK_RULES: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "destructive_ddl",
        "破坏性表结构变更（删表/删列/DROP）",
        re.compile(r"(删表|删列|删除.{0,8}(列|字段|表)|drop\s+(table|column)|alter\s+table.{0,40}drop|truncate\s+table)", re.I),
    ),
    (
        "financial_ledger",
        "资金/账本/计费/支付/退款敏感逻辑",
        re.compile(r"(资金|账本|清结算|结算|计费|余额|扣款|支付|退款|对账单|ledger|billing|payment|refund|wallet)", re.I),
    ),
    (
        "multi_tenant_auth",
        "多租户隔离/鉴权/RBAC/SSO 权限体系",
        re.compile(r"(多租户|租户隔离|鉴权体系|权限体系|权限模型|RBAC|SSO|OAuth|multi-?tenant|tenant\s+isolation)", re.I),
    ),
    (
        "irreversible_client_release",
        "不可逆客户端/SDK/固件发版或强制升级",
        re.compile(r"(客户端发版|App\s*Store|强制升级|固件升级|发布\s*SDK|发版.*(iOS|Android|桌面端))", re.I),
    ),
    (
        "production_mutation",
        "生产环境部署/变更/回滚/重启操作（需显式授权）",
        re.compile(r"(发布生产|上线生产|生产部署|生产发布|重启生产|回滚生产|执行生产|直接重启.*生产|并上线|直接上线|deploy\s+to\s+prod)", re.I),
    ),
]

OFFENSIVE_OUT_OF_SCOPE = re.compile(
    r"(渗透测试|做渗透|渗透爆破|密码爆破|暴力破解|漏洞利用|攻击自动化|主动探测|黑盒攻击|黑盒扫描|提权利用|pentest|penetration\s+test|exploit|brute-?force|\bsqlmap\b|\bnmap\b)",
    re.I,
)

VAGUE_PATTERNS = re.compile(
    r"(想做一个|想做个|打算做|还没想清|不确定怎么做|帮我规划|思路|从零开始|重构整个|重新设计|做一套|做一个.{0,12}(系统|平台|体系|助手))",
    re.I,
)

AMBIGUOUS_ONLY_PATTERNS = re.compile(
    r"^\s*(帮我)?(优化一下|看看这个项目|处理一下数据|改一下|修一下|弄一下|帮我看看|检查一下|分析一下)\s*[。！!？?]*\s*$",
    re.I,
)

# Disambiguation warnings shown in `explain` when common misrouting words appear.
OPS_ENV_TRAP = re.compile(r"运营环境", re.I)

# Preserve classic normal-entry intents so they are NEVER hijacked by clarify_first.
RESUME_PATTERNS = re.compile(
    r"^\s*(?:/sdlc\s+)?(?:继续|接着做|接着刚才|继续上次|继续之前|恢复进度|继续推进|(?:continue|resume)\b)",
    re.I,
)
L0_PATTERNS = re.compile(
    r"(不要走流程|不走流程|跳过流程|只改个?错别字|改个?错别字|修个?错别字|改个?拼写|拼写错误|一行小改|只改一行文案|\blane\s*=\s*L0\b|\btypo\b)",
    re.I,
)
REVIEW_ONLY_PATTERNS = re.compile(
    r"(?:^\s*/sdlc-review\b|^\s*(?:帮我)?\s*(?:只|仅)?\s*(?:做个?|做一次)?\s*(?:独立)?\s*(?:review|审查|评审|挑错)|只要\s*review|只做\s*review|只\s*review|只审查|只评审)",
    re.I,
)
ADVICE_ONLY_PATTERNS = re.compile(
    r"(只给建议|只要建议|先给建议|仅给建议|只提建议|给点建议|只讨论不改|不要改文件|别改文件|不落盘|只出思路|口头建议)",
    re.I,
)

# Disambiguation for "召回策略" (user retention ops vs recommendation/search algorithm).
RECALL_WORD = re.compile(r"召回策略|做召回|召回方案", re.I)
RECALL_OPS_HINTS = re.compile(r"(用户|沉默|流失|促活|短信|push|优惠券|优惠|老客|会员|触达|拉回|运营)", re.I)
RECALL_ALGO_HINTS = re.compile(r"(向量|多路|粗排|精排|重排|推荐|搜索|模型|embedding|faiss|ann|top-?k|召回率|算法|RAG|检索)", re.I)

UI_BLOCKER_CODES = {"APP-START", "APP-URL", "APP-DOWN", "E2E", "UI-TOOL", "UI-CONFIG-NEEDED"}


def _domain_specs() -> list[dict[str, Any]]:
    """Canonical mapping of 16 engineering/product/data/ops domains to registered tasks."""
    return [
        {
            "id": "log_analysis",
            "label": "日志处理与分析",
            "role": "sre",
            "stage": "deliver",
            "task": "log-analysis",
            "patterns": [
                r"(日志解析|解析.{0,12}日志|日志处理|报错日志|错误日志|访问日志|聚合.{0,8}日志|日志告警|日志管道|stacktrace|traceback|log\s*分析|\.log\b)",
            ],
            "negative": [r"(建表|数据表|ORM|model|alembic|迁移|schema)"],
            "priority": 90,
            "reason": "读取并结构化剖析日志文件、聚合错误与时间窗异常（只读分析）",
        },
        {
            "id": "ops_diagnose",
            "label": "日常运维与只读故障排查",
            "role": "sre",
            "stage": "deliver",
            "task": "ops-diagnose",
            "patterns": [
                r"(服务挂了|服务崩了|OOM|CPU\s*飙高|内存泄漏|容器重启|宕机|故障排查|线上故障|502|503|504|超时排查|告警规则|监控告警|runbook|SLI|SLO|K8s|Kubernetes|Docker|运维排查)",
            ],
            "negative": [r"(CI/?CD|流水线|GitHub\s*Actions|GitLab\s*CI)"],
            "priority": 88,
            "reason": "只读故障根因排查、容量与可观测性方案（生产变更仍须显式授权）",
        },
        {
            "id": "cicd_pipeline",
            "label": "CI/CD 与部署流水线",
            "role": "sre",
            "stage": "deliver",
            "task": "ci",
            "patterns": [r"(CI/?CD|流水线|GitHub\s*Actions|GitLab\s*CI|\.gitlab-ci|Dockerfile|构建脚本|部署脚本)"],
            "negative": [],
            "priority": 86,
            "reason": "配置或修复 CI/CD 与构建流水线",
        },
        {
            "id": "security_audit",
            "label": "防御性安全分析与静态审计",
            "role": "architect",
            "stage": "verify",
            "task": "security-audit",
            "patterns": [
                r"(安全分析|安全审计|安全体检|安全扫描|漏洞排查|漏洞审计|代码审计|越权|IDOR|SQL\s*注入|XSS|CSRF|SSRF|密钥泄漏|硬编码密钥|依赖\s*CVE|威胁建模|STRIDE|隐私合规|安全检查)",
            ],
            "negative": [r"(渗透测试|做渗透|渗透爆破|密码爆破|漏洞利用|主动探测|攻击自动化|pentest|exploit|brute-?force)"],
            "priority": 92,
            "reason": "防御性静态安全审计与威胁模型检查（仅本地静态检查，不做主动探测或攻击利用）",
        },
        {
            "id": "schema_db",
            "label": "数据库设计与迁移建模",
            "role": "dba",
            "stage": "dba",
            "task": "migration",
            "patterns": [
                r"(建表|数据表|数据\s*model|ORM\s*model|SQLAlchemy\s*model|alembic|数据库迁移|表结构设计|数据库设计|DDL|schema\.dbml|索引设计|分库分表|慢查询|SQL\s*优化|索引优化|EXPLAIN|查询性能|DROP\s+(?:TABLE|COLUMN)|ALTER\s+TABLE|删表|删列)",
            ],
            "negative": [],
            "priority": 91,
            "reason": "数据库表结构、约束、迁移脚本与 ORM 模型设计实现",
            "sub_selector": [
                (r"(慢查询|SQL\s*优化|索引优化|EXPLAIN|查询性能)", "dba", "dba", "optimize"),
                (r"(仅设计|只出表结构|只画\s*ER|只做\s*schema\s*设计|不执行迁移)", "dba", "dba", "model"),
            ],
        },
        {
            "id": "data_collection",
            "label": "数据采集（爬虫/埋点/CDC/Webhook）",
            "role": "data-collector",
            "stage": "collect",
            "task": "source",
            "patterns": [
                r"(数据采集|爬虫|spider|scrapy|反爬|埋点|tracking|CDC|binlog|webhook\s*接入|第三方\s*API\s*采集|抓取数据)",
            ],
            "negative": [],
            "priority": 85,
            "reason": "采集源契约、埋点方案、爬虫/CDC/Webhook 实现与端到端校验",
            "sub_selector": [
                (r"(埋点|tracking)", "data-collector", "collect", "tracking"),
                (r"(实现爬虫|写爬虫|开发采集|补采集代码|修复爬虫)", "data-collector", "collect", "implement"),
                (r"(校验采集|验证埋点|验证入库)", "data-collector", "collect", "validate"),
                (r"(爬虫报错|采集失败|抓取异常|定位采集)", "data-collector", "collect", "diagnose"),
            ],
        },
        {
            "id": "data_warehouse",
            "label": "数据开发（数仓建模/ETL/口径/补数）",
            "role": "data-warehouse-engineer",
            "stage": "warehouse",
            "task": "design",
            "patterns": [
                r"(数据开发|数仓|数据仓库|ETL|ODS|DWD|DWS|ADS|指标口径|metrics\.yaml|标签体系|tags\.yaml|补数|回填|backfill|数据对账|数据质量审计)",
            ],
            "negative": [r"(建表|ORM|alembic|SQLAlchemy)"],
            "priority": 84,
            "reason": "数仓分层建模、幂等 ETL、统一口径指标/标签与补数对账",
            "sub_selector": [
                (r"(指标树|指标口径|metrics\.yaml)", "data-warehouse-engineer", "warehouse", "metrics"),
                (r"(标签体系|用户标签|tags\.yaml)", "data-warehouse-engineer", "warehouse", "tags"),
                (r"(补数|回填|backfill)", "data-warehouse-engineer", "warehouse", "backfill"),
                (r"(数据审计|数据质量|对账异常)", "data-warehouse-engineer", "warehouse", "audit"),
                (r"(实现\s*ETL|写\s*ETL|开发数仓|加工脚本)", "data-warehouse-engineer", "warehouse", "implement"),
            ],
        },
        {
            "id": "algorithm",
            "label": "算法开发与模型评测",
            "role": "algo",
            "stage": "implement",
            "task": "explore",
            "patterns": [
                r"(算法开发|算法|模型评测|评测集|eval-?set|Prompt\s*优化|RAG|向量检索|排序模型|推荐算法|(?:多路|向量|推荐|搜索|模型|检索).{0,8}召回|粗排|精排|重排|召回率|特征工程|Badcase|模型效果|数据挖掘|机器学习|深度学习)",
            ],
            "negative": [],
            "priority": 87,
            "reason": "算法/模型/Prompt/RAG 离线评测、基线对比、Badcase 诊断与受控实现",
            "sub_selector": [
                (r"(评测|基准|benchmark|对比.*(模型|Prompt))", "algo", "implement", "evaluate"),
                (r"(Badcase|效果下降|漂移|定位.*(召回|排序|模型))", "algo", "implement", "diagnose"),
                (r"(修复.*(算法|模型|Prompt|排序))", "algo", "implement", "fix"),
                (r"(开发|实现|上线).{0,8}(算法|RAG|排序|推荐|提取)", "algo", "implement", "T-1"),
            ],
        },
        {
            "id": "data_analysis_retro",
            "label": "数据分析与运营复盘",
            "role": "analyst",
            "stage": "retro",
            "task": "analyze",
            "patterns": [
                r"(数据分析|运营复盘|活动复盘|上线复盘|转化率.{0,6}(掉|降|跌|升)|留存分析|漏斗分析|A/?B\s*实验|归因分析|指标波动|数据探索|报表分析)",
            ],
            "negative": [],
            "priority": 86,
            "reason": "数据链路体检、SVOT 指标计算、漏斗/因果归因与复盘结论",
            "sub_selector": [
                (r"(上线复盘|活动复盘|效果复盘|readout)", "analyst", "retro", "readout"),
                (r"(实验设计|A/?B\s*实验方案|度量计划|measurement)", "analyst", "define", "measurement-plan"),
            ],
        },
        {
            "id": "ops_design",
            "label": "运营设计与用户运营",
            "role": "ops",
            "stage": "define",
            "task": "ops-design",
            "patterns": [
                r"(运营设计|运营策略|运营方案|活动玩法|促活|(?:沉默|流失|老客|用户|会员|短信|push|优惠券|优惠|触达|运营).{0,8}召回|召回.{0,6}(?:用户|老客|活动|触达|优惠|短信|push)|积分体系|会员权益|用户分层运营|留存机制|发布说明|客服话术|上线公告|用户反馈池|工单汇总)",
            ],
            "negative": [r"运营环境"],
            "priority": 83,
            "reason": "运营活动与留存机制设计、用户信号整理或发布赋能（非机器运维）",
            "sub_selector": [
                (r"(发布说明|客服话术|上线公告|用户指南|onboarding)", "ops", "enablement", "teach-open-announce"),
                (r"(用户反馈|工单汇总|需求信号|舆情收集)", "ops", "signals", "listen"),
            ],
        },
        {
            "id": "growth_marketing",
            "label": "增长定位与精准投放",
            "role": "growth",
            "stage": "growth",
            "task": "positioning",
            "patterns": [r"(增长策略|卖点定位|市场定位|获客|拉新|投放计划|营销文案|渠道转化|精准营销)"],
            "negative": [],
            "priority": 80,
            "reason": "卖点定位、渠道触达与增长转化计划",
            "sub_selector": [(r"(投放|上线推广|营销计划|launch)", "growth", "launch", "precision-marketing")],
        },
        {
            "id": "ui_design",
            "label": "产品 UI 与交互设计",
            "role": "designer",
            "stage": "designer",
            "task": "explore",
            "patterns": [r"(UI\s*设计|界面设计|交互设计|原型设计|画原型|页面布局|视觉规范|设计系统|设计稿|design\s*system)"],
            "negative": [],
            "priority": 85,
            "reason": "界面交互方向、状态流与可运行高保真原型设计",
        },
        {
            "id": "architecture",
            "label": "系统架构与契约设计",
            "role": "architect",
            "stage": "shape",
            "task": "contract",
            "patterns": [r"(架构设计|系统架构|技术方案|模块拆分|服务拆分|接口契约|OpenAPI|可行性评估|技术选型|影响面分析|ADR)"],
            "negative": [],
            "priority": 84,
            "reason": "系统边界、技术选型、接口契约与影响面设计",
            "sub_selector": [
                (r"(可行性|技术调研|spike|压测评估)", "architect", "define", "feasibility"),
                (r"(影响面|变更影响|change-?impact)", "architect", "shape", "change-impact"),
                (r"(一致性核对|架构合规|conformance)", "architect", "verify", "conformance"),
            ],
        },
        {
            "id": "frontend",
            "label": "前端开发与排障",
            "role": "frontend",
            "stage": "implement",
            "task": "T-1",
            "patterns": [r"(前端开发|前端页面|React|Vue|TypeScript|CSS|组件开发|页面报错|样式错位|按钮点不动|浏览器控制台|前端\s*Bug)"],
            "negative": [],
            "priority": 82,
            "reason": "前端组件实现、交互状态修复与界面缺陷定位",
            "sub_selector": [
                (r"(只定位|排查|诊断|为什么.*(白屏|报错|不触发))", "frontend", "implement", "diagnose"),
                (r"(修|修复|解决).{0,10}(Bug|报错|错位|白屏|问题)", "frontend", "implement", "fix"),
            ],
        },
        {
            "id": "backend",
            "label": "后端开发与排障",
            "role": "backend",
            "stage": "implement",
            "task": "T-1",
            "patterns": [r"(后端开发|后端接口|API\s*开发|写个接口|新增接口|服务端|接口报错|500\s*错误|并发锁|幂等|后端\s*Bug|FastAPI|Flask|Django|Spring|Go\s*服务)"],
            "negative": [],
            "priority": 82,
            "reason": "后端 API/服务实现、并发幂等修复与缺陷定位",
            "sub_selector": [
                (r"(只定位|排查|诊断|查一下为什么)", "backend", "implement", "diagnose"),
                (r"(修|修复|解决).{0,10}(Bug|报错|500|异常|问题)", "backend", "implement", "fix"),
            ],
        },
        {
            "id": "qa_testing",
            "label": "测试与质量验证",
            "role": "qa",
            "stage": "verify",
            "task": "risk-based-tests",
            "patterns": [r"(测试用例|测试计划|回归测试|E2E|Playwright|覆盖矩阵|自动化测试|提测验收)"],
            "negative": [],
            "priority": 80,
            "reason": "风险驱动的定向测试计划与自动化验证",
            "sub_selector": [(r"(测试计划|test-?plan)", "qa", "define", "test-plan")],
        },
        {
            "id": "requirements",
            "label": "需求分析与规格定义",
            "role": "pm",
            "stage": "define",
            "task": "spec",
            "patterns": [r"(需求分析|写\s*PRD|需求文档|产品规格|验收标准|GWT|用户故事|功能拆解|需求澄清)"],
            "negative": [],
            "priority": 81,
            "reason": "梳理目标、用户旅程、功能边界与可测试验收标准",
        },
    ]


def bootstrap_project(project_root: str | Path, dry_run: bool = False) -> dict[str, Any]:
    """Idempotent, zero-config Step-0 project bootstrap that never edits sdlc.config.yaml or .gitignore."""
    root = Path(project_root).resolve()
    if not root.is_dir():
        raise ValueError(f"project root does not exist: {project_root}")

    read_only_notices: list[str] = []
    workspace_writable = True
    if dry_run:
        ignore_status = {
            "git_repo": (root / ".git").exists(),
            "exclude_path": None,
            "added": [],
            "already_present": [],
            "tracked": [],
            "dry_run": True,
        }
    else:
        try:
            ignore_status = ensure_local_ignore(root, DEFAULT_LOCAL_IGNORES)
        except PermissionError as exc:
            workspace_writable = False
            read_only_notices.append(f"无法写入 .git/info/exclude（只读工作区，已跳过未改文件）：{exc}")
            ignore_status = {
                "git_repo": (root / ".git").exists(),
                "exclude_path": None,
                "added": [],
                "already_present": [],
                "tracked": [],
                "read_only_skipped": True,
            }

    cfg_check = check_project_config(str(root), probe=False)
    findings = cfg_check.get("findings", [])
    config_present = not any(f.get("code") == "NO-CONFIG" for f in findings)
    ui_roots = cfg_check.get("ui_roots", [])

    global_blockers = [
        {"code": f["code"], "message": f["message"]}
        for f in findings
        if f.get("level") == "blocker" and f.get("code") not in UI_BLOCKER_CODES and f.get("code") != "NO-CONFIG"
    ]
    ui_blockers = [
        {"code": f["code"], "message": f["message"]}
        for f in findings
        if f.get("level") == "blocker" and f.get("code") in UI_BLOCKER_CODES
    ]
    if not config_present and ui_roots:
        ui_blockers.append({
            "code": "UI-CONFIG-NEEDED",
            "message": f"检测到 {len(ui_roots)} 个前端界面目录，执行界面截图/联调/E2E 阶段前需确认启动命令与访问地址。",
        })

    inferred = cfg_check.get("inferred_profile") or {}
    suggested = cfg_check.get("suggested") or {}

    stable_ignored = sorted(set(ignore_status.get("added", [])) | set(ignore_status.get("already_present", [])))
    non_ui_ready = len(global_blockers) == 0
    ui_ready = non_ui_ready and len(ui_blockers) == 0
    snapshot = {
        "schema_version": 1,
        "project_root": str(root),
        "config_present": config_present,
        "config_path": cfg_check.get("config"),
        "config_untouched": True,
        "non_ui_ready": non_ui_ready,
        "ui_ready": ui_ready,
        "global_blockers": global_blockers,
        "ui_roots": [r.get("path") for r in ui_roots],
        "ui_blockers": ui_blockers,
        "inferred_profile": inferred,
        "suggested": suggested,
        "git_repo": bool(ignore_status.get("git_repo")),
        "local_ignored_entries": stable_ignored,
    }

    cache_path = root / ".sdlc" / "_runtime" / "bootstrap.json"
    cache_written = False
    if not dry_run:
        rendered = json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        existing = cache_path.read_text(encoding="utf-8") if cache_path.is_file() else None
        if existing != rendered:
            try:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(rendered, encoding="utf-8")
                cache_written = True
            except PermissionError as exc:
                workspace_writable = False
                read_only_notices.append(f"无法写入缓存 {cache_path}（只读工作区，已保留原状）：{exc}")

    return {
        **snapshot,
        "workspace_writable": workspace_writable,
        "read_only_notices": read_only_notices,
        "ignore_status": ignore_status,
        "cache_path": str(cache_path),
        "cache_written": cache_written,
        "beginner_summary": _format_bootstrap_summary({
            **snapshot,
            "ignore_status": ignore_status,
            "read_only_notices": read_only_notices,
        }),
    }


def _format_bootstrap_summary(snap: dict[str, Any]) -> str:
    if not snap["non_ui_ready"]:
        reasons = "；".join(f"[{b['code']}] {b['message']}" for b in snap.get("global_blockers", []))
        parts = [f"项目尚未就绪（存在全局阻塞）：{snap['project_root']}", f"阻塞项：{reasons}"]
    else:
        parts = [f"项目已就绪：{snap['project_root']}"]
    prof = snap.get("inferred_profile") or {}
    tech = []
    if prof.get("surfaces"):
        tech.append("表面=" + ",".join(prof["surfaces"]))
    if prof.get("db_engines"):
        tech.append("数据库=" + ",".join(prof["db_engines"]))
    if tech:
        parts.append("自动识别栈：" + "；".join(tech))
    if snap["config_present"]:
        parts.append("已保留项目现有 sdlc.config.yaml（未修改）。")
    elif snap["non_ui_ready"]:
        parts.append("无需先写配置文件：日志分析、后端/数据/建表/安全审计等非界面任务可直接开工。")
    if snap["non_ui_ready"] and not snap["ui_ready"]:
        parts.append(f"提示：检测到界面目录 {snap['ui_roots']}，如需做页面截图/联调/E2E 验收，再确认启动命令与端口即可。")
    ig = snap.get("ignore_status") or {}
    if ig.get("added"):
        parts.append(f"已自动将 {', '.join(ig['added'])} 写入本机 .git/info/exclude（未改动 .gitignore）。")
    for notice in snap.get("read_only_notices", []):
        parts.append(f"只读提示：{notice}")
    return "\n".join(parts)


def route_request(text: str, project_root: str | None = None, registry: dict[str, Any] | None = None) -> dict[str, Any]:
    """Deterministically route a natural-language request to registered tasks with explanation & risk gating."""
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("request text is empty")
    reg = registry or load_registry()
    explain: list[str] = []
    bootstrap_info = bootstrap_project(project_root, dry_run=True) if project_root else None

    # 0. Refuse out-of-scope active offensive security requests deterministically before any routing.
    if OFFENSIVE_OUT_OF_SCOPE.search(cleaned):
        res = {
            "input": cleaned,
            "intent_class": "out_of_slice",
            "clarity": "precise",
            "risk_level": "high",
            "risk_triggers": [{"code": "offensive_security_out_of_scope", "reason": "主动渗透/爆破/漏洞利用超出插件防御性静态审计范围"}],
            "track": "out_of_scope",
            "review_policy": "refuse_out_of_scope",
            "recommended_tasks": [],
            "clarifying_question": None,
            "refusal": "本插件仅支持本地源码与配置的防御性静态安全审计（architect/verify/security-audit），拒绝执行线上主动探测、渗透爆破或漏洞利用。",
            "explain": ["命中主动渗透/爆破/攻击利用红线，按 Scope 直接拒绝，不派发任何角色。"],
            "bootstrap": bootstrap_info,
        }
        res["beginner_summary"] = _format_route_summary(res)
        return res

    # 0b. Preserve classic entry intents (resume / L0 / review-only / advice-only) BEFORE domain matching
    #    so they are never hijacked by clarify_first.
    if RESUME_PATTERNS.search(cleaned):
        res = {
            "input": cleaned,
            "intent_class": "resume",
            "clarity": "precise",
            "risk_level": "low",
            "risk_triggers": [],
            "track": "resume",
            "review_policy": "resume_existing_state",
            "recommended_tasks": [],
            "clarifying_question": None,
            "explain": ["命中续跑入口（继续/continue），保留既有 active_work 或未完成任务恢复目标，不触发 clarify_first。"],
            "bootstrap": bootstrap_info,
        }
        res["beginner_summary"] = _format_route_summary(res)
        return res

    if L0_PATTERNS.search(cleaned) and not any(pat.search(cleaned) for _, _, pat in HIGH_RISK_RULES):
        res = {
            "input": cleaned,
            "intent_class": "L0",
            "clarity": "precise",
            "risk_level": "low",
            "risk_triggers": [],
            "track": "L0",
            "review_policy": "none_l0",
            "recommended_tasks": [],
            "clarifying_question": None,
            "no_state_write": True,
            "explain": ["命中 L0 极简修改（错别字/不走流程），免建状态与派单，仅需在提交信息标注 lane=L0。"],
            "bootstrap": bootstrap_info,
        }
        res["beginner_summary"] = _format_route_summary(res)
        return res

    if REVIEW_ONLY_PATTERNS.search(cleaned):
        c = resolve_task(reg, "reviewer", "review", "G-fresh")
        res = {
            "input": cleaned,
            "intent_class": "review-only",
            "clarity": "precise",
            "risk_level": "low",
            "risk_triggers": [],
            "track": "review_only",
            "review_policy": "fresh_read_only_review",
            "recommended_tasks": [{
                "domain_id": "review_only",
                "label": "独立只读审查（不推进状态）",
                "role": "reviewer",
                "stage": "review",
                "task": "G-fresh",
                "skill": c["skill"],
                "mode": "light",
                "read_only": True,
                "requires_source_writes": False,
                "outputs": [reg["artifacts"][a]["paths"][0] for a in c.get("required", []) if a in reg["artifacts"]],
                "reason": "只读独立评审磁盘已有产物，只报告问题，不推进进度",
            }],
            "clarifying_question": None,
            "explain": ["命中只读独立审查入口（review-only），按 /sdlc-review 路径处理，不触发 clarify_first。"],
            "bootstrap": bootstrap_info,
        }
        res["beginner_summary"] = _format_route_summary(res)
        return res

    if ADVICE_ONLY_PATTERNS.search(cleaned):
        res = {
            "input": cleaned,
            "intent_class": "advice_only",
            "clarity": "precise",
            "risk_level": "low",
            "risk_triggers": [],
            "track": "advice_only",
            "review_policy": "advisory_no_disk_write",
            "recommended_tasks": [],
            "clarifying_question": None,
            "no_state_write": True,
            "read_only": True,
            "explain": ["命中「只给建议/不落盘」请求，直接由经理或只读分析口头答复，不强制建任务或写磁盘文件。"],
            "bootstrap": bootstrap_info,
        }
        res["beginner_summary"] = _format_route_summary(res)
        return res

    if OPS_ENV_TRAP.search(cleaned):
        explain.append("防误派提醒：文本出现「运营环境」，已按规则将其识别为预发/生产环境，不误派给用户运营 ops。")

    # Disambiguate bare "召回策略" when neither ops nor algorithm hints appear
    recall_ambiguous = (
        bool(RECALL_WORD.search(cleaned))
        and not bool(RECALL_OPS_HINTS.search(cleaned))
        and not bool(RECALL_ALGO_HINTS.search(cleaned))
    )
    if recall_ambiguous:
        res = {
            "input": cleaned,
            "intent_class": "clarify_first",
            "clarity": "ambiguous",
            "risk_level": "low",
            "risk_triggers": [],
            "track": "clarify_first",
            "review_policy": "pending_clarification",
            "recommended_tasks": [],
            "clarifying_question": "你说的「召回策略」是指【用户运营的沉默/流失用户召回方案】（派给 ops），还是【推荐/搜索算法的候选集多路召回模型】（派给 algo）？",
            "explain": ["「召回策略」在用户运营（ops）与推荐/搜索算法（algo）间存在歧义，先提 1 个定向澄清问题避免误派。"],
            "bootstrap": bootstrap_info,
        }
        res["beginner_summary"] = _format_route_summary(res)
        return res

    # 1. Detect high-risk triggers (independent of phrasing precision)
    risk_triggers = []
    for code, desc, pat in HIGH_RISK_RULES:
        if pat.search(cleaned):
            risk_triggers.append({"code": code, "reason": desc})
            explain.append(f"高风险升档命中 [{code}]：{desc}")

    # 2. Match domains with negative guards & sub-task selectors
    matched: list[dict[str, Any]] = []
    for spec in _domain_specs():
        hit_pat = None
        for pat in spec["patterns"]:
            if re.search(pat, cleaned, re.I):
                hit_pat = pat
                break
        if not hit_pat:
            continue
        neg_hit = next((np for np in spec["negative"] if re.search(np, cleaned, re.I)), None)
        if neg_hit:
            explain.append(f"防误派排除 [{spec['id']}]：命中排除条件 {neg_hit}")
            continue
        role, stage, task_name = spec["role"], spec["stage"], spec["task"]
        for sub_pat, s_role, s_stage, s_task in spec.get("sub_selector", []):
            if re.search(sub_pat, cleaned, re.I):
                role, stage, task_name = s_role, s_stage, s_task
                explain.append(f"细化任务选择 [{spec['id']}] → {role}/{stage}/{task_name}")
                break
        contract = resolve_task(reg, role, stage, task_name)
        matched.append({
            "domain_id": spec["id"],
            "label": spec["label"],
            "priority": spec["priority"],
            "role": role,
            "stage": stage,
            "task": task_name,
            "skill": contract["skill"],
            "protocol_required": bool(contract.get("protocol_required")),
            "writes_source": bool(contract.get("writes_source")),
            "requires_source": bool(contract.get("requires_source")),
            "read_only": not bool(contract.get("writes_source")),
            "outputs": [reg["artifacts"][a]["paths"][0] for a in contract.get("required", []) if a in reg["artifacts"]],
            "reason": spec["reason"],
        })

    matched.sort(key=lambda x: -x["priority"])

    # Deduplicate by (role, stage, task)
    deduped: list[dict[str, Any]] = []
    seen = set()
    for m in matched:
        key = (m["role"], m["stage"], m["task"])
        if key not in seen:
            seen.add(key)
            deduped.append(m)

    is_vague = bool(VAGUE_PATTERNS.search(cleaned))
    is_ambiguous_only = bool(AMBIGUOUS_ONLY_PATTERNS.match(cleaned))
    has_high_risk = len(risk_triggers) > 0

    # 3. Determine clarity, risk_level, track, review_policy, and clarifying question
    clarifying_question = None
    if is_ambiguous_only or (not deduped and not is_vague and not has_high_risk):
        clarity = "ambiguous"
        track = "clarify_first"
        risk_level = "low"
        review_policy = "pending_clarification"
        clarifying_question = (
            "你的目标目前还比较宽泛，为了直接派最合适的专家并避免跑偏，请告诉我一句："
            "你最想先拿到什么结果？（例如：定位某个报错/分析日志、做安全检查、设计表结构/接口、写某块代码，还是先理清产品需求？）"
        )
        explain.append("未命中明确领域或表述过宽，先提 1 个关键问题澄清，避免关键词乱派。")
    elif has_high_risk:
        clarity = "vague" if is_vague else ("multi_domain" if len(deduped) > 1 else "precise")
        track = "full_sdlc"
        risk_level = "high"
        review_policy = "full_g_fresh_and_gates"
        if is_vague:
            clarifying_question = "这个需求涉及高风险改动且目标尚未完全定型：你希望先只出方案与风险评估，还是直接推进到可验证实现？"
        elif any(t["code"] == "production_mutation" for t in risk_triggers):
            clarifying_question = "检测到涉及生产环境操作：本流程默认只做只读诊断与回滚/变更方案，执行生产变更需要你明确确认环境与授权范围，是否先从只读诊断/预案开始？"
        explain.append("触发高风险红线，自动升档为完整护航轨（full_sdlc）并强制独立评审与对应门禁。")
    elif is_vague:
        clarity = "vague"
        track = "full_sdlc"
        risk_level = "medium"
        review_policy = "full_g_fresh_and_gates"
        clarifying_question = "这个想法还在探索阶段，我们先用 1 个问题对齐目标：它最核心要解决谁的什么痛点，做到什么程度算第一版成功？"
        explain.append("命中模糊探索表述，进入探索澄清与完整交付轨（一次一问，不盲目写代码）。")
    elif len(deduped) == 1:
        clarity = "precise"
        item = deduped[0]
        if item["protocol_required"]:
            track = "scoped_team"
            risk_level = "medium"
            review_policy = "focused_g_fresh"
            explain.append("单域精准任务但命中 protocol_required，保留严格任务协议与聚焦核对。")
        else:
            track = "fast_track"
            risk_level = "low"
            review_policy = "manager_mechanical_check"
            explain.append("单域精准低风险任务，命中快车道（fast_track），精简 v2 派发 + 经理 1 轮机械核对。")
    else:
        clarity = "multi_domain"
        track = "scoped_team"
        risk_level = "medium"
        review_policy = "focused_g_fresh"
        explain.append(f"命中 {len(deduped)} 个专业域，进入协作车道（scoped_team），先锚定边界再并发/顺序协作 + 聚焦独立评审。")

    # Annotate recommended dispatch mode per task
    recommended_tasks = []
    for m in deduped:
        mode = "strict" if (track != "fast_track" or m["protocol_required"]) else "light"
        recommended_tasks.append({
            "domain_id": m["domain_id"],
            "label": m["label"],
            "role": m["role"],
            "stage": m["stage"],
            "task": m["task"],
            "skill": m["skill"],
            "mode": mode,
            "read_only": m["read_only"],
            "requires_source_writes": m["writes_source"],
            "outputs": m["outputs"],
            "reason": m["reason"],
        })

    # If high-risk without any matched domain yet, suggest discovery/architecture baseline
    if track == "full_sdlc" and not recommended_tasks and not is_vague:
        if any(t["code"] == "production_mutation" for t in risk_triggers):
            c = resolve_task(reg, "sre", "deliver", "ops-diagnose")
            recommended_tasks.append({
                "domain_id": "ops_diagnose",
                "label": "只读故障诊断与变更预案",
                "role": "sre",
                "stage": "deliver",
                "task": "ops-diagnose",
                "skill": c["skill"],
                "mode": "strict",
                "read_only": True,
                "requires_source_writes": False,
                "outputs": [reg["artifacts"][a]["paths"][0] for a in c["required"]],
                "reason": "先执行只读诊断与预案，生产操作须单独确认授权",
            })
        elif any(t["code"] in ("multi_tenant_auth", "financial_ledger", "destructive_ddl") for t in risk_triggers):
            c = resolve_task(reg, "architect", "shape", "security-review")
            recommended_tasks.append({
                "domain_id": "security_review",
                "label": "高风险架构与安全评估",
                "role": "architect",
                "stage": "shape",
                "task": "security-review",
                "skill": c["skill"],
                "mode": "strict",
                "read_only": True,
                "requires_source_writes": False,
                "outputs": [reg["artifacts"][a]["paths"][0] for a in c["required"]],
                "reason": "高风险改动前置安全与边界评审",
            })

    result = {
        "input": cleaned,
        "intent_class": track,
        "clarity": clarity,
        "risk_level": risk_level,
        "risk_triggers": risk_triggers,
        "track": track,
        "review_policy": review_policy,
        "recommended_tasks": recommended_tasks,
        "clarifying_question": clarifying_question,
        "explain": explain,
        "bootstrap": bootstrap_info,
    }
    result["beginner_summary"] = _format_route_summary(result)
    return result


def _format_route_summary(res: dict[str, Any]) -> str:
    track_cn = {
        "fast_track": "快车道（精准直达）",
        "scoped_team": "协作车道（多专家配合）",
        "full_sdlc": "完整护航流程（探索/高风险保障）",
        "clarify_first": "先澄清 1 个关键问题再开工",
        "resume": "续跑恢复（沿用既有任务状态）",
        "L0": "极简直改 L0（不走流程，提交标注 lane=L0）",
        "review_only": "独立只读审查（不推进状态）",
        "advice_only": "只读建议（不落盘、不改文件）",
        "out_of_scope": "超出授权范围（已拒绝）",
    }[res["track"]]
    lines = [f"执行方式：{track_cn}"]
    if res.get("refusal"):
        lines.append(f"拒绝说明：{res['refusal']}")
    if res["risk_triggers"]:
        lines.append("风险提示：" + "；".join(t["reason"] for t in res["risk_triggers"]))
    if res["recommended_tasks"]:
        who = " → ".join(f"{t['label']}（{t['role']}）" for t in res["recommended_tasks"])
        lines.append(f"建议负责专家：{who}")
    if res["clarifying_question"]:
        lines.append(f"需要你先确认：{res['clarifying_question']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Zero-config bootstrap and explainable deterministic router.")
    sub = parser.add_subparsers(dest="command", required=True)

    pb = sub.add_parser("bootstrap")
    pb.add_argument("--project-root", required=True)
    pb.add_argument("--dry-run", action="store_true")
    pb.add_argument("--json", action="store_true")

    pr = sub.add_parser("route")
    pr.add_argument("--text", "--request", dest="text", required=True)
    pr.add_argument("--project-root")
    pr.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.command == "bootstrap":
            out = bootstrap_project(args.project_root, dry_run=args.dry_run)
        else:
            out = route_request(args.text, project_root=args.project_root)
        if args.json:
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            print(out["beginner_summary"])
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"workflow {args.command}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

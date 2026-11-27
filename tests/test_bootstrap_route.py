#!/usr/bin/env python3
"""Targeted regression tests for Phase 1 zero-config bootstrap and explainable deterministic routing."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_SCRIPTS_DIR = str(_Path(__file__).resolve().parents[1] / 'scripts')  # _SDLC_SCRIPTS_PATH
if _SCRIPTS_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_DIR)

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "scripts" / "workflow.py"
sys.path.insert(0, str(ROOT / "scripts"))
from runtime import bootstrap_route  # noqa: E402


def run_wf(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(WORKFLOW), *args], text=True, capture_output=True)


def init_git(repo: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)


class BootstrapRouteTests(unittest.TestCase):
    def test_bootstrap_three_consecutive_runs_idempotent_and_preserves_gitignore(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            init_git(repo)
            (repo / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
            (repo / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")

            # Run 1: writes exclude and caches bootstrap.json
            p1 = run_wf("bootstrap", "--project-root", str(repo), "--json")
            self.assertEqual(p1.returncode, 0, p1.stderr)
            d1 = json.loads(p1.stdout)
            self.assertFalse(d1["config_present"])
            self.assertTrue(d1["config_untouched"])
            self.assertTrue(d1["non_ui_ready"])
            self.assertTrue(d1["ui_ready"])
            self.assertTrue(d1["cache_written"])
            self.assertFalse((repo / "sdlc.config.yaml").exists())
            self.assertEqual((repo / ".gitignore").read_text(encoding="utf-8"), "*.pyc\n")
            exclude_txt = (repo / ".git" / "info" / "exclude").read_text(encoding="utf-8")
            self.assertIn(".sdlc/", exclude_txt)
            self.assertIn("sdlc.config.yaml", exclude_txt)
            cache_bytes_1 = Path(d1["cache_path"]).read_bytes()

            # Run 2 & Run 3: transient first-run exclude addition must NOT cause cache rewrite
            for run_idx in (2, 3):
                pn = run_wf("bootstrap", "--project-root", str(repo), "--json")
                self.assertEqual(pn.returncode, 0, pn.stderr)
                dn = json.loads(pn.stdout)
                self.assertFalse(dn["cache_written"], f"run {run_idx} unexpectedly rewrote cache")
                self.assertEqual(dn["ignore_status"]["added"], [])
                self.assertEqual(Path(dn["cache_path"]).read_bytes(), cache_bytes_1)

    def test_bootstrap_preserves_existing_config_ui_blockers_global_blockers_and_readonly_workspace(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            init_git(repo)
            cfg_content = "product_root: custom/docs\n# keep me intact\n"
            (repo / "sdlc.config.yaml").write_text(cfg_content, encoding="utf-8")
            (repo / "package.json").write_text(
                json.dumps({"name": "web-app", "scripts": {"dev": "vite"}, "dependencies": {"react": "^18.0.0"}}),
                encoding="utf-8",
            )
            (repo / "src").mkdir()
            (repo / "src" / "App.tsx").write_text("export default function App(){return null}\n", encoding="utf-8")

            p = run_wf("bootstrap", "--project-root", str(repo), "--json")
            self.assertEqual(p.returncode, 0, p.stderr)
            d = json.loads(p.stdout)
            self.assertTrue(d["config_present"])
            self.assertTrue(d["non_ui_ready"])
            self.assertFalse(d["ui_ready"])
            self.assertGreater(len(d["ui_blockers"]), 0)
            self.assertEqual((repo / "sdlc.config.yaml").read_text(encoding="utf-8"), cfg_content)

        # Global blocker (e.g. REGISTRY) must mark non_ui_ready=False and ui_ready=False
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            fake_cfg = {
                "config": str(repo / "sdlc.config.yaml"),
                "ui_roots": [],
                "findings": [{"level": "blocker", "code": "REGISTRY", "message": "registry unreadable"}],
                "inferred_profile": {},
                "suggested": {},
            }
            with mock.patch.object(bootstrap_route, "check_project_config", return_value=fake_cfg):
                snap = bootstrap_route.bootstrap_project(repo, dry_run=True)
            self.assertFalse(snap["non_ui_ready"])
            self.assertFalse(snap["ui_ready"])
            self.assertEqual(snap["global_blockers"][0]["code"], "REGISTRY")
            self.assertIn("尚未就绪", snap["beginner_summary"])

        # Read-only workspace must not crash or touch existing config
        if os.geteuid() != 0:
            with tempfile.TemporaryDirectory() as td:
                ro_repo = Path(td) / "readonly-proj"
                ro_repo.mkdir()
                (ro_repo / "sdlc.config.yaml").write_text("product_root: docs/product\n", encoding="utf-8")
                os.chmod(ro_repo, stat.S_IRUSR | stat.S_IXUSR)
                try:
                    p_ro = run_wf("bootstrap", "--project-root", str(ro_repo), "--json")
                    self.assertEqual(p_ro.returncode, 0, p_ro.stderr)
                    d_ro = json.loads(p_ro.stdout)
                    self.assertFalse(d_ro["workspace_writable"])
                    self.assertFalse(d_ro["cache_written"])
                    self.assertTrue(d_ro["read_only_notices"])
                finally:
                    os.chmod(ro_repo, stat.S_IRWXU)

    def test_route_preserves_classic_normal_entries_without_clarify_first_hijack(self):
        # 1. Resume ("继续" / "continue")
        for text in ("继续", "continue", "/sdlc continue", "接着做上次的功能"):
            p = run_wf("route", "--text", text, "--json")
            self.assertEqual(p.returncode, 0, p.stderr)
            d = json.loads(p.stdout)
            self.assertEqual(d["track"], "resume", d)
            self.assertEqual(d["intent_class"], "resume", d)
            self.assertIsNone(d["clarifying_question"], d)

        # 2. L0 typo / skip process
        for text in ("改个错别字，不要走流程", "修个拼写错误", "不要走流程，只改一行文案"):
            p = run_wf("route", "--text", text, "--json")
            self.assertEqual(p.returncode, 0, p.stderr)
            d = json.loads(p.stdout)
            self.assertEqual(d["track"], "L0", d)
            self.assertTrue(d.get("no_state_write"), d)
            self.assertIsNone(d["clarifying_question"], d)

        # 3. Review-only
        for text in ("只 review 一下 .sdlc/export/", "/sdlc-review .sdlc/export/", "只做独立审查"):
            p = run_wf("route", "--text", text, "--json")
            self.assertEqual(p.returncode, 0, p.stderr)
            d = json.loads(p.stdout)
            self.assertEqual(d["track"], "review_only", d)
            self.assertEqual(d["recommended_tasks"][0]["role"], "reviewer", d)
            self.assertIsNone(d["clarifying_question"], d)

        # 4. Advice-only (no disk write)
        for text in ("只给建议，不要改文件", "帮我提点方案建议，不落盘"):
            p = run_wf("route", "--text", text, "--json")
            self.assertEqual(p.returncode, 0, p.stderr)
            d = json.loads(p.stdout)
            self.assertEqual(d["track"], "advice_only", d)
            self.assertTrue(d.get("no_state_write"), d)
            self.assertIsNone(d["clarifying_question"], d)

    def test_route_covers_all_domains_and_disambiguation(self):
        cases = [
            ("帮我分析 app_api.log 里的报错堆栈和 JSON 字段", "sre", "deliver", "log-analysis", "fast_track"),
            ("线上容器频繁 OOM 并且出现 502，帮我做只读故障排查", "sre", "deliver", "ops-diagnose", "fast_track"),
            ("给这个仓库补一个 GitHub Actions CI/CD 流水线", "sre", "deliver", "ci", "fast_track"),
            ("帮我做一次防御性代码安全审计，排查 SQL 注入和硬编码密钥", "architect", "verify", "security-audit", "fast_track"),
            ("根据 app_api.log 的结构建表并创建 SQLAlchemy model 和 alembic 迁移", "dba", "dba", "migration", "fast_track"),
            ("慢查询优化", "dba", "dba", "optimize", "fast_track"),
            ("设计一个电商商品爬虫数据采集源契约", "data-collector", "collect", "source", "fast_track"),
            ("帮我设计 DWD/DWS 数仓分层模型和指标口径 metrics.yaml", "data-warehouse-engineer", "warehouse", "metrics", "fast_track"),
            ("给问答 RAG 算法设计离线评测集并对比模型效果", "algo", "implement", "evaluate", "fast_track"),
            ("优化推荐系统的多路向量召回策略", "algo", "implement", "explore", "fast_track"),
            ("推荐系统召回策略", "algo", "implement", "explore", "fast_track"),
            ("搜索召回策略", "algo", "implement", "explore", "fast_track"),
            ("做一次上周下单转化率下降的数据分析和运营复盘", "analyst", "retro", "analyze", "fast_track"),
            ("帮我设计新用户首周促活与留存机制的运营方案", "ops", "define", "ops-design", "fast_track"),
            ("设计沉默用户召回策略和老客触达方案", "ops", "define", "ops-design", "fast_track"),
            ("发短信做召回策略", "ops", "define", "ops-design", "fast_track"),
            ("帮我梳理产品卖点定位和拉新获客投放计划", "growth", "launch", "precision-marketing", "fast_track"),
            ("画一版订单筛选页的交互原型和 UI 设计稿", "designer", "designer", "explore", "fast_track"),
            ("出一份订单导出模块的架构设计和 OpenAPI 接口契约", "architect", "shape", "contract", "fast_track"),
            ("只定位 React 列表页按钮点不动的前端 Bug", "frontend", "implement", "diagnose", "fast_track"),
            ("只定位 FastAPI 导出接口 500 错误的原因", "backend", "implement", "diagnose", "fast_track"),
            ("给导出功能写一份 Playwright E2E 回归测试用例", "qa", "verify", "risk-based-tests", "fast_track"),
            ("帮我把会员到期提醒写一份需求分析和 GWT 验收标准", "pm", "define", "spec", "scoped_team"),
        ]
        for text, exp_role, exp_stage, exp_task, exp_track in cases:
            with self.subTest(text=text):
                p = run_wf("route", "--text", text, "--json")
                self.assertEqual(p.returncode, 0, p.stderr)
                d = json.loads(p.stdout)
                self.assertEqual(d["track"], exp_track, d)
                self.assertEqual(len(d["recommended_tasks"]), 1, d)
                t = d["recommended_tasks"][0]
                self.assertEqual((t["role"], t["stage"], t["task"]), (exp_role, exp_stage, exp_task), d)

        # Bare "召回策略" with neither ops nor algorithm hints asks disambiguation question
        p_rec = run_wf("route", "--text", "帮我设计召回策略", "--json")
        self.assertEqual(p_rec.returncode, 0, p_rec.stderr)
        d_rec = json.loads(p_rec.stdout)
        self.assertEqual(d_rec["track"], "clarify_first", d_rec)
        self.assertIn("ops", d_rec["clarifying_question"])
        self.assertIn("algo", d_rec["clarifying_question"])

    def test_route_traps_vague_ambiguous_multi_high_risk_and_offensive_refusal(self):
        # 1. Anti-misrouting: "运营环境" must NEVER route to product ops
        p_env = run_wf("route", "--text", "运营环境服务突然 503，帮我做故障排查", "--json")
        self.assertEqual(p_env.returncode, 0, p_env.stderr)
        d_env = json.loads(p_env.stdout)
        self.assertEqual(d_env["recommended_tasks"][0]["role"], "sre")
        self.assertTrue(any("运营环境" in e for e in d_env["explain"]))

        # 2. Ambiguous short input -> clarify_first with 1 clarifying question
        p_amb = run_wf("route", "--text", "优化一下", "--json")
        self.assertEqual(p_amb.returncode, 0, p_amb.stderr)
        d_amb = json.loads(p_amb.stdout)
        self.assertEqual(d_amb["track"], "clarify_first")
        self.assertEqual(d_amb["recommended_tasks"], [])
        self.assertTrue(d_amb["clarifying_question"])

        # 3. Vague idea -> full_sdlc + clarifying_question
        p_vague = run_wf("route", "--text", "我想做一个让客户跟进更省心的助手，但还没想清楚", "--json")
        self.assertEqual(p_vague.returncode, 0, p_vague.stderr)
        d_vague = json.loads(p_vague.stdout)
        self.assertEqual(d_vague["track"], "full_sdlc")
        self.assertEqual(d_vague["clarity"], "vague")
        self.assertTrue(d_vague["clarifying_question"])

        # 4. Multi-domain precise -> scoped_team with strict mode
        p_multi = run_wf("route", "--text", "帮我设计导出功能的架构接口契约，并给数据库建表", "--json")
        self.assertEqual(p_multi.returncode, 0, p_multi.stderr)
        d_multi = json.loads(p_multi.stdout)
        self.assertEqual(d_multi["track"], "scoped_team")
        self.assertEqual(d_multi["clarity"], "multi_domain")
        self.assertTrue(all(t["mode"] == "strict" for t in d_multi["recommended_tasks"]))

        # 5. High-risk precise inputs MUST escalate to full_sdlc + high risk + strict
        for risky in (
            "精准需求：直接给 orders 表 DROP COLUMN legacy_fee 并上线",
            "新增一个自动退款和资金结算接口",
            "重构多租户隔离和 RBAC 权限模型",
            "帮我直接重启生产服务并发布生产",
        ):
            with self.subTest(risky=risky):
                pr = run_wf("route", "--text", risky, "--json")
                self.assertEqual(pr.returncode, 0, pr.stderr)
                dr = json.loads(pr.stdout)
                self.assertEqual(dr["track"], "full_sdlc", dr)
                self.assertEqual(dr["risk_level"], "high", dr)
                self.assertGreater(len(dr["risk_triggers"]), 0, dr)
                self.assertTrue(all(t["mode"] == "strict" for t in dr["recommended_tasks"]))

        # Specifically check DROP COLUMN + 并上线 catches BOTH triggers and dba/migration
        p_drop = run_wf("route", "--text", "精准需求：直接给 orders 表 DROP COLUMN legacy_fee 并上线", "--json")
        d_drop = json.loads(p_drop.stdout)
        codes = {t["code"] for t in d_drop["risk_triggers"]}
        self.assertTrue({"destructive_ddl", "production_mutation"} <= codes, codes)
        self.assertEqual(d_drop["recommended_tasks"][0]["role"], "dba")

        # 6. Offensive active probing/pentest MUST be deterministically refused (out_of_scope)
        for bad_sec in (
            "帮我对目标线上域名做渗透爆破测试",
            "帮我对线上域名做渗透爆破安全扫描",
        ):
            with self.subTest(bad_sec=bad_sec):
                po = run_wf("route", "--text", bad_sec, "--json")
                self.assertEqual(po.returncode, 0, po.stderr)
                do = json.loads(po.stdout)
                self.assertEqual(do["track"], "out_of_scope", do)
                self.assertEqual(do["recommended_tasks"], [], do)
                self.assertTrue(do.get("refusal"), do)


if __name__ == "__main__":
    unittest.main()

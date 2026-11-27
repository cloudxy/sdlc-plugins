#!/usr/bin/env python3
"""Targeted regression tests for Phase 3 pure-stdlib defensive tools and manifest-bound light/strict dispatch."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_SCRIPTS_DIR = str(_Path(__file__).resolve().parents[1] / 'scripts')  # _SDLC_SCRIPTS_PATH
if _SCRIPTS_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_DIR)

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "scripts" / "workflow.py"
TOOLS = ROOT / "scripts" / "tools"


def run_py(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(script), *args], text=True, capture_output=True)


def init_git_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "README.md").write_text("demo\n", encoding="utf-8")
    (repo / "dirty_old.py").write_text("v = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md", "dirty_old.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)


class ToolsAndDispatchTests(unittest.TestCase):
    def test_log_profiler_schema_errors_and_strict_redaction(self):
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "api.log"
            pw_key = "pass" + "word"
            log.write_text(
                "\n".join([
                    '2026-11-27 10:00:01 INFO GET /cat status=200 {"code": 0, "data": {"items": [{"sku": "A1", "price": 12.5, "tag": null}]}}',
                    f'2026-11-27 10:00:02 ERROR db connect failed postgresql+psycopg://admin:SuperSecret99@db.prod.local/app {pw_key}="QuotedPass123" status=500',
                    '2026-11-27 10:00:03 ERROR Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.SecretPayload99 status=401',
                    '2026-11-27 10:00:04 ERROR {"password": "JsonSecret88", "api_key": "ApiSecret77", "authorization": "Bearer TokSecret66"}',
                ]) + "\n",
                encoding="utf-8",
            )
            p = run_py(TOOLS / "log_profiler.py", str(log))
            self.assertEqual(p.returncode, 0, p.stderr)
            d = json.loads(p.stdout)
            self.assertEqual(d["lines_scanned"], 4)
            self.assertEqual(d["levels"]["ERROR"], 3)
            self.assertEqual(d["http_statuses"]["200"], 1)
            self.assertEqual(d["http_statuses"]["500"], 1)
            self.assertEqual(d["json_records_found"], 2)
            self.assertIn("data.items[].sku", d["json_schema"])
            for secret in ("SuperSecret99", "QuotedPass123", "SecretPayload99", "eyJhbGciOi", "JsonSecret88", "ApiSecret77", "TokSecret66"):
                self.assertNotIn(secret, p.stdout, f"secret leaked in JSON output: {secret}")
            self.assertIn("[REDACTED]", p.stdout)

            p_md = run_py(TOOLS / "log_profiler.py", str(log), "--md")
            self.assertEqual(p_md.returncode, 0, p_md.stderr)
            self.assertIn("# Log Profile:", p_md.stdout)
            for secret in ("SuperSecret99", "QuotedPass123", "SecretPayload99", "JsonSecret88", "TokSecret66"):
                self.assertNotIn(secret, p_md.stdout)

    def test_schema_parity_pass_drift_ident_limit_and_empty_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            model_py = d / "model.py"
            mig_py = d / "001_init.py"
            dbml = d / "erd.dbml"
            fixture = d / "sample.json"

            model_py.write_text(
                "class CatMetric(Base):\n"
                "    __tablename__ = 'ods_cat_metric'\n"
                "    __table_args__ = (Index('idx_cat_sku', 'sku_id'),)\n"
                "    id = Column(Integer, primary_key=True)\n"
                "    sku_id = Column(String(64), nullable=False)\n"
                "    gmv = Column(Numeric(12, 2), nullable=True)\n",
                encoding="utf-8",
            )
            mig_py.write_text(
                "def upgrade():\n"
                "    op.create_table(\n"
                "        'ods_cat_metric',\n"
                "        sa.Column('id', sa.Integer(), nullable=False),\n"
                "        sa.Column('sku_id', sa.String(64), nullable=False),\n"
                "        sa.Column('gmv', sa.Numeric(12, 2), nullable=True),\n"
                "    )\n"
                "    op.create_index('idx_cat_sku', 'ods_cat_metric', ['sku_id'])\n",
                encoding="utf-8",
            )
            dbml.write_text(
                "Table ods_cat_metric {\n"
                "  id int [pk]\n"
                "  sku_id varchar(64) [not null]\n"
                "  gmv decimal(12,2) [null]\n"
                "}\n",
                encoding="utf-8",
            )
            fixture.write_text(json.dumps({"ods_cat_metric": [{"sku_id": "S1", "gmv": 99.5}]}), encoding="utf-8")

            p_ok = run_py(
                TOOLS / "schema_parity.py",
                "--models", str(model_py),
                "--migrations", str(mig_py),
                "--dbml", str(dbml),
                "--fixture", str(fixture),
            )
            self.assertEqual(p_ok.returncode, 0, p_ok.stdout + p_ok.stderr)
            self.assertTrue(json.loads(p_ok.stdout)["parity_ok"])

            # Empty / unsupported inputs MUST NEVER return parity_ok=true
            empty_m = d / "empty_models.py"
            empty_g = d / "empty_mig.py"
            empty_m.write_text("# plain python without SQLAlchemy models\nclass Foo:\n    pass\n", encoding="utf-8")
            empty_g.write_text("# unsupported raw sql comment\n", encoding="utf-8")
            p_empty = run_py(TOOLS / "schema_parity.py", "--models", str(empty_m), "--migrations", str(empty_g))
            self.assertEqual(p_empty.returncode, 1)
            res_empty = json.loads(p_empty.stdout)
            self.assertFalse(res_empty["parity_ok"])
            self.assertEqual(sorted(res_empty["empty_or_unsupported_sources"]), ["migrations", "models"])

            # Empty fixture table must also fail parity_ok
            empty_fix = d / "empty_fix.json"
            empty_fix.write_text(json.dumps({"ods_cat_metric": []}), encoding="utf-8")
            p_efix = run_py(TOOLS / "schema_parity.py", "--models", str(model_py), "--fixture", str(empty_fix))
            self.assertEqual(p_efix.returncode, 1)
            self.assertFalse(json.loads(p_efix.stdout)["parity_ok"])

            # Nullable mismatch + >64-char index name
            long_ix = "idx_" + "x" * 65
            mig_py.write_text(
                "def upgrade():\n"
                "    op.create_table(\n"
                "        'ods_cat_metric',\n"
                "        sa.Column('id', sa.Integer(), nullable=False),\n"
                "        sa.Column('sku_id', sa.String(64), nullable=True),\n"
                "    )\n"
                f"    op.create_index('{long_ix}', 'ods_cat_metric', ['sku_id'])\n",
                encoding="utf-8",
            )
            p_bad = run_py(TOOLS / "schema_parity.py", "--models", str(model_py), "--migrations", str(mig_py))
            self.assertEqual(p_bad.returncode, 1)
            res_bad = json.loads(p_bad.stdout)
            self.assertFalse(res_bad["parity_ok"])
            self.assertTrue(res_bad["column_diffs"])
            self.assertTrue(res_bad["nullable_diffs"])
            self.assertTrue(res_bad["long_identifiers"])

    def test_sec_quickscan_same_line_redaction_symlink_guard_and_counts(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            tok_outside = "ghp_" + "OUTSIDE" + ("0" * 30)
            tok_sk = "sk-" + "SameLineSecretToken123456"
            tok_ghp = "ghp_" + "1234567890" + "abcdefghijklmnopqrstuvwxyz"
            jwt_same = "eyJhbGciOiJIUzI1NiJ9." + "SameLineJwtSecret99"

            outside = base / "outside_secret.py"
            outside.write_text(f"TOKEN = '{tok_outside}'\n", encoding="utf-8")

            scan_dir = base / "repo"
            scan_dir.mkdir()
            (scan_dir / "node_modules").mkdir()
            (scan_dir / "node_modules" / "skip.js").write_text("eval(userInput)\n", encoding="utf-8")
            # Symlink pointing outside scan directory MUST be skipped
            (scan_dir / "escape_link.py").symlink_to(outside)
            # Oversized file (>1MB) must be counted in files_skipped_size
            (scan_dir / "huge.py").write_text("x = 1\n" * 200_000, encoding="utf-8")
            # Same-line secret + non-secret rule (shell=True & verify=False) MUST redact BOTH findings!
            (scan_dir / "app.py").write_text(
                "\n".join([
                    f"subprocess.run(\"curl -H 'Authorization: Bearer {jwt_same}' https://x\", shell=True)",
                    f"subprocess.run('curl -H \"Authorization: Bearer {tok_sk}\"', shell=True)",
                    f"requests.get('https://x', headers={{'token': '{tok_ghp}'}}, verify=False)",
                    "cur.execute(f'SELECT * FROM users WHERE id={uid}')",
                ]) + "\n",
                encoding="utf-8",
            )

            p = run_py(TOOLS / "sec_quickscan.py", str(scan_dir))
            self.assertEqual(p.returncode, 0, p.stderr)
            res = json.loads(p.stdout)
            self.assertEqual(res["scope"], "defensive_static_clues_only")
            self.assertFalse(res["active_probing"])
            self.assertTrue(res["requires_semantic_review"])
            self.assertEqual(res["files_discovered"], 2)  # app.py + huge.py (symlink & node_modules excluded)
            self.assertEqual(res["files_scanned"], 1)     # only app.py scanned
            self.assertEqual(res["files_skipped_size"], 1)
            self.assertEqual(res["files_skipped_symlink"], 1)
            self.assertFalse(res["truncated"])
            # ZERO secret leaks across ANY rule on same line or outside symlink!
            for secret in ("SameLineJwtSecret99", "SameLineSecretToken123456", tok_ghp, "OUTSIDE000000"):
                self.assertNotIn(secret, p.stdout, f"secret leaked: {secret}")
            # Both shell=True and verify=False still reported as clues with redacted snippet
            ids = {f["rule_id"] for f in res["findings"]}
            self.assertTrue({"SEC-SECRET-TOKEN", "SEC-SHELL-TRUE", "SEC-TLS-VERIFY-FALSE", "SEC-RAW-SQL-FORMAT"} <= ids)

            # Verify --max-files truncation flag
            (scan_dir / "extra.py").write_text("eval(x)\n", encoding="utf-8")
            p_trunc = run_py(TOOLS / "sec_quickscan.py", str(scan_dir), "--max-files", "1")
            res_t = json.loads(p_trunc.stdout)
            self.assertTrue(res_t["truncated"])
            self.assertEqual(res_t["files_discovered"], 3)

    def test_dispatch_and_finish_light_bound_audit_dirty_retry_concurrent_and_bypass(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            init_git_repo(repo)
            froot = repo / ".sdlc" / "log-check"
            froot.mkdir(parents=True)

            # Create pre-existing dirty tracked modification AND pre-existing untracked file
            (repo / "dirty_old.py").write_text("v = 2  # preexisting dirty\n", encoding="utf-8")
            (repo / "preexisting_untracked.txt").write_text("keep me\n", encoding="utf-8")

            # 1. Read-only task light dispatch creates bound manifest + baseline snapshot
            p = run_py(
                WORKFLOW, "dispatch", "--mode", "light",
                "--role", "sre", "--stage", "deliver", "--task", "log-analysis",
                "--feature-root", str(froot), "--project-root", str(repo),
                "--intent-quote", "分析 app_api.log 报错",
            )
            self.assertEqual(p.returncode, 0, p.stderr)
            d = json.loads(p.stdout)
            manifest1 = Path(d["manifest"])
            self.assertTrue(manifest1.is_file())
            self.assertTrue(Path(d["packet"]).is_file())

            # 2. High-risk intent_quote MUST be mechanically blocked from --mode light even on non-protocol_required task
            p_hr = run_py(
                WORKFLOW, "dispatch", "--mode", "light",
                "--role", "dba", "--stage", "dba", "--task", "migration",
                "--feature-root", str(froot), "--project-root", str(repo),
                "--intent-quote", "执行 DROP COLUMN legacy_fee 删列迁移",
                "--source-write", "models/",
            )
            self.assertEqual(p_hr.returncode, 2)
            self.assertIn("high-risk", p_hr.stderr)

            # 3. Caller cannot forge finish --mode light without --run or with --source-write / --project-root overrides
            p_no_run = run_py(
                WORKFLOW, "finish", "--mode", "light",
                "--role", "sre", "--stage", "deliver", "--task", "log-analysis",
                "--feature-root", str(froot),
            )
            self.assertEqual(p_no_run.returncode, 2)
            p_override = run_py(
                WORKFLOW, "finish", "--mode", "light",
                "--run", str(manifest1), "--source-write", "dirty_old.py",
            )
            self.assertEqual(p_override.returncode, 2)

            # 4. Legal deliverable + legal role memory_file + UNTOUCHED pre-existing dirty files => PASS!
            out_file = froot / "04-verify" / "log-analysis.md"
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text("# Log Analysis\n\nClustered 3 errors.\n", encoding="utf-8")
            mem_file = froot / "memory" / "sre.md"
            mem_file.parent.mkdir(parents=True, exist_ok=True)
            mem_file.write_text("# SRE Memory\nObserved app_api.log.\n", encoding="utf-8")

            pf_ok = run_py(WORKFLOW, "finish", "--mode", "light", "--run", str(manifest1))
            self.assertEqual(pf_ok.returncode, 0, pf_ok.stdout + pf_ok.stderr)
            res_ok = json.loads(pf_ok.stdout)
            self.assertTrue(res_ok["ok"])
            self.assertEqual(res_ok["write_audit_status"], "verified")
            # Both legal deliverable and role memory must be observed and explicitly authorized
            auth_paths = {a["path"] for a in res_ok["authorized_changes"]}
            self.assertIn(str(out_file.resolve()), auth_paths)
            self.assertIn(str(mem_file.resolve()), auth_paths)
            # Pre-existing dirty files remain intact and were NOT blamed
            self.assertEqual((repo / "dirty_old.py").read_text(encoding="utf-8"), "v = 2  # preexisting dirty\n")
            self.assertTrue((repo / "preexisting_untracked.txt").is_file())

            # 5. Sequential retry: dispatch run 2 after run 1 finished, then modify SAME already-dirty file,
            #    new untracked file, AND another role's memory file inside .sdlc/ => ALL THREE MUST FAIL!
            p2 = run_py(
                WORKFLOW, "dispatch", "--mode", "light",
                "--role", "sre", "--stage", "deliver", "--task", "log-analysis",
                "--feature-root", str(froot), "--project-root", str(repo),
                "--intent-quote", "复核 app_api.log 报错",
            )
            self.assertEqual(p2.returncode, 0, p2.stderr)
            manifest2 = Path(json.loads(p2.stdout)["manifest"])
            (repo / "dirty_old.py").write_text("v = 3  # illegally modified again during run 2!\n", encoding="utf-8")
            (repo / "new_unauthorized.py").write_text("rogue = 1\n", encoding="utf-8")
            (froot / "memory" / "pm.md").write_text("cross-role memory tamper\n", encoding="utf-8")

            pf_bad = run_py(WORKFLOW, "finish", "--mode", "light", "--run", str(manifest2))
            self.assertEqual(pf_bad.returncode, 1)
            res_bad = json.loads(pf_bad.stdout)
            self.assertFalse(res_bad["ok"])
            self.assertEqual(res_bad["write_audit_status"], "failed")
            joined_out = " ".join(res_bad["outside_source_writes"])
            self.assertIn("dirty_old.py", joined_out)
            self.assertIn("new_unauthorized.py", joined_out)
            self.assertIn("pm.md", joined_out)

            # 6. Tampered light manifest => write_audit_status: unknown, ok: False
            tampered = froot / "runs" / "tampered-manifest.json"
            m_data = json.loads(manifest1.read_text(encoding="utf-8"))
            m_data["source_writes"] = ["dirty_old.py"]  # tamper without valid sha
            tampered.write_text(json.dumps(m_data), encoding="utf-8")
            pf_tamp = run_py(WORKFLOW, "finish", "--mode", "light", "--run", str(tampered))
            self.assertEqual(pf_tamp.returncode, 1)
            self.assertEqual(json.loads(pf_tamp.stdout)["write_audit_status"], "unknown")

            # 7. Overlapping concurrent light runs on same project_root => BOTH Run B AND Run A fail closed (unknown_concurrent)
            pa = run_py(
                WORKFLOW, "dispatch", "--mode", "light",
                "--role", "sre", "--stage", "deliver", "--task", "log-analysis",
                "--feature-root", str(froot), "--project-root", str(repo),
                "--intent-quote", "并发任务 A",
            )
            pb = run_py(
                WORKFLOW, "dispatch", "--mode", "light",
                "--role", "sre", "--stage", "deliver", "--task", "ops-diagnose",
                "--feature-root", str(froot), "--project-root", str(repo),
                "--intent-quote", "并发任务 B",
            )
            self.assertEqual(pa.returncode, 0, pa.stderr)
            self.assertEqual(pb.returncode, 0, pb.stderr)
            pf_conc_b = run_py(WORKFLOW, "finish", "--mode", "light", "--run", json.loads(pb.stdout)["manifest"])
            self.assertEqual(pf_conc_b.returncode, 1)
            self.assertEqual(json.loads(pf_conc_b.stdout)["write_audit_status"], "unknown_concurrent")
            # Even after B has finished inside A's lifespan, finishing A MUST ALSO detect the overlap!
            pf_conc_a = run_py(WORKFLOW, "finish", "--mode", "light", "--run", json.loads(pa.stdout)["manifest"])
            self.assertEqual(pf_conc_a.returncode, 1)
            self.assertEqual(json.loads(pf_conc_a.stdout)["write_audit_status"], "unknown_concurrent")

    def test_dispatch_light_dotfiles_parent_escape_deliverable_bounds_and_snapshot_limit(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            init_git_repo(repo)
            froot = repo / ".sdlc" / "ci-dotfile"
            froot.mkdir(parents=True)

            # 1. Legitimate dotfile in --source-write MUST preserve leading dot (never corrupted by lstrip)
            p_dot = run_py(
                WORKFLOW, "dispatch", "--mode", "light",
                "--role", "sre", "--stage", "deliver", "--task", "ci",
                "--feature-root", str(froot), "--project-root", str(repo),
                "--intent-quote", "补一个 GitHub Actions CI 配置",
                "--source-write", "./.github/workflows/ci.yml",
            )
            self.assertEqual(p_dot.returncode, 0, p_dot.stderr)
            d_dot = json.loads(p_dot.stdout)
            self.assertEqual(d_dot["source_writes"], [".github/workflows/ci.yml"])

            # Writing the exact dotfile + required deliverable passes bound audit
            ci_file = repo / ".github" / "workflows" / "ci.yml"
            ci_file.parent.mkdir(parents=True, exist_ok=True)
            ci_file.write_text("name: ci\non: [push]\n", encoding="utf-8")
            ci_doc = froot / "06-deliver" / "ci.md"
            ci_doc.parent.mkdir(parents=True, exist_ok=True)
            ci_doc.write_text("# CI\nWired .github/workflows/ci.yml\n", encoding="utf-8")
            pf_dot = run_py(WORKFLOW, "finish", "--mode", "light", "--run", d_dot["manifest"])
            self.assertEqual(pf_dot.returncode, 0, pf_dot.stdout + pf_dot.stderr)
            res_dot = json.loads(pf_dot.stdout)
            self.assertTrue(res_dot["ok"])
            self.assertEqual(res_dot["write_audit_status"], "verified")
            self.assertIn("baseline_ms", res_dot["snapshot_stats"])

            # 2. Parent traversal & root/sdlc --source-write MUST be rejected (never rewritten into another path!)
            for bad_sw in ("../outside.py", "./../outside.py", "a/../../outside.py", ".", "./", ".sdlc/hack.md"):
                with self.subTest(bad_sw=bad_sw):
                    pb = run_py(
                        WORKFLOW, "dispatch", "--mode", "light",
                        "--role", "sre", "--stage", "deliver", "--task", "ci",
                        "--feature-root", str(froot), "--project-root", str(repo),
                        "--intent-quote", "CI 修改",
                        "--source-write", bad_sw,
                    )
                    self.assertEqual(pb.returncode, 2, f"expected rejection for {bad_sw}, got: {pb.stdout}")

            # 3. --deliverable MUST be constrained to task contract allowed outputs inside feature_root
            for bad_deliv in ("../escape.md", "/tmp/abs.md", "memory/pm.md", "01-define/spec.md", "."):
                with self.subTest(bad_deliv=bad_deliv):
                    pd = run_py(
                        WORKFLOW, "dispatch", "--mode", "light",
                        "--role", "sre", "--stage", "deliver", "--task", "log-analysis",
                        "--feature-root", str(froot), "--project-root", str(repo),
                        "--intent-quote", "日志分析",
                        "--deliverable", bad_deliv,
                    )
                    self.assertEqual(pd.returncode, 2, f"expected rejection for {bad_deliv}, got: {pd.stdout}")

            # 4. Large-repo snapshot limit exceeded => dispatch warns write_audit_capable=False, finish fails closed as unknown!
            froot_big = repo / ".sdlc" / "big-repo-check"
            p_lim = run_py(
                WORKFLOW, "dispatch", "--mode", "light",
                "--role", "sre", "--stage", "deliver", "--task", "log-analysis",
                "--feature-root", str(froot_big), "--project-root", str(repo),
                "--intent-quote", "大仓日志分析",
                "--snapshot-limit", "1",
            )
            self.assertEqual(p_lim.returncode, 0, p_lim.stderr)
            d_lim = json.loads(p_lim.stdout)
            self.assertFalse(d_lim["write_audit_capable"])
            self.assertEqual(d_lim["snapshot_stats"]["status"], "unprovable_limit_exceeded")
            self.assertTrue(any(w.get("code") == "LIGHT-SNAPSHOT-UNPROVABLE" for w in d_lim["warnings"]))

            # Even if deliverable is created, finish --mode light MUST NOT return ok=True when audit is unprovable
            big_out = froot_big / "04-verify" / "log-analysis.md"
            big_out.parent.mkdir(parents=True, exist_ok=True)
            big_out.write_text("# Log Analysis\nDone.\n", encoding="utf-8")
            pf_lim = run_py(WORKFLOW, "finish", "--mode", "light", "--run", d_lim["manifest"])
            self.assertEqual(pf_lim.returncode, 1)
            res_lim = json.loads(pf_lim.stdout)
            self.assertFalse(res_lim["ok"])
            self.assertEqual(res_lim["write_audit_status"], "unknown")
            self.assertTrue(res_lim.get("missing_audit_reason"))

    def test_dispatch_and_finish_strict_roundtrip_interrupted_and_light_bypass_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            init_git_repo(repo)
            froot = repo / ".sdlc" / "sec-audit"
            froot.mkdir(parents=True)
            (repo / "sdlc.config.yaml").write_text("product_root: docs/product\n", encoding="utf-8")
            (repo / "docs" / "product").mkdir(parents=True, exist_ok=True)
            (repo / "docs" / "product" / "architecture.md").write_text("# Architecture\nAccepted baseline.\n", encoding="utf-8")
            (froot / "state.yaml").write_text(
                "\n".join([
                    "feature: sec-audit",
                    "sdlc_version: 4",
                    "task_protocol: 1",
                    "required_capabilities:",
                    '  - "input-contract-v1"',
                    '  - "result-v1"',
                    '  - "task-closure-v1"',
                    "lane: L2",
                    "ui: false",
                    "tracking: false",
                    "q_security: true",
                    "rework_rounds: 0",
                    "selected_tasks:",
                    "  - id: T-SEC-1",
                    "    role: architect",
                    "    stage: verify",
                    "    task: security-audit",
                    "    gate_stage: verify",
                    "    depends_on: []",
                    "    status: todo",
                    "    selection:",
                    "      required: true",
                    '      reason: "user request"',
                    '      source: "user quote"',
                    "obligations: []",
                ]) + "\n",
                encoding="utf-8",
            )
            scope_doc = froot / "00-discover" / "audit-scope.md"
            scope_doc.parent.mkdir(parents=True, exist_ok=True)
            scope_doc.write_text("# Audit Scope\nTarget: src/auth.py and token verification paths.\n", encoding="utf-8")
            bindings = froot / "bindings.json"
            bindings.write_text(json.dumps({
                "task_id": "T-SEC-1",
                "intent_quote": "检查认证权限安全",
                "assignment": "对仓库执行只读防御性静态安全审计并输出 04-verify/security-audit.md。",
                "project_root": str(repo),
                "product_root": str(repo / "docs/product"),
                "inputs": {"audit_scope": str(scope_doc)},
                "deliverable_paths": ["04-verify/security-audit.md"],
            }), encoding="utf-8")
            draft = froot / "draft.json"

            pd = run_py(
                WORKFLOW, "dispatch", "--mode", "strict",
                "--role", "architect", "--stage", "verify", "--task", "security-audit",
                "--feature-root", str(froot),
                "--bindings", str(bindings),
                "--draft-out", str(draft),
            )
            self.assertEqual(pd.returncode, 0, pd.stdout + pd.stderr)
            d = json.loads(pd.stdout)
            self.assertTrue(d["ready"])
            self.assertTrue(d["packet_valid"])
            self.assertTrue(Path(d["manifest"]).is_file())

            # Attempting to close a strict manifest via finish --mode light MUST fail (MODE-MISMATCH)
            p_bypass = run_py(WORKFLOW, "finish", "--mode", "light", "--run", d["manifest"])
            self.assertEqual(p_bypass.returncode, 1)
            bypass_res = json.loads(p_bypass.stdout)
            self.assertFalse(bypass_res["ok"])
            self.assertEqual(bypass_res["errors"][0]["code"], "MODE-MISMATCH")

            # Strict interrupted recovery path preserves --interrupted semantics
            pf = run_py(
                WORKFLOW, "finish", "--mode", "strict",
                "--run", d["manifest"],
                "--interrupted", "host timeout",
                "--feature-root", str(froot),
            )
            self.assertEqual(pf.returncode, 1, pf.stdout + pf.stderr)
            fin = json.loads(pf.stdout)
            self.assertFalse(fin["ok"])
            self.assertTrue(any("host timeout" in str(e) for e in fin["record"]["errors"]), fin["record"]["errors"])


if __name__ == "__main__":
    unittest.main()

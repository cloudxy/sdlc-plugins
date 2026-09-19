#!/usr/bin/env python3
"""Behavioral tests for shared contracts and task boundaries; no model/network calls."""
import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

from workflow import (ROOT, load_registry, resolve_task, validate_registry,
                      check_task, check_groups, render_commands, generated_files)
from check_packet import lint


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.registry = load_registry()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.code_temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.code_temp.cleanup)
        self.project = Path(self.code_temp.name)

    def put(self, path, text="test artifact\n"):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def packet(self, role="designer", stage="designer", task="explore", skill="design-contract", outputs=None,
               check=None, evidence=None):
        if outputs is None:
            outputs = ["02-shape/design-brief.md", "02-shape/design-directions.md", "02-shape/prototypes/"]
        if check is None:
            check = f"python3 {ROOT}/scripts/workflow.py check-task --role {role} --stage {stage} --task {task} --root {self.root}"
        if evidence is None:
            evidence = ["web", "screenshots"] if (role, task) == ("designer", "explore") else []
        reads = [f"{ROOT}/{rd}" for t in self.registry["tasks"]
                 if (t["role"], t["stage"]) == (role, stage) and (t["task"] == task or t.get("task_pattern"))
                 for rd in t.get("reads", [])]
        extra_inputs = "inputs:\n" + "".join(f"  - {{path: {r}, required: true}}\n" for r in reads) if reads else ""
        source_scope = ""
        try:
            if resolve_task(self.registry, role, stage, task).get("writes_source"):
                project = self.project
                project.mkdir(exist_ok=True)
                source_scope = f"project_root: {project}\nsource_writes:\n  - src/\n"
        except ValueError:
            pass
        return (f"## SPAWN PACKET v2\nhat: {role}\nstage: {stage}\ntask: {task}\n" + extra_inputs + ""
                f"subagent_type: sdlc-workflow:{role}\nPLUGIN_ROOT: {ROOT}\n" + source_scope +
                f"feature_dir: {self.root}\nlane: L2\nprimary_skill: sdlc-workflow:{skill}\n"
                "deliverable_paths:\n" + "".join(f"  - {p}\n" for p in outputs)
                + f"success_checks:\n  - {check}\nreturn: output paths + summary\n"
                + ("evidence_required:\n" + "".join(f"  - {e}\n" for e in evidence) if evidence else "")
                + "forbidden:\n  - Do not spawn further subagents (host depth 1).\n")

    def errors(self, **kw):
        return {e["code"] for e in lint(self.packet(**kw))["errors"]}

    def test_registry_references_resolve(self):
        self.assertEqual(validate_registry(self.registry), [])

    def test_broken_contract_fails_validation(self):
        self.registry["tasks"][0]["required"] = ["missing-artifact"]
        self.assertTrue(validate_registry(self.registry))

    def test_duplicate_task_rejected(self):
        self.registry["tasks"].append(copy.deepcopy(self.registry["tasks"][0]))
        self.assertTrue(validate_registry(self.registry))
        with self.assertRaises(ValueError):
            resolve_task(self.registry, "researcher", "market", "survey")

    def test_same_role_routes_to_different_procedures(self):
        self.assertEqual(resolve_task(self.registry, "ops", "signals", "listen")["skill"], "signals")
        self.assertEqual(resolve_task(self.registry, "ops", "enablement", "teach-open-announce")["skill"], "enablement")

    def test_task_alias_preserves_existing_packets(self):
        self.assertEqual(resolve_task(self.registry, "qa", "verify", "risk-based tests")["task"], "risk-based-tests")

    def test_wrong_role_stage_rejected_before_spawn(self):
        self.assertIn("TASK", self.errors(role="backend"))

    def test_wrong_primary_skill_rejected(self):
        self.assertIn("TASKSKILL", self.errors(skill="architecture"))

    def test_packet_must_declare_task_outputs(self):
        self.assertIn("DELIVERABLE", self.errors(outputs=["02-shape/flows.md"]))

    def test_explore_packet_is_valid_without_specify_outputs(self):
        self.assertEqual(self.errors(), set())

    def test_explore_rejects_premature_stage_gate(self):
        self.assertIn("EARLYGATE", self.errors(check="bash check-sdlc.sh --hat designer ."))

    def test_packet_rejects_different_stage_gate(self):
        self.assertIn("GATESTAGE", self.errors(check="bash check-sdlc.sh --hat shape ."))

    def test_architecture_partial_tasks_are_independent_of_stage_outputs(self):
        for stage, task, directory in [("define", "feasibility", "01-define"),
                                        ("shape", "change-impact", "02-shape"),
                                        ("verify", "conformance", "04-verify")]:
            with self.subTest(task=task):
                output = f"{directory}/architecture-{task}.md"
                pk = self.packet(role="architect", stage=stage, task=task,
                                 skill="architecture", outputs=[output])
                self.assertEqual({e["code"] for e in lint(pk)["errors"]}, set())
                self.assertTrue(check_task(self.registry, self.root, "architect", stage, task))
                self.put(output, f"Completed {task} report; dependent decisions may remain open.\n")
                self.assertEqual(check_task(self.registry, self.root, "architect", stage, task), [])
                # A partial task's report cannot satisfy spec/contract/QA stage obligations.
                self.assertTrue(check_groups(self.registry, self.root,
                                            self.registry["stages"][stage]["required"]))
                early = pk.replace("success_checks:\n", f"success_checks:\n  - bash check-sdlc.sh --hat {stage} {self.root}\n")
                self.assertIn("EARLYGATE", {e["code"] for e in lint(early)["errors"]})

    def test_architecture_outputs_cannot_substitute_for_other_tasks(self):
        for path in ["01-define/spec.md", "02-shape/contract.md", "04-verify/coverage.md"]:
            self.put(path)
        for stage, task in [("define", "feasibility"), ("shape", "change-impact"), ("verify", "conformance")]:
            with self.subTest(task=task):
                self.assertTrue(check_task(self.registry, self.root, "architect", stage, task))
                self.assertIn("DELIVERABLE", self.errors(role="architect", stage=stage, task=task,
                              skill="architecture", outputs=["02-shape/contract.md"]))

    def test_feasibility_can_declare_isolated_spike_without_final_security_diagram(self):
        self.put("state.yaml", "feature: f\nq_security: yes\n")
        self.assertEqual(self.errors(role="architect", stage="define", task="feasibility",
                         skill="architecture", outputs=["01-define/architecture-feasibility.md",
                         "01-define/spikes/lease/probe.py", "01-define/spikes/lease/results.txt"]), set())
        self.assertIn("DELIVERABLE-SCOPE", self.errors(role="architect", stage="define", task="feasibility",
                      skill="architecture", outputs=["01-define/architecture-feasibility.md", "/etc/probe.py"]))

    def test_partial_stage_flag_is_typed(self):
        self.registry["tasks"][0]["partial_stage"] = "false"
        self.assertTrue(any("partial_stage" in e for e in validate_registry(self.registry)))

    def test_explore_passes_without_pick_or_flows(self):
        for path in ["02-shape/design-brief.md", "02-shape/design-directions.md", "02-shape/prototypes/D1.html"]:
            self.put(path)
        self.assertEqual(check_task(self.registry, self.root, "designer", "designer", "explore"), [])
        self.assertTrue(check_task(self.registry, self.root, "designer", "designer", "specify"))

    def test_empty_prototype_directory_is_not_a_deliverable(self):
        self.put("02-shape/design-brief.md"); self.put("02-shape/design-directions.md")
        (self.root / "02-shape/prototypes").mkdir()
        self.assertTrue(check_task(self.registry, self.root, "designer", "designer", "explore"))

    def test_another_ticket_cannot_satisfy_task(self):
        self.put("03-impl/T-10-evidence.md")
        self.assertTrue(check_task(self.registry, self.root, "backend", "implement", "T-1"))
        self.put("03-impl/T-1-backend-evidence.md")
        self.assertEqual(check_task(self.registry, self.root, "backend", "implement", "T-1"), [])

    def test_implementation_packet_checks_lane_file(self):
        self.assertIn("TASKLANE", self.errors(role="backend", stage="implement", task="T-1", skill="impl-evidence", outputs=["03-impl/T-1-evidence.md"]))

    def test_implementation_requires_one_integrator(self):
        packet = self.packet(role="backend", stage="implement", task="T-1", skill="impl-evidence", outputs=["03-impl/T-1-backend-evidence.md"])
        packet += "lane_file: api\n"
        self.assertIn("INTEGRATOR", {e["code"] for e in lint(packet)["errors"]})
        self.assertEqual(lint(packet + "slice_integrator: backend\n")["errors"], [])

    # ---- second-diagnosis counterexamples N01-N06 (2026-09-18)
    def test_product_outputs_resolve_under_product_root(self):  # N01
        prod = self.root / "docs/product"
        (prod).mkdir(parents=True)
        (prod / "strategy.md").write_text("# s\n"); (prod / "feature-map.md").write_text("# f\n")
        feat = self.root / ".sdlc/_product"; feat.mkdir(parents=True)
        self.assertEqual(check_task(self.registry, feat, "pm", "product", "bootstrap", product_root=prod), [])
        self.assertEqual({r[1] for r in check_task(self.registry, feat, "pm", "product", "bootstrap")}, {"USAGE"})

    def test_other_lane_evidence_cannot_satisfy_task(self):  # N02
        self.put("03-impl/T-1-frontend-evidence.md")
        self.assertTrue(check_task(self.registry, self.root, "backend", "implement", "T-1"))
        self.assertEqual(check_task(self.registry, self.root, "frontend", "implement", "T-1"), [])

    def test_blank_hidden_or_template_files_are_not_deliverables(self):  # N03 + C03
        self.put("02-shape/design-brief.md", "")
        self.put("02-shape/design-directions.md", "<!-- sdlc:unfilled -->\n# D1\n")
        self.put("02-shape/prototypes/.gitkeep", "")
        missing = {r[2].split()[1] for r in check_task(self.registry, self.root, "designer", "designer", "explore")}
        self.assertEqual(missing, {"02-shape/design-brief.md", "02-shape/design-directions.md", "02-shape/prototypes/*"})

    def test_deliverable_outside_feature_dir_is_rejected(self):  # N04
        codes = self.errors(outputs=["02-shape/design-brief.md", "02-shape/design-directions.md", "02-shape/prototypes/", "/etc/hosts"])
        self.assertIn("DELIVERABLE-SCOPE", codes)

    def test_success_check_must_be_this_tasks_check(self):  # N05
        self.assertIn("MISSING-CHECK", self.errors(check="echo ok"))
        wrong = f"python3 {ROOT}/scripts/workflow.py check-task --role pm --stage define --task spec --root /tmp"
        self.assertIn("CHECKMISMATCH", self.errors(check=wrong))

    def test_evidence_cannot_be_dropped_by_rewording(self):  # N06
        self.assertIn("EVIDENCE", self.errors(evidence=["web"]))
        self.assertEqual(self.errors(evidence=["web", "screenshots", "running_app"]), set())

    def test_explore_does_not_borrow_throwaway_prototype(self):  # V08 / D3
        packet = self.packet() + "companion_skills: [sdlc-workflow:prototype]\n"
        self.assertIn("COMPANION", {e["code"] for e in lint(packet)["errors"]})

    def test_direction_prototypes_live_in_subfolders(self):
        self.put("02-shape/design-brief.md"); self.put("02-shape/design-directions.md")
        self.put("02-shape/prototypes/D1/index.html", "<h1>D1</h1>\n")
        self.assertEqual(check_task(self.registry, self.root, "designer", "designer", "explore"), [])

    def test_specify_requires_final_prototype(self):
        for path in ["02-shape/design-directions.md", "02-shape/flows.md", "02-shape/edge-states.md"]:
            self.put(path)
        self.assertEqual([r[1] for r in check_task(self.registry, self.root, "designer", "designer", "specify")], ["HATMISS"])
        self.put("02-shape/prototypes/final/index.html", "<h1>final</h1>\n")
        self.assertEqual(check_task(self.registry, self.root, "designer", "designer", "specify"), [])

    # ---- package C: diagrams
    def dba_packet(self, extra=""):
        return (self.packet(role="dba", stage="dba", task="model", skill="schema",
                            outputs=["02-shape/db-spec.md", "02-shape/schema.dbml"]) + extra)

    def test_visuals_require_svg_guide_and_diagram_check(self):
        codes = {e["code"] for e in lint(self.dba_packet("visuals: [er]\n"))["errors"]}
        self.assertIn("DIAGRAM", codes)
        good = self.dba_packet("visuals: [er]\n").replace(
            "deliverable_paths:\n", "deliverable_paths:\n  - 02-shape/assets/f-er.svg\n").replace(
            "success_checks:\n", f"success_checks:\n  - python3 {ROOT}/scripts/diagram/lint.py --root {self.root} {self.root}/02-shape/assets/f-er.svg\n")
        good += (f"inputs:\n  - {{path: {ROOT}/vendor/svg-diagram/SKILL.md, required: true}}\n"
                 f"  - {{path: {ROOT}/skills/schema/references/er-diagram.md, required: true}}\n")
        self.assertEqual({e["code"] for e in lint(good)["errors"]}, set())

    def test_visual_not_in_contract_is_rejected(self):
        self.assertIn("VISUALS", {e["code"] for e in lint(self.dba_packet("visuals: [lineage]\n"))["errors"]})

    def test_security_feature_requires_trust_boundary(self):
        self.put("state.yaml", "feature: f\nq_security: yes\n")
        pk = self.packet(role="architect", stage="shape", task="contract", skill="architecture", outputs=["02-shape/contract.md"])
        self.assertIn("VISUALS", {e["code"] for e in lint(pk)["errors"]})

    # ---- frontend handoff: required reading is enforced, not suggested
    def test_frontend_packet_must_list_frontend_design(self):
        pk = self.packet(role="frontend", stage="implement", task="T-1", skill="impl-evidence",
                         outputs=["03-impl/T-1-frontend-evidence.md"], evidence=["running_app", "screenshots"])
        pk += "lane_file: ui\nslice_integrator: frontend\n"
        self.assertEqual({e["code"] for e in lint(pk)["errors"]}, set())
        stripped = "\n".join(l for l in pk.splitlines() if "frontend-design" not in l) + "\n"
        self.assertIn("READS", {e["code"] for e in lint(stripped)["errors"]})

    def test_reads_resolve_through_vendor_locks(self):
        self.assertEqual(validate_registry(self.registry), [])
        broken = copy.deepcopy(self.registry)
        next(t for t in broken["tasks"] if t["role"] == "frontend")["reads"] = ["vendor/anthropic-skills/nope.md"]
        self.assertTrue(any("reads" in e for e in validate_registry(broken)))

    def test_symlink_outside_root_cannot_satisfy_task(self):
        self.put("02-shape/design-brief.md"); self.put("02-shape/design-directions.md")
        directory = self.root / "02-shape/prototypes"; directory.mkdir()
        (directory / "external.html").symlink_to(ROOT / "README.md")
        self.assertTrue(check_task(self.registry, self.root, "designer", "designer", "explore"))

    def test_stage_skip_does_not_remove_other_roles_outputs(self):
        groups = self.registry["stages"]["accept"]["required"]
        self.put("04-verify/accept-pm.md")
        result = check_groups(self.registry, self.root, groups, skipped=["growth"], ui=True)
        self.assertEqual(len(result), 1)
        self.assertIn("accept-design.md", result[0][2])

    def test_legacy_paths_only_accepted_by_compatibility_gate(self):
        self.put("01-define/prd.md")
        result = check_groups(self.registry, self.root, self.registry["stages"]["define"]["required"])
        self.assertEqual(result[0][:2], ("warning", "DEPRECATED"))
        self.assertTrue(check_task(self.registry, self.root, "pm", "define", "spec"))

    def test_registry_path_change_reaches_both_consumers(self):
        self.registry["artifacts"]["market"]["paths"] = ["survey/market.md"]
        self.put("00-discover/market.md")
        self.assertTrue(check_task(self.registry, self.root, "researcher", "market", "survey"))
        self.assertTrue(check_groups(self.registry, self.root, self.registry["stages"]["market"]["required"]))
        self.put("survey/market.md")
        self.assertEqual(check_task(self.registry, self.root, "researcher", "market", "survey"), [])
        self.assertEqual(check_groups(self.registry, self.root, self.registry["stages"]["market"]["required"]), [])

    def test_command_routes_and_generated_artifacts_are_current(self):
        self.assertEqual(len(list(render_commands(self.registry))), 6)
        for path, expected in generated_files(self.registry):
            self.assertEqual((ROOT / path).read_text(), expected, path)
        self.assertEqual(self.registry["commands"]["sdlc-review"]["mode"], "review-only")
        self.assertEqual(self.registry["commands"]["sdlc-product"]["mode"], "product")

    def test_renderer_uses_registry_and_preserves_profiles(self):
        spec = importlib.util.spec_from_file_location("render_roles", ROOT / "scripts/render-role-agents.py")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        role = next(r for r in module.ROLES if r["name"] == "ops")
        text = module.assemble(role, {})
        self.assertIn("sdlc-workflow:enablement", text)
        self.assertIn("sdlc-workflow:signals", text)
        self.assertNotIn("Excellent looks like", text)
        self.assertFalse(hasattr(module, "seed_profile"))


    def implementation_packet(self):
        return self.packet(role="backend", stage="implement", task="T-1", skill="impl-evidence",
                           outputs=["03-impl/T-1-backend-evidence.md"]) + "lane_file: api\nslice_integrator: backend\n"

    def test_source_write_scope_is_required_and_bounded(self):
        pk = self.implementation_packet()
        self.assertEqual(lint(pk)["errors"], [])
        for value in ("../outside", "/tmp/file", ".", ".git/config", ".sdlc/state.yaml", "src/*"):
            with self.subTest(value=value):
                self.assertIn("SOURCE-SCOPE", {e["code"] for e in lint(pk.replace("  - src/", "  - " + value))["errors"]})
        self.assertIn("SOURCE-SCOPE", {e["code"] for e in lint(pk.replace("source_writes:\n  - src/", "source_writes: []"))["errors"]})

    def test_source_scope_rejects_symlink_and_product_bypass(self):
        (self.project / "escape").symlink_to(self.root, target_is_directory=True)
        pk = self.implementation_packet()
        for value in ("escape/test.py", "docs/", "docs/product/strategy.md"):
            candidate = pk.replace("  - src/", "  - " + value) + f"product_root: {self.project}/docs/product\n"
            self.assertIn("SOURCE-SCOPE", {e["code"] for e in lint(candidate)["errors"]})

    def test_nonwriter_cannot_acquire_source_scope(self):
        pk = self.packet() + f"project_root: {self.project}\nsource_writes: [src/]\n"
        self.assertIn("SOURCE-SCOPE", {e["code"] for e in lint(pk)["errors"]})

    def test_internal_research_does_not_require_web(self):
        pk = self.packet(role="researcher", stage="market", task="survey", skill="market", outputs=["00-discover/market.md"])
        pk += "scope: no web search; dated internal artifact answers this question\n"
        self.assertEqual(lint(pk)["errors"], [])
        # When web is explicitly required, contradicting it still fails.
        self.assertIn("WAIVER", {e["code"] for e in lint(pk + "evidence_required: [web]\n")["errors"]})

    def test_non_ui_acceptance_does_not_require_screenshot(self):
        pk = self.packet(role="pm", stage="accept", task="walkthrough", skill="prd-gwt",
                         outputs=["04-verify/accept-pm.md"], evidence=["running_app"])
        self.assertEqual(lint(pk + "ui: no\n")["errors"], [])
        self.assertIn("EVIDENCE", {e["code"] for e in lint(pk + "ui: yes\n")["errors"]})

    def test_added_partial_tasks_can_be_dispatched_independently(self):
        added = [("qa", "define", "test-plan"), ("analyst", "define", "measurement-plan"),
                 ("sre", "deliver", "prepare"), ("sre", "deliver", "ci"),
                 ("designer", "market", "prototype"), ("data-collector", "collect", "implement"),
                 ("data-collector", "collect", "validate"), ("data-warehouse-engineer", "warehouse", "design"),
                 ("data-warehouse-engineer", "warehouse", "implement"), ("data-warehouse-engineer", "warehouse", "validate")]
        for role, stage, name in added:
            with self.subTest(task=(role, stage, name)):
                contract = resolve_task(self.registry, role, stage, name)
                output = self.registry["artifacts"][contract["required"][0]]["paths"][0]
                pk = self.packet(role=role, stage=stage, task=name, skill=contract["skill"], outputs=[output])
                self.assertEqual(lint(pk)["errors"], [])
                self.assertIn("EARLYGATE", {e["code"] for e in lint(pk.replace("return: output paths + summary", f"  - bash check-sdlc.sh --hat {stage} .\nreturn: output paths + summary"))["errors"]})

    def test_tags_only_warehouse_contract(self):
        self.put("02-shape/warehouse/tags.yaml", "tags: [active]\n")
        self.assertEqual(check_task(self.registry, self.root, "data-warehouse-engineer", "warehouse", "tags"), [])
        self.assertEqual(check_groups(self.registry, self.root, self.registry["stages"]["warehouse"]["required"]), [])

    def test_source_writer_registry_flag_is_typed(self):
        self.registry["tasks"][0]["writes_source"] = "true"
        self.assertTrue(any("writes_source" in e for e in validate_registry(self.registry)))


    def test_qa_test_sources_are_optional_and_planning_stays_read_only(self):
        pk = self.packet(role="qa", stage="verify", task="risk-based-tests", skill="coverage-matrix",
                         outputs=["04-verify/coverage.md"])
        self.assertEqual(lint(pk)["errors"], [])
        self.assertEqual(lint(pk.replace("source_writes:\n  - src/", "source_writes: []"))["errors"], [])
        self.assertIn("SOURCE-SCOPE", {e["code"] for e in lint(pk.replace("  - src/", "  - ../outside"))["errors"]})
        plan = self.packet(role="qa", stage="define", task="test-plan", skill="coverage-matrix",
                           outputs=["01-define/test-plan.md"])
        plan += f"project_root: {self.project}\nsource_writes: [tests/]\n"
        self.assertIn("SOURCE-SCOPE", {e["code"] for e in lint(plan)["errors"]})

    def test_generated_agents_preserve_reader_writer_capability_boundary(self):
        spec = importlib.util.spec_from_file_location("render_agents", ROOT / "scripts/render-role-agents.py")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        for role in module.ROLES:
            with self.subTest(role=role["name"]):
                text = module.assemble(role, {})
                self.assertNotIn("{{", text)
                if role["fresh"] == "1":
                    self.assertIn("You cannot execute commands", text)
                    self.assertIn("no file writes", text)
                    self.assertNotIn("Run applicable checks with the tools available", text)
                else:
                    self.assertIn("actual scoped source changes", text)
                    self.assertIn("Do not create an implicit memory path", text)
        # A registry permission change reaches the agent without a second handwritten rule.
        task = next(t for t in module.REGISTRY["tasks"] if (t["role"], t["task"]) == ("sre", "ci"))
        task["requires_source"] = False
        sre = next(r for r in module.ROLES if r["name"] == "sre")
        row = next(line for line in module.assemble(sre, {}).splitlines() if "`ci`" in line)
        self.assertIn("optional scoped source_writes", row)


if __name__ == "__main__":
    unittest.main(verbosity=2)

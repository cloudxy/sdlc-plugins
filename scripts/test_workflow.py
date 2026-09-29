#!/usr/bin/env python3
"""Behavioral tests for shared contracts and task boundaries; no model/network calls."""
import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

from workflow import (ROOT, load_registry, resolve_task, validate_registry,
                      check_task, check_groups, render_commands, generated_files)
from check_packet import lint as lint_packet


def lint(text):
    # These 75 historical tests exercise the shared v2 authority adapter.
    # Public pilot downgrade rejection and v3 dispatch are tested in test_task_runtime.py.
    return lint_packet(text, enforce_protocol=False)


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

    # ---- generated imagery: a packet that asks for an image carries the practice, the落点 and the gate
    def designer_packet(self, extra=""):
        return (self.packet(role="designer", stage="designer", task="explore") + extra)

    def test_imagery_requires_practice_landing_dir_and_check(self):
        codes = {e["code"] for e in lint(self.designer_packet("imagery: [ref]\n"))["errors"]}
        self.assertIn("IMAGERY", codes)
        good = self.designer_packet("imagery: [ref]\n").replace(
            "deliverable_paths:\n", "deliverable_paths:\n  - 02-shape/assets/refs/probe-warm.png\n").replace(
            "success_checks:\n", f"success_checks:\n  - python3 {ROOT}/scripts/image/check.py --root {self.root}\n")
        good = good.replace(          # designer explore already has an inputs block (frontend-design is required reading)
            "inputs:\n", f"inputs:\n  - {{path: {ROOT}/skills/imagery/SKILL.md, required: true}}\n"
                          f"  - {{path: {ROOT}/skills/design-contract/references/generated-imagery.md, required: true}}\n", 1)
        self.assertEqual({e["code"] for e in lint(good)["errors"]}, set())

    def test_imagery_kind_not_in_contract_is_rejected(self):
        self.assertIn("IMAGERY", {e["code"] for e in lint(self.designer_packet("imagery: [hero]\n"))["errors"]})
        self.assertIn("IMAGERY", {e["code"] for e in lint(self.dba_packet("imagery: [ref]\n"))["errors"]})

    def test_imagery_is_never_required(self):
        self.assertEqual({e["code"] for e in lint(self.designer_packet())["errors"]}, set())
        self.assertNotIn("imagery", self.registry["imagery"]["enforced_when"])
        self.assertEqual(self.registry["imagery"]["enforced_when"], [])

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
        self.assertEqual({Path(path).stem for path, _ in render_commands(self.registry)}, set(self.registry['commands']))
        for path, expected in generated_files(self.registry):
            self.assertEqual((ROOT / path).read_text(), expected, path)
        self.assertEqual(self.registry["commands"]["sdlc-review"]["mode"], "review-only")
        self.assertEqual(self.registry["commands"]["sdlc-product"]["mode"], "product")
        self.assertEqual(self.registry["commands"]["sdlc-grok"]["skill"], "imagery")
        for mode in ('refine', 'fix'):
            self.assertEqual(self.registry['commands']['sdlc-' + mode]['mode'], mode)
            self.assertEqual(self.registry['commands']['sdlc-' + mode]['skill'], 'sdlc')

    def test_eval_entry_lists_exactly_the_routed_skills(self):
        import re
        hint = self.registry["commands"]["sdlc-eval"]["argument_hint"]
        hinted = set(re.search(r"\[skill: ([^\]]+)\]", hint).group(1).split("|"))
        text = (ROOT / "skills/sdlc-eval/SKILL.md").read_text()
        table = text[text.index("## Harness routing"):text.index("## Gotchas")]
        routed = set(re.findall(r"^\| `([a-z0-9-]+)` \|", table, re.M))
        with_evals = {p.parent.parent.name for p in (ROOT / "skills").glob("*/evals/evals.json")}
        self.assertEqual(hinted, routed)
        self.assertEqual(routed, with_evals)
        self.assertNotRegex(self.registry["commands"]["sdlc-eval"]["description"], r"\d+ skills")

    def test_renderer_uses_registry_and_preserves_profiles(self):
        spec = importlib.util.spec_from_file_location("render_roles", ROOT / "scripts/render-role-agents.py")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        role = next(r for r in module.ROLES if r["name"] == "ops")
        text = module.assemble(role, {})
        self.assertIn("sdlc-workflow:enablement", text)
        self.assertIn("sdlc-workflow:signals", text)
        self.assertNotIn("Excellent looks like", text)
        self.assertFalse(hasattr(module, "seed_profile"))


    # ---- C06/C09: every output field is judged by what it really writes, not by the field that names it
    def product_packet(self, role="designer", task="bootstrap", skill="design-contract", outputs=None, writes=None,
                       evidence=("running_app", "screenshots"), extra=""):
        prod = self.root / "docs/product"
        prod.mkdir(parents=True, exist_ok=True)
        for name in ("strategy.md", "design-system.md"):
            (prod / name).write_text(f"# {name}\n")
        outputs = [f"{prod}/design-system.md"] if outputs is None else outputs
        writes = [f"{prod}/design-system.md"] if writes is None else writes
        check = f"python3 {ROOT}/scripts/workflow.py check-task --role {role} --stage product --task {task} --root {prod}"
        if resolve_task(self.registry, role, "product", task).get("product_outputs"):
            check += f" --product-root {prod}"
        return (f"## SPAWN PACKET v2\nhat: {role}\nstage: product\ntask: {task}\n"
                f"subagent_type: sdlc-workflow:{role}\nPLUGIN_ROOT: {ROOT}\nproduct_root: {prod}\n"
                f"primary_skill: sdlc-workflow:{skill}\n"
                + ("product_writes:\n" + "".join(f"  - {w}\n" for w in writes) if writes else "")
                + "deliverable_paths:\n" + "".join(f"  - {o}\n" for o in outputs)
                + f"success_checks:\n  - {check}\nreturn: output paths + summary\n"
                + ("evidence_required:\n" + "".join(f"  - {e}\n" for e in evidence) if evidence else "")
                + "forbidden:\n  - Do not spawn further subagents (host depth 1).\n" + extra)

    def codes(self, packet):
        return {e["code"] for e in lint(packet)["errors"]}

    def test_product_screenshots_need_a_declared_evidence_path(self):  # C06
        prod = self.root / "docs/product"
        self.assertEqual(self.codes(self.product_packet()), set())
        work = f"{self.root}/.sdlc/_product/screens/main.png"
        self.assertIn("DELIVERABLE-SCOPE", self.codes(self.product_packet(outputs=[f"{prod}/design-system.md", work])))
        shot = f"{prod}/assets/screens/main.png"
        self.assertEqual(self.codes(self.product_packet(outputs=[f"{prod}/design-system.md", shot])), set())
        stray = f"{prod}/notes.md"  # inside product_root, but neither owned product file nor declared evidence
        self.assertIn("DELIVERABLE-SCOPE", self.codes(self.product_packet(outputs=[f"{prod}/design-system.md", stray])))

    def test_product_file_ownership_is_checked_in_every_output_field(self):  # C09
        prod = self.root / "docs/product"
        own = f"{prod}/design-system.md"
        self.product_packet()  # creates the product files
        (prod / "assets").mkdir()
        (prod / "assets/alias.md").symlink_to(prod / "strategy.md")
        outside = self.project / "elsewhere"; outside.mkdir()
        (prod / "assets/out").symlink_to(outside, target_is_directory=True)
        for variant in (f"{prod}/strategy.md", "strategy.md", f"{prod}/assets/../strategy.md", f"{prod}/assets/alias.md"):
            with self.subTest(deliverable=variant):
                self.assertIn("UNOWNED", self.codes(self.product_packet(outputs=[own, variant])))
        self.assertIn("UNOWNED", self.codes(self.product_packet(writes=[own, f"{prod}/strategy.md"])))
        self.assertIn("DELIVERABLE", self.codes(self.product_packet(outputs=[own, "assets/../strategy.md"])))
        self.assertIn("DELIVERABLE-SCOPE", self.codes(self.product_packet(outputs=[own, f"{prod}/assets/out/x.md"])))
        # An owned file still needs a product_writes entry: deliverable_paths alone is not a grant.
        self.assertIn("UNOWNED", self.codes(self.product_packet(writes=[])))
        # The same rule holds from a feature stage.
        feature = self.packet() + f"product_root: {prod}\n"
        feature = feature.replace("deliverable_paths:\n", f"deliverable_paths:\n  - {prod}/strategy.md\n")
        self.assertIn("UNOWNED", self.codes(feature))

    def test_manager_report_path_is_legal_only_for_the_judge(self):  # C06
        prod = self.root / "docs/product"
        report = f"{self.root}/.sdlc/_product/findings.md"
        review = self.product_packet(role="reviewer", task="G-fresh", skill="findings", outputs=[report],
                                     writes=[], evidence=())
        self.assertEqual(self.codes(review + f"project_root: {self.root}\n"), set())
        self.assertIn("DELIVERABLE-SCOPE", self.codes(review))  # cannot resolve the report without project_root
        self.assertIn("DELIVERABLE-SCOPE", self.codes(self.product_packet(outputs=[f"{prod}/design-system.md", report])
                                                      + f"project_root: {self.root}\n"))
        self.assertIn("UNOWNED", self.codes(self.product_packet(role="reviewer", task="G-fresh", skill="findings",
                                                                outputs=[report, f"{prod}/strategy.md"], writes=[],
                                                                evidence=()) + f"project_root: {self.root}\n"))

    def test_memory_file_stays_in_the_roles_memory_folder(self):  # C09
        prod = self.root / "docs/product"
        self.product_packet()
        base = self.packet() + f"product_root: {prod}\n"
        self.assertEqual(self.codes(base + f"memory_file: {self.root}/memory/designer.md\n"), set())
        self.assertIn("MEMORY", self.codes(base + f"memory_file: {prod}/strategy.md\n"))
        self.assertIn("MEMORY", self.codes(base + f"memory_file: {self.root}/memory/pm.md\n"))
        self.assertIn("MEMORY", self.codes(base + f"memory_file: {self.project}/memory/designer.md\n"))

    def test_evidence_paths_are_validated(self):
        broken = copy.deepcopy(self.registry)
        task = next(t for t in broken["tasks"] if (t["role"], t["stage"]) == ("designer", "product"))
        for bad in ("../screens/*", "/abs/*", "strategy.md"):
            with self.subTest(pattern=bad):
                task["evidence_paths"] = [bad]
                self.assertTrue(any("evidence path" in e for e in validate_registry(broken)))

    # ---- batch B: lifecycle/scope metadata, skill kinds, role functions, decision records
    def test_model_metadata_is_complete(self):
        self.assertEqual(set(self.registry["functions"]), {"product-mgmt", "operations", "design", "engineering", "quality"})
        for role, item in self.registry["roles"].items():
            self.assertIn(item["function"], self.registry["functions"], role)
        for t in self.registry["tasks"]:
            self.assertEqual(t["scopes"], {"product": ["product"], "cycle": ["cycle"]}.get(t["stage"], ["feature"]), t)
            self.assertTrue(set(t["lifecycle_phases"]) <= set(self.registry["lifecycle"]), t)
        on_disk = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
        self.assertEqual(set(self.registry["skills"]), on_disk)
        self.assertEqual(self.registry["skills"]["falsify"]["kind"], "compat")

    def test_model_metadata_errors_are_reported(self):
        cases = [
            (lambda r: r["roles"]["pm"].__setitem__("function", "marketing"), "function"),
            (lambda r: r["tasks"][0].__setitem__("scopes", ["everywhere"]), "scopes"),
            (lambda r: r["tasks"][0].__setitem__("scopes", ["product"]), "go together"),
            (lambda r: r["tasks"][0].__setitem__("lifecycle_phases", ["operate"]), "lifecycle"),
            (lambda r: r["skills"].pop("tdd"), "missing from registry.skills"),
            (lambda r: r["tasks"][0].__setitem__("skill", "discover"), "not a task method"),
            (lambda r: r["skills"]["falsify"].__setitem__("replaced_by", "nope"), "live replacement"),
            (lambda r: r["skills"]["prd-gwt"].__setitem__("kind", "practice"), "must be kind role"),
        ]
        for mutate, needle in cases:
            with self.subTest(needle=needle):
                broken = copy.deepcopy(self.registry)
                mutate(broken)
                self.assertTrue(any(needle in e for e in validate_registry(broken)), validate_registry(broken))

    def test_compat_entry_gets_a_migration_hint(self):  # batch C: falsify is deprecated, not silently remapped
        self.assertEqual(self.registry["skills"]["falsify"]["sunset"], "2026-12-31")
        messages = [e["message"] for e in lint(self.packet() + "companion_skills: [sdlc-workflow:falsify]\n")["errors"]]
        self.assertTrue(any("migrate to sdlc-workflow:discover" in m for m in messages), messages)
        messages = [e["message"] for e in lint(self.packet(skill="falsify"))["errors"]]
        self.assertTrue(any("migrate to sdlc-workflow:discover" in m for m in messages), messages)
        broken = copy.deepcopy(self.registry)
        broken["skills"]["falsify"]["sunset"] = "soon"
        self.assertTrue(any("sunset" in e for e in validate_registry(broken)))
        # The method's template now lives with its owner, so retiring the entry cannot break discover.
        self.assertTrue((ROOT / "skills/discover/templates/assumptions.md").is_file())
        self.assertNotIn("falsify/templates", (ROOT / "skills/discover/references/assumption-testing.md").read_text())

    def test_run_scope_is_optional_and_bounded(self):
        self.assertEqual(self.errors(), set())
        self.assertEqual(self.codes(self.packet() + "run_scope: feature\n"), set())
        self.assertIn("SCOPE", self.codes(self.packet() + "run_scope: product\n"))
        # Free-text `scope:` notes in old packets are not the run scope and stay legal.
        self.assertEqual(self.codes(self.packet() + "scope: smaller deliverable, same evidence\n"), set())

    def test_function_map_is_a_generated_view(self):
        from workflow import render_function_map
        text = render_function_map(self.registry)
        for fn, meta in self.registry["functions"].items():
            self.assertIn(f"## {meta['name']} (`{fn}`)", text)
        self.assertIn("grants no product writes", text)
        self.assertIn("| ops | enablement / teach-open-announce |", text)

    def test_relayed_decision_record_stays_compatible(self):
        spec = importlib.util.spec_from_file_location("evidence_mod", ROOT / "scripts/evidence.py")
        evidence = importlib.util.module_from_spec(spec); spec.loader.exec_module(evidence)
        base = "feature: f\nopen_questions:\n  - id: Q-ACCEPT-PM\n    status: answered\n    by: user\n"
        self.put("state.yaml", base + "    quote: \"同意，下个迭代补\"\n    decided_by: 产品负责人\n    relayed_by: user\n    authority: owners.product-mgmt\n")
        self.assertTrue(evidence.check_conditional(self.root, "pm")[0])
        self.put("state.yaml", base + "    decided_by: 产品负责人\n    relayed_by: user\n")
        self.assertFalse(evidence.check_conditional(self.root, "pm")[0])  # names without the recorded words are not an answer

    # ---- batch D: product cycles run in their own root with their own write rules
    def cycle_packet(self, role="ops", task="signals-digest", skill="signals", outputs=None, extra="",
                     cycle=None, check_root=None, config="product_root: docs/product\nsignals_path: docs/signals\n"):
        cycle = cycle if cycle is not None else self.root / ".sdlc/_product/cycles/2026-09"
        Path(cycle).mkdir(parents=True, exist_ok=True)
        (self.root / "docs/product").mkdir(parents=True, exist_ok=True)
        (self.root / "docs/signals").mkdir(parents=True, exist_ok=True)
        (self.root / "docs/product/growth.md").write_text("# growth\n")
        (self.root / "sdlc.config.yaml").write_text(config)
        output = self.registry["artifacts"][resolve_task(self.registry, role, "cycle", task)["required"][0]]["paths"][0]
        outputs = [output] if outputs is None else outputs
        check = (f"python3 {ROOT}/scripts/workflow.py check-task --role {role} --stage cycle --task {task} "
                 f"--root {check_root or cycle}")
        return (f"## SPAWN PACKET v2\nhat: {role}\nstage: cycle\ntask: {task}\nrun_scope: cycle\n"
                f"subagent_type: sdlc-workflow:{role}\nPLUGIN_ROOT: {ROOT}\ncycle_dir: {cycle}\n"
                f"product_root: {self.root}/docs/product\nproject_root: {self.root}\nprimary_skill: sdlc-workflow:{skill}\n"
                "deliverable_paths:\n" + "".join(f"  - {o}\n" for o in outputs)
                + f"success_checks:\n  - {check}\nreturn: output paths + summary\n"
                + "forbidden:\n  - Do not spawn further subagents (host depth 1).\n" + extra)

    def test_cycle_packet_runs_in_its_own_root(self):
        self.assertEqual(self.codes(self.cycle_packet()), set())
        self.assertIn("MISSING", self.codes(self.cycle_packet().replace(f"cycle_dir: {self.root}/.sdlc/_product/cycles/2026-09\n", "")))
        elsewhere = self.root / "notes/2026-09"
        self.assertIn("CYCLE-DIR", self.codes(self.cycle_packet(cycle=elsewhere)))
        self.assertIn("SCOPE", self.codes(self.cycle_packet().replace("run_scope: cycle", "run_scope: feature")))
        self.assertIn("DELIVERABLE-SCOPE", self.codes(self.cycle_packet(outputs=["outputs/signals-digest.md", f"{self.root}/elsewhere.md"])))
        self.assertIn("CHECKMISMATCH", self.codes(self.cycle_packet(check_root=self.root / "docs/product")))
        contract = resolve_task(self.registry, "analyst", "cycle", "readout")
        from workflow import success_check
        self.assertIn("--root <cycle_dir>", success_check(contract))

    def test_cycle_product_writes_follow_ownership(self):
        growth = self.cycle_packet(role="growth", task="experiments", skill="growth",
                                   extra=f"product_writes:\n  - {self.root}/docs/product/growth.md\n")
        self.assertEqual(self.codes(growth), set())
        ops = self.cycle_packet(extra=f"product_writes:\n  - {self.root}/docs/product/growth.md\n")
        self.assertIn("UNOWNED", self.codes(ops))
        cycle = self.root / ".sdlc/_product/cycles/2026-09"
        self.assertEqual(self.codes(self.cycle_packet(extra=f"memory_file: {cycle}/memory/ops.md\n")), set())
        self.assertIn("MEMORY", self.codes(self.cycle_packet(extra=f"memory_file: {self.root}/docs/product/ops.md\n")))

    def test_signals_store_has_one_writer_inside_its_directory(self):
        self.assertEqual(self.codes(self.cycle_packet(extra="store_writes:\n  - signals.md\n")), set())
        for value in ("../product/strategy.md", "/tmp/x.md", "*.md"):
            with self.subTest(value=value):
                self.assertIn("STORE-SCOPE", self.codes(self.cycle_packet(extra=f"store_writes:\n  - {value}\n")))
        readout = self.cycle_packet(role="analyst", task="readout", skill="retro", extra="store_writes:\n  - signals.md\n")
        self.assertIn("STORE-SCOPE", self.codes(readout))
        unset = self.cycle_packet(extra="store_writes:\n  - signals.md\n", config="product_root: docs/product\n")
        self.assertIn("STORE-SCOPE", self.codes(unset))
        inside_product = self.cycle_packet(extra="store_writes:\n  - s.md\n",
                                           config="product_root: docs/product\nsignals_path: docs/product/signals\n")
        (self.root / "docs/product/signals").mkdir(parents=True, exist_ok=True)
        self.assertIn("STORE-SCOPE", self.codes(inside_product))

    def test_source_writes_cannot_reach_the_signals_store(self):
        (self.project / "sdlc.config.yaml").write_text("signals_path: docs/signals\n")
        (self.project / "docs/signals").mkdir(parents=True)
        pk = self.implementation_packet().replace("  - src/", "  - docs/signals/")
        self.assertIn("SOURCE-SCOPE", self.codes(pk))

    def test_runner_refuses_an_unknown_schema(self):
        from workflow import SUPPORTED_SCHEMAS, load_registry as load
        self.assertIn(2, SUPPORTED_SCHEMAS)
        self.assertEqual(self.registry["schema_version"], 3)
        fake = self.root / "workflow"; fake.mkdir()
        data = copy.deepcopy(self.registry); data["schema_version"] = 999
        import json
        (fake / "registry.json").write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            load(self.root)

    def test_cycle_readout_is_interim_until_the_window_closes(self):
        import datetime as dt
        from workflow import check_cycle
        cycle = self.root / ".sdlc/_product/cycles/2026-09"
        (cycle / "outputs").mkdir(parents=True)
        (cycle / "outputs/readout.md").write_text("# readout\n")
        base = ("id: 2026-09\nstatus: open\nwindow:\n  from: 2026-09-01\n  to: 2026-09-30\ndata_cutoff: 2026-10-02\n"
                "selected_tasks:\n  - role: analyst\n    task: readout\n    status: done\n")
        (cycle / "cycle.yaml").write_text(base)
        codes = {r[1] for r in check_cycle(self.registry, cycle, today=dt.date(2026, 9, 20))}
        self.assertIn("CYCLE-INTERIM", codes)
        self.assertEqual(check_cycle(self.registry, cycle, today=dt.date(2026, 10, 5)), [])
        (cycle / "cycle.yaml").write_text(base.replace("data_cutoff: 2026-10-02", "data_cutoff: 2026-09-15"))
        self.assertIn("CYCLE-INTERIM", {r[1] for r in check_cycle(self.registry, cycle, today=dt.date(2026, 10, 5))})

    # ---- batch E: read-only trace over scoped, versioned ids
    def trace_fixture(self):
        files = {
            "sdlc.config.yaml": "product_root: docs/product\nsignals_path: docs/signals\n",
            "docs/product/data/metrics.yaml": "metrics:\n  - id: export_rate\n    owner: pm\n    version: 3\n  - id: churn\n    formula: x\n",
            "docs/product/strategy.md": "北极星：metric:export_rate\n",
            "docs/signals/signals.md": "| ID | 来源 |\n|---|---|\n| SIG-202609-1 | 工单 #12 |\n",
            ".sdlc/export/01-define/spec.md": "| J-1 | 导出本周工单 |\n| FR-01 | 一键导出（J-1）；来自 SIG-202609-1 |\n| FR-02 | 失败给原因（J-1） |\n| FR-03 | 只在验收里提到 |\n",
            ".sdlc/export/01-define/tracking.md": "| EV-1 | export_clicked | J-1 | metric:export_rate |\n",
            ".sdlc/export/02-shape/contract.md": "| T-1 | 导出 | FR-01, FR-02 | J-1 |\n",
            ".sdlc/export/03-impl/T-1-backend-evidence.md": "exit code 0\n",
            ".sdlc/export/04-verify/coverage.md": "| FR/NFR | Case | File | Result |\n|---|---|---|---|\n| FR-01 | TC-1 | t.py:1 | ✅ |\n| FR-02 | — | — | ❌ hole |\n",
            ".sdlc/export/04-verify/accept-pm.md": "FR-03 走查通过（这只是提到，不是验证记录）\n",
            ".sdlc/export/state.yaml": "feature: export\nstale_artifacts: [01-define/tracking.md]\n",
            ".sdlc/billing/01-define/spec.md": "| FR-01 | 按月出账 |\n",
            ".sdlc/_product/cycles/2026-09/outputs/decisions.md": "| P-1 | SIG-202609-1 | 采纳 |\n",
        }
        for rel, text in files.items():
            self.put(rel, text)

    def trace(self, ident, **kw):
        from sdlc_trace import build_index, query
        return query(build_index(**{k: str(v) for k, v in kw.items()}), ident)

    def test_trace_scopes_short_ids_and_refuses_ambiguity(self):
        self.trace_fixture()
        code, result = self.trace("FR-01", project_root=self.root)
        self.assertEqual(code, 2)
        self.assertIn("pass --feature", result["error"])
        code, result = self.trace("FR-01", feature=self.root / ".sdlc/export")
        self.assertEqual(code, 0)
        self.assertEqual(result["container"], "feature:export")
        self.assertEqual(result["status"][0]["status"], "verified by coverage rows")
        self.assertIn(("anchored to journey", "J-1"), {(r["relation"], r["id"]) for r in result["upstream"]})
        self.assertIn(("implemented by ticket", "T-1"), {(r["relation"], r["id"]) for r in result["downstream"]})
        self.assertIn(("from signal", "SIG-202609-1"), {(r["relation"], r["id"]) for r in result["upstream"]})

    def test_trace_status_comes_only_from_records(self):
        self.trace_fixture()
        feature = self.root / ".sdlc/export"
        self.assertEqual(self.trace("FR-02", feature=feature)[1]["status"][0]["status"], "unverified (matrix hole)")
        mentioned = self.trace("FR-03", feature=feature)[1]  # an acceptance note mentions it; no coverage row
        self.assertNotIn("verified by coverage rows", [s["status"] for s in mentioned["status"]])
        self.assertIn("coverage.md exists but has no row for this id", mentioned["gaps"])
        ticket = self.trace("T-1", feature=feature)[1]
        self.assertEqual(ticket["status"][0], {"status": "evidence recorded", "records": ["03-impl/T-1-backend-evidence.md"]})
        event = self.trace("EV-1", feature=feature)[1]
        self.assertIn("stale (listed in state.yaml stale_artifacts)", [s["status"] for s in event["status"]])

    def test_trace_product_ids_are_versioned_and_global(self):
        self.trace_fixture()
        code, metric = self.trace("metric:export_rate", project_root=self.root)
        self.assertEqual(code, 0)
        self.assertEqual(metric["definitions"][0]["version"], "3")
        self.assertIn(("fed by event", "EV-1"), {(r["relation"], r["id"]) for r in metric["upstream"]})
        churn = self.trace("metric:churn", product_root=self.root / "docs/product")[1]
        self.assertNotEqual(churn["definitions"][0]["version"], "3")  # the next entry's version is not borrowed
        signal = self.trace("SIG-202609-1", project_root=self.root)[1]
        self.assertIn("cycle:2026-09", {m["container"] for m in signal["mentions"]})
        self.assertEqual(self.trace("metric:missing", project_root=self.root)[0], 1)

    def test_trace_is_read_only(self):
        self.trace_fixture()
        before = sorted((p.as_posix(), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file())
        from sdlc_trace import main as trace_main
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(trace_main(["FR-01", "--feature", str(self.root / ".sdlc/export"), "--json"]), 0)
            self.assertEqual(trace_main(["FR-01"]), 2)
        after = sorted((p.as_posix(), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file())
        self.assertEqual(before, after)

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

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

    def put(self, path, text="test artifact\n"):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def packet(self, role="designer", stage="designer", task="explore", skill="design-contract", outputs=None, check="listed outputs exist"):
        if outputs is None:
            outputs = ["02-shape/design-brief.md", "02-shape/design-directions.md", "02-shape/prototypes/"]
        return (f"## SPAWN PACKET v2\nhat: {role}\nstage: {stage}\ntask: {task}\n"
                f"subagent_type: sdlc-workflow:{role}\nPLUGIN_ROOT: {ROOT}\n"
                f"feature_dir: {self.root}\nlane: L2\nprimary_skill: sdlc-workflow:{skill}\n"
                "deliverable_paths:\n" + "".join(f"  - {p}\n" for p in outputs)
                + f"success_checks:\n  - {check}\nreturn: output paths + summary\n"
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
        packet = self.packet(role="backend", stage="implement", task="T-1", skill="impl-evidence", outputs=["03-impl/T-1-evidence.md"])
        packet += "lane_file: api\n"
        self.assertIn("INTEGRATOR", {e["code"] for e in lint(packet)["errors"]})
        self.assertEqual(lint(packet + "slice_integrator: backend\n")["errors"], [])

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


if __name__ == "__main__":
    unittest.main(verbosity=2)

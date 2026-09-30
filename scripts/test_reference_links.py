"""Behavioral regressions for project-only, non-destructive host integration."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from hosts import ROOT
from reference_links import execute


class LinkOperations(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.scope = self.root / "project"
        self.scope.mkdir()
        self.pairs = []
        for name in ("a", "b"):
            target = self.source / name
            target.write_text(name)
            self.pairs.append((self.scope / "links" / name, target, True))

    def run_links(self, **kwargs):
        return execute(self.pairs, scope=self.scope, **kwargs)

    def test_all_conflicts_are_preflighted_no_partial_install(self):
        foreign = self.pairs[-1][0]
        foreign.parent.mkdir()
        foreign.write_text("keep")
        self.assertTrue(self.run_links()[0])
        self.assertFalse(self.pairs[0][0].is_symlink())
        self.assertEqual(foreign.read_text(), "keep")

    def test_foreign_symlink_is_never_replaced_or_removed(self):
        foreign = self.pairs[-1][0]
        foreign.parent.mkdir()
        foreign.symlink_to(self.root / "foreign-dangling")
        self.assertTrue(self.run_links()[0])
        self.assertTrue(self.run_links(remove=True)[0])
        self.assertEqual(os.readlink(foreign), str(self.root / "foreign-dangling"))

    def test_missing_source_does_not_create_targets(self):
        self.pairs[-1][1].unlink()
        self.assertTrue(self.run_links()[0])
        self.assertFalse((self.scope / "links").exists())

    def test_idempotence_live_reference_and_owned_dangling_removal(self):
        self.assertEqual(self.run_links(), ([], 2))
        self.assertEqual(self.run_links(), ([], 0))
        self.assertEqual(self.run_links(check=True), ([], 0))
        self.pairs[0][1].write_text("updated source")
        self.assertEqual(self.pairs[0][0].read_text(), "updated source")
        self.pairs[-1][1].unlink()
        self.assertEqual(self.run_links(remove=True), ([], 2))
        self.assertEqual(self.run_links(remove=True), ([], 0))

    def test_same_real_source_through_hub_is_preserved(self):
        hub = self.root / "hub"
        hub.symlink_to(self.source)
        self.pairs[0][0].parent.mkdir()
        self.pairs[0][0].symlink_to(hub / "a")
        before = os.readlink(self.pairs[0][0])
        self.assertEqual(self.run_links(), ([], 1))
        self.assertEqual(os.readlink(self.pairs[0][0]), before)

    def test_symlinked_parent_cannot_redirect_install_or_remove(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.scope / "links").symlink_to(outside)
        self.assertTrue(self.run_links()[0])
        self.assertTrue(self.run_links(remove=True)[0])
        self.assertEqual(list(outside.iterdir()), [])

    def test_io_error_rolls_back_only_new_links(self):
        original = Path.symlink_to
        def fail_second(link, *args, **kwargs):
            if link.name == "b":
                raise OSError("simulated failure")
            return original(link, *args, **kwargs)
        with patch.object(Path, "symlink_to", fail_second):
            self.assertTrue(self.run_links()[0])
        self.assertFalse(self.pairs[0][0].is_symlink())

    def test_kimi_project_hub_and_removal_do_not_touch_other_projects(self):
        project = self.scope
        (project / ".git").mkdir()
        hub = project / ".agents" / "plugins" / "sdlc-workflow"
        hub.parent.mkdir(parents=True)
        hub.symlink_to(ROOT)
        other = self.root / "other"
        other.mkdir()
        def run(*flags):
            return subprocess.run([sys.executable, str(hub / "scripts/link-kimi.py"),
                                   "--project", str(project), *flags], text=True, capture_output=True)
        self.assertEqual(run("--check").returncode, 1)
        result = run()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(run("--check").returncode, 0)
        self.assertEqual(len(list((project / ".kimi-code/skills").iterdir())), 27)
        self.assertEqual(len(list((project / ".kimi-code/agents").iterdir())), 19)
        for folder in ("skills", "agents"):
            for path in (project / ".kimi-code" / folder).iterdir():
                self.assertTrue(path.is_symlink())
                self.assertFalse(os.path.isabs(os.readlink(path)))
                self.assertTrue(path.resolve().is_relative_to(ROOT))
        self.assertEqual(list(other.iterdir()), [])
        self.assertEqual(run("--remove").returncode, 0)
        self.assertFalse(list((project / ".kimi-code/agents").iterdir()))


class HostMethodValidity(unittest.TestCase):
    def test_host_variant_changes_invalidate_only_the_same_role(self):
        import json
        from task_runtime import method_closure
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / 'skills/test').mkdir(parents=True)
            (base / 'skills/test/SKILL.md').write_text('A stable method.')
            (base / 'agents').mkdir()
            (base / 'agents/pm.md').write_text('PM role.')
            for host, ext in (('codex', 'toml'), ('kimi', 'md')):
                d = base / 'adapters' / host / 'agents'; d.mkdir(parents=True)
                for role in ('pm', 'reviewer'):
                    (d / f'sdlc-workflow-{role}.{ext}').write_text(role + ' original')
            (base / 'adapters/hosts.json').write_text(json.dumps({
                h: {'agent_prefix': 'sdlc-workflow-'} for h in ('codex', 'kimi')}))
            method = {'primary': 'test'}
            before = method_closure('pm', method, base=base)['sha256']
            (base / 'adapters/kimi/agents/sdlc-workflow-reviewer.md').write_text('reviewer changed')
            self.assertEqual(before, method_closure('pm', method, base=base)['sha256'])
            (base / 'adapters/kimi/agents/sdlc-workflow-pm.md').write_text('PM Kimi permission changed')
            after = method_closure('pm', method, base=base)['sha256']
            self.assertNotEqual(before, after)
            (base / 'adapters/codex/agents/sdlc-workflow-pm.toml').write_text('PM Codex permission changed')
            self.assertNotEqual(after, method_closure('pm', method, base=base)['sha256'])


if __name__ == "__main__":
    unittest.main()

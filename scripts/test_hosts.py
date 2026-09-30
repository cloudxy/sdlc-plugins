#!/usr/bin/env python3
"""Cross-host packaging tests: generated manifests, the host reference, Codex agents and their installer.

Structure only. Loading on real hosts is checked with their CLIs (adapters/HOST-NOTES.md, "Cross-host packaging").
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hosts import CODEX_AGENT_DIR, KIMI_AGENT_DIR, ROOT, codex_agent_name, kimi_agent_name, host_problems, load_hosts, render_hosts  # noqa: E402
from workflow import generated_files, load_registry  # noqa: E402

REGISTRY = load_registry()
HOSTS = load_hosts()
GENERATED = dict(render_hosts(REGISTRY))


def manifest(rel):
    return json.loads(GENERATED[rel])


class Manifests(unittest.TestCase):
    def test_every_manifest_is_generated_and_current(self):
        rendered = dict(generated_files(REGISTRY))
        for rel in (".zcode-plugin/plugin.json", ".claude-plugin/plugin.json", ".claude-plugin/marketplace.json",
                    ".grok-plugin/plugin.json", ".codex-plugin/plugin.json", ".kimi-plugin/plugin.json", ".agents/plugins/marketplace.json",
                    "skills/sdlc/references/hosts.md"):
            self.assertIn(rel, rendered)
            self.assertEqual((ROOT / rel).read_text(encoding="utf-8"), rendered[rel], f"{rel}: run workflow.py render")

    def test_identity_is_the_same_everywhere(self):
        plugin = HOSTS["plugin"]
        for rel in (".zcode-plugin/plugin.json", ".claude-plugin/plugin.json", ".grok-plugin/plugin.json",
                    ".codex-plugin/plugin.json", ".kimi-plugin/plugin.json"):
            m = manifest(rel)
            self.assertEqual((m["name"], m["version"], m["description"]),
                             (plugin["name"], plugin["version"], plugin["description"]), rel)

    def test_claude_and_grok_list_exactly_the_rendered_role_agents(self):
        want = [f"./agents/{role}.md" for role in REGISTRY["roles"]]
        for rel in (".claude-plugin/plugin.json", ".grok-plugin/plugin.json"):
            self.assertEqual(manifest(rel)["agents"], want, rel)
        self.assertFalse(any("/_lib/" in a or "/profiles/" in a for a in want))

    def test_zcode_keeps_directory_components(self):
        m = manifest(".zcode-plugin/plugin.json")
        self.assertEqual((m["skills"], m["commands"], m["agents"]), ("skills", "commands", "agents"))

    def test_recursive_agent_scan_contains_no_source_fragments(self):
        self.assertEqual({p.relative_to(ROOT / "agents").as_posix() for p in (ROOT / "agents").rglob("*.md")},
                         {f"{role}.md" for role in REGISTRY["roles"]})

    def test_kimi_components_exist_inside_plugin(self):
        m = manifest(".kimi-plugin/plugin.json")
        self.assertEqual(m["agents"], "./adapters/kimi/agents/")
        for key in ("skills", "commands", "agents"):
            target = (ROOT / m[key]).resolve()
            self.assertTrue(target.is_dir())
            self.assertTrue(target.is_relative_to(ROOT))

    def test_codex_manifest_and_marketplace(self):
        m = manifest(".codex-plugin/plugin.json")
        self.assertEqual(m["skills"], "./skills/")
        self.assertNotIn("agents", m)
        self.assertNotIn("commands", m)
        for key in ("displayName", "shortDescription", "developerName", "category", "capabilities"):
            self.assertIn(key, m["interface"])
        entry = manifest(".agents/plugins/marketplace.json")["plugins"][0]
        self.assertEqual(entry["source"], {"source": "local", "path": "./"})
        self.assertEqual(set(entry["policy"]), {"installation", "authentication"})
        self.assertIn("category", entry)

    def test_claude_marketplace_has_no_codex_only_fields(self):
        # Claude Code reports unknown entry fields and --strict fails on them.
        entry = manifest(".claude-plugin/marketplace.json")["plugins"][0]
        self.assertEqual(entry["source"], "./")
        self.assertNotIn("policy", entry)

    def test_marketplace_ids_match(self):
        name = HOSTS["plugin"]["name"]
        for rel in (".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json"):
            data = manifest(rel)
            self.assertEqual((data["name"], data["plugins"][0]["name"]), (HOSTS["marketplace"]["name"], name), rel)

    def test_no_root_manifest_and_no_problems(self):
        self.assertFalse((ROOT / "plugin.json").exists())
        self.assertEqual(host_problems(REGISTRY), [])

    def test_root_manifest_is_reported(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "adapters").mkdir()
            (root / "adapters" / "hosts.json").write_text(json.dumps(HOSTS))
            (root / "plugin.json").write_text("{}")
            problems = host_problems(REGISTRY, root)
            self.assertTrue(any("root" in p and "Grok" in p for p in problems), problems)
            self.assertTrue(any("listed agent missing" in p for p in problems))


class HostReference(unittest.TestCase):
    TEXT = GENERATED["skills/sdlc/references/hosts.md"]

    def test_every_command_has_a_codex_route(self):
        for name, item in REGISTRY["commands"].items():
            self.assertIn(f"| `/{name}` | `sdlc-workflow:{item['skill']}` | `{item['mode']}` |", self.TEXT)
            self.assertIn(f"`/skill:{item['skill']} mode: {item['mode']} <arguments>`", self.TEXT)

    def test_every_role_has_both_names(self):
        for role in REGISTRY["roles"]:
            self.assertIn(f"| {role} | `sdlc-workflow:{role}` | `{codex_agent_name(HOSTS, role)}` |", self.TEXT)

    def test_reference_only_for_every_host(self):
        self.assertIn("## Reference only", self.TEXT)
        for h in HOSTS["hosts"]:
            self.assertIn(f"- **{h['label']}**:", self.TEXT)
        for command in ("claude plugin install", "grok plugin install", "codex plugin add"):
            self.assertIn(f"Never `{command}`", self.TEXT)
        self.assertIn("real path", self.TEXT)

    def test_generic_fallbacks(self):
        self.assertIn("| `general-purpose` |", self.TEXT)
        self.assertIn("| `default` |", self.TEXT)

    def test_skills_honour_an_explicit_mode_without_commands(self):
        for rel in ("skills/sdlc/SKILL.md", "skills/discover/SKILL.md", "skills/imagery/SKILL.md"):
            self.assertRegex((ROOT / rel).read_text(encoding="utf-8"), r"`mode:", rel)


class CodexAgents(unittest.TestCase):
    def files(self):
        return {role: (ROOT / CODEX_AGENT_DIR / f"{codex_agent_name(HOSTS, role)}.toml").read_text(encoding="utf-8")
                for role in REGISTRY["roles"]}

    def test_one_agent_per_role_with_codex_header(self):
        for role, text in self.files().items():
            agent = codex_agent_name(HOSTS, role)
            self.assertIn(f'name = "{agent}"\n', text)
            self.assertIn(f"You are **sdlc-workflow:{role}** (Codex agent `{agent}`)", text)
            self.assertIn("## Host (Codex)", text)
            self.assertNotIn("\n---\nname:", text)
            self.assertNotIn("<!-- GENERATED", text)
            self.assertEqual(text.count("'''"), 2)

    def test_reviewers_are_read_only_and_writers_inherit(self):
        for role, text in self.files().items():
            read_only = 'sandbox_mode = "read-only"\n' in text
            self.assertEqual(read_only, REGISTRY["roles"][role]["fresh"], role)

    def test_toml_parses_when_tomllib_exists(self):
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            self.skipTest("tomllib unavailable on this Python; structure checked above")
        for role, text in self.files().items():
            data = tomllib.loads(text)
            self.assertEqual(set(data) - {"sandbox_mode"}, {"name", "description", "developer_instructions"}, role)

    def test_link_codex_references_and_never_copies(self):
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            home, project = td / "codex-home", td / "project"
            (project / ".agents" / "plugins").mkdir(parents=True)
            hub = project / ".agents" / "plugins" / "sdlc-workflow"
            hub.symlink_to(ROOT)                       # a project plugin hub, like .agents/plugins/<name>
            agents = project / ".codex" / "agents"
            agents.mkdir(parents=True)
            (agents / "mine.toml").write_text('name = "mine"\n')
            script = hub / "scripts" / "link-codex.py"  # invoked through the hub: links go through it

            def run(*extra):
                return subprocess.run([sys.executable, str(script), "--codex-home", str(home), "--project",
                                       str(project), *extra], capture_output=True, text=True, env=env)

            self.assertEqual(run("--check").returncode, 1)
            self.assertEqual(run().returncode, 0, run().stdout)
            self.assertEqual(run("--check").returncode, 0)
            skills = project / ".codex" / "skills" / "sdlc-workflow"  # project-scoped, like .claude/
            self.assertTrue(skills.is_symlink())
            self.assertEqual(os.readlink(skills), "../../.agents/plugins/sdlc-workflow/skills")
            self.assertEqual(skills.resolve(), (ROOT / "skills").resolve())
            self.assertFalse((home / "skills").exists(), "--project must not touch the user-level Codex home")
            links = sorted(agents.glob("sdlc-workflow-*.toml"))
            self.assertEqual(len(links), len(REGISTRY["roles"]))
            for link in links:
                self.assertTrue(link.is_symlink())
                self.assertFalse(os.path.isabs(os.readlink(link)), "agent links inside the project stay relative")
                self.assertEqual(link.resolve(), (ROOT / CODEX_AGENT_DIR / link.name).resolve())
            # A copy standing where a link belongs is reported and left alone.
            first = links[0]
            first.unlink()
            first.write_text("copied")
            result = run()
            self.assertEqual(result.returncode, 1)
            self.assertIn("copy:", result.stdout)
            self.assertEqual(first.read_text(), "copied")
            first.unlink()
            # A copied plugin install in Codex's cache is reported.
            (home / "plugins" / "cache" / "any" / "sdlc-workflow").mkdir(parents=True)
            self.assertIn("copied plugin install", run().stdout)
            shutil.rmtree(home / "plugins")
            self.assertEqual(run().returncode, 0)
            self.assertEqual(run("--remove").returncode, 0)
            self.assertEqual([p.name for p in agents.iterdir()], ["mine.toml"])
            self.assertFalse(skills.exists() or skills.is_symlink())

class KimiAgents(unittest.TestCase):
    def test_role_names_tool_boundaries_and_no_nested_agents(self):
        for role, meta in REGISTRY["roles"].items():
            text = (ROOT / KIMI_AGENT_DIR / f"{kimi_agent_name(HOSTS, role)}.md").read_text()
            header = dict(line.split(":", 1) for line in text.split("---", 2)[1].strip().splitlines())
            tools = {t.strip() for t in header["tools"].split(",")}
            denied = {t.strip() for t in header["disallowedTools"].split(",")}
            self.assertEqual(header["name"].strip(), f"sdlc-workflow-{role}")
            self.assertEqual(header["subagents"].strip(), "[]")
            self.assertFalse(tools & {"Agent", "AgentSwarm", "*"})
            self.assertTrue({"Agent", "AgentSwarm"} <= denied)
            if meta["fresh"]:
                self.assertEqual(tools, {"Read", "Glob", "Grep", "Skill"})
                self.assertTrue({"Bash", "Edit", "Write"} <= denied)
            else:
                self.assertTrue({"Read", "Edit", "Write", "Bash"} <= tools)


if __name__ == "__main__":
    unittest.main()

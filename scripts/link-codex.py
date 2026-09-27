#!/usr/bin/env python3
"""Use this plugin from Codex by reference: symlinks only, never copies.

  python3 <PLUGIN_ROOT>/scripts/link-codex.py --project <root>   # this project only: <root>/.codex/{skills,agents}
  python3 <PLUGIN_ROOT>/scripts/link-codex.py                    # every project: $CODEX_HOME (~/.codex)/{skills,agents}
  ... --check     exit 1 when a link is missing, points elsewhere, or a copy stands in its place
  ... --remove    delete only this plugin's links

What gets linked (verified with Codex CLI 0.156.1, adapters/HOST-NOTES.md):
  <codex dir>/skills/sdlc-workflow  ->  <PLUGIN_ROOT>/skills        Codex lists them as sdlc-workflow:<skill>
  <codex dir>/agents/sdlc-workflow-<role>.toml -> <PLUGIN_ROOT>/adapters/codex/agents/sdlc-workflow-<role>.toml
where <codex dir> is <root>/.codex with --project, else $CODEX_HOME.

Prefer --project: Codex reads a project's .codex/skills (from any subdirectory; not in the official docs) and
.codex/agents (trusted projects), so the plugin stays isolated to that project, like .claude/. $CODEX_HOME is
shared by every project. `codex plugin add` installs a copy (it also drops symlinks and refuses a symlinked
cache), so it is not used. Links point at the path this script was invoked through: run it via a hub symlink
(for example <repo>/.agents/plugins/sdlc-workflow/scripts/link-codex.py) to reference the hub; inside the
project the links stay relative. Existing real files or directories are never overwritten or deleted; they are
reported as copies.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hosts import CODEX_AGENT_DIR, codex_agent_name, load_hosts  # noqa: E402
from workflow import load_registry  # noqa: E402

PLUGIN = Path(os.path.abspath(__file__)).parent.parent  # the invoked path, not its realpath


def codex_home(value) -> Path:
    if value:
        return Path(value).expanduser().absolute()
    env = os.environ.get("CODEX_HOME")
    return Path(env).expanduser().absolute() if env else Path.home() / ".codex"


def link_value(link: Path, target: Path, relative: bool) -> str:
    return os.path.relpath(target, link.parent) if relative else str(target)


def plan(args):
    hosts = load_hosts()
    name = hosts["plugin"]["name"]
    home = codex_home(args.codex_home)
    if args.project:
        project = Path(args.project).expanduser().absolute()
        if not project.is_dir():
            raise SystemExit(f"project directory not found: {project}")
        # Inside the project (e.g. a hub symlink) links stay relative, so the project stays portable.
        base, relative = project / ".codex", PLUGIN.is_relative_to(project)
    else:
        base, relative = home, False
    pairs = [(base / "skills" / name, PLUGIN / "skills", relative)]
    for role in load_registry()["roles"]:
        file = f"{codex_agent_name(hosts, role)}.toml"
        pairs.append((base / "agents" / file, PLUGIN / CODEX_AGENT_DIR / file, relative))
    return home, name, pairs, base


def state(link: Path, target: Path, relative: bool) -> str:
    if link.is_symlink():
        return "ok" if os.readlink(link) == link_value(link, target, relative) else "elsewhere"
    if link.exists():
        return "copy"
    return "missing"


def copied_installs(home: Path, name: str):
    cache = home / "plugins" / "cache"
    return sorted(str(p) for p in cache.glob(f"*/{name}") if p.is_dir()) if cache.is_dir() else []


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--project", help="project root: link role agents into <root>/.codex/agents/")
    p.add_argument("--codex-home", help="Codex home (default $CODEX_HOME or ~/.codex)")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="report missing, foreign or copied entries; change nothing")
    mode.add_argument("--remove", action="store_true", help="remove this plugin's links only")
    args = p.parse_args(argv)

    home, name, pairs, base = plan(args)
    missing_src = [str(t) for _, t, _ in pairs if not t.exists()]
    if missing_src:
        print("sources missing (run python3 scripts/render-role-agents.py):\n  " + "\n  ".join(missing_src))
        return 1

    if args.remove:
        removed = 0
        for link, target, relative in pairs:
            if link.is_symlink():
                link.unlink()
                removed += 1
        print(f"removed {removed} link(s)")
        return 0

    problems = []
    for link, target, relative in pairs:
        s = state(link, target, relative)
        if s == "ok":
            continue
        if args.check or s == "copy":
            problems.append(f"{s}: {link}" + (" (a real file or directory: reference only — remove it, then re-run)" if s == "copy" else ""))
            continue
        if link.is_symlink():
            link.unlink()
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(link_value(link, target, relative))
    for path in copied_installs(home, name):
        problems.append(f"copied plugin install: {path} (codex plugin remove {name}@<marketplace>)")
    if problems:
        print("\n".join(problems))
        return 1
    scope = "this project only" if args.project else "every project (user-level)"
    print(f"{'up to date' if args.check else 'linked'}: {len(pairs)} reference(s) in {base} ({scope}) -> {PLUGIN}")
    if args.project and not args.check:
        print("Codex loads project .codex/ only for trusted projects.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Install the generated Codex role agents (adapters/codex/agents/*.toml) for Codex.

Codex plugins carry skills only, so role agents live in a Codex agents directory:

  python3 scripts/install-codex-agents.py --project /path/to/project   # <project>/.codex/agents/ (trusted projects)
  python3 scripts/install-codex-agents.py --user                       # $CODEX_HOME/agents or ~/.codex/agents
  ... --check    exit 1 when an installed copy is missing or differs (nothing written)
  ... --remove   delete only this plugin's sdlc-workflow-*.toml files

Only files named after this plugin's roles are touched; other agents in the directory are left alone.
Re-run after render-role-agents.py changes the sources.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hosts import CODEX_AGENT_DIR, ROOT, codex_agent_name, load_hosts  # noqa: E402
from workflow import load_registry  # noqa: E402


def target_dir(args) -> Path:
    if args.project:
        project = Path(args.project).expanduser().resolve()
        if not project.is_dir():
            raise SystemExit(f"project directory not found: {project}")
        return project / ".codex" / "agents"
    home = os.environ.get("CODEX_HOME")
    return (Path(home).expanduser() if home else Path.home() / ".codex") / "agents"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    where = p.add_mutually_exclusive_group(required=True)
    where.add_argument("--project", help="project root; installs into <project>/.codex/agents/")
    where.add_argument("--user", action="store_true", help="install into $CODEX_HOME/agents or ~/.codex/agents/")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="report missing or outdated copies; write nothing")
    mode.add_argument("--remove", action="store_true", help="remove this plugin's agent files")
    args = p.parse_args(argv)

    hosts = load_hosts()
    names = [codex_agent_name(hosts, role) + ".toml" for role in load_registry()["roles"]]
    source = ROOT / CODEX_AGENT_DIR
    missing = [n for n in names if not (source / n).is_file()]
    if missing:
        print("generated agents missing (run python3 scripts/render-role-agents.py): " + ", ".join(missing))
        return 1
    dest = target_dir(args)

    if args.remove:
        removed = [n for n in names if (dest / n).is_file()]
        for n in removed:
            (dest / n).unlink()
        print(f"removed {len(removed)} agent file(s) from {dest}")
        return 0
    stale = [n for n in names if not (dest / n).is_file() or (dest / n).read_bytes() != (source / n).read_bytes()]
    if args.check:
        print(f"{dest}: " + ("up to date" if not stale else "missing or outdated: " + ", ".join(stale)))
        return int(bool(stale))
    dest.mkdir(parents=True, exist_ok=True)
    for n in stale:
        shutil.copyfile(source / n, dest / n)
    print(f"installed {len(stale)} of {len(names)} agent file(s) into {dest}" + ("" if stale else " (already up to date)"))
    if args.project:
        print("Codex loads project .codex/ only for trusted projects.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

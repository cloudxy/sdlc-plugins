#!/usr/bin/env python3
"""Link Kimi Code skills and agents into one Git project; never copy or install globally.

  python3 PLUGIN_ROOT/scripts/link-kimi.py --project <git root> [--check | --remove]

Run through .agents/plugins/sdlc-workflow/scripts/link-kimi.py to keep links relative
to that project's plugin hub. --remove only removes links still owned by this source.
Kimi plugin installation uses a user-level managed copy, so it is not used here.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hosts import KIMI_AGENT_DIR, kimi_agent_name, load_hosts
from workflow import load_registry
from reference_links import execute

PLUGIN = Path(os.path.abspath(__file__)).parent.parent


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", required=True, help="Git root (.git directory or worktree marker)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--remove", action="store_true")
    args = parser.parse_args(argv)
    project = Path(args.project).expanduser().absolute()
    if not project.is_dir() or (not args.remove and not (project / ".git").exists()):
        parser.error("--project must be an existing Git root; Kimi discovers the nearest .git, including from subdirectories")
    hosts = load_hosts()
    relative = PLUGIN.is_relative_to(project)
    base = project / ".kimi-code"
    # Registry skills are complete and stable even if a source directory is missing.
    skills = sorted(load_registry()["skills"])
    pairs = [(base / "skills" / name, PLUGIN / "skills" / name, relative) for name in skills]
    for role in load_registry()["roles"]:
        name = kimi_agent_name(hosts, role) + ".md"
        pairs.append((base / "agents" / name, PLUGIN / KIMI_AGENT_DIR / name, relative))
    problems, changed = execute(pairs, scope=project, check=args.check, remove=args.remove)
    if args.remove:
        print(f"removed {changed} owned link(s)")
    if problems:
        print("\n".join(problems))
        return 1
    if not args.remove:
        print(f"{'up to date' if args.check else 'linked'}: {len(skills)} skills, {len(pairs) - len(skills)} agents in {base} (this project only)")
        if not args.check:
            print("Start a new Kimi session; use /skill:sdlc mode: <mode> <arguments>.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

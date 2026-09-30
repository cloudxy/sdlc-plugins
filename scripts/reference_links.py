"""Shared project-link operations. Preflight the whole plan; never replace foreign entries."""
from __future__ import annotations

import os
from pathlib import Path


def link_value(link: Path, target: Path, relative: bool) -> str:
    return os.path.relpath(target, link.parent) if relative else str(target)


def state(link: Path, target: Path, relative: bool) -> str:
    if link.is_symlink():
        actual = Path(os.path.abspath(link.parent / os.readlink(link)))
        # Lexical equality also recognizes our dangling links for safe removal.
        if actual == Path(os.path.abspath(target)):
            return "ok"
        if link.exists() and target.exists() and link.resolve() == target.resolve():
            return "ok"
        return "elsewhere"
    return "copy" if link.exists() else "missing"


def parent_problems(link: Path, scope: Path):
    """Do not follow a redirected host directory out of the requested install scope."""
    problems = []
    for parent in link.parents:
        if parent == scope:
            break
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            problems.append(f"unsafe parent: {parent} (expected a real directory)")
    return problems


def execute(pairs, *, scope: Path, check=False, remove=False, problems=()):
    """Return (problems, changed count); check/remove never create directories.

    Remove checks ownership independently of source availability and leaves foreign entries
    intact. Install checks all sources/destinations before its first write. On an I/O error,
    roll back only the links created by this invocation, with ownership rechecked.
    """
    pairs = list(pairs)
    errors = list(problems)
    states = []
    for link, target, relative in pairs:
        errors.extend(parent_problems(link, scope))
        s = state(link, target, relative)
        states.append(s)
        if not remove and not target.exists():
            errors.append(f"source missing: {target} (render the plugin first)")
        if s in ("copy", "elsewhere") or (check and s == "missing"):
            errors.append(f"{s}: {link} (left unchanged)")
    # Unsafe parents make even removal unsafe; ordinary foreign entries are preserved.
    if check or (errors and not remove) or any(e.startswith("unsafe parent:") for e in errors):
        return errors, 0
    changed = []
    try:
        for (link, target, relative), s in zip(pairs, states):
            if remove:
                if s == "ok" and state(link, target, relative) == "ok":
                    link.unlink()
                    changed.append((link, target, relative))
            elif s == "missing":
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(link_value(link, target, relative))
                changed.append((link, target, relative))
    except OSError as exc:
        if not remove:
            for link, target, relative in reversed(changed):
                if state(link, target, relative) == "ok":
                    link.unlink()
        return errors + [f"link operation failed: {exc}"], len(changed) if remove else 0
    return errors, len(changed)

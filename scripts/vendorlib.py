"""vendor/ lock files: one place for the tree-digest algorithm and for resolving a vendored file.

The digest must match plugin-updater/scripts/update/vendor.py and vendor/install.sh:
sha256 over sorted "<relpath>\\0<sha256 of file>\\n" lines.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FREE_LICENSES = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC"}


def tree(root: str | Path) -> tuple[str, dict[str, str]]:
    files: dict[str, str] = {}
    for dp, _dn, fn in os.walk(root):
        for f in fn:
            p = os.path.join(dp, f)
            files[os.path.relpath(p, root).replace(os.sep, "/")] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    h = hashlib.sha256()
    for rel in sorted(files):
        h.update(f"{rel}\0{files[rel]}\n".encode())
    return h.hexdigest(), files


def lock(name: str, root: Path = ROOT) -> dict | None:
    try:
        return json.loads((root / "vendor" / f"{name}.lock.json").read_text())
    except (OSError, ValueError):
        return None


class VendorError(Exception):
    pass


def resolve(name: str, rel: str, root: Path = ROOT) -> Path:
    """Path of a vendored file, after checking the installed tree still matches its lock."""
    lk = lock(name, root)
    if not lk:
        raise VendorError(f"vendor/{name}.lock.json missing")
    target = root / "vendor" / name
    if not target.is_dir():
        raise VendorError(f"vendor/{name} is not installed: run bash vendor/install.sh {name}")
    digest, _ = tree(target)
    if digest != lk.get("tree_digest"):
        raise VendorError(f"vendor/{name} does not match its lock (edited locally?): run bash vendor/install.sh --force {name}")
    p = target / rel
    if not p.is_file():
        raise VendorError(f"vendor/{name}/{rel} is not in the locked tree")
    return p

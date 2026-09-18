#!/usr/bin/env python3
"""Run evidence bound to the code it ran against — a pass in state.yaml is not evidence, a run record is.

  python3 scripts/evidence.py run --feature <feature_dir> --name e2e -- npx playwright test
      Runs the command in the project root, writes <feature>/evidence/runs/<name>-<time>.json (+ .log) with the
      exit code and the source fingerprint before and after, and prints the gate record to paste into state.yaml:
        - {name: e2e, kind: script, result: pass, evidence: evidence/runs/e2e-….json}
  python3 scripts/evidence.py gate --feature <feature_dir> --name e2e
      The LAST gates[] record named e2e decides (an older pass never outweighs a newer fail). It must say pass,
      point at a run record whose exit code is 0, and that run's fingerprint must equal the current source.
  python3 scripts/evidence.py fingerprint --feature <feature_dir>
  python3 scripts/evidence.py conditional --feature <feature_dir> --who pm
      A 有条件通过 acceptance needs open_questions entry Q-ACCEPT-<WHO> with status answered, by: user, quote.
  python3 scripts/evidence.py --self-test

Fingerprint = git HEAD + working-tree diff + untracked files, excluding .sdlc/, the product layer and test output
(or, without git, every source file's path/size/mtime). Changing code after the run makes the evidence stale.
Exit: 0 ok · 1 not acceptable (reason printed) · 2 usage.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SKIP_DIRS = {".sdlc", ".git", "node_modules", "dist", "build", "out", ".next", ".venv", "venv", "__pycache__",
             "test-results", "playwright-report", "coverage", ".pytest_cache", ".turbo", ".cache", "target"}


# ----------------------------------------------------------------------------- project / fingerprint
def project_root(feature: Path) -> Path:
    for d in [feature.resolve(), *feature.resolve().parents]:
        if (d / "sdlc.config.yaml").is_file():
            return d
    return feature.resolve().parent.parent  # <root>/.sdlc/<feature>


def product_root(root: Path) -> str:
    try:
        m = re.search(r"^product_root:\s*([^\s#]+)", (root / "sdlc.config.yaml").read_text(), re.M)
        return m.group(1).strip("'\"") if m else "docs/product"
    except OSError:
        return "docs/product"


def fingerprint(feature: Path) -> str:
    root = project_root(feature)
    pr = product_root(root).strip("/")
    h = hashlib.sha256()
    git = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True)
    if git.returncode == 0:
        pathspec = ["--", ".", ":(exclude).sdlc", f":(exclude){pr}"] + [f":(exclude)**/{d}/**" for d in sorted(SKIP_DIRS - {'.git', '.sdlc'})]
        h.update(git.stdout.strip().encode())
        diff = subprocess.run(["git", "-C", str(root), "diff", "HEAD", "--binary", *pathspec], capture_output=True)
        h.update(diff.stdout)
        other = subprocess.run(["git", "-C", str(root), "ls-files", "-o", "--exclude-standard", "-z", *pathspec], capture_output=True)
        for rel in sorted(x for x in other.stdout.decode(errors="replace").split("\0") if x):
            p = root / rel
            if p.is_file():
                h.update(rel.encode() + b"\0" + hashlib.sha256(p.read_bytes()).digest())
        return "git:" + h.hexdigest()[:24]
    for dp, dn, fn in os.walk(root):
        rel_dir = os.path.relpath(dp, root)
        dn[:] = sorted(d for d in dn if d not in SKIP_DIRS and os.path.normpath(os.path.join(rel_dir, d)) != pr)
        for f in sorted(fn):
            p = os.path.join(dp, f)
            st = os.stat(p)
            h.update(f"{os.path.relpath(p, root)}\0{st.st_size}\0{st.st_mtime_ns}\n".encode())
    return "fs:" + h.hexdigest()[:24]


# ----------------------------------------------------------------------------- tiny YAML list reader
def _scalar(v: str) -> str:
    v = re.sub(r"\s+#.*$", "", v.strip())
    return v[1:-1] if len(v) >= 2 and v[0] in "\"'" and v[-1] == v[0] else v


def read_list(state_text: str, key: str) -> list[dict]:
    """Items of a top-level list (block or flow mappings). Enough for gates[] and open_questions[]."""
    m = re.search(rf"^{key}:[ \t]*(\[\])?[ \t]*$", state_text, re.M)
    if not m or m.group(1):
        return []
    items: list[dict] = []
    for line in state_text[m.end():].splitlines():
        if line.strip() == "" or line.lstrip().startswith("#"):
            continue
        if re.match(r"^\S", line):
            break
        im = re.match(r"^\s*-\s*(.*)$", line)
        if im:
            body = im.group(1).strip()
            items.append({})
            if body.startswith("{") and body.endswith("}"):
                for part in re.split(r",\s*(?=[\w-]+\s*:)", body[1:-1]):
                    if ":" in part:
                        k, _, v = part.partition(":")
                        items[-1][k.strip()] = _scalar(v)
                continue
            line = body
        km = re.match(r"^\s*([\w-]+)\s*:\s*(.*)$", line)
        if km and items:
            items[-1][km.group(1)] = _scalar(km.group(2))
    return items


# ----------------------------------------------------------------------------- commands
def cmd_run(feature: Path, name: str, argv: list[str]) -> int:
    if not argv:
        print("usage: evidence.py run --feature F --name N -- <command ...>", file=sys.stderr)
        return 2
    root = project_root(feature)
    out_dir = feature / "evidence" / "runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    log = out_dir / f"{name}-{stamp}.log"
    before = fingerprint(feature)
    started = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    with open(log, "wb") as fh:
        p = subprocess.run(argv, cwd=root, stdout=fh, stderr=subprocess.STDOUT)
    after = fingerprint(feature)
    rec = {"name": name, "command": argv, "cwd": str(root), "exit_code": p.returncode,
           "started": started, "finished": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
           "fingerprint": before, "fingerprint_after": after, "changed_during_run": before != after,
           "log": log.name}
    rj = out_dir / f"{name}-{stamp}.json"
    rj.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n")
    result = "pass" if p.returncode == 0 and before == after else "fail"
    rel = rj.relative_to(feature)
    print(f"{name}: exit {p.returncode}{' (source changed during the run)' if before != after else ''} → record in state.yaml gates:")
    print(f"  - {{name: {name}, kind: script, result: {result}, evidence: {rel}}}")
    return 0 if result == "pass" else 1


def check_gate(feature: Path, name: str) -> tuple[bool, str]:
    st = feature / "state.yaml"
    try:
        items = [g for g in read_list(st.read_text(encoding="utf-8"), "gates") if g.get("name") == name]
    except OSError:
        return False, f"{st} missing"
    if not items:
        return False, f"no gates[] record named {name}"
    last = items[-1]
    if last.get("result") != "pass":
        return False, f"the latest {name} record is result: {last.get('result') or 'null'} (an earlier pass does not count)"
    ev = last.get("evidence")
    if not ev:
        return False, (f"the latest {name} record says pass but has no evidence: — run it through "
                       f"python3 PLUGIN_ROOT/scripts/evidence.py run --feature <feature_dir> --name {name} -- <command>")
    p = (feature / ev).resolve()
    if not p.is_file() or not p.is_relative_to(feature.resolve()):
        return False, f"{name} evidence {ev} does not exist under the feature directory"
    try:
        rec = json.loads(p.read_text())
    except ValueError:
        return False, f"{ev} is not a run record"
    if rec.get("name") != name or rec.get("exit_code") != 0:
        return False, f"{ev}: run {rec.get('name')} exited {rec.get('exit_code')} — the record cannot say pass"
    if rec.get("changed_during_run"):
        return False, f"{ev}: source changed while the run was in progress — rerun"
    cur = fingerprint(feature)
    if rec.get("fingerprint") != cur:
        return False, f"{ev} is stale: the source changed after that run (recorded {rec.get('fingerprint')}, now {cur}) — rerun"
    return True, f"{name} evidence {ev} is current"


def check_conditional(feature: Path, who: str) -> tuple[bool, str]:
    qid = f"Q-ACCEPT-{who.upper()}"
    try:
        items = read_list((feature / "state.yaml").read_text(encoding="utf-8"), "open_questions")
    except OSError:
        items = []
    q = next((i for i in items if i.get("id") == qid), None)
    if not q:
        return False, f"有条件通过 needs open_questions {qid}: the user accepts the conditions in their own words (or sends the slice back)"
    if q.get("status") != "answered" or q.get("by") != "user" or not q.get("quote"):
        return False, f"{qid} must be status: answered, by: user, with the user's quote"
    return True, f"{qid} accepted by the user"


def self_test() -> int:
    def fail(msg, *x):
        print("self-test FAILED:", msg, *x); return 1
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "sdlc.config.yaml").write_text("product_root: docs/product\n")
        (root / "app.py").write_text("print('v1')\n")
        (root / "docs/product").mkdir(parents=True)
        feat = root / ".sdlc/f"
        feat.mkdir(parents=True)
        base = "feature: f\nsdlc_version: 4\nui: yes\n"
        if cmd_run(feat, "e2e", [sys.executable, "-c", "print('ok')"]) != 0:
            return fail("a passing run must return 0")
        rj = sorted((feat / "evidence/runs").glob("e2e-*.json"))[-1].relative_to(feat)
        (feat / "state.yaml").write_text(base + f"gates:\n  - {{name: e2e, kind: script, result: pass, evidence: {rj}}}\n")
        ok, why = check_gate(feat, "e2e")
        if not ok:
            return fail("a current passing run must satisfy the gate", why)
        (root / "docs/product/strategy.md").write_text("# edited\n")
        (feat / "notes.md").write_text("manager notes\n")
        if not check_gate(feat, "e2e")[0]:
            return fail("product docs and .sdlc edits must not make code evidence stale")
        (root / "app.py").write_text("print('v2')\n")
        ok, why = check_gate(feat, "e2e")
        if ok or "stale" not in why:
            return fail("changing code after the run must make it stale", why)
        (feat / "state.yaml").write_text(base + "gates:\n  - name: e2e\n    kind: script\n    result: pass\n")
        ok, why = check_gate(feat, "e2e")
        if ok or "no evidence" not in why:
            return fail("a self-reported pass without evidence must fail (C01)", why)
        (feat / "state.yaml").write_text(base + f"gates:\n  - {{name: e2e, result: pass, evidence: {rj}}}\n  - name: e2e\n    result: fail\n")
        ok, why = check_gate(feat, "e2e")
        if ok or "latest" not in why:
            return fail("an older pass must not outweigh the latest fail (P03)", why)
        if cmd_run(feat, "e2e", [sys.executable, "-c", "import sys; sys.exit(3)"]) != 1:
            return fail("a failing run must return 1")
        bad = sorted((feat / "evidence/runs").glob("e2e-*.json"))[-1].relative_to(feat)
        (feat / "state.yaml").write_text(base + f"gates:\n  - {{name: e2e, result: pass, evidence: {bad}}}\n")
        ok, why = check_gate(feat, "e2e")
        if ok or "exited 3" not in why:
            return fail("a pass pointing at a failed run must fail", why)
        # git mode: committed code + untracked source count, gitignored output does not
        subprocess.run(["git", "init", "-q"], cwd=root)
        (root / ".gitignore").write_text("test-results/\n")
        subprocess.run(["git", "add", "-A"], cwd=root)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "c"], cwd=root)
        if not fingerprint(feat).startswith("git:"):
            return fail("a git project must use the git fingerprint")
        cmd_run(feat, "e2e", [sys.executable, "-c", "import os; os.makedirs('test-results', exist_ok=True); open('test-results/r.txt','w').write('x')"])
        gj = sorted((feat / "evidence/runs").glob("e2e-*.json"))[-1]
        if json.loads(gj.read_text())["changed_during_run"]:
            return fail("ignored test output written by the run must not count as a source change")
        (feat / "state.yaml").write_text(base + f"gates:\n  - {{name: e2e, result: pass, evidence: {gj.relative_to(feat)}}}\n")
        (root / "new_module.py").write_text("x = 1\n")
        if check_gate(feat, "e2e")[0]:
            return fail("a new untracked source file after the run must make it stale")
        (feat / "state.yaml").write_text(base + "open_questions:\n  - id: Q-ACCEPT-PM\n    status: answered\n    by: user\n    quote: \"同意，下个迭代补空状态\"\n")
        if not check_conditional(feat, "pm")[0] or check_conditional(feat, "design")[0]:
            return fail("conditional acceptance must need the user's recorded answer")
    print("self-test ok")
    return 0


def main() -> int:
    argv = sys.argv[1:]
    cmd_args = []
    if "--" in argv:
        i = argv.index("--")
        argv, cmd_args = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", choices=["run", "gate", "fingerprint", "conditional"])
    ap.add_argument("--feature")
    ap.add_argument("--name", default="e2e")
    ap.add_argument("--who")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if not a.command or not a.feature or not Path(a.feature).is_dir():
        ap.print_usage(sys.stderr)
        return 2
    feat = Path(a.feature)
    if a.command == "run":
        return cmd_run(feat, a.name, cmd_args)
    if a.command == "fingerprint":
        print(fingerprint(feat))
        return 0
    if a.command == "conditional":
        ok, why = check_conditional(feat, a.who or "")
    else:
        ok, why = check_gate(feat, a.name)
    print(("✓ " if ok else "✗ ") + why)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""vendor/install.sh 的离线测试：本地 git 仓库充当上游（file://），不联网。

  python3 scripts/test_vendor_install.py
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "vendor/install.sh"


def sh(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def digest(files: dict[str, bytes]) -> str:
    h = hashlib.sha256()
    for rel in sorted(files):
        h.update(f"{rel}\0{hashlib.sha256(files[rel]).hexdigest()}\n".encode())
    return h.hexdigest()


class Env:
    def __init__(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vendor-install-"))
        self.vendor = self.tmp / "plugin/vendor"
        self.vendor.mkdir(parents=True)
        shutil.copy2(INSTALL, self.vendor / "install.sh")

    def upstream(self, name: str, files: dict[str, str], extra: dict[str, str] | None = None) -> str:
        r = self.tmp / "up" / name
        r.mkdir(parents=True)
        sh(["git", "init", "-q", "-b", "main"], r)
        for rel, text in {**files, **(extra or {})}.items():
            (r / rel).parent.mkdir(parents=True, exist_ok=True)
            (r / rel).write_text(text)
        sh(["git", "add", "-A"], r)
        sh(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "c"], r)
        sh(["git", "config", "uploadpack.allowAnySHA1InWant", "true"], r)
        return sh(["git", "rev-parse", "HEAD"], r).stdout.strip()

    def lock(self, name: str, files: dict[str, str], include: str, commit: str, license_: str, runtime=(), digest_override=None):
        data = {"source": name, "url": f"file://{self.tmp / 'up' / name}", "commit": commit, "license": license_,
                "included_paths": include.split(),
                "tree_digest": digest_override or digest({k: v.encode() for k, v in files.items()}),
                "files": [{"path": k, "sha256": hashlib.sha256(v.encode()).hexdigest(),
                           "purpose": "runtime" if k in runtime else "maintainer"} for k, v in files.items()]}
        (self.vendor / f"{name}.lock.json").write_text(json.dumps(data))

    def run(self, *args):
        p = sh(["bash", str(self.vendor / "install.sh"), *args], self.tmp)
        return p.returncode, p.stdout + p.stderr

    def cleanup(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


FILES = {"LICENSE": "MIT\n", "docs/a.md": "# a\n", "docs/b.mdx": "# b\n"}


def case_install_and_check(e):
    c = e.upstream("s", FILES, extra={"other/x.sh": "echo no\n"})
    e.lock("s", FILES, "LICENSE docs", c, "MIT")
    rc, out = e.run()
    assert rc == 0 and "已安装并校验" in out, out
    got = sorted(p.relative_to(e.vendor / "s").as_posix() for p in (e.vendor / "s").rglob("*") if p.is_file())
    assert got == sorted(FILES), got  # INCLUDE 之外的上游文件不落盘
    rc, out = e.run("--check")
    assert rc == 0 and "与锁文件一致" in out, out
    rc, out = e.run()
    assert rc == 0 and "已是锁定版本" in out, out


def case_digest_mismatch(e):
    c = e.upstream("s", FILES)
    e.lock("s", FILES, "LICENSE docs", c, "MIT", digest_override="0" * 64)
    rc, out = e.run()
    assert rc == 1 and "不一致" in out and not (e.vendor / "s").exists(), out


def case_local_edit(e):
    c = e.upstream("s", FILES)
    e.lock("s", FILES, "LICENSE docs", c, "MIT")
    assert e.run()[0] == 0
    (e.vendor / "s/docs/a.md").write_text("edited\n")
    rc, out = e.run()
    assert rc == 1 and "未覆盖" in out and (e.vendor / "s/docs/a.md").read_text() == "edited\n", out
    rc, out = e.run("--check")
    assert rc == 1 and "不一致" in out, out
    rc, out = e.run("--force")
    assert rc == 0 and (e.vendor / "s/docs/a.md").read_text() == "# a\n", out


def case_restricted(e):
    c = e.upstream("r", FILES)
    e.lock("r", FILES, "LICENSE docs", c, "All rights reserved")
    rc, out = e.run()
    assert rc == 0 and "默认不下载" in out and not (e.vendor / "r").exists(), out
    rc, out = e.run("--check")
    assert rc == 0 and "可选" in out, out
    rc, out = e.run("--accept-restricted")
    assert rc == 0 and (e.vendor / "r/docs/a.md").exists(), out


def case_missing_required(e):
    c = e.upstream("s", FILES)
    e.lock("s", FILES, "LICENSE docs", c, "Apache-2.0", runtime=("docs/a.md",))
    rc, out = e.run("--check")
    assert rc == 1 and "未安装" in out, out


def case_fetch_failure(e):
    e.lock("s", FILES, "LICENSE docs", "0" * 40, "MIT")
    rc, out = e.run()
    assert rc == 1 and "下载失败" in out and not (e.vendor / "s").exists(), out


def case_only_named(e):
    c1 = e.upstream("a", FILES)
    c2 = e.upstream("b", FILES)
    e.lock("a", FILES, "LICENSE docs", c1, "MIT")
    e.lock("b", FILES, "LICENSE docs", c2, "MIT")
    rc, out = e.run("b")
    assert rc == 0 and (e.vendor / "b").exists() and not (e.vendor / "a").exists(), out


CASES = {k[5:]: v for k, v in dict(globals()).items() if k.startswith("case_")}


def main() -> int:
    failed = 0
    for name, fn in CASES.items():
        e = Env()
        try:
            fn(e)
            print(f"ok   {name}")
        except Exception as ex:  # noqa: BLE001
            failed += 1
            print(f"FAIL {name}: {ex}")
        finally:
            e.cleanup()
    print("vendor install tests: " + ("all passed" if not failed else f"{failed} failed"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Imagery gate: every generated image is bound to its prompt, its evidence and the artifact that declares it.

  python3 scripts/image/check.py --root <feature_dir> [<image> ...]   # no paths → every generated image under root
  python3 scripts/image/check.py --self-test

Pass = all of: the file has an evidence record written by scripts/image/generate.py · the recorded digest still
matches the file · the bytes really are png/jpeg/webp · the kind is known and matches where the file lives
(ref → assets/refs/, product material → assets/generated/) · purpose is a real sentence · the declaring artifact
exists, its digest still matches (edit it and the image is stale) and it actually references the file · the prompt
is on record and unmodified · no credential-shaped string leaked into the evidence.

Nobody writes these evidence files by hand. A missing record means the image did not come from the tool, and an
image nobody can trace to a prompt is not evidence of anything — it is an unattributed asset in a product.

Exit: 0 pass · 1 violations · 2 usage or nothing to check that was asked for.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate import (IMAGE_SUFFIXES, KIND_DIR, KINDS, REF_KIND,  # noqa: E402  one definition per capability
                      image_format, sha, sha_file)

LEAKS = [
    (re.compile(r"\bxai-[A-Za-z0-9_-]{16,}"), "an xAI API key"),
    (re.compile(r'"(?:access|refresh|device)_token"'), "a token field"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}"), "a JWT"),
    (re.compile(r"\bBearer\s+[A-Za-z0-9._-]{16,}"), "a bearer header"),
]
OK, FAIL, USAGE = 0, 1, 2


def collect(root: Path) -> list[Path]:
    found: list[Path] = []
    for pattern in ("*/assets/refs/*", "*/assets/generated/*", "assets/refs/*", "assets/generated/*"):
        for path in sorted(root.glob(pattern)):
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
                found.append(path)
    return found


def load_evidence(root: Path) -> tuple[dict[str, dict], list[str]]:
    """Map each recorded file path → (record, file entry). Duplicate claims on one file are a violation."""
    index: dict[str, dict] = {}
    problems: list[str] = []
    directory = root / "evidence" / "images"
    if not directory.is_dir():
        return index, problems
    for evidence_file in sorted(directory.glob("*.json")):
        try:
            record = json.loads(evidence_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            problems.append(f"✗ [IMAGE-EVIDENCE] {evidence_file.name}: 不是合法 JSON（证据文件由工具写，不要手改）")
            continue
        text = evidence_file.read_text(encoding="utf-8")
        for pattern, what in LEAKS:
            if pattern.search(text):
                problems.append(f"✗ [IMAGE-LEAK] {evidence_file.name}: 证据里出现了{what}，凭据不得进工件")
        for entry in record.get("files") or []:
            path = entry.get("path")
            if not path:
                continue
            if path in index:
                problems.append(f"✗ [IMAGE-EVIDENCE] {path}: 有两份证据同时声明它"
                                f"（{index[path]['evidence']} 与 {evidence_file.name}）")
                continue
            index[path] = {"record": record, "entry": entry, "evidence": evidence_file.name}
    return index, problems


def check(root: Path, files: list[Path]) -> tuple[int, list[str]]:
    out: list[str] = []

    def bad(tag: str, message: str) -> None:
        out.append(f"✗ [IMAGE-{tag}] {message}")

    root = root.resolve()
    if not root.is_dir():
        return USAGE, [f"✗ [IMAGE-USAGE] --root 不是目录：{root}"]
    index, problems = load_evidence(root)
    out.extend(problems)

    for path in files:
        path = path.resolve()
        if not path.is_file() or path.stat().st_size == 0:
            bad("SOURCE", f"{path}: 不存在或是空文件")
            continue
        if not path.is_relative_to(root):
            bad("SOURCE", f"{path}: 在 {root} 之外")
            continue
        relative = os.path.relpath(path, root)
        blob = path.read_bytes()
        if image_format(blob) is None:
            bad("FORMAT", f"{relative}: 不是 png/jpeg/webp（后缀骗不过字节）")
        claim = index.get(relative)
        if claim is None:
            bad("NOEVID", f"{relative}: 没有 evidence/images/*.json 声明它"
                          "（图必须由 scripts/image/generate.py 生成；手放进来的图无法追溯提示词与模型）")
            continue
        record, entry = claim["record"], claim["entry"]
        if entry.get("sha256") != sha(blob):
            bad("DIGEST", f"{relative}: 与 {claim['evidence']} 记录的 digest 不一致"
                          "（图被改过或被替换：重新生成，或重新走一次生成流程）")
        kind = record.get("kind")
        if kind not in KINDS:
            bad("KIND", f"{relative}: 证据里的 kind={kind!r} 不在 {', '.join(KINDS)}")
        else:
            expected = KIND_DIR[kind]
            if os.path.dirname(relative).replace(os.sep, "/") != expected:
                bad("KIND", f"{relative}: kind={kind} 应落在 {expected}/"
                            f"（{REF_KIND} 是方向参考，其余是进产品的素材，两者不混放）")
        purpose = (record.get("purpose") or "").strip()
        if len(purpose) < 8:
            bad("PURPOSE", f"{relative}: 证据里缺 purpose（这张图承担什么信息，一句话）")
        prompt = record.get("prompt") or ""
        if not prompt.strip():
            bad("PROMPT", f"{relative}: 证据里没有提示词原文（审查者要能判断提示词本身）")
        elif record.get("prompt_sha256") and sha(prompt.encode()) != record["prompt_sha256"]:
            bad("PROMPT", f"{relative}: 提示词与其 digest 不一致（证据被手改过）")
        declared = record.get("declared_in") or {}
        declared_rel = declared.get("path")
        if not declared_rel:
            bad("DECLARED", f"{relative}: 证据里没有声明源（哪份工件用这张图）")
            continue
        source = (root / declared_rel).resolve()
        if not source.is_file():
            bad("DECLARED", f"{relative}: 声明源 {declared_rel} 不存在")
            continue
        if sha_file(source) != declared.get("sha256"):
            bad("STALE", f"{relative}: 声明源 {declared_rel} 在生成之后改过（图已 stale）"
                         "——确认这张图仍然对，然后重新生成或重新声明")
        text = source.read_text(encoding="utf-8", errors="replace")
        basename = os.path.basename(relative)
        if basename not in text and relative not in text:
            bad("DECLARED", f"{relative}: {declared_rel} 并没有引用它"
                            "（生成了但没人用的图不算工件；引用时标注 AI 生成）")
    return (OK if not out else FAIL), out


def _self_test() -> int:
    import io
    import struct
    import tempfile
    import unittest

    png = (b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 8, 8)
           + b"\x08\x06\x00\x00\x00" + b"\x00" * 16)

    class Tests(unittest.TestCase):
        def setUp(self):
            self.temp = tempfile.TemporaryDirectory()
            self.addCleanup(self.temp.cleanup)
            self.root = Path(self.temp.name) / ".sdlc" / "feat"
            (self.root / "02-shape/assets/generated").mkdir(parents=True)
            (self.root / "evidence/images").mkdir(parents=True)
            self.asset = self.root / "02-shape/assets/generated/empty-orders.png"
            self.asset.write_bytes(png)
            self.declared = self.root / "02-shape/design-directions.md"
            self.declared.write_text("# 方向\n\n![空态（AI 生成）](assets/generated/empty-orders.png)\n",
                                     encoding="utf-8")
            self.write_evidence()

        def write_evidence(self, **over):
            prompt = "a calm empty-state illustration, flat vector, one accent colour"
            record = {
                "name": "empty-orders", "kind": "empty-state",
                "purpose": "订单空态：说明还没有数据以及下一步",
                "declared_in": {"path": "02-shape/design-directions.md", "sha256": sha_file(self.declared)},
                "prompt": prompt, "prompt_sha256": sha(prompt.encode()),
                "files": [{"path": "02-shape/assets/generated/empty-orders.png",
                           "sha256": sha(self.asset.read_bytes()), "bytes": len(png), "format": "png"}],
            }
            record.update(over)
            (self.root / "evidence/images/empty-orders.json").write_text(
                json.dumps(record, ensure_ascii=False), encoding="utf-8")

        def run_check(self):
            return check(self.root, collect(self.root))

        def test_pass(self):
            code, out = self.run_check()
            self.assertEqual((code, out), (OK, []))

        def test_image_without_evidence_fails(self):
            (self.root / "02-shape/assets/generated/stray.png").write_bytes(png)
            code, out = self.run_check()
            self.assertEqual(code, FAIL)
            self.assertTrue(any("IMAGE-NOEVID" in line for line in out))

        def test_changed_image_fails(self):
            self.asset.write_bytes(png + b"\x00")
            code, out = self.run_check()
            self.assertTrue(any("IMAGE-DIGEST" in line for line in out), out)

        def test_edited_declaring_artifact_is_stale(self):
            self.declared.write_text(self.declared.read_text() + "\n改了一行\n", encoding="utf-8")
            code, out = self.run_check()
            self.assertTrue(any("IMAGE-STALE" in line for line in out), out)

        def test_unreferenced_image_fails(self):
            self.declared.write_text("# 方向\n\n选定：D1\n", encoding="utf-8")
            self.write_evidence()                       # re-record so only the reference is missing
            code, out = self.run_check()
            self.assertTrue(any("IMAGE-DECLARED" in line for line in out), out)

        def test_kind_must_match_directory(self):
            self.write_evidence(kind="ref")
            code, out = self.run_check()
            self.assertTrue(any("IMAGE-KIND" in line for line in out), out)

        def test_not_really_an_image(self):
            self.asset.write_bytes(b"<html>not an image</html>")
            self.write_evidence()
            code, out = self.run_check()
            self.assertTrue(any("IMAGE-FORMAT" in line for line in out), out)

        def test_thin_purpose_fails(self):
            self.write_evidence(purpose="图")
            code, out = self.run_check()
            self.assertTrue(any("IMAGE-PURPOSE" in line for line in out), out)

        def test_hand_edited_prompt_fails(self):
            self.write_evidence(prompt="something else entirely, rewritten by hand")
            code, out = self.run_check()
            self.assertTrue(any("IMAGE-PROMPT" in line for line in out), out)

        def test_credential_in_evidence_fails(self):
            self.write_evidence(note="Bearer abcdefghijklmnopqrstuvwxyz123456")
            code, out = self.run_check()
            self.assertTrue(any("IMAGE-LEAK" in line for line in out), out)

        def test_empty_feature_passes(self):
            self.asset.unlink()
            (self.root / "evidence/images/empty-orders.json").unlink()
            self.assertEqual(check(self.root, collect(self.root)), (OK, []))

    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.TestLoader().loadTestsFromTestCase(Tests))
    sys.stdout.write(stream.getvalue())
    print("image check self-test: ok" if result.wasSuccessful() else "image check self-test: FAILED")
    return OK if result.wasSuccessful() else FAIL


def main() -> int:
    parser = argparse.ArgumentParser(description="生成图闸门：图 ↔ 证据 ↔ 声明源")
    parser.add_argument("--root", help="feature 目录")
    parser.add_argument("files", nargs="*", help="要检查的图；省略则检查 root 下全部生成图")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return _self_test()
    if not args.root:
        parser.error("需要 --root")
    root = Path(args.root)
    targets = [Path(f) for f in args.files] if args.files else collect(root.resolve())
    if args.files and not targets:
        print("✗ [IMAGE-USAGE] 给了空的文件列表（空列表不算通过）", file=sys.stderr)
        return USAGE
    code, out = check(root, targets)
    for line in out:
        print(line)
    if code == OK:
        print(f"生成图检查通过：{len(targets)} 张（图 ↔ 提示词 ↔ 声明源 digest 均一致）"
              if targets else "没有生成图，跳过（这不是缺陷）")
    return code


if __name__ == "__main__":
    sys.exit(main())

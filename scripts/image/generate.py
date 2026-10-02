#!/usr/bin/env python3
"""Generate a bitmap asset with Grok (xAI) and leave evidence nobody could have written by hand.

  python3 scripts/image/generate.py --root <feature_dir> --kind ref|illustration|empty-state|hero|icon \
      --name <slug> --purpose "<one line: what information this image carries>" \
      --declared-in 02-shape/design-directions.md --prompt-file <path> \
      [--aspect 16:9] [--resolution 1k|2k] [--n 1] [--model …] [--config <sdlc.config.yaml>]

  python3 scripts/image/generate.py --probe        # is this account allowed to generate at all? (one cheap image)
  python3 scripts/image/generate.py --self-test    # offline, fake transport

Where images land, and what they are allowed to be, is decided by --kind:
  ref                                  → <root>/02-shape/assets/refs/      a visual-language probe for design
                                         exploration. NOT a design direction: a direction is prototype code.
  illustration|empty-state|hero|icon   → <root>/02-shape/assets/generated/  material that ships inside the product.
Neither may stand in for a rendered prototype or a walkthrough screenshot; check-sdlc.sh ignores both when it
demands real shots, and scripts/image/check.py binds every file to its prompt and to the artifact that declares it.

Evidence: <root>/evidence/images/<name>.json — the prompt verbatim, model, parameters, request id, the digest of
every file and of the declaring artifact. Change the declaring artifact later and check.py calls the image stale.
Ledger: <root>/evidence/images/ledger.jsonl — one line per call, so the quota this feature burned is visible and
`imagery.budget.max_per_feature` can stop it. No token or credential ever reaches either file.

Authorization comes from scripts/grok/auth.py (your Grok subscription, or XAI_API_KEY as the fallback tier gating
may force). Exit codes: 0 ok · 1 failure · 2 usage/config · 3 not authorized (or the tier is not allowed).
"""
from __future__ import annotations

import argparse
import base64
import binascii
import datetime
import hashlib
import json
import os
import re
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "grok"))
import auth  # noqa: E402  scripts/grok/auth.py — the only place credentials live
from check_config import parse_yaml  # noqa: E402  reuse the project's YAML reader, no new parser

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
REF_KIND = "ref"
KINDS = ("ref", "illustration", "empty-state", "hero", "icon")
KIND_DIR = {"ref": "02-shape/assets/refs", "illustration": "02-shape/assets/generated",
            "empty-state": "02-shape/assets/generated", "hero": "02-shape/assets/generated",
            "icon": "02-shape/assets/generated"}
ASPECTS = ("1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "2:1", "1:2",
           "19.5:9", "9:19.5", "20:9", "9:20", "21:9", "5:2", "auto")
RESOLUTIONS = ("1k", "2k")
QUALITIES = ("low", "medium", "auto")
DEFAULT_MODEL = "grok-imagine-image-2.0"
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,48}$")
MAGIC = {b"\x89PNG\r\n\x1a\n": "png", b"\xff\xd8\xff": "jpeg", b"RIFF": "webp"}
EXT = {"png": ".png", "jpeg": ".jpg", "webp": ".webp"}
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")
TOOL = "scripts/image/generate.py"
TOOL_VERSION = 1

OK, FAIL, USAGE, UNAUTHORIZED = 0, 1, 2, 3

# Tests inject a callable: TRANSPORT(url, body: dict, headers: dict) -> (status, dict, request_id)
TRANSPORT = None


class ImageError(Exception):
    def __init__(self, message: str, code: int = FAIL):
        super().__init__(message)
        self.code = code


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha(path.read_bytes())


def project_root(start: Path) -> Path | None:
    for directory in [start, *start.parents]:
        if (directory / "sdlc.config.yaml").is_file():
            return directory
    return None


# ---------- config ----------

DEFAULTS = {
    "enabled": False,
    "provider": "grok",
    "model": None,
    "auth": "auto",
    "allowed_kinds": list(KINDS),
    "defaults": {"aspect_ratio": "16:9", "resolution": "1k", "quality": "auto"},
    "budget": {"max_per_feature": 20},
}


def registry_default_model() -> str:
    try:
        registry = json.loads((PLUGIN_ROOT / "workflow/registry.json").read_text(encoding="utf-8"))
        return registry.get("imagery", {}).get("model_default") or DEFAULT_MODEL
    except (OSError, ValueError):
        return DEFAULT_MODEL


def load_settings(root: Path | None, explicit: str | None) -> tuple[dict, Path | None]:
    """imagery: from the project's sdlc.config.yaml. Missing file → defaults (and therefore disabled)."""
    path = Path(explicit).resolve() if explicit else None
    if path is None and root is not None:
        found = project_root(root.resolve())
        path = (found / "sdlc.config.yaml") if found else None
    settings = json.loads(json.dumps(DEFAULTS))
    if path and path.is_file():
        block = parse_yaml(path.read_text(encoding="utf-8")).get("imagery")
        if isinstance(block, dict):
            for key, value in block.items():
                if isinstance(value, dict) and isinstance(settings.get(key), dict):
                    settings[key].update(value)
                else:
                    settings[key] = value
    for section in ("defaults", "budget"):
        # The project's YAML reader does not expand inline {a: b}; a mis-written section must not silently
        # become a string and take the budget cap with it.
        if not isinstance(settings.get(section), dict):
            settings[section] = dict(DEFAULTS[section])
            settings.setdefault("_warnings", []).append(
                f"imagery.{section} 不是块式映射（本文件的 YAML 读法不认行内字典），已用默认值")
    settings["model"] = settings.get("model") or registry_default_model()
    return settings, path


# ---------- image bytes ----------

def image_format(data: bytes) -> str | None:
    for magic, name in MAGIC.items():
        if data.startswith(magic):
            return name
    return None


def png_size(data: bytes) -> tuple[int, int] | None:
    if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) < 24 or data[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", data[16:24])
    return width, height


# ---------- api ----------

def _post_images(bearer: str, body: dict, base: str | None = None, timeout: int = 180) -> tuple[int, dict, str]:
    url = (base or auth.API_BASE).rstrip("/") + "/images/generations"
    headers = {"Authorization": f"Bearer {bearer}", "Content-Type": "application/json",
               "Accept": "application/json", "User-Agent": "sdlc-workflow/image"}
    if TRANSPORT is not None:
        return TRANSPORT(url, body, headers)
    import urllib.error
    import urllib.request
    request = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            request_id = response.headers.get("x-request-id") or response.headers.get("x-amzn-requestid") or ""
            return response.status, (json.loads(raw) if raw else {}), request_id
    except urllib.error.HTTPError as error:
        raw = error.read()
        try:
            payload = json.loads(raw) if raw else {}
        except ValueError:
            payload = {"error": raw[:300].decode("utf-8", "replace")}
        return error.code, payload, error.headers.get("x-request-id") or ""
    except urllib.error.URLError as error:
        raise ImageError(f"无法连接 api.x.ai：{error.reason}", FAIL) from error


def _api_message(payload: dict) -> str:
    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or error.get("code") or error)
    return str(error or payload.get("message") or payload)[:300]


def call_api(body: dict, mode: str) -> tuple[dict, str, str]:
    """One call, with the two recoveries that matter: a stale access token, and a tier that is not allowed."""
    bearer, auth_mode = auth.get_bearer(mode)
    status, payload, request_id = _post_images(bearer, body)
    if status == 401 and auth_mode == "oauth":
        bearer, auth_mode = auth.force_refresh()
        status, payload, request_id = _post_images(bearer, body)
    if status == 403:
        raise ImageError(
            "xAI 拒绝了这次调用（403）。你的订阅档位可能没开放 OAuth API 面（社区报告一度只对 "
            "SuperGrok Heavy 开）。两条出路：① 在 xAI 控制台拿 API key，设 XAI_API_KEY 并把 "
            "sdlc.config.yaml 的 imagery.auth 改成 api-key；② 升级订阅档位。"
            f"（xAI 原话：{_api_message(payload)}）", UNAUTHORIZED)
    if status == 429:
        raise ImageError(f"被限流（429），稍后再试：{_api_message(payload)}", FAIL)
    if status == 401:
        raise ImageError("授权无效（401）：重新跑 `/sdlc-grok login`，或检查 XAI_API_KEY", UNAUTHORIZED)
    if status != 200:
        raise ImageError(f"出图失败（HTTP {status}）：{_api_message(payload)}", FAIL)
    images = payload.get("data")
    if not isinstance(images, list) or not images:
        raise ImageError("xAI 返回里没有图片数据", FAIL)
    return payload, auth_mode, request_id


# ---------- ledger ----------

def ledger_path(root: Path) -> Path:
    return root / "evidence" / "images" / "ledger.jsonl"


def ledger_spend(root: Path) -> int:
    path = ledger_path(root)
    if not path.is_file():
        return 0
    total = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            total += int(json.loads(line).get("n") or 0)
        except ValueError:
            continue
    return total


def ledger_append(root: Path, row: dict) -> None:
    path = ledger_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


# ---------- generate ----------

def generate(args) -> tuple[int, list[str]]:
    lines: list[str] = []
    root = Path(args.root).resolve()
    if not root.is_dir():
        raise ImageError(f"--root 不是目录：{root}", USAGE)
    if args.kind not in KINDS:
        raise ImageError(f"--kind 必须是 {', '.join(KINDS)}", USAGE)
    if not NAME_RE.match(args.name or ""):
        raise ImageError("--name 用小写字母数字与连字符（2-49 字符）", USAGE)
    purpose = (args.purpose or "").strip()
    if len(purpose) < 8:
        raise ImageError("--purpose 要写一句话：这张图承担什么信息（空话过不了 check.py）", USAGE)

    settings, config_path = load_settings(root, args.config)
    if not settings.get("enabled"):
        where = config_path or "<project>/sdlc.config.yaml"
        raise ImageError(f"出图能力默认关闭。要用就在 {where} 里把 imagery.enabled 设为 true"
                         "（它会消耗你的 Grok 订阅额度）。", USAGE)
    for warning in settings.get("_warnings") or []:
        print(f"配置告警：{warning}", file=sys.stderr)
    allowed = settings.get("allowed_kinds") or list(KINDS)
    if args.kind not in allowed:
        raise ImageError(f"kind {args.kind} 不在项目允许的 imagery.allowed_kinds={allowed}", USAGE)

    declared_rel = args.declared_in
    declared = (root / declared_rel).resolve()
    if not declared.is_file():
        raise ImageError(f"--declared-in 不存在：{declared}（图必须由一份工件声明并引用）", USAGE)
    if not declared.is_relative_to(root):
        raise ImageError(f"--declared-in 必须在 {root} 之内", USAGE)

    prompt_path = Path(args.prompt_file).resolve()
    if not prompt_path.is_file():
        raise ImageError(f"--prompt-file 不存在：{prompt_path}", USAGE)
    prompt = prompt_path.read_text(encoding="utf-8").strip()
    if len(prompt) < 12:
        raise ImageError("提示词太短：写清内容、构图、风格锚点与禁止项", USAGE)

    count = int(args.n or 1)
    if not 1 <= count <= 10:
        raise ImageError("--n 取 1..10", USAGE)
    budget = int((settings.get("budget") or {}).get("max_per_feature") or 0)
    spent = ledger_spend(root)
    if budget and spent + count > budget:
        raise ImageError(f"超预算：本功能已生成 {spent} 张，上限 imagery.budget.max_per_feature={budget}"
                         f"（本次要 {count} 张）。要么复用已有的，要么由人调高上限。", FAIL)

    defaults = settings.get("defaults") or {}
    aspect = args.aspect or defaults.get("aspect_ratio") or "16:9"
    resolution = args.resolution or defaults.get("resolution") or "1k"
    quality = args.quality or defaults.get("quality") or "auto"
    if aspect not in ASPECTS:
        raise ImageError(f"--aspect 必须是 {', '.join(ASPECTS)}", USAGE)
    if resolution not in RESOLUTIONS:
        raise ImageError(f"--resolution 必须是 {', '.join(RESOLUTIONS)}", USAGE)
    if quality not in QUALITIES:
        raise ImageError(f"--quality 必须是 {', '.join(QUALITIES)}", USAGE)

    model = args.model or settings.get("model") or registry_default_model()
    body = {"model": model, "prompt": prompt, "n": count, "aspect_ratio": aspect,
            "resolution": resolution, "quality": quality, "response_format": "b64_json"}
    payload, auth_mode, request_id = call_api(body, settings.get("auth") or "auto")

    out_dir = root / KIND_DIR[args.kind]
    out_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for index, item in enumerate(payload["data"], start=1):
        encoded = item.get("b64_json")
        if not encoded:
            raise ImageError("xAI 返回的条目里没有 b64_json（response_format 被忽略？）", FAIL)
        try:
            blob = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as error:
            raise ImageError(f"第 {index} 张图的 base64 解不开：{error}", FAIL) from error
        fmt = image_format(blob)
        if fmt is None:
            raise ImageError(f"第 {index} 张图不是 png/jpeg/webp，拒绝落盘", FAIL)
        name = f"{args.name}-{index}" if count > 1 else args.name
        target = out_dir / (name + EXT[fmt])
        target.write_bytes(blob)
        record = {"path": os.path.relpath(target, root), "sha256": sha(blob), "bytes": len(blob), "format": fmt}
        size = png_size(blob)
        if size:
            record["width"], record["height"] = size
        if item.get("revised_prompt"):
            record["revised_prompt"] = item["revised_prompt"]
        files.append(record)
        lines.append(f"生成：{record['path']}（{fmt}, {len(blob)//1024} KB）")

    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    evidence = {
        "name": args.name, "kind": args.kind, "purpose": purpose,
        "declared_in": {"path": os.path.relpath(declared, root), "sha256": sha_file(declared)},
        "prompt": prompt, "prompt_sha256": sha(prompt.encode()), "prompt_file": os.path.relpath(prompt_path, root)
        if prompt_path.is_relative_to(root) else str(prompt_path),
        "provider": settings.get("provider") or "grok", "model": model,
        "params": {"aspect_ratio": aspect, "resolution": resolution, "quality": quality,
                   "n": count, "response_format": "b64_json"},
        "request_id": request_id, "auth_mode": auth_mode, "files": files,
        "created_at": now, "tool": TOOL, "tool_version": TOOL_VERSION,
    }
    evidence_dir = root / "evidence" / "images"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_file = evidence_dir / f"{args.name}.json"
    evidence_file.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")
    ledger_append(root, {"at": now, "name": args.name, "kind": args.kind, "model": model, "n": count,
                         "resolution": resolution, "aspect_ratio": aspect, "auth_mode": auth_mode,
                         "request_id": request_id, "files": [f["path"] for f in files]})
    lines.append(f"证据：{os.path.relpath(evidence_file, root)}（提示词原文 + digest；没人手写这个文件）")
    lines.append(f"下一步：在 {evidence['declared_in']['path']} 里引用这张图并标注 AI 生成，"
                 f"然后 python3 {TOOL.replace('generate', 'check')} --root {root}")
    if args.kind == REF_KIND:
        lines.append("提醒：参考图不是设计方向。方向要落成原型代码，闸门只认原型渲染。")
    return OK, lines


# ---------- probe ----------

def probe(args) -> tuple[int, list[str]]:
    lines: list[str] = []
    report = auth.status_report()
    settings, _path = load_settings(Path(args.root).resolve() if args.root else None, args.config)
    mode = settings.get("auth") or "auto"
    lines = [f"授权状态：{report['state']}（auth_mode={report.get('auth_mode')}）｜配置模式 {mode}"]
    if report["state"] == "logged_out" and not report["api_key_env"]:
        lines.append("未授权：先跑 `/sdlc-grok login`。")
        return UNAUTHORIZED, lines
    model = args.model or settings.get("model") or registry_default_model()
    body = {"model": model, "prompt": "a plain flat neutral grey square, no text, no logo",
            "n": 1, "aspect_ratio": "1:1", "resolution": "1k", "quality": "low", "response_format": "b64_json"}
    started = time.time()
    payload, auth_mode, request_id = call_api(body, mode)
    blob = base64.b64decode(payload["data"][0].get("b64_json") or "", validate=False)
    fmt = image_format(blob) or "?"
    result = {"at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "ok": True,
              "model": model, "auth_mode": auth_mode, "request_id": request_id,
              "format": fmt, "bytes": len(blob), "seconds": round(time.time() - started, 1)}
    try:
        cache = Path(auth.probe_cache_path())
        cache.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        cache.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        lines.append(f"结果缓存：{cache}")
    except OSError:
        pass
    lines.append(f"可以出图：{model} 返回 {fmt} {len(blob)//1024} KB，用的是 {auth_mode}"
                 f"（{result['seconds']}s，request {request_id or '—'}）。探针图未落盘。")
    return OK, lines


# ---------- self-test（离线） ----------

def _self_test() -> int:
    import io
    import tempfile
    import unittest

    one_png = (b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 8, 8)
               + b"\x08\x06\x00\x00\x00" + b"\x00" * 16)

    def fake_ok(url, body, headers):
        fake_ok.seen = {"url": url, "body": body, "auth": headers.get("Authorization", "")}
        return 200, {"data": [{"b64_json": base64.b64encode(one_png).decode()} for _ in range(int(body["n"]))]}, "req-1"

    def fake_403(url, body, headers):
        return 403, {"error": {"message": "subscription tier not allowed"}}, "req-2"

    class Tests(unittest.TestCase):
        def setUp(self):
            global TRANSPORT
            TRANSPORT = fake_ok
            self.addCleanup(self._reset)
            self.temp = tempfile.TemporaryDirectory()
            self.addCleanup(self.temp.cleanup)
            self.project = Path(self.temp.name)
            (self.project / "sdlc.config.yaml").write_text(
                "product_root: docs/product\nimagery:\n  enabled: true\n  budget:\n    max_per_feature: 3\n",
                encoding="utf-8")
            self.root = self.project / ".sdlc" / "feat"
            (self.root / "02-shape").mkdir(parents=True)
            self.declared = self.root / "02-shape" / "design-directions.md"
            self.declared.write_text("# 方向\n\n选定：D1\n", encoding="utf-8")
            self.prompt = self.root / "prompt.txt"
            self.prompt.write_text("a calm empty-state illustration, flat vector, single accent colour\n",
                                   encoding="utf-8")
            os.environ["XAI_API_KEY"] = "test-key"

        def _reset(self):
            global TRANSPORT
            TRANSPORT = None
            os.environ.pop("XAI_API_KEY", None)

        def args(self, **over):
            base = dict(root=str(self.root), kind="empty-state", name="empty-orders",
                        purpose="订单空态：告诉用户还没有数据以及下一步做什么",
                        declared_in="02-shape/design-directions.md", prompt_file=str(self.prompt),
                        aspect=None, resolution=None, quality=None, n=1, model=None, config=None)
            base.update(over)
            return argparse.Namespace(**base)

        def test_generates_file_and_evidence(self):
            code, _lines = generate(self.args())
            self.assertEqual(code, OK)
            asset = self.root / "02-shape/assets/generated/empty-orders.png"
            self.assertTrue(asset.is_file())
            evidence = json.loads((self.root / "evidence/images/empty-orders.json").read_text())
            self.assertEqual(evidence["files"][0]["sha256"], sha(asset.read_bytes()))
            self.assertEqual(evidence["declared_in"]["sha256"], sha(self.declared.read_bytes()))
            self.assertIn("flat vector", evidence["prompt"])
            self.assertEqual(evidence["auth_mode"], "api-key")
            self.assertNotIn("test-key", json.dumps(evidence), "no credential may reach evidence")
            self.assertEqual(json.loads(ledger_path(self.root).read_text().splitlines()[0])["n"], 1)

        def test_ref_kind_lands_in_refs(self):
            generate(self.args(kind="ref", name="direction-probe"))
            self.assertTrue((self.root / "02-shape/assets/refs/direction-probe.png").is_file())

        def test_disabled_by_default(self):
            (self.project / "sdlc.config.yaml").write_text("product_root: docs/product\n", encoding="utf-8")
            with self.assertRaises(ImageError) as caught:
                generate(self.args())
            self.assertEqual(caught.exception.code, USAGE)

        def test_budget_stops_the_call(self):
            generate(self.args(name="shot-a"))
            generate(self.args(name="shot-b"))
            generate(self.args(name="shot-c"))
            with self.assertRaises(ImageError) as caught:
                generate(self.args(name="shot-d"))
            self.assertIn("超预算", str(caught.exception))

        def test_403_explains_the_tier_fallback(self):
            global TRANSPORT
            TRANSPORT = fake_403
            with self.assertRaises(ImageError) as caught:
                generate(self.args())
            self.assertEqual(caught.exception.code, UNAUTHORIZED)
            self.assertIn("XAI_API_KEY", str(caught.exception))

        def test_rejects_non_image_bytes(self):
            global TRANSPORT
            TRANSPORT = lambda url, body, headers: (200, {"data": [{"b64_json": base64.b64encode(b"<html>").decode()}]}, "r")
            with self.assertRaises(ImageError):
                generate(self.args())

        def test_rejects_missing_declaration_and_thin_purpose(self):
            with self.assertRaises(ImageError):
                generate(self.args(declared_in="02-shape/nope.md"))
            with self.assertRaises(ImageError):
                generate(self.args(purpose="图"))

        def test_multiple_images_are_numbered(self):
            code, _lines = generate(self.args(n=2, name="hero"))
            self.assertEqual(code, OK)
            self.assertTrue((self.root / "02-shape/assets/generated/hero-1.png").is_file())
            self.assertTrue((self.root / "02-shape/assets/generated/hero-2.png").is_file())

    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.TestLoader().loadTestsFromTestCase(Tests))
    sys.stdout.write(stream.getvalue())
    print("image generate self-test: ok" if result.wasSuccessful() else "image generate self-test: FAILED")
    return OK if result.wasSuccessful() else FAIL


def main() -> int:
    parser = argparse.ArgumentParser(description="Grok 出图（带证据）")
    parser.add_argument("--root", help="feature 目录（工件与证据的根）")
    parser.add_argument("--kind", choices=KINDS)
    parser.add_argument("--name")
    parser.add_argument("--purpose")
    parser.add_argument("--declared-in", dest="declared_in", help="声明并引用这张图的工件（相对 --root）")
    parser.add_argument("--prompt-file", dest="prompt_file")
    parser.add_argument("--aspect", choices=ASPECTS)
    parser.add_argument("--resolution", choices=RESOLUTIONS)
    parser.add_argument("--quality", choices=QUALITIES)
    parser.add_argument("--n", type=int, default=None)
    parser.add_argument("--model")
    parser.add_argument("--config", help="sdlc.config.yaml 路径（默认从 --root 往上找）")
    parser.add_argument("--probe", action="store_true", help="只验授权与出图面（一张最便宜的图，不落盘）")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return _self_test()
    try:
        if args.probe:
            code, lines = probe(args)
        else:
            missing = [flag for flag, value in (("--root", args.root), ("--kind", args.kind), ("--name", args.name),
                                                ("--purpose", args.purpose), ("--declared-in", args.declared_in),
                                                ("--prompt-file", args.prompt_file)) if not value]
            if missing:
                parser.error("缺少参数：" + " ".join(missing))
            code, lines = generate(args)
        for line in lines:
            print(line)
        return code
    except (ImageError, auth.AuthError) as error:
        print(str(error), file=sys.stderr)
        return error.code


if __name__ == "__main__":
    sys.exit(main())

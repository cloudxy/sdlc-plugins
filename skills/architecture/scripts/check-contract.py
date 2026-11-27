#!/usr/bin/env python3
"""Executable API contract verifier (OpenAPI 3.x / Swagger 2.0 JSON & block YAML).

Enforces Seam 4 (Contract Lock) deterministically with zero external dependencies:
  1. Spec non-empty & structurally valid (`openapi` or `swagger` + non-empty `paths`).
  2. Every HTTP operation declares both a `2xx` success response AND explicit error semantics (`4xx`/`5xx`/`default`).
  3. Breaking-change lock (via `--baseline <old>` or sibling `<name>.baseline.<ext>`): flags removed endpoints,
     removed 2xx response properties, or newly required request properties on existing versioned paths.

Usage:
  python3 check-contract.py <spec-file-or-dir> [--baseline <old-spec>]
  python3 check-contract.py --self-test
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")


def _strip_comment(line: str) -> str:
    out, quote = [], None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1].isspace()):
            break
        out.append(ch)
    return "".join(out).rstrip()


def _scalar(v: str) -> Any:
    v = _strip_comment(v).strip()
    if v in ("", "~", "null", "Null", "NULL"):
        return None
    if len(v) >= 2 and v[0] in "\"'" and v[-1] == v[0]:
        return v[1:-1]
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        return [_scalar(x) for x in inner.split(",") if x.strip()] if inner else []
    if v in ("true", "True"):
        return True
    if v in ("false", "False"):
        return False
    try:
        return int(v)
    except ValueError:
        return v


def _parse_yaml_lite(text: str) -> dict[str, Any]:
    rows: list[tuple[int, str]] = []
    for raw in text.splitlines():
        c = _strip_comment(raw)
        if c.strip():
            rows.append((len(c) - len(c.lstrip(" ")), c.strip()))
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    for i, (ind, c) in enumerate(rows):
        while len(stack) > 1 and ind <= stack[-1][0]:
            stack.pop()
        is_item = c == "-" or c.startswith("- ")
        if not is_item:
            while len(stack) > 1 and isinstance(stack[-1][1], list):
                stack.pop()
        parent = stack[-1][1]
        nxt = rows[i + 1] if i + 1 < len(rows) else None
        if is_item:
            if not isinstance(parent, list):
                continue
            body = c[1:].strip()
            m = re.match(r"^([^:]+?):(\s+.*|)$", body)
            if m:
                k = str(_scalar(m.group(1)))
                v_raw = m.group(2).strip()
                item: dict[str, Any] = {k: _scalar(v_raw) if v_raw else None}
                parent.append(item)
                stack.append((ind, item))
            else:
                parent.append(_scalar(body))
            continue
        m = re.match(r"^([^:]+?):(\s+.*|)$", c)
        if not m or not isinstance(parent, dict):
            continue
        key = str(_scalar(m.group(1)))
        val = m.group(2).strip()
        if val == "{}":
            parent[key] = {}
        elif val == "[]":
            parent[key] = []
        elif val:
            parent[key] = _scalar(val)
        elif nxt and (nxt[0] > ind or (nxt[0] == ind and nxt[1].startswith("-"))):
            container: Any = [] if nxt[1].startswith("-") else {}
            parent[key] = container
            stack.append((ind if nxt[0] > ind else ind - 1, container))
        else:
            parent[key] = None
    return root


def load_spec(path: Path) -> dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw:
        return None
    if path.suffix.lower() == ".json" or raw.startswith("{"):
        try:
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else None
        except ValueError:
            return None
    obj = _parse_yaml_lite(raw)
    return obj if isinstance(obj, dict) else None


def _resolve_ref(doc: dict[str, Any], node: Any) -> dict[str, Any]:
    if not isinstance(node, dict):
        return {}
    ref = node.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/"):
        cur: Any = doc
        for part in ref[2:].split("/"):
            cur = cur.get(part) if isinstance(cur, dict) else None
        return cur if isinstance(cur, dict) else {}
    return node


def _extract_schema(doc: dict[str, Any], container: Any) -> dict[str, Any]:
    c = _resolve_ref(doc, container)
    if "schema" in c and isinstance(c["schema"], dict):
        return _resolve_ref(doc, c["schema"])
    content = c.get("content")
    if isinstance(content, dict):
        for media in content.values():
            if isinstance(media, dict) and isinstance(media.get("schema"), dict):
                return _resolve_ref(doc, media["schema"])
    return {}


def _response_props(doc: dict[str, Any], op: dict[str, Any]) -> set[str]:
    resps = op.get("responses")
    if not isinstance(resps, dict):
        return set()
    props: set[str] = set()
    for code, rbody in resps.items():
        if str(code).startswith("2"):
            sch = _extract_schema(doc, rbody)
            p = sch.get("properties")
            if isinstance(p, dict):
                props.update(str(k) for k in p.keys())
            items = _resolve_ref(doc, sch.get("items"))
            if isinstance(items.get("properties"), dict):
                props.update(str(k) for k in items["properties"].keys())
    return props


def _required_request_fields(doc: dict[str, Any], op: dict[str, Any]) -> set[str]:
    req: set[str] = set()
    rb = op.get("requestBody")
    if isinstance(rb, dict):
        sch = _extract_schema(doc, rb)
        rlist = sch.get("required")
        if isinstance(rlist, list):
            req.update(str(x) for x in rlist)
    params = op.get("parameters")
    if isinstance(params, list):
        for p in params:
            rp = _resolve_ref(doc, p)
            if rp.get("required") is True and rp.get("name"):
                req.add(f"param:{rp['name']}")
    return req


def verify_spec_file(path: Path, baseline_path: Path | None = None) -> list[str]:
    errs: list[str] = []
    doc = load_spec(path)
    if not doc or not (doc.get("openapi") or doc.get("swagger")):
        return [f"✗ [CONTRACT] {path}: spec is empty, unreadable, or missing 'openapi'/'swagger' version"]
    paths = doc.get("paths")
    if not isinstance(paths, dict) or not paths:
        return [f"✗ [CONTRACT] {path}: spec defines no endpoints under 'paths'"]

    ops_found = 0
    for route, item in sorted(paths.items()):
        if not isinstance(item, dict):
            continue
        for method in HTTP_METHODS:
            op = item.get(method)
            if not isinstance(op, dict):
                continue
            ops_found += 1
            resps = op.get("responses")
            if not isinstance(resps, dict) or not resps:
                errs.append(f"✗ [CONTRACT] {path}: {method.upper()} {route} defines no 'responses'")
                continue
            codes = [str(k) for k in resps.keys()]
            has_2xx = any(c.startswith("2") for c in codes)
            has_err = any(c.startswith(("4", "5")) or c == "default" for c in codes)
            if not has_2xx:
                errs.append(f"✗ [CONTRACT] {path}: {method.upper()} {route} lacks a 2xx success response")
            if not has_err:
                errs.append(
                    f"✗ [CONTRACT] {path}: {method.upper()} {route} lacks explicit error semantics (4xx/5xx/default)"
                )
    if ops_found == 0:
        errs.append(f"✗ [CONTRACT] {path}: 'paths' contains zero HTTP operations")

    auto_base = baseline_path
    if auto_base is None:
        cand = path.with_name(f"{path.stem}.baseline{path.suffix}")
        if cand.is_file():
            auto_base = cand
    if auto_base is not None:
        base_doc = load_spec(auto_base)
        if not base_doc or not isinstance(base_doc.get("paths"), dict):
            errs.append(f"✗ [CONTRACT] {auto_base}: baseline contract is unreadable or invalid")
        else:
            for route, b_item in sorted(base_doc["paths"].items()):
                if not isinstance(b_item, dict):
                    continue
                c_item = paths.get(route)
                for method in HTTP_METHODS:
                    b_op = b_item.get(method)
                    if not isinstance(b_op, dict):
                        continue
                    c_op = c_item.get(method) if isinstance(c_item, dict) else None
                    if not isinstance(c_op, dict):
                        errs.append(
                            f"✗ [CONTRACT] {path}: breaking change — removed endpoint {method.upper()} {route} (use expand-contract or versioned path)"
                        )
                        continue
                    removed_props = sorted(_response_props(base_doc, b_op) - _response_props(doc, c_op))
                    for prop in removed_props:
                        errs.append(
                            f"✗ [CONTRACT] {path}: breaking change — removed 2xx response property '{prop}' on {method.upper()} {route}"
                        )
                    added_req = sorted(_required_request_fields(doc, c_op) - _required_request_fields(base_doc, b_op))
                    for rf in added_req:
                        errs.append(
                            f"✗ [CONTRACT] {path}: breaking change — added required request input '{rf}' on {method.upper()} {route}"
                        )
    return errs


def discover_specs(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if not target.is_dir():
        return []
    hits: list[Path] = []
    for p in sorted(target.rglob("*")):
        if not p.is_file() or ".baseline." in p.name:
            continue
        low = p.name.lower()
        if low in ("openapi.yaml", "openapi.yml", "openapi.json", "swagger.yaml", "swagger.yml", "swagger.json") or low.endswith(
            (".openapi.yaml", ".openapi.yml", ".openapi.json")
        ):
            hits.append(p)
    return hits


def self_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        good = d / "openapi.yaml"
        good.write_text(
            "openapi: '3.0.3'\n"
            "paths:\n"
            "  /api/v1/orders:\n"
            "    post:\n"
            "      requestBody:\n"
            "        content:\n"
            "          application/json:\n"
            "            schema:\n"
            "              required: [sku]\n"
            "              properties:\n"
            "                sku: {type: string}\n"
            "      responses:\n"
            "        '201':\n"
            "          content:\n"
            "            application/json:\n"
            "              schema:\n"
            "                properties:\n"
            "                  order_id: {type: string}\n"
            "                  amount_minor: {type: integer}\n"
            "        '400':\n"
            "          description: Bad request\n",
            encoding="utf-8",
        )
        assert verify_spec_file(good) == [], verify_spec_file(good)

        no_err = d / "no_err.json"
        no_err.write_text(
            json.dumps({"openapi": "3.0.0", "paths": {"/ping": {"get": {"responses": {"200": {"description": "ok"}}}}}}),
            encoding="utf-8",
        )
        e1 = verify_spec_file(no_err)
        assert len(e1) == 1 and "error semantics" in e1[0], e1

        broken = d / "broken.yaml"
        broken.write_text(
            "openapi: '3.0.3'\n"
            "paths:\n"
            "  /api/v1/orders:\n"
            "    post:\n"
            "      requestBody:\n"
            "        content:\n"
            "          application/json:\n"
            "            schema:\n"
            "              required: [sku, tenant_code]\n"
            "      responses:\n"
            "        '201':\n"
            "          content:\n"
            "            application/json:\n"
            "              schema:\n"
            "                properties:\n"
            "                  order_id: {type: string}\n"
            "        '400':\n"
            "          description: Bad request\n",
            encoding="utf-8",
        )
        e2 = verify_spec_file(broken, baseline_path=good)
        assert any("removed 2xx response property 'amount_minor'" in x for x in e2), e2
        assert any("added required request input 'tenant_code'" in x for x in e2), e2
    print("self-test ok")
    return 0


def main(argv: list[str] | None = None) -> int:
    if (argv if argv is not None else sys.argv[1:]) == ["--self-test"]:
        return self_test()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", type=Path)
    ap.add_argument("--baseline", type=Path, default=None)
    args = ap.parse_args(argv)
    specs = discover_specs(args.target)
    if not specs:
        print(f"✗ [CONTRACT] {args.target}: no OpenAPI/Swagger spec file found")
        return 1
    errors: list[str] = []
    for sp in specs:
        errors.extend(verify_spec_file(sp, baseline_path=args.baseline if len(specs) == 1 else None))
    for line in errors:
        print(line)
    if not errors:
        print(f"✓ [CONTRACT] verified {len(specs)} contract file(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

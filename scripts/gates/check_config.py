#!/usr/bin/env python3
"""check_config.py — read-only check of a project's sdlc.config.yaml against what v4 needs. Never writes a file.

Why it exists: on 2026-09-17 a v4 run on a project with two React frontends never started the app. Its config predated
v4 (no `app` block, no `product_root`, `e2e: null` with the reason "no E2E suite" although frontend/admin ships a
Playwright `e2e` script). Screenshots, integration runs, E2E and acceptance walkthroughs quietly degraded into reading
source code, and design-system.md described screens nobody had looked at.

  python3 check_config.py [--project-root DIR] [--probe] [--json]
  python3 check_config.py --self-test

Exit codes: 0 no blockers · 1 blockers (UI stages must not start) · 2 no config or usage error.
--probe also requests app.base_url (3 s timeout); an unreachable app is the blocker APP-DOWN.
The suggested block is printed for the user to review and paste. The plugin never edits a user's config.
No PyYAML: a small indentation parser reads the keys this check needs. `.env` files are never read.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_SCRIPTS_DIR = str(_Path(__file__).resolve().parents[1])  # _SDLC_SCRIPTS_PATH
if _SCRIPTS_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_DIR)

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from runtime._sdlc_core import (
    SKIP_DIRS,
    VALID_ARCH_STYLES,
    VALID_COMPLIANCE,
    VALID_DB_ENGINES,
    VALID_EXTRA_GATES,
    VALID_INDUSTRIES,
    VALID_SURFACES,
    VALID_TRAITS,
    parse_scalar as _scalar,
    parse_yaml,
    strip_comment as _strip_comment,
)

UI_DEPS = {"react", "vue", "svelte", "@angular/core", "next", "nuxt", "solid-js", "preact", "@remix-run/react", "astro",
           "umi", "@umijs/max"}
E2E_DEPS = {"@playwright/test", "playwright", "cypress", "puppeteer", "webdriverio", "@wdio/cli"}
RUN_SCRIPTS = ("dev", "start", "serve", "preview")
PLACEHOLDER = re.compile(r"<[^>]+>")


# ----------------------------------------------------------------------------- project inspection
def _read_small(path: str, limit: int = 200_000) -> str:
    try:
        if os.path.getsize(path) > limit:
            return ""
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _config_port(project_root: str, name: str) -> tuple[int | None, str]:
    """PORT from a project config file named after the UI root, e.g. config/default/admin.yml (default env first)."""
    base = os.path.join(project_root, "config")
    hits = []
    for dirpath, dirs, files in os.walk(base):
        if os.path.relpath(dirpath, base).count(os.sep) >= 2:
            dirs[:] = []
        for fn in files:
            if fn in (f"{name}.yml", f"{name}.yaml"):
                hits.append(os.path.join(dirpath, fn))
    hits.sort(key=lambda p: (0 if f"{os.sep}default{os.sep}" in p else 1 if f"{os.sep}local{os.sep}" in p else 2, p))
    for path in hits:
        m = re.search(r"^\s*port:\s*[\"']?(\d{2,5})", _read_small(path), re.I | re.M)
        if m:
            return int(m.group(1)), os.path.relpath(path, project_root)
    return None, ""


def _guess_port(dirpath: str, scripts: dict[str, Any], deps: dict[str, Any], project_root: str | None = None) -> tuple[int | None, str]:
    for k in RUN_SCRIPTS:
        m = re.search(r"(?:--port[= ]|\s-p\s+|PORT=)(\d{2,5})", " " + str(scripts.get(k, "")))
        if m:
            return int(m.group(1)), f"scripts.{k}"
    if project_root:
        port, src = _config_port(project_root, os.path.basename(dirpath))
        if port:
            return port, src
    try:
        names = sorted(os.listdir(dirpath))
    except OSError:
        names = []
    for fn in names:
        if re.match(r"^(vite|vue|next|nuxt|umi|webpack|rsbuild|farm)\.config\.[cm]?[jt]s$", fn) or fn == ".umirc.ts":
            m = re.search(r"\bport\s*[:=]\s*(\d{2,5})", _read_small(os.path.join(dirpath, fn)))
            if m:
                return int(m.group(1)), fn
    for dep, port in (("react-scripts", 3000), ("next", 3000), ("vite", 5173), ("@angular/core", 4200), ("umi", 8000),
                      ("@umijs/max", 8000), ("nuxt", 3000)):
        if dep in deps:
            return port, f"{dep} default"
    return None, ""


def find_ui_roots(root: str, max_depth: int = 3) -> list[dict[str, Any]]:
    found = []
    for dirpath, dirs, files in os.walk(root):
        rel = os.path.relpath(dirpath, root).replace("\\", "/")
        depth = 0 if rel == "." else rel.count("/") + 1
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")) if depth < max_depth else []
        if "package.json" not in files:
            continue
        try:
            with open(os.path.join(dirpath, "package.json"), encoding="utf-8") as f:
                pkg = json.load(f)
        except (OSError, ValueError):
            continue
        deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
        frameworks = sorted(UI_DEPS & set(deps))
        if not frameworks:
            continue
        scripts = pkg.get("scripts") or {}
        port, port_src = _guess_port(dirpath, scripts, deps, root)
        found.append({
            "path": rel,
            "frameworks": frameworks,
            "run_scripts": {k: scripts[k] for k in RUN_SCRIPTS if k in scripts},
            "e2e_scripts": {k: v for k, v in scripts.items() if re.search(r"e2e|playwright|cypress", f"{k} {v}", re.I)},
            "e2e_deps": sorted(E2E_DEPS & set(deps)),
            "port": port,
            "port_source": port_src,
        })
    return found


def _compose_files(root: str) -> list[str]:
    out = []
    for d in (root, os.path.join(root, "deploy"), os.path.join(root, "docker")):
        try:
            names = sorted(os.listdir(d))
        except OSError:
            continue
        out += [os.path.relpath(os.path.join(d, n), root) for n in names
                if re.match(r"^(docker-)?compose[\w.-]*\.ya?ml$", n)]
    return out


def _placeholder(v: Any) -> bool:
    return v is None or (isinstance(v, str) and (not v.strip() or bool(PLACEHOLDER.search(v))))


def _is_local(url: str) -> bool:
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    return host in ("localhost", "0.0.0.0", "::1") or host.endswith(".local") or host.endswith(".localhost") \
        or bool(re.match(r"^(127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)", host))


def _probe(url: str) -> tuple[bool, str]:
    # A local app must not go through HTTP(S)_PROXY: a proxy answers 502 for 127.0.0.1 and hides whether the app is up.
    handlers = [urllib.request.ProxyHandler({})] if _is_local(url) else []
    opener = urllib.request.build_opener(*handlers)
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "sdlc-check-config"})
        with opener.open(req, timeout=3) as r:  # noqa: S310 — the user's own app
            return True, f"HTTP {r.status}"
    except urllib.error.HTTPError as e:
        return e.code < 500, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return False, type(e).__name__ + (f": {e.reason}" if hasattr(e, "reason") else "")


# ----------------------------------------------------------------------------- checks
def _function_ids() -> set[str]:
    """Function ids come from workflow/registry.json (one source). An unreadable or unsupported registry raises:
    the caller reports it instead of silently skipping the key check."""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from workflow import load_registry  # noqa: PLC0415
    return set(load_registry().get("functions", {}))


def check(root: str, probe: bool = False) -> dict[str, Any]:
    cfg_path = os.path.join(root, "sdlc.config.yaml")
    result: dict[str, Any] = {"project_root": root, "config": cfg_path, "findings": [], "ui_roots": [], "suggested": {}}
    if not os.path.isfile(cfg_path):
        result["findings"].append({"level": "blocker", "code": "NO-CONFIG",
                                   "message": "sdlc.config.yaml is missing — copy skills/sdlc/templates/sdlc.config.yaml and fill it with the user"})
        return result
    cfg = parse_yaml(_read_small(cfg_path, 1_000_000))
    gates = cfg.get("gates") if isinstance(cfg.get("gates"), dict) else {}
    app = cfg.get("app") if isinstance(cfg.get("app"), dict) else {}
    lane = cfg.get("lane_rules") if isinstance(cfg.get("lane_rules"), dict) else {}
    research = cfg.get("research") if isinstance(cfg.get("research"), dict) else {}
    roots = find_ui_roots(root)
    apps = [r for r in roots if r["run_scripts"]]
    result["ui_roots"] = roots
    add = result["findings"].append
    sug = result["suggested"]

    if _placeholder(cfg.get("product_root")):
        exists = os.path.isdir(os.path.join(root, "docs", "product"))
        add({"level": "warn", "code": "PRODUCT-ROOT",
             "message": "product_root is not set; v4 falls back to docs/product" + (" (which exists)" if exists else "") + " — set it explicitly"})
        sug["product_root"] = "docs/product"

    if apps:
        names = ", ".join(r["path"] for r in apps)
        first = apps[0]
        run_key = "dev" if "dev" in first["run_scripts"] else next(iter(first["run_scripts"]))
        if _placeholder(app.get("start")):
            add({"level": "blocker", "code": "APP-START",
                 "message": f"the project has runnable UI ({names}) but app.start is not set — nobody can start it for screenshots, integration, E2E or walkthroughs"})
            sug.setdefault("app", {})["start"] = (f"npm run {run_key} --prefix {first['path']}", f"[推断] {first['path']}/package.json scripts.{run_key}; add the backend start too")
        if _placeholder(app.get("base_url")):
            add({"level": "blocker", "code": "APP-URL", "message": "app.base_url is not set — ui-evidence.sh, E2E and walkthroughs need the URL of the running app"})
            if first["port"]:
                sug.setdefault("app", {})["base_url"] = (f"http://localhost:{first['port']}", f"[推断] {first['port_source']}")
        if not app.get("widths"):
            sug.setdefault("app", {})["widths"] = ("[375, 768, 1440]", "screenshot widths, same as design-system.md")
        if _placeholder(gates.get("e2e")):
            e2e_roots = [r for r in apps + roots if r["e2e_scripts"] or r["e2e_deps"]]
            msg = f"gates.e2e is {'null' if gates.get('e2e') is None else 'a placeholder'} but the project has UI ({names}); v4 requires E2E on core journeys"
            reason = gates.get("e2e_reason")
            if e2e_roots:
                r = e2e_roots[0]
                what = f"script {next(iter(r['e2e_scripts']))}" if r["e2e_scripts"] else f"dependency {r['e2e_deps'][0]}"
                msg += f"; {r['path']}/package.json already has {what}"
                if reason:
                    msg += f" — e2e_reason 「{reason}」 is contradicted"
                if r["e2e_scripts"]:
                    k = next(iter(r["e2e_scripts"]))
                    sug.setdefault("gates", {})["e2e"] = (f"npm run {k} --prefix {r['path']}", f"[推断] {r['path']}/package.json scripts.{k}")
            elif reason:
                msg += f"; e2e_reason 「{reason}」 is only valid for a project without any user interface — add an E2E suite for the core journeys"
            add({"level": "blocker", "code": "E2E", "message": msg})
        if len(apps) > 1:
            urls = app.get("urls") if isinstance(app.get("urls"), dict) else {}
            missing = [r for r in apps if _placeholder(urls.get(os.path.basename(r["path"])))]
            if missing:
                add({"level": "warn", "code": "APP-URLS",
                     "message": f"{len(apps)} UI roots, but app.urls has no entry for {', '.join(os.path.basename(r['path']) for r in missing)} — "
                                "hats cannot screenshot, walk or E2E those surfaces, and --probe cannot check them"})
                entries = sug.setdefault("app", {}).setdefault("urls", {})
                for r in missing:
                    if r["port"]:
                        entries[os.path.basename(r["path"])] = (f"http://localhost:{r['port']}", f"[推断] {r['port_source']}")
        if not lane.get("ui_paths"):
            add({"level": "warn", "code": "UI-PATHS", "message": "lane_rules.ui_paths is empty — the Q-ui trigger cannot mark features `ui: yes`"})
            sug.setdefault("lane_rules", {})["ui_paths"] = ("[" + ", ".join(r["path"] for r in apps) + "]", "detected UI roots")
    elif _placeholder(gates.get("e2e")) and not gates.get("e2e_reason"):
        add({"level": "warn", "code": "E2E", "message": "no runnable UI detected and gates.e2e has no value or e2e_reason — state why E2E does not apply"})

    for k in ("test", "lint", "build", "migration"):
        v = gates.get(k)
        if isinstance(v, str) and PLACEHOLDER.search(v):
            add({"level": "warn", "code": "GATE-PLACEHOLDER", "message": f"gates.{k} is still the template placeholder {v!r}"})
    constitution = cfg.get("constitution")
    if isinstance(constitution, str) and not _placeholder(constitution) and not os.path.exists(os.path.join(root, constitution)):
        add({"level": "warn", "code": "CONSTITUTION", "message": f"constitution {constitution} does not exist"})
    signals = cfg.get("signals_path")
    if signals is not None:
        product = cfg.get("product_root") if isinstance(cfg.get("product_root"), str) else "docs/product"
        sp = os.path.normpath(str(signals)) if isinstance(signals, str) else ""
        if not sp or _placeholder(signals) or os.path.isabs(sp) or sp.startswith(".."):
            add({"level": "warn", "code": "SIGNALS-PATH", "message": f"signals_path must be a project-relative directory, got {signals!r}"})
        elif sp == ".sdlc" or sp.startswith(".sdlc" + os.sep) or sp == os.path.normpath(product) or sp.startswith(os.path.normpath(product) + os.sep):
            add({"level": "warn", "code": "SIGNALS-PATH",
                 "message": "signals_path must not sit inside product_root or .sdlc: the store is ops-owned raw evidence, not a product fact or a manager file"})
    owners = cfg.get("owners")
    if owners is not None:
        try:
            known = _function_ids()
        except (OSError, ValueError) as e:
            known = set()
            add({"level": "blocker", "code": "REGISTRY",
                 "message": f"workflow registry is unreadable or unsupported by this runner, owners keys unchecked: {e}"})
        if not isinstance(owners, dict):
            add({"level": "warn", "code": "OWNERS",
                 "message": "owners must be a block mapping of function id → person or team (this reader does not expand inline {a: b})"})
        else:
            for key, who in owners.items():
                if known and key not in known:
                    add({"level": "warn", "code": "OWNERS",
                         "message": f"owners.{key} is not a function id ({', '.join(sorted(known))})"})
                elif not isinstance(who, str) or _placeholder(who):
                    add({"level": "warn", "code": "OWNERS", "message": f"owners.{key} is empty or still a placeholder"})
            add({"level": "info", "code": "OWNERS",
                 "message": "owners only names who to ask for a decision; it grants no permission, does not replace the "
                            "operator's recorded answer, and the plugin contacts nobody outside the conversation"})
    if research.get("offline") is True:
        add({"level": "info", "code": "RESEARCH-OFFLINE",
             "message": "research.offline: true — web-source requirements are waived; only the user sets this, never a hat or the manager"})
    imagery = cfg.get("imagery") if isinstance(cfg.get("imagery"), dict) else {}
    if imagery.get("enabled") is True:
        kinds = imagery.get("allowed_kinds")
        if not isinstance(kinds, list) or not kinds:
            add({"level": "warn", "code": "IMAGERY-KINDS",
                 "message": "imagery.enabled: true but allowed_kinds is empty — no hat could generate anything"})
        for section in ("defaults", "budget"):
            if section in imagery and not isinstance(imagery[section], dict):
                add({"level": "warn", "code": "IMAGERY-SHAPE",
                     "message": f"imagery.{section} must be a block mapping (this reader does not expand inline "
                                f"{{a: b}}); the tool falls back to its defaults, so the cap you wrote is not in effect"})
        mode = str(imagery.get("auth") or "auto")
        if mode not in ("auto", "oauth", "api-key"):
            add({"level": "warn", "code": "IMAGERY-AUTH", "message": f"imagery.auth {mode!r} is not auto|oauth|api-key"})
        state = "unknown"
        try:                                   # ask auth.py; never read the credential file from here
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "grok"))
            import auth as _auth                                            # noqa: PLC0415
            state = _auth.status_report()["state"]
        except Exception:                                                   # noqa: BLE001
            state = "unknown"
        if state != "logged_in" and mode != "api-key" and not os.environ.get("XAI_API_KEY"):
            add({"level": "warn", "code": "IMAGERY-AUTH",
                 "message": f"imagery.enabled: true but Grok authorization is {state} — the operator runs "
                            "/sdlc-grok login, then /sdlc-grok probe (a hat never logs in)"})
        add({"level": "info", "code": "IMAGERY",
             "message": f"imagery.enabled: true (model {imagery.get('model') or 'registry default'}, auth {mode}) — "
                        "generating spends the operator's subscription quota; "
                        f"budget.max_per_feature={(imagery.get('budget') or {}).get('max_per_feature') if isinstance(imagery.get('budget'), dict) else 'default'}"})
    if probe:
        targets: list[tuple[str, str]] = []
        if not _placeholder(app.get("base_url")):
            targets.append(("base_url", str(app["base_url"])))
        urls = app.get("urls") if isinstance(app.get("urls"), dict) else {}
        for name, url in urls.items():
            if not _placeholder(url) and str(url) not in (t[1] for t in targets):
                targets.append((f"urls.{name}", str(url)))
        if not targets:
            add({"level": "blocker", "code": "APP-DOWN", "message": "cannot probe: app.base_url is not set"})
        down = []
        for name, url in targets:
            ok, detail = _probe(url)
            if ok:
                add({"level": "info", "code": "APP-UP", "message": f"{name} {url} answered ({detail})"})
            else:
                down.append(f"{name} {url} ({detail})")
        if down:
            start = app.get("start")
            add({"level": "blocker", "code": "APP-DOWN",
                 "message": f"not reachable: {'; '.join(down)} — run app.start{f' ({start})' if not _placeholder(start) else ''}, probe again; still down → stop and ask the user"})
        # The screenshot tool itself (E01): take one real screenshot from this project's directory, because
        # ui-evidence.sh prefers the project's own Playwright. A package name in package.json proves nothing.
        if os.environ.get("SDLC_SKIP_UI_PROBE") != "1":
            ui = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui-evidence.sh")
            try:
                pr = subprocess.run(["bash", ui, "--probe"], cwd=root, capture_output=True, text=True, timeout=180)
                rc, detail = pr.returncode, (pr.stderr or pr.stdout).strip().splitlines()[-1:] or [""]
            except (OSError, subprocess.TimeoutExpired) as e:
                rc, detail = 1, [str(e)]
            if rc == 0:
                add({"level": "info", "code": "UI-TOOL", "message": "ui-evidence.sh took a probe screenshot"})
            elif rc == 3:
                add({"level": "blocker", "code": "UI-TOOL",
                     "message": "no screenshot tool: designer directions, integration runs and walkthroughs cannot produce evidence. "
                                "Install one: `pip3 install --user playwright && python3 -m playwright install chromium` "
                                "(or in a Node project `npm i -D @playwright/test && npx playwright install chromium`)"})
            else:
                add({"level": "blocker", "code": "UI-TOOL", "message": f"ui-evidence.sh probe failed (exit {rc}): {detail[0]}"})
    if roots and not apps:
        add({"level": "info", "code": "UI-LIBS", "message": "UI packages without a dev/start script (libraries): " + ", ".join(r["path"] for r in roots)})
    compose = _compose_files(root)
    if compose and "app" in sug:
        sug["app"]["_compose"] = (", ".join(compose), "compose files found — the start command may need them")

    # ----------------------------------------------------------------- profile & extra_gates validation + smart inference
    _check_profile_and_extra_gates(root, cfg, apps, roots, add, sug)
    return result


def _infer_repo_signals(root: str, apps: list[dict[str, Any]], roots: list[dict[str, Any]]) -> dict[str, Any]:
    surfaces: list[str] = []
    if apps or roots:
        surfaces.append("web")
    py_text = _read_small(os.path.join(root, "pyproject.toml")) + "\n" + _read_small(os.path.join(root, "requirements.txt"))
    pkg_text = _read_small(os.path.join(root, "package.json"))
    combined = (py_text + "\n" + pkg_text).lower()
    if any(k in combined for k in ("fastapi", "flask", "django", "starlette", "express", "nestjs", "@nestjs/core", "gin", "axum")):
        surfaces.append("api")
    if any(os.path.exists(os.path.join(root, p)) for p in ("ios", "android", "Podfile", "AndroidManifest.xml", "pubspec.yaml")):
        surfaces.append("native-mobile")
    if any(os.path.exists(os.path.join(root, p)) for p in ("src-tauri", "tauri.conf.json", "electron.vite.config.ts")) or '"electron"' in combined:
        surfaces.append("desktop")
    if os.path.exists(os.path.join(root, "project.config.json")) or "miniprogram" in combined:
        surfaces.append("miniprogram")
    if not surfaces and (os.path.exists(os.path.join(root, "pyproject.toml")) or os.path.exists(os.path.join(root, "Cargo.toml")) or os.path.exists(os.path.join(root, "go.mod"))):
        surfaces.append("cli-sdk")

    engines: list[str] = []
    if any(k in combined for k in ("psycopg", "asyncpg", "postgres", "pg")):
        engines.append("postgresql")
    if any(k in combined for k in ("pymysql", "mysqlclient", "aiomysql", "mysql2")):
        engines.append("mysql")
    if "sqlite" in combined or "aiosqlite" in combined or "better-sqlite3" in combined:
        engines.append("sqlite")
    if "redis" in combined or "ioredis" in combined:
        engines.append("redis")
    if "clickhouse" in combined:
        engines.append("clickhouse")

    industry = "b2b-saas"
    if any(k in combined for k in ("scrapy", "playwright", "selenium", "beautifulsoup4", "crawlee")) and "fastapi" not in combined and not apps:
        industry = "data-crawler"
    elif any(k in combined for k in ("ffmpeg", "moviepy", "sharp", "canvas", "remotion", "comfy")) and any(k in combined for k in ("openai", "anthropic", "genai", "torch", "diffusers")):
        industry = "aigc-workbench"
    elif any(k in combined for k in ("openai", "anthropic", "langchain", "llamaindex", "litellm", "vllm")):
        industry = "ai-agentic"
    elif any(k in combined for k in ("stripe", "alipay", "wechatpay", "braintree", "ledger")):
        industry = "fintech-ledger"
    elif any(s in surfaces for s in ("native-mobile", "desktop", "miniprogram", "cli-sdk")) and "web" not in surfaces:
        industry = "client-iot-localfirst"

    layering_dir = None
    for cand in ("backend", "src", "app", "server"):
        cpath = os.path.join(root, cand)
        if os.path.isdir(cpath):
            subdirs = {d.lower() for _, dn, _ in os.walk(cpath) for d in dn if d not in SKIP_DIRS}
            if ({"routers", "routes", "api", "controllers"} & subdirs) and ({"services", "service", "domain", "repositories"} & subdirs):
                layering_dir = cand
                break
    arch_style = "hexagonal-ddd" if layering_dir and os.path.isdir(os.path.join(root, layering_dir, "domain")) else ("modular-monolith" if layering_dir else "layered-crud")
    frontend_dir = apps[0]["path"] if apps else (roots[0]["path"] if roots else None)
    contract_spec = None
    for cand in ("openapi.yaml", "openapi.yml", "openapi.json", "swagger.yaml", "swagger.json", "docs/openapi.yaml", "docs/openapi.json", "api/openapi.yaml"):
        if os.path.isfile(os.path.join(root, cand)):
            contract_spec = cand
            break
    return {
        "industry": industry,
        "surfaces": surfaces or ["web"],
        "db_engines": engines or ["none"],
        "architecture_style": arch_style,
        "layering_dir": layering_dir,
        "frontend_dir": frontend_dir,
        "contract_spec": contract_spec,
    }


def _check_enum_list(vals: Any, allowed: tuple[str, ...], label: str, add: Any) -> None:
    if not isinstance(vals, list):
        add({"level": "warn", "code": "PROFILE", "message": f"{label} must be a list of values from {', '.join(allowed)}"})
        return
    bad = [str(v) for v in vals if str(v) not in allowed]
    if bad:
        add({"level": "warn", "code": "PROFILE", "message": f"{label} has unknown value(s) {', '.join(bad)} (allowed: {', '.join(allowed)})"})


def _check_profile_and_extra_gates(root: str, cfg: dict[str, Any], apps: list[dict[str, Any]], roots: list[dict[str, Any]], add: Any, sug: dict[str, Any]) -> None:
    inferred = _infer_repo_signals(root, apps, roots)
    prof = cfg.get("profile")
    if prof is None:
        if apps or roots or inferred["layering_dir"]:
            add({"level": "warn", "code": "PROFILE",
                 "message": f"profile is not set in sdlc.config.yaml — inferred industry={inferred['industry']}, "
                            f"surfaces={inferred['surfaces']}; confirm high-risk industry SOPs in sdlc.config.yaml"})
            sug["profile"] = {
                "industry": (inferred["industry"], f"[推断] allowed: {', '.join(VALID_INDUSTRIES)}"),
                "surfaces": ("[" + ", ".join(inferred["surfaces"]) + "]", "[推断] detected client/API surfaces"),
                "db_engines": ("[" + ", ".join(inferred["db_engines"]) + "]", "[推断] detected database engines"),
                "architecture_style": (inferred["architecture_style"], f"[推断] allowed: {', '.join(VALID_ARCH_STYLES)}"),
            }
    elif not isinstance(prof, dict):
        add({"level": "warn", "code": "PROFILE", "message": "profile must be a block mapping (industry, traits, surfaces, db_engines, architecture_style, compliance)"})
    else:
        ind = prof.get("industry")
        if _placeholder(ind):
            add({"level": "warn", "code": "PROFILE", "message": f"profile.industry is missing or placeholder (allowed: {', '.join(VALID_INDUSTRIES)})"})
        elif str(ind) not in VALID_INDUSTRIES:
            add({"level": "warn", "code": "PROFILE", "message": f"profile.industry {ind!r} is not in {', '.join(VALID_INDUSTRIES)}"})
        arch = prof.get("architecture_style")
        if arch is not None and not _placeholder(arch) and str(arch) not in VALID_ARCH_STYLES:
            add({"level": "warn", "code": "PROFILE", "message": f"profile.architecture_style {arch!r} is not in {', '.join(VALID_ARCH_STYLES)}"})
        if "surfaces" in prof and prof["surfaces"] is not None:
            _check_enum_list(prof["surfaces"], VALID_SURFACES, "profile.surfaces", add)
        if "traits" in prof and prof["traits"] is not None:
            _check_enum_list(prof["traits"], VALID_TRAITS, "profile.traits", add)
        if "db_engines" in prof and prof["db_engines"] is not None:
            _check_enum_list(prof["db_engines"], VALID_DB_ENGINES, "profile.db_engines", add)
        if "compliance" in prof and prof["compliance"] is not None:
            _check_enum_list(prof["compliance"], VALID_COMPLIANCE, "profile.compliance", add)

    eg = cfg.get("extra_gates")
    rec_gates: list[str] = []
    if inferred["layering_dir"]:
        rec_gates.append("layering")
    if inferred["frontend_dir"] and inferred["frontend_dir"] != ".":
        rec_gates.append("frontend")
    if inferred["contract_spec"]:
        rec_gates.append("contract")
    if eg is None and rec_gates:
        add({"level": "info", "code": "EXTRA-GATES",
             "message": f"detected structured directories/specs for static checks; consider enabling extra_gates: [{', '.join(rec_gates)}]"})
        sug["extra_gates"] = ("[" + ", ".join(rec_gates) + "]", "[推断] static architecture/token/contract verifiers")
        if inferred["layering_dir"]:
            sug["layering_root"] = (inferred["layering_dir"], "[推断] layered backend root")
        if inferred["frontend_dir"] and inferred["frontend_dir"] != ".":
            sug["frontend_root"] = (inferred["frontend_dir"], "[推断] frontend source root")
        if inferred["contract_spec"]:
            sug["contract_spec"] = (inferred["contract_spec"], "[推断] OpenAPI/Swagger executable contract")
    elif eg is not None:
        if not isinstance(eg, list):
            add({"level": "warn", "code": "EXTRA-GATES", "message": f"extra_gates must be a list (allowed: {', '.join(VALID_EXTRA_GATES)})"})
        else:
            bad_eg = [str(x) for x in eg if str(x) not in VALID_EXTRA_GATES]
            if bad_eg:
                add({"level": "warn", "code": "EXTRA-GATES",
                     "message": f"extra_gates has unknown gate(s) {', '.join(bad_eg)} (allowed: {', '.join(VALID_EXTRA_GATES)})"})
            if "layering" in eg:
                lr = str(cfg.get("layering_root") or "backend")
                if not os.path.exists(os.path.join(root, lr)):
                    add({"level": "warn", "code": "EXTRA-GATES", "message": f"extra_gates includes layering, but layering_root {lr!r} does not exist"})
            if "frontend" in eg:
                fr = str(cfg.get("frontend_root") or (inferred["frontend_dir"] or "frontend"))
                if not os.path.exists(os.path.join(root, fr)):
                    add({"level": "warn", "code": "EXTRA-GATES", "message": f"extra_gates includes frontend, but frontend_root {fr!r} does not exist"})
            if "contract" in eg:
                cs = str(cfg.get("contract_spec") or (inferred["contract_spec"] or "openapi.yaml"))
                if not os.path.exists(os.path.join(root, cs)):
                    add({"level": "warn", "code": "EXTRA-GATES", "message": f"extra_gates includes contract, but contract_spec {cs!r} does not exist"})


def render_suggestion(sug: dict[str, Any]) -> str:
    if not sug:
        return ""
    lines = ["# Suggested additions for sdlc.config.yaml — review, correct and paste yourself (this script never writes).",
             "# Lines marked [推断] are inferred from package.json and framework defaults; confirm the ports and start commands."]
    if "product_root" in sug:
        lines.append(f"product_root: {sug['product_root']}")
    for section in ("profile", "app", "gates", "lane_rules"):
        if section not in sug:
            continue
        lines.append(f"{section}:")
        for key, entry in sug[section].items():
            if isinstance(entry, dict):
                lines.append(f"  {key}:")
                for sub, (value, note) in entry.items():
                    lines.append(f"    {sub}: {json.dumps(value, ensure_ascii=False)}   # {note}")
                continue
            value, note = entry
            if key.startswith("_"):
                lines.append(f"  # {note}: {value}")
                continue
            rendered = value if value.startswith("[") else json.dumps(value, ensure_ascii=False)
            lines.append(f"  {key}: {rendered}   # {note}")
    for top_scalar in ("extra_gates", "layering_root", "frontend_root"):
        if top_scalar in sug:
            value, note = sug[top_scalar]
            rendered = value if value.startswith("[") else json.dumps(value, ensure_ascii=False)
            lines.append(f"{top_scalar}: {rendered}   # {note}")
    return "\n".join(lines)


def main_check(args: argparse.Namespace) -> int:
    root = os.path.abspath(os.path.expanduser(args.project_root))
    result = check(root, probe=args.probe)
    blockers = [f for f in result["findings"] if f["level"] == "blocker"]
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"check_config: {result['config']}")
        for r in result["ui_roots"]:
            runnable = ", ".join(f"{k}: {v}" for k, v in r["run_scripts"].items()) or "no dev/start script"
            port = f" · port {r['port']} ({r['port_source']})" if r["port"] else ""
            print(f"  UI root {r['path']} [{', '.join(r['frameworks'])}] {runnable}{port}")
        icon = {"blocker": "✗", "warn": "⚠", "info": "·"}
        for f in result["findings"]:
            print(f"{icon[f['level']]} [{f['code']}] {f['message']}")
        block = render_suggestion(result["suggested"])
        if block:
            print("\n" + block)
        print("\n" + ("✗ blockers: UI stages (designer explore on an existing product, implement integration, verify E2E, accept "
                      "walkthroughs) must not start. Show this to the user." if blockers else "✓ no blockers"))
    if any(f["code"] == "NO-CONFIG" for f in blockers):
        return 2
    return 1 if blockers else 0


# ----------------------------------------------------------------------------- self-test
def self_test() -> int:
    os.environ["SDLC_SKIP_UI_PROBE"] = "1"  # the self-test must not depend on this machine having a browser
    import http.server
    import socket

    def fail(msg: str, *extra: Any) -> int:
        print("self-test FAILED:", msg, *extra)
        return 1

    y = parse_yaml("gates:\n  test: \"pytest -q\"  # comment\n  e2e: null\napp:\n  widths: [375, 1440]\nlane_rules:\n  ui_paths:\n  - web\n"
                   "  schema_paths:\n    - models\nmcp_adapters:\n  - name: playwright\n    hats: [designer]\nproduct_root: docs/product\n")
    if y["gates"] != {"test": "pytest -q", "e2e": None} or y["app"]["widths"] != [375, 1440] or y["lane_rules"]["ui_paths"] != ["web"] \
            or y["lane_rules"]["schema_paths"] != ["models"] or y["mcp_adapters"] != [{"name": "playwright", "hats": ["designer"]}] \
            or y["product_root"] != "docs/product":
        return fail("parse_yaml", y)
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "frontend", "admin"))
        os.makedirs(os.path.join(td, "frontend", "shared"))
        with open(os.path.join(td, "frontend", "admin", "package.json"), "w") as f:
            json.dump({"scripts": {"start": "react-scripts start", "e2e": "playwright test"},
                       "dependencies": {"react": "18", "react-scripts": "5"}, "devDependencies": {"@playwright/test": "1"}}, f)
        with open(os.path.join(td, "frontend", "shared", "package.json"), "w") as f:
            json.dump({"dependencies": {"react": "18"}}, f)
        with open(os.path.join(td, "sdlc.config.yaml"), "w") as f:
            f.write("gates:\n  test: \"pytest\"\n  e2e: null\n  e2e_reason: \"no E2E suite\"\nartifact_root: .\n")
        r = check(td)
        codes = {f["code"] for f in r["findings"] if f["level"] == "blocker"}
        if codes != {"APP-START", "APP-URL", "E2E"}:
            return fail("old config on a UI project must block on APP-START, APP-URL, E2E", r["findings"])
        e2e_msg = next(f["message"] for f in r["findings"] if f["code"] == "E2E")
        if "contradicted" not in e2e_msg or r["suggested"]["gates"]["e2e"][0] != "npm run e2e --prefix frontend/admin":
            return fail("E2E finding must name the existing e2e script and the contradicted reason", e2e_msg, r["suggested"])
        if r["suggested"]["app"]["base_url"][0] != "http://localhost:3000":
            return fail("react-scripts default port expected", r["suggested"])
        if r["suggested"]["lane_rules"]["ui_paths"][0] != "[frontend/admin]":
            return fail("a UI library without a dev/start script is not an app root", r["suggested"]["lane_rules"])
        if "npm run start --prefix frontend/admin" not in render_suggestion(r["suggested"]):
            return fail("suggestion block must carry the start command", render_suggestion(r["suggested"]))
        # a complete config and a live app pass the probe
        srv = http.server.HTTPServer(("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler)
        port = srv.server_address[1]
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            with open(os.path.join(td, "sdlc.config.yaml"), "w") as f:
                f.write(f"product_root: docs/product\ngates:\n  e2e: \"npm run e2e --prefix frontend/admin\"\napp:\n"
                        f"  start: \"npm start --prefix frontend/admin\"\n  base_url: \"http://127.0.0.1:{port}/\"\n  widths: [375, 1440]\n"
                        "lane_rules:\n  ui_paths: [frontend/admin]\n")
            r = check(td, probe=True)
            if any(f["level"] == "blocker" for f in r["findings"]) or not any(f["code"] == "APP-UP" for f in r["findings"]):
                return fail("complete config with a live app must pass", r["findings"])
        finally:
            srv.shutdown()
            srv.server_close()
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            closed = s.getsockname()[1]
        with open(os.path.join(td, "sdlc.config.yaml"), "w") as f:
            f.write(f"product_root: docs/product\ngates:\n  e2e: \"x\"\napp:\n  start: \"x\"\n  base_url: \"http://127.0.0.1:{closed}/\"\n"
                    "  widths: [375]\nlane_rules:\n  ui_paths: [frontend/admin]\n")
        r = check(td, probe=True)
        if [f["code"] for f in r["findings"] if f["level"] == "blocker"] != ["APP-DOWN"]:
            return fail("a closed port must be APP-DOWN", r["findings"])
        with open(os.path.join(td, "sdlc.config.yaml"), "w") as f:
            f.write("product_root: docs/product\ngates:\n  e2e: \"x\"\napp:\n  start: \"x\"\n  base_url: \"http://127.0.0.1:1/\"\n"
                    "lane_rules:\n  ui_paths: [frontend/admin]\nowners:\n  product-mgmt: 张三\n  marketing: 李四\n  design: <人或团队>\n")
        r = check(td)
        if any(x["code"] == "SIGNALS-PATH" for x in r["findings"]):
            return fail("no signals_path configured must not warn", r["findings"])
        owner_warn = [x["message"] for x in r["findings"] if x["code"] == "OWNERS" and x["level"] == "warn"]
        if len(owner_warn) != 2 or not any("marketing" in m for m in owner_warn) or not any("owners.design" in m for m in owner_warn):
            return fail("owners must warn on an unknown function id and a placeholder, and accept a known one", r["findings"])
        if any(x["level"] == "blocker" and x["code"] == "OWNERS" for x in r["findings"]):
            return fail("owners never blocks: it only names who to ask")
        global _function_ids  # an unsupported registry must be reported, not skipped as "no ids to check"
        real_ids = _function_ids
        def _unsupported() -> set[str]:
            raise ValueError("unsupported workflow schema_version 99")
        _function_ids = _unsupported
        try:
            r = check(td)
        finally:
            _function_ids = real_ids
        if "REGISTRY" not in {x["code"] for x in r["findings"] if x["level"] == "blocker"}:
            return fail("an unsupported registry must be a REGISTRY blocker", r["findings"])
        for value, ok in (("docs/signals", True), ("docs/product/signals", False), (".sdlc/signals", False), ("../x", False)):
            with open(os.path.join(td, "sdlc.config.yaml"), "w") as f:
                f.write(f"product_root: docs/product\nsignals_path: {value}\n")
            warned = any(x["code"] == "SIGNALS-PATH" for x in check(td)["findings"])
            if warned == ok:
                return fail(f"signals_path {value} should {'pass' if ok else 'warn'}")
        os.remove(os.path.join(td, "sdlc.config.yaml"))
        if main_check(argparse.Namespace(project_root=td, probe=False, json=True)) != 2:
            return fail("missing config must exit 2")
    # two UIs: ports from config/default/<name>.yml, app.urls suggestion, probe of every url
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "config", "default"))
        for name, port in (("admin", 9112), ("official", 9113)):
            os.makedirs(os.path.join(td, "frontend", name))
            with open(os.path.join(td, "frontend", name, "package.json"), "w") as f:
                json.dump({"scripts": {"start": "react-scripts start"}, "dependencies": {"react": "18", "react-scripts": "5"}}, f)
            with open(os.path.join(td, "config", "default", f"{name}.yml"), "w") as f:
                f.write(f"{name.upper()}:\n  PORT: {port}\n")
        roots = {r["path"]: (r["port"], r["port_source"]) for r in find_ui_roots(td)}
        if roots.get("frontend/official") != (9113, os.path.join("config", "default", "official.yml")):
            return fail("port must come from config/default/official.yml before the react-scripts default", roots)
        base = "product_root: docs/product\ngates:\n  e2e: \"x\"\napp:\n  start: \"x\"\n  base_url: \"{live}\"\n{urls}  widths: [375]\nlane_rules:\n  ui_paths: [frontend/admin, frontend/official]\n"
        with open(os.path.join(td, "sdlc.config.yaml"), "w") as f:
            f.write(base.format(live="http://localhost:9112/", urls=""))
        r = check(td)
        if not any(x["code"] == "APP-URLS" for x in r["findings"]) or r["suggested"]["app"]["urls"]["official"][0] != "http://localhost:9113":
            return fail("two UI roots without app.urls must warn and suggest per-root URLs", r["findings"], r["suggested"])
        if 'official: "http://localhost:9113"' not in render_suggestion(r["suggested"]):
            return fail("nested urls must render", render_suggestion(r["suggested"]))
        srv = http.server.HTTPServer(("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler)
        live = f"http://127.0.0.1:{srv.server_address[1]}/"
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            with socket.socket() as s:
                s.bind(("127.0.0.1", 0))
                closed = f"http://127.0.0.1:{s.getsockname()[1]}/"
            with open(os.path.join(td, "sdlc.config.yaml"), "w") as f:
                f.write(base.format(live=live, urls=f"  urls:\n    admin: \"{live}\"\n    official: \"{closed}\"\n"))
            r = check(td, probe=True)
            down = [x["message"] for x in r["findings"] if x["code"] == "APP-DOWN"]
            if any(x["code"] == "APP-URLS" for x in r["findings"]) or len(down) != 1 or "urls.official" not in down[0] or "urls.admin" in down[0]:
                return fail("probe must check every app.urls entry and name only the one that is down", r["findings"])
        finally:
            srv.shutdown()
            srv.server_close()
    print("self-test ok")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only v4 check of sdlc.config.yaml (never writes).")
    ap.add_argument("--project-root", default=".")
    ap.add_argument("--probe", action="store_true", help="also request app.base_url")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    return main_check(args)


if __name__ == "__main__":
    sys.exit(main())

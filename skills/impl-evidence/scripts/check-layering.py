#!/usr/bin/env python3
"""分层与依赖倒置（DIP）违规检查器——支持 Python 与 TypeScript/JavaScript。

检查两类架构边界不变量（不替代 architect 与 reviewer 的深模块/职责边界判断）：
  1. 经典单向分层：Router/API → Service → Repository → Model（严禁跨层直调 ORM 或反向依赖上层 API）
  2. 六边形 / DIP 领域核隔离：Domain/Core 层严禁反向依赖 API、Infrastructure/Adapters 或 ORM Model

层按文件路径里最靠近文件的层名识别（目录名，或文件名去掉扩展名后等于层名、以 _<层名> / .<层名> 结尾）：
  api：api / router / routers / routes / endpoints / controllers
  service：service / services / application / usecases
  domain：domain / domains / core / entities
  repository：repository / repositories / repo / repos / dal
  infra：infra / infrastructure / adapters / gateways
  model：model / models / orm

行内含 `sdlc-layer-ignore` 可显式豁免单行特殊装配代码（如组合根 DI 注册）。
测试代码（test/tests/__tests__，test_*.py、*_test.py、*.test.ts、*.spec.ts 等）自动跳过。

用法：python3 check-layering.py <源码目录或文件> [...]
      python3 check-layering.py --self-test
退出码：0 = 通过；否则为违规数（封顶 125）。目标不存在或没有可检查源码文件也算违规——配置了的闸门不能空跑通过。
"""
from __future__ import annotations

import pathlib
import re
import sys
import tempfile

CODE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs"}
SKIP_PARTS = {"__pycache__", "node_modules", "dist", "build", ".next", ".nuxt", ".venv", "venv", "coverage", ".git"}

LAYERS = {
    "api": {"api", "router", "routers", "routes", "endpoints", "controller", "controllers"},
    "service": {"service", "services", "application", "usecase", "usecases"},
    "domain": {"domain", "domains", "core", "entity", "entities"},
    "repository": {"repository", "repositories", "repo", "repos", "dal"},
    "infra": {"infra", "infrastructure", "adapter", "adapters", "gateway", "gateways"},
    "model": {"model", "models", "orm"},
}


def _py_imports(mod: str) -> re.Pattern[str]:
    return re.compile(
        rf"^\s*(?:from\s+(?:[\w.]*\.)?{mod}(?:\.[\w.]+)?\s+import\b|import\s+(?:[\w.]+\.)?{mod}\b)",
        re.M,
    )


def _js_imports(mod: str) -> re.Pattern[str]:
    return re.compile(
        rf"""(?:^\s*import\s+.*?\s+from\s+['"](?:[^'"]*?/)?{mod}(?:/[^'"]*)?['"]|\brequire\(\s*['"](?:[^'"]*?/)?{mod}(?:/[^'"]*)?['"]\s*\))""",
        re.M,
    )


def _rule(layer: str, mod: str, msg: str):
    return (layer, _py_imports(mod), _js_imports(mod), msg)


API_MOD = r"(?:api|routers?|routes|endpoints|controllers?)"
SVC_MOD = r"(?:services?|application|usecases?)"
REPO_MOD = r"(?:repository|repositories|repos?|dal)"
INFRA_MOD = r"(?:infra|infrastructure|adapters?|gateways?)"
MODEL_MOD = r"(?:models?|orm)"

RULES = [
    _rule("api", MODEL_MOD, "Router/API 直接 import ORM 模型（应经 Service 与 DTO/Schema；模型即契约违规 / ISP 违规）"),
    _rule("api", REPO_MOD, "Router/API 越过 Service 直接调 Repository"),
    _rule("service", API_MOD, "Service 反向依赖上层 Router/API（违反单向依赖与 Sans-IO）"),
    _rule("repository", SVC_MOD, "Repository 调 Service（反向依赖）"),
    _rule("repository", API_MOD, "Repository 调 Router/API（反向依赖）"),
    _rule("model", rf"(?:{SVC_MOD}|{REPO_MOD}|{API_MOD}|{INFRA_MOD})", "Model 依赖上层（Service/Repository/API/Infra）"),
    _rule("domain", rf"(?:{API_MOD}|{INFRA_MOD}|{MODEL_MOD}|{REPO_MOD})", "Domain 领域核直接依赖外层（API/Infra/ORM/Repo），违反依赖倒置（DIP）"),
]


def layer_of(path: pathlib.Path) -> str | None:
    stem = re.sub(r"\.(controller|service|repo|repository|model|entity|router|route|adapter)$", r"_\1", path.stem.lower())
    parts = [p.lower() for p in path.parts[:-1]] + [stem]
    for part in reversed(parts):
        for layer, names in LAYERS.items():
            if part in names or any(part.endswith("_" + n) or part.endswith("-" + n) for n in names):
                return layer
    return None


def is_test(path: pathlib.Path) -> bool:
    name = path.name.lower()
    if any(p.lower() in ("test", "tests", "__tests__", "e2e", "fixtures") for p in path.parts[:-1]):
        return True
    return (
        name.startswith("test_")
        or name.endswith(("_test.py", ".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx", ".test.js", ".spec.js"))
        or name == "conftest.py"
    )


def check_file(path: pathlib.Path) -> list[str]:
    layer = layer_of(path)
    if layer is None:
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    is_py = path.suffix.lower() == ".py"
    violations: list[str] = []
    for rule_layer, py_rx, js_rx, msg in RULES:
        if rule_layer != layer:
            continue
        rx = py_rx if is_py else js_rx
        for m in rx.finditer(text):
            lineno = text[:m.start()].count("\n") + 1
            if "sdlc-layer-ignore" in lines[lineno - 1]:
                continue
            violations.append(f"{path}:{lineno}: {msg}")
    return violations


def run(targets: list[str]) -> list[str]:
    violations: list[str] = []
    for target in targets:
        p = pathlib.Path(target)
        if p.is_file():
            files = [p] if p.suffix.lower() in CODE_EXTS else []
        elif p.is_dir():
            files = [
                f for f in sorted(p.rglob("*"))
                if f.is_file()
                and f.suffix.lower() in CODE_EXTS
                and not (set(f.parts) & SKIP_PARTS)
                and not is_test(f.relative_to(p))
            ]
        else:
            violations.append(f"{p}: 目标不存在（检查 sdlc.config.yaml 的 layering_root）")
            continue
        if not files:
            violations.append(f"{p}: 没有可检查的源码文件（.py/.ts/.tsx/.js）")
            continue
        for f in files:
            violations.extend(check_file(f))
    return violations


def self_test() -> int:
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d) / "latest-app" / "backend"
        for rel, body in {
            "app/api/v1/users.py": "from app.models.user import User\n",
            "app/routers/orders.py": "from app.services.orders import OrderService\n",
            "app/repositories/user_repo.py": "from app.services.user import UserService\n",
            "app/services/user.py": "from app.repositories.user_repo import UserRepo\nfrom app.models import User\n",
            "app/services/bad_svc.py": "from app.routers.orders import router\n",
            "app/domain/pricing.py": "from app.infra.stripe_adapter import StripeClient\n",
            "app/api/tests/test_users.py": "from app.models import User\n",
            "app/api/services/billing.py": "from app.models import Invoice\n",
            "web/api/orders.controller.ts": "import { OrderModel } from '../models/order';\n",
        }.items():
            f = root / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(body, encoding="utf-8")
        got = run([str(root)])
        want = ["users.py:1", "user_repo.py:1", "bad_svc.py:1", "pricing.py:1", "orders.controller.ts:1"]
        if len(got) != 5 or not all(any(w in g for g in got) for w in want):
            print("self-test FAILED:", got)
            return 1
        if run([str(root / "missing")]) == [] or run([d + "/latest-app/backend/app/api/tests"]) == []:
            print("self-test FAILED: a missing or empty target must not pass")
            return 1
    print("self-test ok")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        sys.exit(self_test())
    found = run(sys.argv[1:] or ["backend"])
    for v in found:
        print(f"✗ [LAYER] {v}")
    if not found:
        print("✓ 分层与依赖倒置（DIP）检查通过（Python / TS / JS import 方向）")
    sys.exit(min(len(found), 125))

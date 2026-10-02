#!/usr/bin/env python3
"""分层违规检查器——Python 后端的 import 方向是否单向（Router/API → Service → Repository → Model）。

只检查 import 方向，不证明架构合理；架构判断仍由 architect 与 reviewer 做。
层按文件路径里最靠近文件的层名识别（目录名，或文件名去掉 .py 后等于层名、以 _<层名> 结尾）：
  api：api / router / routers / routes / endpoints
  service：service / services
  repository：repository / repositories / repo / repos
  model：model / models
测试代码（目录 test/tests，文件 test_*.py、*_test.py、conftest.py）不检查。

用法：python3 check-layering.py <后端目录或文件> [...]
      python3 check-layering.py --self-test
退出码：0 = 通过；否则为违规数（封顶 125）。目标不存在或没有可检查的 .py 文件也算违规——配置了的闸门不能空跑通过。
"""
import pathlib
import re
import sys
import tempfile

LAYERS = {
    "api": {"api", "router", "routers", "routes", "endpoints"},
    "service": {"service", "services"},
    "repository": {"repository", "repositories", "repo", "repos"},
    "model": {"model", "models"},
}


def _imports(mod):
    return re.compile(rf"^\s*(from\s+(?:[\w.]+\.)?{mod}(?:\.[\w.]+)?\s+import\b|import\s+(?:[\w.]+\.)?{mod}\b)", re.M)


# (所在层, 被禁止 import 的模块, 说明)
RULES = [
    ("api", _imports(r"models?"), "Router/API 直接 import ORM 模型（应经 Service 与 schema/DTO；模型即契约违规）"),
    ("api", _imports(r"(?:repository|repositories|repos?)"), "Router/API 越过 Service 直接调 Repository"),
    ("repository", _imports(r"services?"), "Repository 调 Service（反向依赖）"),
    ("model", _imports(r"(?:services?|repository|repositories|repos?)"), "Model 依赖上层（Service/Repository）"),
]


def layer_of(path):
    parts = [p.lower() for p in path.parts[:-1]] + [path.stem.lower()]
    for part in reversed(parts):
        for layer, names in LAYERS.items():
            if part in names or any(part.endswith("_" + n) for n in names):
                return layer
    return None


def is_test(path):
    name = path.name.lower()
    return (any(p.lower() in ("test", "tests") for p in path.parts[:-1])
            or name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py")


def check_file(path):
    layer = layer_of(path)
    if layer is None:
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    violations = []
    for rule_layer, pattern, msg in RULES:
        if rule_layer != layer:
            continue
        for m in pattern.finditer(text):
            violations.append(f"{path}:{text[:m.start()].count(chr(10)) + 1}: {msg}")
    return violations


def run(targets):
    violations = []
    for target in targets:
        p = pathlib.Path(target)
        if p.is_file():
            files = [p]
        elif p.is_dir():
            files = [f for f in sorted(p.rglob("*.py")) if "__pycache__" not in f.parts and not is_test(f.relative_to(p))]
        else:
            violations.append(f"{p}: 目标不存在（检查 sdlc.config.yaml 的 layering_root）")
            continue
        if not files:
            violations.append(f"{p}: 没有可检查的 .py 文件")
        for f in files:
            violations.extend(check_file(f))
    return violations


def self_test():
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d) / "latest-app" / "backend"
        for rel, body in {
            "app/api/v1/users.py": "from app.models.user import User\n",
            "app/routers/orders.py": "from app.services.orders import OrderService\n",
            "app/repositories/user_repo.py": "from app.services.user import UserService\n",
            "app/services/user.py": "from app.repositories.user_repo import UserRepo\nfrom app.models import User\n",
            "app/api/tests/test_users.py": "from app.models import User\n",
            "app/api/services/billing.py": "from app.models import Invoice\n",
        }.items():
            f = root / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(body)
        got = run([str(root)])
        want = ["users.py:1", "user_repo.py:1"]
        if len(got) != 2 or not all(any(w in g for g in got) for w in want):
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
        print("✓ 分层依赖检查通过（只检查 import 方向）")
    sys.exit(min(len(found), 125))

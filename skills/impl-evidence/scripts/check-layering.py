#!/usr/bin/env python3
"""分层违规检查器——检查 Python 后端代码是否违反分层依赖单向原则。

用法：python check-layering.py <backend目录或文件>
退出码：0 = 通过，违规数 = 非零
"""
import sys, re, pathlib

# 分层依赖规则：允许的 import 方向
ALLOWED = {
    "router":   ["service", "schema", "deps"],      # Router → Service, Schema, Deps
    "api":      ["service", "schema", "deps"],
    "service":  ["repository", "model", "external"], # Service → Repository, ORM
    "repository": ["model"],                          # Repository → ORM
}

VIOLATIONS_PATTERNS = [
    # Router/API 直接 import ORM
    (r"(from\s+platform_core\.models|from\s+backend\.models)\s+import",
     ["router", "api"], "Router/API 直接 import ORM 模型（模型即契约违规）"),
    # Repository 调 Service（反向依赖）
    (r"from\s+backend\.(services|service)\.\w+\s+import",
     ["repository"], "Repository 调 Service（反向依赖）"),
    # Service 返回 ORM 对象给 Router
    (r"from\s+backend\.(models|platform_core\.models)\.",
     ["router", "api"], "Router/API 引用 ORM 模型路径"),
]

def check_file(path):
    """检查单个文件。"""
    violations = []
    t = pathlib.Path(path).read_text()
    rel = str(path).lower()
    for pattern, layers, msg in VIOLATIONS_PATTERNS:
        if any(layer in rel for layer in layers):
            for m in re.finditer(pattern, t):
                line_no = t[:m.start()].count("\n") + 1
                violations.append(f"{path}:{line_no}: {msg}")
    return violations

if __name__ == "__main__":
    targets = sys.argv[1:] if len(sys.argv) > 1 else ["backend/app/api", "backend/services", "backend/repositories"]
    all_v = []
    for target in targets:
        p = pathlib.Path(target)
        if p.is_file():
            all_v.extend(check_file(p))
        elif p.is_dir():
            for f in sorted(p.rglob("*.py")):
                if "__pycache__" in str(f) or "test" in str(f): continue
                all_v.extend(check_file(f))
    if all_v:
        for v in all_v:
            print(f"✗ [LAYER] {v}")
        sys.exit(len(all_v))
    else:
        print("✓ 分层依赖检查通过")
        sys.exit(0)

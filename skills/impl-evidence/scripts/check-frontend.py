#!/usr/bin/env python3
"""前端静态防呆与设计 Token 一致性检查器（零外部依赖）。

检查三类机械可判的常见前端交付缺陷（不替代真实浏览器渲染、视觉走查与 E2E）：
  1. [TOKEN]     非 Token/主题定义文件中硬编码 #hex / rgb() / hsl() 色值（破坏 Design Token SSOT）
  2. [NOOP]      交互事件（onClick/onSubmit/onChange/@click 等）绑定空函数 ()=>{}（外壳按钮假交互）
  3. [CSP-STYLE] JSX/HTML 模板中写死字符串内联 style="..." 或 setAttribute('style', ...)（触发严格 CSP 拦截）

行内或上一行含 `sdlc-frontend-ignore` 注释可显式豁免单处合理例外。
测试目录（test/tests/__tests__/*.test.*/*.spec.*）与构建产物自动跳过。

用法：python3 check-frontend.py <前端目录或文件> [...]
      python3 check-frontend.py --self-test
退出码：0 = 通过；否则为违规数（封顶 125）。目标不存在或无可检查前端文件也判违规（防门禁空跑假绿）。
"""
from __future__ import annotations

import pathlib
import re
import sys
import tempfile

FRONTEND_EXTS = {".tsx", ".jsx", ".ts", ".js", ".vue", ".svelte", ".css", ".scss"}
SKIP_PARTS = {"node_modules", "dist", "build", ".next", ".nuxt", "coverage", "__pycache__", ".git", "vendor", "prototypes"}
TOKEN_FILE_RE = re.compile(r"(token|theme|palette|design-system|variables|tailwind\.config|uno\.config)", re.I)
TEST_FILE_RE = re.compile(r"(\.(test|spec|stories)\.[A-Za-z0-9]+$|^setupTests\.)", re.I)

HEX_COLOR_RE = re.compile(r"(?<![&\w-])#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")
FUNC_COLOR_RE = re.compile(r"\b(?:rgba?|hsla?)\(\s*\d+")
NOOP_HANDLER_RE = re.compile(
    r"""(?:\bon(?:Click|Submit|Change|Confirm|Delete|Select|Save|Close|Cancel)|@(?:click|submit|change))\s*=\s*[{"']?\s*(?:\(\s*\)\s*=>\s*\{\s*\}|function\s*\(\s*\)\s*\{\s*\})"""
)
CSP_INLINE_STYLE_RE = re.compile(
    r"""(?:\bstyle\s*=\s*["'][^"']+["']|\.setAttribute\(\s*["']style["']\s*,)"""
)
IGNORE_MARKER = "sdlc-frontend-ignore"


def is_skipped(path: pathlib.Path) -> bool:
    parts_lower = {p.lower() for p in path.parts[:-1]}
    if parts_lower & SKIP_PARTS or parts_lower & {"test", "tests", "__tests__", "e2e", "fixtures", "mocks"}:
        return True
    return bool(TEST_FILE_RE.search(path.name))


def is_token_source(path: pathlib.Path) -> bool:
    return bool(TOKEN_FILE_RE.search(path.name)) or any(bool(TOKEN_FILE_RE.search(p)) for p in path.parts[:-1])


def check_file(path: pathlib.Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    token_src = is_token_source(path)
    is_style_sheet = path.suffix.lower() in {".css", ".scss"}
    violations: list[str] = []

    for idx, raw in enumerate(lines, 1):
        prev = lines[idx - 2] if idx >= 2 else ""
        if IGNORE_MARKER in raw or IGNORE_MARKER in prev:
            continue
        stripped = raw.strip()
        if stripped.startswith(("//", "/*", "*", "<!--")):
            continue
        # 1. Hardcoded colors outside token definition files (allow CSS custom property declarations `--foo: #...`)
        if not token_src and not re.match(r"^--[\w-]+\s*:", stripped):
            # Ignore URL hash anchors like href="#section"
            cleaned = re.sub(r"""(?:href|to|id|url)\s*=\s*["']#[A-Za-z][\w-]*["']""", "", raw)
            if HEX_COLOR_RE.search(cleaned) or FUNC_COLOR_RE.search(cleaned):
                violations.append(f"{path}:{idx}: [TOKEN] 非 Token 文件硬编码色值（应引用 design-system / CSS 变量语义 Token）")
        # 2. No-op placeholder callbacks on interactive controls
        if not is_style_sheet and NOOP_HANDLER_RE.search(raw):
            violations.append(f"{path}:{idx}: [NOOP] 交互控件绑定空回调 ()=>{{}}（严禁外壳占位按钮）")
        # 3. String inline style attributes risking strict CSP `style-src 'self'` violations
        if not is_style_sheet and CSP_INLINE_STYLE_RE.search(raw):
            violations.append(f"{path}:{idx}: [CSP-STYLE] 字符串内联 style 注入（严格 CSP 下会被拦截，改用 className / Token 类）")
    return violations


def run(targets: list[str]) -> list[str]:
    violations: list[str] = []
    for target in targets:
        p = pathlib.Path(target)
        if p.is_file():
            files = [p] if p.suffix.lower() in FRONTEND_EXTS and not is_skipped(p) else []
        elif p.is_dir():
            files = [
                f for f in sorted(p.rglob("*"))
                if f.is_file() and f.suffix.lower() in FRONTEND_EXTS and not is_skipped(f.relative_to(p))
            ]
        else:
            violations.append(f"{p}: 目标不存在（检查 sdlc.config.yaml 的 frontend_root 或传入路径）")
            continue
        if not files:
            violations.append(f"{p}: 没有可检查的前端源码文件")
            continue
        for f in files:
            violations.extend(check_file(f))
    return violations


def self_test() -> int:
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d) / "web"
        files = {
            "src/styles/tokens.css": ":root { --color-primary: #2563eb; }\n.palette { color: rgb(37, 99, 235); }\n",
            "src/components/Card.tsx": (
                'export function Card() {\n'
                '  return <div style="color: red"><button onClick={() => {}}>Delete</button></div>;\n'
                '}\n'
            ),
            "src/components/BadColor.tsx": (
                'export const x = "#ff0000";\n'
                '// sdlc-frontend-ignore: chart canvas fallback\n'
                'export const allowed = "#00ff00";\n'
            ),
            "src/components/Clean.tsx": (
                'export function Clean({ onRun }: { onRun: () => void }) {\n'
                '  return <a href="#top"><button className="btn-primary" onClick={onRun}>Run</button></a>;\n'
                '}\n'
            ),
            "src/components/Card.test.tsx": 'const mock = <button onClick={() => {}} style="top:0">#123456</button>;\n',
        }
        for rel, body in files.items():
            fp = root / rel
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(body, encoding="utf-8")
        got = run([str(root)])
        expect_tags = ["Card.tsx:2: [NOOP]", "Card.tsx:2: [CSP-STYLE]", "BadColor.tsx:1: [TOKEN]"]
        if len(got) != 3 or not all(any(tag in g for g in got) for tag in expect_tags):
            print("self-test FAILED:", got)
            return 1
        if run([str(root / "missing")]) == []:
            print("self-test FAILED: missing target must fail")
            return 1
    print("self-test ok")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        sys.exit(self_test())
    found = run(sys.argv[1:] or ["frontend"])
    for v in found:
        print(f"✗ [FRONTEND] {v}")
    if not found:
        print("✓ 前端静态防呆与 Token 检查通过（Token 色值 / 空回调 / CSP 内联样式）")
    sys.exit(min(len(found), 125))

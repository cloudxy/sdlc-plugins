#!/usr/bin/env bash
# vendor/install.sh — 按锁文件从上游源头下载原件到 vendor/<来源>/，并逐字节校验
#
# 本仓库不分发任何上游内容：vendor/ 下只提交本脚本、README.md 和各来源的 <来源>.lock.json。
# 锁文件记录维护者审查过的上游仓库、commit、收纳路径和树摘要；本脚本下载同一个 commit 的同一批文件，
# 算出的树摘要必须与锁文件一致才会落盘，否则什么都不写。
#
#   bash vendor/install.sh                       # 安装全部可安装来源（跳过许可证受限的来源）
#   bash vendor/install.sh svg-diagram           # 只装列出的来源
#   bash vendor/install.sh --accept-restricted   # 也下载许可证为 All rights reserved 等受限来源（表示你接受其上游条款）
#   bash vendor/install.sh --check               # 只检查：每个来源 已安装且一致 / 缺失 / 被改动
#   bash vendor/install.sh --force               # 覆盖被本地改动过的来源
#
# 退出码：0 全部完成（或 --check 全部一致）· 1 有来源失败/缺失/不一致 · 2 用法或环境错误
# 依赖：bash、python3，以及 git（首选，只下载需要的文件）或 curl + tar（备用，下载整个 commit 的归档）。
# 维护者机器上由 plugin-updater 每日更新这些来源并改写锁文件；使用者不需要 updater。
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
CHECK=0; FORCE=0; RESTRICTED=0; ONLY=()
for arg in "$@"; do
    case "$arg" in
        --check) CHECK=1 ;;
        --force) FORCE=1 ;;
        --accept-restricted) RESTRICTED=1 ;;
        -h|--help) sed -n '2,19p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*) echo "未知参数: $arg" >&2; exit 2 ;;
        *) ONLY+=("$arg") ;;
    esac
done
command -v python3 >/dev/null 2>&1 || { echo "需要 python3" >&2; exit 2; }

# 与 plugin-updater/scripts/update/vendor.py 的 tree_digest 同一算法
digest() {
    python3 - "$1" <<'PY'
import hashlib, os, sys
root = sys.argv[1]
files = {}
for dp, _dn, fn in os.walk(root):
    for f in fn:
        p = os.path.join(dp, f)
        if os.path.islink(p):
            print("SYMLINK"); sys.exit(0)
        files[os.path.relpath(p, root).replace(os.sep, "/")] = hashlib.sha256(open(p, "rb").read()).hexdigest()
h = hashlib.sha256()
for rel in sorted(files):
    h.update(f"{rel}\0{files[rel]}\n".encode())
print(h.hexdigest() if files else "EMPTY")
PY
}

field() {  # field <lock> <key>  → 标量或空格分隔的列表
    python3 - "$1" "$2" <<'PY'
import json, sys
v = json.load(open(sys.argv[1])).get(sys.argv[2])
print(" ".join(v) if isinstance(v, list) else ("" if v is None else v))
PY
}

restricted() {
    case "$1" in
        MIT|Apache-2.0|BSD-2-Clause|BSD-3-Clause|ISC) return 1 ;;
        *) return 0 ;;
    esac
}

# 取 commit 的选定文件到 $3：git 部分克隆 + 稀疏检出优先，失败退回 codeload 归档
fetch_into() {
    local url="$1" commit="$2" out="$3" include="$4" tmp p owner_repo inner rc
    tmp="$(mktemp -d)"
    if command -v git >/dev/null 2>&1; then
        git -C "$tmp" init -q && git -C "$tmp" remote add origin "$url" \
          && git -C "$tmp" config core.sparseCheckout true \
          && git -C "$tmp" config core.sparseCheckoutCone false \
          && { for p in $include; do echo "/${p%/}"; done > "$tmp/.git/info/sparse-checkout"; } \
          && git -c http.version=HTTP/1.1 -C "$tmp" fetch -q --depth 1 --filter=blob:none origin "$commit" 2>/dev/null \
          && git -C "$tmp" -c advice.detachedHead=false checkout -q FETCH_HEAD 2>/dev/null \
          && { copy_include "$tmp" "$out" "$include"; rc=$?; rm -rf "$tmp"; return $rc; }
        rm -rf "$tmp"; tmp="$(mktemp -d)"
    fi
    case "$url" in https://github.com/*) ;; *) rm -rf "$tmp"; return 1 ;; esac
    command -v curl >/dev/null 2>&1 && command -v tar >/dev/null 2>&1 || { rm -rf "$tmp"; return 1; }
    owner_repo="${url#https://github.com/}"; owner_repo="${owner_repo%.git}"
    if curl -fsSL --retry 3 --connect-timeout 30 --max-time 600 \
         -o "$tmp/src.tar.gz" "https://codeload.github.com/${owner_repo}/tar.gz/${commit}" \
       && tar -xzf "$tmp/src.tar.gz" -C "$tmp" 2>/dev/null; then
        inner="$(ls -d "$tmp"/*/ 2>/dev/null | head -1)"
        [ -n "$inner" ] && { copy_include "${inner%/}" "$out" "$include"; rc=$?; rm -rf "$tmp"; return $rc; }
    fi
    rm -rf "$tmp"; return 1
}

copy_include() {  # copy_include <src-root> <out> <include>
    local src="$1" out="$2" p
    mkdir -p "$out"
    for p in $3; do
        case "$p" in /*|*..*) echo "  锁文件里的路径越界: $p" >&2; return 1 ;; esac
        [ -e "$src/$p" ] || { echo "  上游缺少路径: $p" >&2; return 1; }
        mkdir -p "$out/$(dirname "$p")"
        cp -R "$src/$p" "$out/$(dirname "$p")/" || return 1
    done
}

shopt -s nullglob
LOCKS=("$HERE"/*.lock.json)
[ ${#LOCKS[@]} -gt 0 ] || { echo "vendor/ 下没有锁文件"; exit 2; }
FAIL=0
for lock in "${LOCKS[@]}"; do
    name="$(basename "$lock" .lock.json)"
    if [ ${#ONLY[@]} -gt 0 ]; then
        hit=0; for o in "${ONLY[@]}"; do [ "$o" = "$name" ] && hit=1; done
        [ "$hit" -eq 1 ] || continue
    fi
    url="$(field "$lock" url)"; commit="$(field "$lock" commit)"; want="$(field "$lock" tree_digest)"
    include="$(field "$lock" included_paths)"; license="$(field "$lock" license)"
    target="$HERE/$name"
    have=""; [ -d "$target" ] && have="$(digest "$target")"

    if [ "$CHECK" -eq 1 ]; then
        if [ -z "$have" ] && restricted "${license:-unknown}"; then echo "- ${name}：未安装（许可证「${license:-未声明}」，可选；需要时 --accept-restricted）"
        elif [ -z "$have" ]; then echo "✗ ${name}：未安装（bash vendor/install.sh ${name}）"; FAIL=1
        elif [ "$have" = "$want" ]; then echo "✓ ${name}：已安装，与锁文件一致（${commit:0:12}）"
        else echo "✗ ${name}：与锁文件不一致（被改动或版本不同；bash vendor/install.sh --force ${name}）"; FAIL=1; fi
        continue
    fi
    if [ "$have" = "$want" ]; then
        echo "✓ ${name}：已是锁定版本（${commit:0:12}）"; continue
    fi
    if restricted "${license:-unknown}" && [ "$RESTRICTED" -eq 0 ]; then
        echo "- ${name}：许可证为「${license:-未声明}」，默认不下载；需要时加 --accept-restricted（表示你接受其上游条款）"
        continue
    fi
    if [ -n "$have" ] && [ "$FORCE" -eq 0 ]; then
        echo "✗ ${name}：本地内容与锁文件不一致，未覆盖（确认后加 --force）"; FAIL=1; continue
    fi
    echo ">> ${name}：下载 ${url} @ ${commit:0:12}（许可证 ${license:-未声明}）"
    stage="$(mktemp -d)/$name"
    if ! fetch_into "$url" "$commit" "$stage" "$include"; then
        echo "✗ ${name}：下载失败（网络或上游已删除该 commit），保持原状"; rm -rf "$(dirname "$stage")"; FAIL=1; continue
    fi
    got="$(digest "$stage")"
    if [ "$got" != "$want" ]; then
        echo "✗ ${name}：下载内容的树摘要与锁文件不一致（${got}），未写入"; rm -rf "$(dirname "$stage")"; FAIL=1; continue
    fi
    rm -rf "$target.installing-old"
    [ -d "$target" ] && mv "$target" "$target.installing-old"
    if mv "$stage" "$target"; then
        rm -rf "$target.installing-old"
        echo "✓ ${name}：已安装并校验（${commit:0:12}）"
    else
        [ -d "$target.installing-old" ] && mv "$target.installing-old" "$target"
        echo "✗ ${name}：写入失败，已恢复原状"; FAIL=1
    fi
    rm -rf "$(dirname "$stage")"
done
exit $FAIL

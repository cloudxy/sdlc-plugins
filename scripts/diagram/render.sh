#!/usr/bin/env bash
# render.sh — render SVG diagrams to PNG for a human or reviewer to look at (4th layer of the diagram gate).
#   bash scripts/diagram/render.sh <out-dir> <a.svg> [<b.svg> ...]
# Screenshots an HTML page that embeds the SVG as an <img>: a sandboxed image context runs no scripts and
# loads no external resources, and it avoids the full-page timeout of screenshotting a bare .svg document.
# Exit codes follow ui-evidence.sh: 0 all rendered · 1 a render failed · 2 usage · 3 no screenshot tool.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
[ $# -ge 2 ] || { echo "usage: render.sh <out-dir> <a.svg> ..." >&2; exit 2; }
OUT="$1"; shift
mkdir -p "$OUT" || exit 1
RC=0
for svg in "$@"; do
  [ -s "$svg" ] || { echo "render: ${svg} missing or empty" >&2; RC=1; continue; }
  abs="$(cd "$(dirname "$svg")" && pwd)/$(basename "$svg")"
  name="$(basename "$svg" .svg)"
  tmp="$(mktemp -d)"
  printf '<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:#fff}img{display:block;width:100%%;height:auto}</style><img src="file://%s">\n' "$abs" >"$tmp/${name}.html"
  UI_EVIDENCE_NAME="$name" bash "$HERE/../ui-evidence.sh" "$tmp/${name}.html" "$OUT" 1280 >/dev/null
  r=$?
  rm -rf "$tmp"
  if [ "$r" -eq 0 ]; then echo "rendered: ${OUT%/}/${name}-1280.png — Read it and check text, clipping and overlaps"
  else [ "$r" -eq 3 ] && exit 3; echo "render: ${svg} failed (exit ${r})" >&2; RC=1; fi
done
exit "$RC"

#!/usr/bin/env bash
# ui-evidence.sh — capture screenshots of a URL or local HTML file at several widths (Playwright).
# Used by designer (prototypes, design QA), frontend (integration runs), qa, pm (walkthrough), growth (claims check).
#
#   bash ui-evidence.sh <url|file.html> <out-dir> [widths]      # widths: comma-separated, default 375,1440
#   UI_EVIDENCE_WAIT_MS=1500 bash ui-evidence.sh ...            # extra wait for animations (default 800)
#   UI_EVIDENCE_NAME=j1-step2 bash ui-evidence.sh ...           # file name prefix (default: derived from target)
#
# Exit codes: 0 all captured · 1 capture failed · 2 usage error · 3 Playwright not available (install hint printed)
# After capturing, READ the PNG files and look at them — a screenshot nobody looked at is not evidence.
set -u

usage() { echo "usage: ui-evidence.sh <url|file.html> <out-dir> [widths e.g. 375,1440]" >&2; exit 2; }
[ $# -ge 2 ] || usage
TARGET="$1"
OUT="$2"
WIDTHS="${3:-375,1440}"
WAIT_MS="${UI_EVIDENCE_WAIT_MS:-800}"

case "$WIDTHS" in
  *[!0-9,]*|'') echo "ui-evidence: widths must be comma-separated integers, got '${WIDTHS}'" >&2; exit 2 ;;
esac

if [ -f "$TARGET" ]; then
  ABS="$(cd "$(dirname "$TARGET")" && pwd)/$(basename "$TARGET")"
  URL="file://${ABS}"
else
  URL="$TARGET"
fi

NAME="${UI_EVIDENCE_NAME:-}"
if [ -z "$NAME" ]; then
  NAME=$(printf '%s' "$TARGET" | sed -E 's#^[a-z]+://##; s#[?#].*$##; s#/+$##; s#.*/##; s#\.html?$##; s#[^A-Za-z0-9._-]+#-#g')
  [ -n "$NAME" ] || NAME="page"
fi

mkdir -p "$OUT" || { echo "ui-evidence: cannot create ${OUT}" >&2; exit 1; }

MODE=""
if command -v npx >/dev/null 2>&1 && npx --no-install playwright --version >/dev/null 2>&1; then
  MODE="npx"
elif command -v python3 >/dev/null 2>&1 && python3 -c "import playwright.sync_api" >/dev/null 2>&1; then
  MODE="python"
fi

if [ -z "$MODE" ]; then
  cat >&2 <<'HINT'
ui-evidence: Playwright is not available (exit 3).
Install one of:
  Node   : npm i -D @playwright/test && npx playwright install chromium
  Python : pip install playwright && python3 -m playwright install chromium
Or connect a browser MCP server and list its tools in adapters/extra-tools.json.
Do not claim UI behaviour without screenshots — record this as an open question instead.
HINT
  exit 3
fi

FAILED=0
OLDIFS=$IFS
IFS=','
for W in $WIDTHS; do
  IFS=$OLDIFS
  if [ "$W" -lt 600 ]; then H=812; else H=900; fi
  FILE="${OUT%/}/${NAME}-${W}.png"
  if [ "$MODE" = "npx" ]; then
    npx --no-install playwright screenshot --full-page --viewport-size="${W},${H}" --wait-for-timeout="$WAIT_MS" "$URL" "$FILE" >/dev/null 2>&1
    RC=$?
  else
    python3 - "$URL" "$FILE" "$W" "$H" "$WAIT_MS" <<'PY'
import sys
from playwright.sync_api import sync_playwright
url, out, w, h, wait_ms = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": w, "height": h})
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(wait_ms)
    page.screenshot(path=out, full_page=True)
    browser.close()
PY
    RC=$?
  fi
  if [ "$RC" -eq 0 ] && [ -s "$FILE" ]; then
    echo "screenshot: ${FILE} (${W}px, ${MODE})"
  else
    echo "ui-evidence: capture failed for ${URL} at ${W}px (exit ${RC})" >&2
    FAILED=1
  fi
  IFS=','
done
IFS=$OLDIFS

[ "$FAILED" -eq 0 ] || exit 1
echo "ui-evidence: done — now Read each PNG and look at it before judging."
exit 0

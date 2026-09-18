#!/usr/bin/env bash
# health-check.sh — 插件健康门禁（违规计退出码；警告不计）
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/scripts/health_check.py" "$ROOT"

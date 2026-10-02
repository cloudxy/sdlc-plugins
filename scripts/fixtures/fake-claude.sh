#!/usr/bin/env bash
# Stand-in for the `claude` CLI in behavior_smoke tests: prints a fixed stream-json transcript, never calls a model.
#   FAKE_MODE=malformed   non-JSON output and exit 1 (a host failure, not a scenario result)
#   FAKE_COST=<usd>       total_cost_usd of the result event (default 0.25)
#   FAKE_REPLY=<text>     final reply text (default names the method file the prompt points at)
set -u
if [ "${1:-}" = "--version" ]; then echo "0.0.0 (fake claude)"; exit 0; fi
if [ "${FAKE_MODE:-}" = "malformed" ]; then echo "not json at all"; exit 1; fi
prompt=""
while [ $# -gt 0 ]; do
  if [ "$1" = "-p" ]; then shift; prompt="${1:-}"; fi
  shift
done
reply="${FAKE_REPLY:-我读了方法文件，按其中规则回复。}"
python3 - "$reply" "${FAKE_COST:-0.25}" "$prompt" <<'PY'
import json, sys
reply, cost, prompt = sys.argv[1], float(sys.argv[2]), sys.argv[3]
print(json.dumps({"type": "system", "subtype": "init", "model": "fake-model", "tools": ["Read"]}))
print(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": reply}]}}))
print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": reply,
                  "total_cost_usd": cost, "duration_ms": 1200, "prompt_chars": len(prompt)}))
PY

# Working on sdlc-workflow itself

For sessions that edit this plugin. Projects that use the plugin load its skills, commands and agents, not this file.

- Start at [maintainers/README.md](maintainers/README.md): the method change ledger, the gate catalog, rejected ideas (`maintainers/out-of-scope/`) and the review cadence.
- Earlier plans, decisions and evaluation evidence live outside the repository, in the maintainer's archive `~/Documents/grok-files/sdlc-workflow/<date>-…/`. Read the relevant record before stating how an earlier round went or proposing something it may already have decided.
- A change is done when `bash scripts/health-check.sh`, every `python3 scripts/test_*.py` and `bash scripts/test-check-sdlc.sh` (also under `LC_ALL=zh_CN.UTF-8 /bin/bash`) pass. Method text changes also need a ledger record and, when they change behavior, a `scripts/behavior_smoke.py` comparison.

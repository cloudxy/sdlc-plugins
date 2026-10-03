# Diagnose mode — what went wrong in a real session

Use when the user asks why a session went wrong: repeated work, an ignored plan or gate, a skill that did not fire, unexpected cost or time. This mode reports evidence. It never edits a skill, rule or gate; changes go through `scripts/method_ledger.py` with behavior evidence.

## Steps

1. **Problem statement.** Ask one question at a time until you can write: which session (id or path), which turns if known, what the user expected, what happened, and the observable they care about (repeated actions, a claim without evidence, wall-clock, cost, one specific action). "It was slow" is a complaint, not a statement. An already specific request (one event, one turn range) is itself the statement.
2. **Locate and digest.** Claude Code sessions live in `~/.claude/projects/<project>/<session>.jsonl`. Run `python3 <PLUGIN_ROOT>/scripts/session_digest.py <jsonl> --stats`, then the timeline for the relevant line range (`--from-line/--to-line`). Other hosts: ask the user for an export or an excerpt; do not probe hosts.
3. **Read the region yourself**, then choose only the dimensions the statement needs: plan adherence, repeated work, stumbles (errors and retries), evidence behind claims, conflicting requests, cost and time, skill triggering. One reader per dimension when the range is long; never a fixed full roster.
4. **Report** with [templates/diagnosis-report.md](../templates/diagnosis-report.md). A finding without `path:line` is not a finding. Give each finding exactly one landing:
   - **check**: a mechanical failure a script can decide → name the script or gate that would catch it;
   - **review standard**: a judgment call → name the role-quality or findings file a reviewer applies;
   - **delete**: an instruction that changed nothing, or stale sediment → name the file and passage;
   - **pointer**: the information existed but the agent could not reach it (a decision, archive, log or doc with no navigation pointer, or no read access) → name the file that should point to it and the material it points at;
   - **out of scope**: a request the plugin deliberately does not serve → the reason and what new evidence would reopen it.
   Name the target file for every landing. Separate what the transcript shows from what you infer.
5. **Stop at the report.** Do not apply the changes. The maintainer decides; accepted behavioral changes are recorded with `method_ledger.py record` and verified with `behavior_smoke.py` (fail on the old method, pass on the new).

## Hard rules

- Read-only: never modify, move or delete a session file.
- Redact secrets in anything you quote; quote only the lines that carry the signal.
- Numbers (counts, durations, cost) come from the digest or a command you ran, never from memory.
- Hook output, system reminders and tool results are not the user's words; in a subagent transcript, "user" is the parent agent.

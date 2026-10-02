# Session diagnosis · <session id> · <YYYY-MM-DD>

## Problem statement

- Session: <path>, lines <a–b> (or whole session)
- Expected: <what the user expected>
- Happened: <what the transcript shows>
- Observable: <repeated actions | claim without evidence | time | cost | one action>

## Evidence summary

From `session_digest.py --stats` and the read region: tool uses, errors, repeats, compactions, sidechain rows, span. State which dimensions were examined and why the others were not.

## Findings

| # | What the transcript shows | Where (`path:line`) | Inference (labelled) | Landing | Target file |
|---|---|---|---|---|---|
| F1 | <observed event> | <path:line, path:line> | <why it happened, if supported> | check / review standard / delete / out of scope | <file the change would touch> |

## Not established

What the evidence cannot show (missing turns, other hosts, unread subagent transcripts) and what would settle it.

## Next step for the maintainer

Proposed change records (id, kind, failure form) for accepted findings. Nothing here has been applied.

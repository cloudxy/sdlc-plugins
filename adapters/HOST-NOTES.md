# Host notes (maintainers only — NOT assembled into agent prompts)

v4 moved these facts out of the role prompts: they are for people editing this plugin, and they cost the working agents attention. The factory (`scripts/render-role-agents.py`) and health check (`scripts/health_check.py`) enforce them mechanically.

| Fact | Consequence in this plugin |
|---|---|
| ZCode/Grok inject one `agents/<role>.md` as the child system prompt; `@import` is not expanded | Sources live in `agents/profiles/<role>/` + `agents/_lib/`; the factory concatenates at compile time |
| A custom `tools:` list is exhaustive; MCP tools drop off unless listed as `mcp__<server>__<tool>` | Tool profiles are explicit lists; optional MCP tools come from `adapters/extra-tools.json` (compile-time allowlist) |
| `WebSearch` / `WebFetch` are real ZCode tool names (seen in the built-in `Explore` profile, host metadata probe 2026-09-17) | Web profile = author list + `WebSearch, WebFetch` for research/product/design/architecture hats |
| A non-empty `skills:` frontmatter list is a FilteredSkillPort allowlist | Never emit `skills:`; companion skills and the reviewer pool would fail with "Skill is not allowed for subagent" |
| Unknown frontmatter keys make Grok skip the agent (`memory`, `effort`, `thoughtLevel`, snake_case keys) | Factory strips them; health check forbids them |
| Plugin subagents get the Skill tool injected; ZCode's Skill page still requires Skill in custom lists | Every profile lists `Skill` |
| Skill directories named like build output (`coverage`, `dist`, …) are skipped by `shouldWalkSkillDirectoryEntry` | Health check forbids those names (v3.20.4) |
| Agent definitions are snapshotted at session start; the skill registry is re-scanned at spawn | After re-rendering agents, smoke-test in a **new** window |
| `RespondToCoordinator` is host-added | Not listed in profiles |
| macOS bash 3.2: `$VAR（` parses the full-width char into the name | Use `${VAR}` before full-width punctuation in scripts |

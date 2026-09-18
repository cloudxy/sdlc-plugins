# SubAgent design (Hermes + platform synthesis)

This is the contract for **source files + the assembled host adapter**. It is adapted from Hermes Agent (Nous / cloudxy fork), OpenClaw workspace files, Anthropic agent prompts, Grok Build subagents, and this repo's `.claude/IDENTITY.md` + `SOUL.md` + `MEMORY.md`. We do **not** copy Hermes' runtime (gateway, cron, memory tool). We copy the **file taxonomy and prompt stack**, then map them onto hosts that only inject one markdown file as the child system prompt.

## v4 principles

1. **Role prompts carry craft, not host plumbing.** Up to v3 roughly 90% of every agent file was host mechanics (ZCode allowlists, tool-profile rationale) and 10% role. Host facts now live in `adapters/HOST-NOTES.md` (maintainers only); the prompt keeps the role's mission, refuse list and red lines.
2. **An excellence bar, not only a refuse list.** Negative rules prevent mistakes; they do not produce good work. Each professional skill owns its quality criteria; both the producer and the reviewer load them. IDENTITY does not repeat those criteria.
3. **Product context tier.** Between project context (`AGENTS.md`) and feature inputs sits the product layer (`product_root`): strategy, feature map, growth, design system, architecture, domain model, data. Hats read it first and keep the files they own true.
4. **Diverge, then converge.** Creative hats produce real alternatives and recommend one; missing business rules become recommended defaults marked 待确认, not stop signs.
5. **Evidence from the world and from the build.** Research, product, design and architecture hats have web tools; UI work is judged from screenshots of rendered screens.

## Source vs assembled (extract, then render)

Grok / ZCode inject **one** `agents/<role>.md` as the child system prompt. That is the host constraint, not the authoring model. Authoring follows Hermes / OpenClaw: **who / how it talks / what it learned / what the project needs** live in separate files; a factory concatenates them.

| Layer | Source (edit these) | Assembled / runtime | Hermes / OpenClaw analogue |
|---|---|---|---|
| **SOUL** 性格 | `agents/profiles/<role>/SOUL.md` | `## SOUL` in `agents/<role>.md` | Hermes `~/.hermes/SOUL.md` (slot #1). OpenClaw `SOUL.md`. This repo `.claude/SOUL.md` |
| **分身** IDENTITY | `agents/profiles/<role>/IDENTITY.md` + spawn frontmatter | `## IDENTITY` + YAML (`name`, `tools`, `permission_mode`) | OpenClaw `IDENTITY.md` (structured badge). This repo `.claude/IDENTITY.md`. Hermes folds this into SOUL; we split hard vs soft like OpenClaw |
| **Loop / Tools / Skills / Contract** | `agents/_lib/{LOOP,TOOLS,SKILLS,CONTRACT}.md` (+ `adapters/extra-tools.json` compile-time MCP allowlist) | matching `##` sections; tools in frontmatter | Hermes stable tier (tools + skills index) |
| **宿主事实** | `adapters/HOST-NOTES.md` | **not assembled** — maintainers only | — |
| **产品层** | `<product_root>/…` (project repo) | packet `product_context` / `product_writes` | Hermes context tier, product-scoped |
| **记忆 protocol** | `agents/_lib/MEMORY-writer.md` or `MEMORY-reviewer.md` | `## Memory` | Hermes memory *tool protocol*; not the facts |
| **记忆 facts** | — (role writes at hat end) | `<feature>/memory/<role>.md` (cap 2200). Reviewer/qc: **no file** | Hermes `MEMORY.md` (volatile snapshot). Grok `~/.grok/memory/` is host-level; SDLC memory is per-role artifacts |
| **上下文** | 仓库 `AGENTS.md` / `CLAUDE.md` | `agents_md: true` (host injects). **No** per-role `CONTEXT.md` | Hermes context tier. Do not paste into SOUL |
| **USER** | 不按角色建 | 不注入 specialist | Hermes `USER.md` is the operator. Specialists do not own it |

Edit identity or voice in `agents/profiles/<role>/`. Re-run `python3 scripts/render-role-agents.py`. Existing `IDENTITY.md` / `SOUL.md` are never overwritten by the renderer.

Do **not** hand-edit `agents/<role>.md`.

## What a SubAgent is

| Platform | Primitive | What we take |
|---|---|---|
| **Hermes** | Prompt tiers: stable (SOUL + tools + skills index) → context (AGENTS.md) → volatile (MEMORY/USER snapshot). Skills = procedures. Memory = facts, bounded. Profiles isolate state. Delegated workers skip global SOUL. | Slot order. SOUL ≠ AGENTS.md. Memory ≠ skill. Bound MEMORY. Progressive skill load. |
| **Anthropic AgentDefinition** | `description` (when to delegate, keep short, `Use proactively`) + `prompt` (system) + `tools` / `disallowedTools` + `skills` (preload full SKILL.md; unlisted still via Skill tool) + `maxTurns` + optional `memory: user\|project\|local`. Subagent has its own window and returns a summary. | description 自动委派；审查者 tools allowlist + disallowedTools。本插件**不发射** `skills:`：ZCode 把非空列表当 FilteredSkillPort allowlist，会挡住伴生做法与 reviewer 池。不写 `memory:` YAML（Grok/ZCode 未知键会 skip）。角色学习记忆用文件协议。 |
| **BigModel Coding Plan** | Subagent = 独立执行单元、上下文隔离、只向主会话返回摘要。Skills = 可复用知识/流程（Reference vs Action），可预载进 Subagent。Agent 循环：获取上下文 → 执行操作 → 验证结果。角色级记忆隔离。description 启用自动委派；工具只给实际需要的。 | Loop 五步对齐该循环。Return 只摘要。写作者/审查者记忆隔离。 |
| **Grok Build** | `agents/*.md` = session: model, tools, prompt. Spawn = independent context. `resume_from` same type only. Personas overlay tone. Plugin type = `plugin-name:agent-name`. | Frontmatter (`name`, `description`, `color`, `tools`, `permissionMode`). **Omit `skills:`** (ZCode allowlist). Unknown keys (`agents_md`, `prompt_mode`, `permission_mode`) **skip the agent**. Spawn type `sdlc-workflow:<role>`. Isolation `none`. |
| **OpenAI Agents** | Agent = name + instructions + tools + handoffs + output contract. | Named handoff (refuse list). Structured return: paths + summary + open_questions. |

Hermes' global `SOUL.md` is one personality for one home. **Our specialists each have a SOUL.** A delegated `sdlc-workflow:dba` must not inherit the orchestrator's voice. That is the opposite of Hermes' `skip_soul` on generic workers — and it is correct here, because the child *is* the specialist.

## Prompt stack (encoded in assembled `agents/<role>.md`)

Hosts inject the whole file. Order is the stack. Do not reorder.

| Slot | Section | Source | Hermes analogue | Volatile? |
|---|---|---|---|---|
| 1 | **SOUL** | `profiles/<role>/SOUL.md` | `SOUL.md` | No — tone, never-do |
| 2 | **IDENTITY** | `profiles/<role>/IDENTITY.md` | OpenClaw `IDENTITY.md`; Hermes folds into SOUL | No — generated assignments, mission, refuse, red lines |
| 3 | **Loop** | `_lib/LOOP.md` | turn loop | No — orient (skill + product context) → work (diverge → converge) → check (excellence bar) → write back → return |
| 4 | **Tools** | `_lib/TOOLS.md` | tool-aware guidance | No — capability, not a tutorial |
| 5 | **Skills** | `_lib/SKILLS.md` | skills index | No — *how* to work; load SKILL.md on demand |
| 6 | **Memory** | `_lib/MEMORY-*.md` | MEMORY.md *protocol* | Protocol no; facts file yes |
| 7 | **Contract** | `_lib/CONTRACT.md` | output schema | No |

**Project context** is not a section in the agent file. `agents_md: true` already injects `AGENTS.md` / `CLAUDE.md` (Hermes "context" tier). Do not paste the constitution into SOUL. Do not create `agents/profiles/<role>/CONTEXT.md`.

**USER.md** is the operator profile. Specialists do not own it. Do not write "the operator prefers …" into role memory.

## File taxonomy (what goes where)

| File | Holds | Who writes | When seen |
|---|---|---|---|
| `agents/profiles/<role>/IDENTITY.md` | 分身：帽子、职责、拒绝、红线 | Plugin authors | Assembled into slot 2 |
| `agents/profiles/<role>/SOUL.md` | 性格 | Plugin authors | Assembled into slot 1 |
| `agents/_lib/*.md` | Shared loop / tools / skills / memory protocol / contract | Plugin authors | Assembled into slots 3–7 |
| `agents/<role>.md` | Host adapter = frontmatter + stack | **Factory only** (`render-role-agents.py`) | Child system prompt |
| `skills/<proc>/SKILL.md` | Procedure (how) — named by artifact, not hat | Plugin authors | Skill tool invoke, or fallback Read |
| `<feature>/memory/<role>.md` | Facts this role learned on this feature (what) | The role, after a successful hat | Read at start of next spawn; **cap 2,200 chars** |
| `<product_root>/*` | Durable product facts: value path, journeys, positioning, design system, architecture, domain model, data | The owning hat (see `product-layer.md`) | Every packet's `product_context` |
| `spec.md` / `contract.md` / `state.yaml` | Shared team facts | The producing hat | Caller lists as Inputs |
| Project `AGENTS.md` | Repo conventions (上下文) | Humans | `agents_md: true` |
| Pitfalls `references/auto-agents-pitfalls.md` | Verified procedures/traps | Role, only with code+test/ESC/gate | Skill progressive load |

Hermes: memory is "what", skills are "how". Same split. Do not copy AGENTS.md sentences into role memory. Do not copy SKILL.md into SOUL.

## Memory rules (Hermes, bounded)

- Frozen snapshot: read the memory file **once at start**. Writes this session land on disk; the next spawn sees them. Do not re-read in a loop.
- Cap **2,200 characters**. If a write would overflow, consolidate first (merge overlapping bullets, drop stale).
- Entries are compact facts, separated by `§` or short bullets.
- **Save:** decisions this role owns, environment quirks that bit this role, output paths, open questions still this role's.
- **Skip:** operator preferences (USER), procedures (skill), session temp paths, dumps, anything already in spec/contract/AGENTS.md, unverified guesses.
- Reviewer / qc: **no memory file**. G-fresh dies if they read producer `memory/*.md`.

## Loop (every hat)

1. **Orient（获取上下文）** — Invoke `primary_skill` (Read `PLUGIN_ROOT/skills/<proc>/SKILL.md` if Skill fails). Read `product_context` first, then inputs. Writers read their memory once.
2. **Work（执行操作）** — Stay in role. Creative work diverges before it converges; missing rules become recommended defaults marked 待确认.
3. **Check（验证结果）** — Self-check **and** excellence bar. Code/UI hats keep command + exit code and look at screenshots.
4. **Write back（回写）** — Writers update the product files they own, return delta rows (the manager logs `product-delta.md` and `CHANGELOG.md`), rewrite memory under the cap. Reviewer/qc skip.
5. **Return（摘要）** — paths + summary + decisions + open_questions with recommended defaults. No raw dumps, no half artifacts.

## What we deliberately do not take from Hermes

- Messaging gateway, cron, Honcho, session FTS5, skill hub, `skill_manage` creating skills at runtime.
- Mid-session system-prompt mutation (breaks Grok/Anthropic prefix cache). Memory writes are files, not prompt edits.
- Generic worker that strips SOUL on delegate.
- A real `memory` tool — hosts here expose Read/Write. The protocol in the agent body is the tool.

## Renderer

`python3 scripts/render-role-agents.py` assembles role prompts. Metadata comes from `workflow/registry.json`, tool profiles from `adapters/zcode.json`, identities and voices from `agents/profiles/<role>/`, and shared behavior from `_lib/`. The renderer has no seed copies and never overwrites source profiles. Do not hand-fork `agents/*.md`.

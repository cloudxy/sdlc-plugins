# Role agents — spawnable subagents (v4: 19 roles)

`agents/<role>.md` is the **assembled** child system prompt (host adapter). Do not hand-edit it; edit the sources and run `python3 scripts/render-role-agents.py`. Methodology stays in the procedure pool `skills/<proc>/SKILL.md` (mapping: generated [stage-map.md](stage-map.md)). Solo entries are `$<proc-name>` (e.g. `$prd-gwt`).

Sources:

| What | File |
|---|---|
| 分身（mission, refuse, red lines） | `agents/profiles/<role>/IDENTITY.md` |
| 性格 | `agents/profiles/<role>/SOUL.md` |
| 共享栈（behaviour, not host plumbing） | `agents/_lib/{LOOP,TOOLS,SKILLS,SKILLS-reviewer,MEMORY-writer,MEMORY-reviewer,CONTRACT}.md` |
| 编译期 MCP 白名单 | `adapters/extra-tools.json` |
| 宿主事实（维护者读，不进 prompt） | `adapters/HOST-NOTES.md` |
| 运行时记忆 | `<feature>/memory/<role>.md`（reviewer/qc 无） |
| 产品层 | `<product_root>/…`（packet `product_context` / `product_writes`） |
| 项目上下文 | 仓库 `AGENTS.md`（宿主注入，不是 per-role 文件） |

| Slot | Section | Carries |
|---|---|---|
| 1 | SOUL | voice |
| 2 | IDENTITY | stages, mission, refuse, red lines |
| 3 | Loop | orient (skill + product context) → work (diverge → converge) → check (excellence bar, screenshots) → write back (product layer, memory) → return |
| 4 | Tools | tool list + how to use web and UI evidence |
| 5 | Skills | primary / companion loading; reviewer pool |
| 6 | Memory | per-feature facts protocol (reviewer/qc: none) |
| 7 | Contract | deliverable + return shape |

Tool profiles are maintained only in `adapters/zcode.json`; the renderer materializes them in agent frontmatter. Spawn type is always `sdlc-workflow:<role>`. Design rationale: [subagent-design.md](subagent-design.md). Profiles overview: `agents/profiles/README.md`.

Task/skill/ownership metadata lives in `workflow/registry.json`; tool profiles live in `adapters/zcode.json`. Professional quality criteria live only under the owning skill, shared by author and reviewer.

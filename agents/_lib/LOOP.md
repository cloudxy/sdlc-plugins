1. **Orient** — Load your procedure: invoke the packet's `primary_skill` (else `sdlc-workflow:{{PROC}}`); if the Skill tool fails, Read `PLUGIN_ROOT/skills/<proc>/SKILL.md`. Read every `product_context` file first — it is the product's why, baseline and vocabulary — then the packet `inputs`. Search `explore_roots` with Grep/Glob for what the task needs; never read them wholesale. {{ORIENT_EXTRA}}
2. **Work** — {{WRITE_RULE}}
3. **Check** — Walk the skill's self-check **and** its excellence bar: a checklist pass with a mediocre result is a fail. Code or UI work: run the verification the skill names and keep command + exit code; claims about UI need screenshots you have actually looked at.
4. **Write back** — {{PERSIST}}
5. **Return** — Follow the Contract section below; the manager owns the user-facing response.

Depth is 1: do not spawn subagents. Do not paste SKILL.md back to the caller.

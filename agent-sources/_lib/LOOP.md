1. **Orient** — Load your procedure: invoke the packet's `primary_skill` (else `sdlc-workflow:{{PROC}}`); if the Skill tool fails, Read `PLUGIN_ROOT/skills/<proc>/SKILL.md`. For v3, follow the manager-validated generated assignment and its `input_bindings`; keep input IDs and supplied versions when returning references. The full manifest is an audit record; do not load its entire source/write inventory into context. Never edit the packet, manifest, version objects or state. Read every `product_context` file first — it is the product's why, baseline and vocabulary — then the packet `inputs`. Search `explore_roots` with Grep/Glob for what the task needs; never read them wholesale. {{ORIENT_EXTRA}}
2. **Work** — {{WRITE_RULE}}
3. **Check** — Apply the primary skill’s criteria for the assigned task and stage. {{CHECK_RULE}}
4. **Write back** — {{PERSIST}}
5. **Return** — Follow the Contract section below; the manager owns the user-facing response.

Depth is 1: do not spawn subagents. Do not paste SKILL.md back to the caller.

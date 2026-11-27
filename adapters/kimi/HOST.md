## Host (Kimi Code)

- Run as `{{AGENT}}`. Packets keep logical names `sdlc-workflow:<role>` and `sdlc-workflow:<skill>`. In project-link mode the Skill tool takes the bare skill name; drop `sdlc-workflow:` when invoking it. If discovery or invocation fails, Read `PLUGIN_ROOT/skills/<skill>/SKILL.md` and relevant references.
- Use the listed Kimi tools. Optional MCP tools are available only when their server is connected. Resolve PLUGIN_ROOT from the real path of SKILL.md; no plugin environment variable is assumed for project links.
- Do not delegate: the tool allowlist excludes Agent/AgentSwarm and `subagents: []` disables nested dispatch.{{READ_ONLY}}
- Your final message is the complete, self-contained handoff to the manager, including actual outputs, checks and anything still unverified.

# Legacy packet v2

```
## SPAWN PACKET v2
hat: <spawn_role>
stage: <stage-id from stage-map.md>
task: <explore|specify|walkthrough|design-qa|claims-check|positioning|launch|T-n|…>
subagent_type: sdlc-workflow:<spawn_role>
intent_quote: "<user's last substantive message, ≤200 chars>"
lane: L1|L2|L3|L4
feature_dir: <abs>
PLUGIN_ROOT: <abs>
constitution: <abs or none>
product_root: <abs>
project_root: <abs>          # actual code repository, required when source_writes is nonempty
source_writes: []            # scoped relative project files/subdirectories for registered source-writing tasks
product_context:            # read first — defaults in product-layer.md
  - <abs>
product_writes:             # files this hat owns and must keep true; empty for reviewer/qc
  - <abs>
lane_file: <ui|api|ai|model|none>
slice_integrator: <one implementation role, required for implement tasks>
primary_skill: sdlc-workflow:<proc>
companion_skills: []        # only what the contract lists: read allowed companions from the registry; discovery prototypes have their own registered task
inputs:   # files the hat must read — never directories; include every contract `reads` path
  - {path: <abs>, required: true|false}
explore_roots:              # directories it may search with Grep/Glob, not read wholesale
  - <abs>
deliverable_paths:
  - <relative to feature_dir>   # implement: 03-impl/T-<n>-<role>-evidence.md (one file per lane)
evidence_required:          # copy the contract's `evidence` list (web | screenshots | running_app | e2e); add, never drop
  - <kind>
visuals: []   # diagrams this task draws (contract `visuals`; trust-boundary is required when q_security: yes).
    # Non-empty → add contract.diagram.inputs to inputs, contract.diagram.deliverable to
    # deliverable_paths and contract.diagram.check to success_checks. A diagram is a view of its
    # source: draw it only when it removes ambiguity for the next hat.
imagery: []   # generated images (contract `imagery`; never required). Non-empty → add contract.image
    # inputs/deliverable/check like visuals. Not a rendered direction, screenshot or UI
    # contract. Not authorized → ask the operator for /sdlc-grok login; a hat never logs in.
forbidden:
  - Do not spawn further subagents (host depth 1).
  - Do not invoke procedure skills beyond primary_skill and companion_skills (reviewer/qc may load any to judge; debug_protocol adds sdlc-workflow:debug).
  - Do not Write outside deliverable_paths, product_writes, source_writes and the assigned memory_file (reviewer/qc: do not Write at all).
  - Do not read <feature>/memory/*.md unless it is your own memory_file.
memory_file: <abs or empty>
debug_protocol: <abs or empty>
success_checks:
  - each deliverable_paths exists on disk
  - <the contract's success_check with the real paths filled in>
return: output paths + summary + decisions + open_questions (strategic → Q-* 待确认 + options + recommendation; operational → default applied) + product-delta rows + lesson rows (verified traps only)
```

**Apply the task contract to its actual scope.** A packet never waives evidence required by the resolved task and participation flags — no "smoke run: no WebSearch needed", no "URLs optional", no "fall back to reading source code". To save cost, ask for a shorter artifact. Save every packet to `<feature>/packets/YYYY-MM-DD-HHMMSS-<stage>-<hat>-<unique>.md` and run `python3 <PLUGIN_ROOT>/scripts/check_packet.py <file>` before spawning. It rejects waivers like these, a missing or mismatched check-task line (`workflow.py contract` prints the exact `success_check`), an `evidence_required` list shorter than the contract's `evidence`, deliverables outside the feature directory, directory inputs, oversized `product_context`, writes to files a hat does not own (including `product-delta.md` and `CHANGELOG.md`, which only you write), and `--hat <role>`. Errors → fix the packet; never spawn around them.

`subagent_type` is always the qualified name. Unknown type → one `general-purpose` fallback that Reads `PLUGIN_ROOT/agents/<role>.md` and the primary SKILL.md; record `host_spawn`. Native and fallback both succeeding for one hat is a dual-dispatch defect. Reviewer and qc: no `memory_file`, no `product_writes`; write their deliverable from the final message before any other spawn. For qc you run `skills/coverage-matrix/scripts/check-matrix.py` and paste its output into the packet. `mcp_adapters` in the config is a warning list only.


V2 applies only when the resolved registry task has no `protocol_required`. Pilot tasks cannot downgrade by removing version fields. See [task-protocol.md](task-protocol.md) for v3.

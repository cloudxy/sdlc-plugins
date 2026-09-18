# Threat model — lightweight STRIDE at shape time

Read this when the lane judge says **Q-security = yes**: new external contract (Q3), auth/tenant surface (Q2), or irreversible operation (Q4). It is a Reference, not a SKILL and not a new hat (design A: security depth is constitution + reviewer dimension 4 + this procedure). The architect reads it at shape; the reviewer re-reads it for dimension-4 depth. Output lands in **existing artifacts** — no new files.

Purpose: a security major found at review costs a full rework round; the same threat named in `contract.md` at shape costs one line.

## The walk (30 minutes at shape, not a security program)

1. **List data flows.** For each module boundary in `contract.md`: what data crosses, in which direction, who is on each side. Keep it to the flows this feature adds or changes.
2. **Mark trust boundaries.** A crossing where the other side is not your code: user input, third-party API, queue consumer, browser, agent tool call. Every finding below attaches to a numbered boundary.
3. **Per boundary, ask the six questions (STRIDE):**
   - **Spoofing** — can the caller be someone else? (authn on every boundary or an explicit delegation note)
   - **Tampering** — can data change in transit/at rest? (signature, checksum, immutable audit)
   - **Repudiation** — can the actor deny the action? (audit log with actor id)
   - **Info disclosure** — does the response leak more than the FR asks? (field allowlists, tenant isolation, error messages without internals)
   - **Denial of service** — can one request be expensive? (pagination, rate limit, bounded loops on user input)
   - **Elevation** — can the action exceed the caller's role? (server-side permission check, not UI hiding)
4. **Write findings into existing artifacts**, one line each, tagged `[SEC-n]`:
   - Mitigation that belongs to a module → that module's section in `contract.md` (or the API contract field).
   - A constraint every implementer must satisfy → NFR-security rows in the spec (via open_questions to pm — you do not edit the spec).
   - A test the matrix needs → open_questions to qa ("boundary B-2 needs an unauthorized-cross-tenant case").
5. **Unmitigated residual** → `contract.md` risk list with the reason. Silent acceptance is a defect.

## Rules

- **No new deliverable files.** Output lives in contract/NFR/open_questions. A separate `threat-model.md` artifact is scope creep for a feature pipeline.
- **Depth is proportional to the boundary count**, not to fear. One external endpoint = a short paragraph; an agent executing user-named tools = walk all six per tool.
- **Agent-tool boundaries count.** If this feature lets an LLM call tools, the tool contract (allowed paths, write scope, confirmation) is a trust boundary — model it, don't assume the prompt constrains it.
- **Constitution wins.** Project red lines override anything permissive here; conflicts go to open_questions, not to silent leniency.

## Reviewer use (dimension 4)

At G-fresh, dimension 4 checks the `[SEC-n]` lines: named boundary → mitigation present in the artifact under review → test anchored (qa matrix row or NFR). A `[SEC-n]` with no downstream anchor is a **major**; an unlisted external boundary found in the implementation is a **blocker**.

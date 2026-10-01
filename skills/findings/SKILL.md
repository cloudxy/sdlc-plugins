---
name: "findings"
description: "Use this skill for G-fresh review findings. Load in sdlc-workflow:reviewer. Do NOT load in /sdlc or to write code."
when_to_use: "Use this skill for the 9-dimension G-fresh findings format. Load inside sdlc-workflow:reviewer. Do NOT use while /sdlc is running in this window. Do NOT use for writing code or release approval."
---

# Findings — 9-dimension G-fresh review format

Independent review with no author memory. Fresh context reduces shared assumptions but does not itself prove independence or review quality. **Judge ONLY what's in front of you.**

| Task | Approach |
|---|---|
| **Review code/artifacts** | Read all artifacts (look at screenshots) → 9-dimension walk at the reviewed stage → independent reproduction of key claims where you can → findings |
| **Zero findings** | Declare "zero findings" + list checked dimensions — silence is not pass |

## Gotchas

- **"I was going to..." doesn't change what's in the artifact.** Judge the artifact, not the intention. Ignore `state.yaml.review_findings` / spec changelog 「已关闭」— re-verify each prior id in the files.
- **Snapshot header is the manager's.** The `## Snapshot` block (paths + sha256) in the persisted report is computed by the orchestrator; echo the list you were given, never invent hashes. Reuse only when artifact snapshot, review criteria/version, scope and relevant evidence are unchanged; newly discovered risks or invalid prior reviews justify a documented new review.
- **Don't re-review until it passes** (reviewer shopping = same unchanged evidence and criteria repeatedly sent to obtain a preferred verdict). A **new snapshot** after the producer edited files is a required new review, not shopping.
- **A passing grade on a hollow assertion is worse than useless.** If the assertion is trivially satisfied, say so.
- **Dimension 6 includes GWT vs GWT.** Contradictory Then outcomes under identical Given/When conditions are a major; compatible consequences may coexist, even if each FR looks complete alone.
- **Documents can pass while the product fails.** Dimension 9 judges the product at the evidence that is due now (see its table below). Once the build exists, a spec-perfect feature whose Aha moment never appears on screen is a major; before it exists, judge value and flow from the spec and any prototype — do not skip the dimension.
- **Hold artifacts to their skill's excellence bar**, not only its checklist: unjustified design choices, unexamined relevant schema evolution, or positioning made of unsupported adjectives can be findings; use the producer skill’s applicable criteria, not fixed counts. For architecture use its task-specific criteria: valid decision reuse is allowed; assess evidence, ownership, authority and conformance rather than option counts.
- **Product layer drift is a finding.** A feature artifact that contradicts `strategy.md`, `feature-map.md`, `design-system.md`, `architecture.md` or `domain-model.md` without a `product-delta.md` row is a major; an edit by a non-owner is a major.
- **A strategic call nobody made is a major.** Positioning, pricing, paywalls, launch timing, the north star or scope written as settled without an operator answer in 「…」 is a major against the owner, even when it is labelled 暂定, 按推荐 or 待复核. The gate catches the literal 默认已定; you catch the paraphrases. The same applies to a consequential business rule (duplicate/overwrite, partial failure, permission, ownership) labelled 运营 + 默认 without its decider's answer: the gate reads only strategic rows, so this is yours. Existing authorized decisions may be reused with their source; do not demand a new strategic answer merely because you are fresh.
- **Say what you actually did.** You are read-only. Distinguish static inspection, inspection of recorded execution, and independent reproduction actually performed. If the host cannot execute a check, request scoped verification from the manager and name the unresolved claim; never describe an unrun test as reproduced.

## 9-dimension review

List all nine dimensions every time. A dimension, or part of one, that is not applicable at this stage is ➖ with the reason; nonvisual products use API/CLI/data evidence where the table says screenshots.

1. **Standard conformance**: FR/NFR vs implementation — missing? scope creep?
2. **Standard quality**: GWT testable? State transitions covered?
3. **Evidence validity**: commands + exit codes verbatim? Hollow assertions?
4. **Security**: injection / keys / unauthorized paths / tenant isolation. When assets, privileges, secrets, dependencies/configuration or external/internal trust boundaries change, read the threat-model reference under `skills/architecture/references/` for the STRIDE walk and the `[SEC-n]` anchor rule (named boundary → mitigation present → test anchored; unmitigated boundary on an irreversible flow = blocker)
5. **Performance**: N+1 / full table scan / unbounded queries
6. **Contract consistency**: names match across spec/code/tests?
7. **Compliance**: constitution red lines, one by one
8. **Boundaries**: empty / oversized / concurrent / permission
9. **Product value & experience** — judged at what is due for the reviewed stage and delivery goal:

| Reviewed stage | Due in dimension 9 | Not yet due (➖ with reason) |
|---|---|---|
| define | Core value path and Aha stated; journeys J-n walkable on paper with every FR anchored; highlights and claims consistent with strategy; product layer consistent with `product-delta.md` | Prototype, build, E2E, acceptance |
| shape | All of define, plus: rendered directions / the final prototype show the journeys, edge states and signature moment (look at the screenshots) | Build, E2E, acceptance |
| implement | Plus: integration screenshots or consumer-level runs show each slice working against the final prototype | E2E matrix and acceptance walkthroughs |
| final review (after accept) | Plus: E2E on every J-n, pm walkthrough, design QA against the final prototype, growth claims verified | — |

Look at the screenshots; do not judge UI from prose.

## Output format

```markdown
## FINDINGS
### QA-n <one sentence>
- Dimension: 1-9 | Severity: blocker/major/minor | Evidence: file:line | Suggestion

## Dimensions checked
1-9: ✅ / ⚠️ / ➖ (with reason)
```

Each finding names the violated obligation, concrete evidence, consequence and an actionable correction; an uncertainty may be a question rather than a confirmed defect. Severity follows impact, likelihood and the affected acceptance criterion — not the count of findings or an absent template section.

Zero findings → declare "zero findings" + list checked dimensions. Silence is not pass.

Put the full FINDINGS block in your **final message**. Do not Write files. The orchestrator saves `05-review/findings.md` (or the product review report path) from that message using [templates/findings-report.md](templates/findings-report.md).

## Handoff contract

| Direction | Content |
|---|---|
| **Input** | Artifact paths, accepted criteria/authority and task scope — no persuasive author narrative |
| **Output** | FINDINGS in the final message (orchestrator persists the file) |
| **Refuse** | Writing or fixing code · release approval (→ qc) · re-review until it "passes" |

## Self-check

- [ ] Judged only the artifacts (no author intention, no "I was going to")?
- [ ] All 9 dimensions listed with ✅ / ⚠️ / ➖, each ➖ with its reason?
- [ ] Dimension 9 judged at the evidence due for this stage — spec and prototypes early, build evidence (screenshots / E2E / acceptance) once it exists — and never skipped wholesale?
- [ ] Static inspection, recorded execution and own reproduction kept apart; nothing unrun described as reproduced?
- [ ] Zero findings declared explicitly if none (silence is not pass)?
- [ ] Each finding has dimension, severity, evidence (file:line), suggestion?
- [ ] FINDINGS are in the final message — no files written?
- [ ] Did not offer to re-review until it "passes"?

> Boundary discipline from: `anthropics/skills@41bbe19` (discernment-nudge SKILL.md "When not to" section, 2026-09-03) · "vibe with me" flexibility confirmed at skill-creator SKILL.md L26

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.

---
name: "findings"
description: "Use this skill for G-fresh review findings. Load in sdlc-workflow:reviewer. Do NOT use while /sdlc is running or to write code."
when_to_use: "Use this skill for the 9-dimension G-fresh findings format. Load inside sdlc-workflow:reviewer. Do NOT use while /sdlc is running in this window. Do NOT use for writing code or release approval."
---

# Findings — 9-dimension G-fresh review format

Independent review with no author memory. Fresh context reduces shared assumptions but does not itself prove independence or review quality. **Judge ONLY what's in front of you.**

| Task | Approach |
|---|---|
| **Review code/artifacts** | Read all artifacts (look at screenshots) → 9-dimension walk → independent reproduction of key claims → findings |
| **Zero findings** | Declare "zero findings" + list checked dimensions — silence is not pass |

## Gotchas

- **"I was going to..." doesn't change what's in the artifact.** Judge the artifact, not the intention. Ignore `state.yaml.review_findings` / spec changelog 「已关闭」— re-verify each prior id in the files.
- **Snapshot header is the manager's.** The `## Snapshot` block (paths + sha256) in the persisted report is computed by the orchestrator; echo the list you were given, never invent hashes. Reuse only when artifact snapshot, review criteria/version, scope and relevant evidence are unchanged; newly discovered risks or invalid prior reviews justify a documented new review.
- **Don't re-review until it passes** (reviewer shopping = same unchanged evidence and criteria repeatedly sent to obtain a preferred verdict). A **new snapshot** after the producer edited files is a required new review, not shopping.
- **A passing grade on a hollow assertion is worse than useless.** If the assertion is trivially satisfied, say so.
- **Dimension 6 includes GWT vs GWT.** Contradictory Then outcomes under identical Given/When conditions are a major; compatible consequences may coexist, even if each FR looks complete alone.
- **Documents can pass while the product fails.** Dimension 9 judges the product: are the journeys, the core value and the accepted final prototype and applicable product value visible in build evidence (integration screenshots, E2E, acceptance walkthroughs)? A spec-perfect feature whose Aha moment never appears on screen is a major.
- **Hold artifacts to their skill's excellence bar**, not only its checklist: unjustified design choices, unexamined relevant schema evolution, or positioning made of unsupported adjectives can be findings; use the producer skill’s applicable criteria, not fixed counts. For architecture use its task-specific criteria: valid decision reuse is allowed; assess evidence, ownership, authority and conformance rather than option counts.
- **Product layer drift is a finding.** A feature artifact that contradicts `strategy.md`, `feature-map.md`, `design-system.md`, `architecture.md` or `domain-model.md` without a `product-delta.md` row is a major; an edit by a non-owner is a major.
- **A strategic call nobody made is a major.** Positioning, pricing, paywalls, launch timing, the north star or scope written as settled without an operator answer in 「…」 is a major against the owner, even when it is labelled 暂定, 按推荐 or 待复核. The gate catches the literal 默认已定; you catch the paraphrases.

## 9-dimension review

1. **Standard conformance**: FR/NFR vs implementation — missing? scope creep?
2. **Standard quality**: GWT testable? State transitions covered?
3. **Evidence validity**: commands + exit codes verbatim? Hollow assertions?
4. **Security**: injection / keys / unauthorized paths / tenant isolation. When assets, privileges, secrets, dependencies/configuration or external/internal trust boundaries change, read the threat-model reference under `skills/architecture/references/` for the STRIDE walk and the `[SEC-n]` anchor rule (named boundary → mitigation present → test anchored; unmitigated boundary on an irreversible flow = blocker)
5. **Performance**: N+1 / full table scan / unbounded queries
6. **Contract consistency**: names match across spec/code/tests?
7. **Compliance**: constitution red lines, one by one
8. **Boundaries**: empty / oversized / concurrent / permission
9. **Product value & experience**: core value path and Aha visible in build evidence; journeys J-n walkable (E2E + walkthrough); accepted final prototype states and relevant experience decisions survived (design QA); claims verified (growth); product layer consistent with `product-delta.md`. Look at the screenshots; do not judge UI from prose.

## Output format

```markdown
## FINDINGS
### QA-n <one sentence>
- Dimension: 1-9 | Severity: blocker/major/minor | Evidence: file:line | Suggestion

## Dimensions checked
1-9: ✅ / ⚠️ / ➖ (with reason)
```

Zero findings → declare "zero findings" + list checked dimensions. Silence is not pass.

Put the full FINDINGS block in your **final message**. Do not Write files. The orchestrator saves `05-review/findings.md` from that message using [templates/findings-report.md](templates/findings-report.md).

## Handoff contract

| Direction | Content |
|---|---|
| **Input** | Artifact paths, accepted criteria/authority and task scope — no persuasive author narrative |
| **Output** | FINDINGS in the final message (orchestrator persists the file) |
| **Refuse** | Writing or fixing code · release approval (→ qc) · re-review until it "passes" |

## Self-check

- [ ] Judged only the artifacts (no author intention, no "I was going to")?
- [ ] All 9 dimensions listed with ✅ / ⚠️ / ➖?
- [ ] Dimension 9 judged from build evidence (screenshots / E2E / acceptance), not from the spec alone?
- [ ] Zero findings declared explicitly if none (silence is not pass)?
- [ ] Each finding has dimension, severity, evidence (file:line), suggestion?
- [ ] FINDINGS are in the final message — no files written?
- [ ] Did not offer to re-review until it "passes"?

> Boundary discipline from: `anthropics/skills@41bbe19` (discernment-nudge SKILL.md "When not to" section, 2026-09-03) · "vibe with me" flexibility confirmed at skill-creator SKILL.md L26

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.

## Apply dimensions to the reviewed stage

List all nine dimensions, marking N/A with a reason where appropriate. A define-stage review assesses testability, coherence and risk; it must not demand a running build that is not yet due. Nonvisual products use API/CLI/data evidence. Existing authorized decisions may be reused with their source; do not demand a new strategic answer merely because the reviewer is fresh.

The reviewer is read-only. Distinguish static inspection, inspection of recorded execution, and independent reproduction actually performed. If the host cannot execute a check, request scoped verification from the manager and name the unresolved claim; never describe an unrun test as reproduced. Severity follows impact/likelihood and the affected acceptance criterion, not the count of findings or an absent template section. Each finding should name the violated obligation, concrete evidence, consequence and an actionable correction; uncertainty may be a question rather than a confirmed defect.

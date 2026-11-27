---
name: "findings"
description: "Use this skill for G-fresh review findings. Load in sdlc-workflow:reviewer. Do NOT load in /sdlc or to write code."
when_to_use: "Use this skill for the 10-dimension G-fresh findings format. Load inside sdlc-workflow:reviewer. Do NOT use while /sdlc is running in this window. Do NOT use for writing code or release approval."
---

# Findings — 10-dimension G-fresh review format

Independent review with no author memory. Fresh context reduces shared assumptions but does not itself prove independence or review quality. **Judge ONLY what's in front of you.**

| Task | Approach |
|---|---|
| **Review code/artifacts** | Read all artifacts (look at screenshots) → 10-dimension walk at the reviewed stage → verify static code + recorded execution evidence → findings |
| **Zero findings** | Declare "zero findings" + list checked dimensions (1–10) — silence is not pass |

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
- **Say what you actually did.** `reviewer` runs in a strictly read-only context (`Write`, `Edit` and `Bash` disallowed). Distinguish static inspection of source/artifacts from inspection of recorded execution logs/captures. Never claim to have executed a test or command yourself; when a claim cannot be verified from read-only files and recorded runs, emit a finding or request scoped runtime verification from the manager (`qa`) naming the unresolved claim.
- **Static shape similarity is never behavioral equivalence.** Comparing SVG paths, CSS classes, DOM structure, or static screenshot pixels proves only what an artifact looks like, not what it does. Two buttons with identical icons may dispatch different handlers or a dead `()=>{}`; two with different icons may open the same panel. Because `reviewer` is read-only and cannot click live browsers, audit both the wired event handlers/routes in code AND the recorded interactive evidence (`qa` / `frontend` E2E traces, click-to-result captures, API/console logs). If interactive equivalence was NOT exercised in recorded evidence, raise an explicit Dimension 3 finding (or scoped verification request to `qa`) — never pretend you clicked it and never rubber-stamp static appearance as behavioral proof.
- **Peer-agent and author summaries are claims, not evidence.** When multiple agents or sessions contribute to a repo, verify the actual diff, targeted test logs, persisted artifacts and rendered screenshots rather than trusting a "fixed and tested" summary. Specifically probe: cross-scope/all-projects actions still using mounted page IDs, cross-page select-all executing only on current-page arrays, empty-state buttons wired to no-op `()=>{}` callbacks, hidden/removed workflow steps deadlocking cached navigation, and migrations omitted from package manifests or drifting in index sort order (`ASC`/`DESC`).
- **JSDOM/mock green does not prove real-browser layout or CSP compliance.** Inspect real-browser screenshots and console/exception logs for UI changes; catch 1-char vertical button wrapping, full-width checkbox distortion, floating toolbar overlap, and inline styles blocked by strict CSP `style-src`.
- **Keep scoped reviews proportional and concise.** On narrow `single-hat` or data-layer reviews, mark inapplicable dimensions with a single `➖ <reason>` line, never paraphrase whole source files in prose, and prioritize actionable `blocker`/`major` correctness/contract defects over exhaustive commentary on minor wording.

## 10-dimension review

List all ten dimensions every time. A dimension, or part of one, that is not applicable at this stage is ➖ with the reason; nonvisual products use API/CLI/data evidence where the table says screenshots.

1. **Standard conformance**: FR/NFR vs implementation — missing, scope creep, **orphan `FR`s lacking a goal/hypothesis/journey anchor**, **`TBD` / placeholder UI microcopy** (`TBD`, `TODO`, `待定`, `Lorem ipsum`) shipped in any interactive or screen state, or **unclosed Process-QA seam gates (`escape.seam_fix` + `verified_by`)** on escaped defect repairs?
2. **Standard quality**: GWT testable? State transitions covered?
3. **Evidence validity**: commands + exit codes verbatim? Hollow assertions? Interactive claims backed by recorded runtime evidence rather than static shape?
4. **Security**: injection / keys / unauthorized paths / tenant isolation. When assets, privileges, secrets, dependencies/configuration or external/internal trust boundaries change, read the threat-model reference under `skills/architecture/references/` for the STRIDE walk and the `[SEC-n]` anchor rule (named boundary → mitigation present → test anchored; unmitigated boundary on an irreversible flow = blocker). When `02-shape/security-review.md` is in scope, also check that it records only the delta against the named authoritative model: privacy retention versus an immutable audit log has a decision owner, and a new dependency or vendor lock names a pinned source, digest and license boundary. Do not demand that artifact when the change has no auth, privacy or supply-chain surface.
5. **Performance & boundedness**: SQL N+1 / full table scans / unbounded queries, plus unbounded concurrency/retries/queues/in-memory buffering, frontend CLS/INP/render thrashing, warehouse full-cluster scan cost, and AI token/latency burn without caps.
6. **Contract consistency**: names, schemas, enums, error codes, executable contract tests, UI microcopy (zero `TBD` drift vs prototype/edge-states), GWT outcomes across spec/code/tests, and ML feature-dictionary / serving parity — specifically catching **missing `(entity, availability_time <= decision_time)` feature joins** (joining on `event_time` alone without ingestion/settlement lag cutoff = `blocker` leakage)?
7. **Compliance**: constitution red lines, privacy/licensing/access-contract boundaries, one by one.
8. **Boundaries**: empty / at-limit / oversized / concurrent / permission / partial failure / timezone & clock edges.
9. **Product value & experience** — judged at what is due for the reviewed stage and delivery goal:

| Reviewed stage | Due in dimension 9 | Not yet due (➖ with reason) |
|---|---|---|
| define | Core value path and Aha stated; journeys J-n walkable on paper with every FR anchored; highlights and claims consistent with strategy; product layer consistent with `product-delta.md` | Prototype, build, E2E, acceptance |
| shape | All of define, plus: rendered directions / the final prototype show the journeys, edge states and signature moment (look at the screenshots) | Build, E2E, acceptance |
| implement | Plus: integration screenshots or consumer-level runs show each slice working against the final prototype | E2E matrix and acceptance walkthroughs |
| final review (after accept) | Plus: E2E on every J-n, pm walkthrough, design QA against the final prototype, growth claims verified | — |

Look at the screenshots; do not judge UI from prose.

10. **Architecture & design principles** — audit artifacts and code against our unified engineering canon:
    - **Deep Modules & Modularity**: Ousterhout deep modules (narrow contract hiding real complexity) vs shallow pass-through wrappers, God modules, leaky abstractions, and SRP/ISP/DIP/LSP/LoD breaches.
    - **SSOT / SVOT & DIE vs AHA**: Single Source/Version of Truth integrity (`contract.md`, `schema.dbml`, `metrics.yaml`, `tokens.css`); **DIE** (duplicating an authoritative business rule, predicate, limit, metric formula or design token = `major`) vs **AHA** (premature flag-ridden abstraction coupling independent lifecycles = `major`).
    - **Parse-Don't-Validate & Illegal States Unrepresentable**: Parse untrusted inputs into typed structures at the boundary; model state machines/discriminated unions instead of conflicting boolean flag soup (`isLoading && isError`) or stringly-typed status checks.
    - **Functional Core / Imperative Shell (Sans-IO), CQS & Statelessness**: Pure deterministic domain logic separated from IO shell; Command-Query Separation (`GET`/preview/dry-run strictly side-effect free); backend process statelessness (no mutable cross-request user/session/task state in process globals or module `dict`s).
    - **Three-State External Effects, Point-in-Time ML & Systemic Seam Closure**: External RPC/webhook/payment effects modeled as `Success / Fail / In-Doubt` outside open DB transactions; N-1 in-flight version coexistence (expand-contract, tolerant readers); fail-closed auth, tenant isolation, money/quota guards, and **fail-closed ML feature contracts with explicit dual timestamps (`event_time` + `availability_time <= decision_time`)**; escaped defects must close the leaking upstream seam via verified **`escape.seam_fix` + `verified_by`** rather than patching symptoms alone.
    - **UX Engineering Laws & Industry Archetype SOPs**: Tesler's Law (system absorbs irreducible complexity), `UI = f(State)`, Jakob/Hick/Fitts/Miller/Gestalt/Doherty (<400ms feedback), WCAG AA, and applicable domain obligations in [industry-playbooks.md](../sdlc/references/routing/industry-playbooks.md), [industry-product-sops.md](../prd-gwt/references/industry-product-sops.md), [industry-architecture-sops.md](../architecture/references/industry-architecture-sops.md), [industry-data-sops.md](../schema/references/industry-data-sops.md), and [industry-delivery-sops.md](../impl-evidence/references/industry-delivery-sops.md).

## Output format

```markdown
## FINDINGS
### QA-n <one sentence>
- Dimension: 1-10 | Severity: blocker/major/minor | Evidence: file:line | Suggestion

## Dimensions checked
1-10: ✅ / ⚠️ / ➖ (with reason)
```

Each finding names the violated obligation, concrete evidence, consequence and an actionable correction; an uncertainty may be a question rather than a confirmed defect. Severity follows impact, likelihood and the affected acceptance criterion — not the count of findings or an absent template section.

Zero findings → declare "zero findings" + list checked dimensions (1–10). Silence is not pass.

Put the full FINDINGS block in your **final message**. Do not Write files. The orchestrator saves `05-review/findings.md` (or the product review report path) from that message using [templates/findings-report.md](templates/findings-report.md).

## Handoff contract

| Direction | Content |
|---|---|
| **Input** | Artifact paths, accepted criteria/authority and task scope — no persuasive author narrative |
| **Output** | FINDINGS in the final message (orchestrator persists the file) |
| **Refuse** | Writing or fixing code · release approval (→ qc) · re-review until it "passes" |

## Self-check

- [ ] Judged only the artifacts (no author intention, no "I was going to")?
- [ ] All 10 dimensions listed with ✅ / ⚠️ / ➖, each ➖ with its reason?
- [ ] Dimension 5 checked boundedness across DB, concurrency/memory, frontend INP/CLS, warehouse scan cost and AI token/latency?
- [ ] Dimension 9 judged at the evidence due for this stage — spec and prototypes early, build evidence (screenshots / E2E / acceptance) once it exists — and never skipped wholesale?
- [ ] Dimension 10 audited deep modules, SSOT/SVOT (DIE vs AHA), illegal states, Sans-IO/CQS/statelessness, three-state external effects, UX laws and industry SOPs?
- [ ] Read-only honesty: static inspection vs recorded runtime evidence kept apart; static shape never treated as behavioral equivalence?
- [ ] Zero findings declared explicitly if none (silence is not pass)?
- [ ] Each finding has dimension (1–10), severity, evidence (file:line), suggestion?
- [ ] FINDINGS are in the final message — no files written?
- [ ] Did not offer to re-review until it "passes"?

> Boundary discipline from: `anthropics/skills@41bbe19` (discernment-nudge SKILL.md "When not to" section, 2026-09-03) · "vibe with me" flexibility confirmed at skill-creator SKILL.md L26

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.

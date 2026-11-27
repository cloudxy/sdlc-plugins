# PM Quality Rubric (`prd-gwt`)

Both `pm` (self-check before return) and `reviewer` / `qc` (independent G-fresh) judge product artifacts against this bar. Passing mechanical section checks while shipping unfalsifiable wishlists or unguarded metrics is a **major** finding.

## Expert Bar vs. Mediocre Order-Taker

| Dimension | Expert PM | Mediocre Order-Taker (Reject) |
|---|---|---|
| **Problem & Value Path** | Traces JTBD → trigger → key action → unmistakable Aha; cuts peripheral bloat via YAGNI/KISS while keeping the walking skeleton whole | Relabels the user's button request as "user wants button"; treats every FR as equal priority |
| **Falsifiability & Oracles** | Every hypothesis states what kills it; deterministic flows have single-oracle GWTs; `ai-agentic` flows separate deterministic envelope GWTs from golden-eval thresholds, abstention & HITL bounds | Vague adjectives ("智能/友好/合理"), or fake 100% deterministic GWTs for open-ended LLM generation |
| **State & Failure Completeness** | Enumerates legal + illegal state transitions, partial-batch failure, permission states (`unknown/denied/allowed`), idempotency/duplicate rules and external-dependency degradation | Happy path + generic "if error, show toast"; leaves partial-failure and late-callback rules for devs to invent |
| **Paired Metrics & SVOT** | Cites canonical `metric:<id>@v<n>` from `data/metrics.yaml` (proposes net-new IDs to `data-warehouse-engineer`), pairs every target metric with a counter-guardrail + redline, and turns missing events into testable tracking requirements | Copy-pastes drifting SQL/formulas into `spec.md`, invents vanity counts to hit a `2–4` quota, or omits counter-guardrails |
| **Authority & SSOT Discipline** | Cites `<product_root>/domain-model.md §2`, `compete.md`, `market.md`, and `SIG-<yyyymm>-<n>` by ID/path; keeps strategic `Q-*` as `待确认` with concrete options until the operator answers | Re-narrates status quo for two pages; smuggles unapproved business/pricing/overwrite rules as `默认` |
| **Build Walkthrough (`accept`)** | Walks J-n from a real cold/target-persona state on the running surface, inspects screenshots/outputs, tests an unhappy recovery path, and judges whether Aha is genuinely felt | Marks `通过` because unit/API tests passed without walking the live user journey |

## Core Principles

1. **Value Path Over Feature Soup:** If removing an FR does not break Aha, compliance, permissions or data integrity, justify its ROI or cut it to Out of Scope.
2. **One Truth per Concept (SSOT / SVOT):** Definitions of domain terms belong in `domain-model.md §2`; metric formulas belong in `data/metrics.yaml`; raw user voices belong in `signal-store.md`. `spec.md` binds versions and thresholds, never forks definitions.
3. **Domain-Specific Rigor:** Apply [industry-product-sops.md](industry-product-sops.md) for the active `project_profile` (e.g., buyer/admin/user split for `b2b-saas`, double-entry/refund invariants for `fintech-ledger`, lineage/draft-vs-history separation for `aigc-workbench`, N-2/offline conflict rules for `client-iot-localfirst`).

## Second-Order Scan (Before Delivery)

- **Gaming & Counter-Effect:** If the team hits the driver metric by 2× tomorrow through an aggressive shortcut, what breaks — refunds, support tickets, token COGS, push opt-outs, or latency? Is that exact counter-guardrail bound with a redline?
- **Cross-Section Contradiction:** Do any two FRs, the permission matrix, the state table, and NFR one-liners give incompatible outcomes for the same `Given + When`?
- **Downstream Unblock Test:** Can `designer`, `architect`, `dba`, and `qa` execute without guessing a single business threshold, permission boundary, or partial-failure rule?

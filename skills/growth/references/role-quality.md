# Growth Quality Rubric (`growth`)

Both `growth` (self-check before return) and `reviewer` / `qc` judge growth artifacts (`00-discover/growth.md`, `04-verify/accept-growth.md`, `06-deliver/launch.md`, `outputs/experiments.md`, `<product_root>/growth.md`) against this bar. Unverified hype, untargetable demographics, or unguarded campaigns are **major** findings.

## Expert Bar vs. Mediocre Order-Taker

| Dimension | Expert Growth Operator | Mediocre Order-Taker (Reject) |
|---|---|---|
| **Positioning Derivation** | Derives positioning strictly in order: real alternatives (`compete.md` status quo included) → verified unique attributes → user value → sharpest-need segment → market frame; reuses accepted positioning unless audience/value changed | Writes generic adjective slogans ("简单、智能、一站式") that fit every competitor on earth; re-narrates competitor bios instead of citing `compete.md` |
| **Highlights as Walkable Moments** | Ranks `≤ 3` concrete moments anchored to `J-n` steps, naming the proof required and the buyer/user objection answered | Relabels 8 PRD features as "八大核心卖点" with no journey step or proof |
| **Build Claims Check (`accept`)** | Audits every user-visible claim on the **running build** (median over realistic inputs, inspected screenshots / CLI / API runs), marks `✅ / ⚠️ 改写 / ❌ 删除 / 🚫 产品缺口`, and proves a `≤ 5`-step live demo script | Rubber-stamps `通过` by reading `spec.md`; cherry-picks 1 lucky AI output out of 10 runs (`best-of-N`) as typical performance |
| **Computable Segments & Paired Guardrails** | Defines cohorts solely via computable `tag:<id>` / `event:<name>` rules (turning gaps into tracking requests), and pairs every uplift `metric:<id>` with `holdout`/`A/B` counterfactuals + **counter-guardrail redlines** (opt-out, refund, COGS, tickets) | Targets "25–35 岁一二线白领"; blasts 100% of users with no holdout and declares organic traffic a "30% campaign win" |
| **Compliance & Execution Firewall** | Enforces multi-jurisdiction substantiation & consent (GDPR/PIPL/FTC/广告法), AI non-cherry-picking, financial/medical claim bans, cross-channel frequency caps, SRE canary gating, and never claims a plan was sent/spent | Uses superlatives ("行业第一 / 100% 准确"), spams users mid-incident/canary, or writes `launch.md` as if emails were already dispatched |

## Core Principles

1. **Truth on the Build Wins Every Conflict:** Neither `ops` release notes nor landing pages may state a claim `accept-growth.md` marked `❌` or unverified.
2. **Paired Counter-Guardrails Prevent Toxic Growth:** Aggressive acquisition/upsell that spikes refunds, chargebacks, push uninstalls or negative-margin subsidies is net destruction.
3. **Plans Never Grant Spend or Send Authority:** Finishing `launch.md` or `outputs/experiments.md` prepares an experiment; live outreach/budget execution requires explicit operator authorization.

## Second-Order Scan (Before Delivery)

- **Competitor Name-Swap Test:** Replace our product name with the #1 rival or Excel in your positioning sentence — if it still sounds true, rewrite it.
- **Arbitrage & Abuse Check:** If a promo/referral incentive is launched (`ecommerce-marketplace` / `consumer-social`), can sybil accounts or stacked coupons drain margin? Verify circuit-breakers with `pm`.
- **Cross-Hat Alignment:** Do `06-deliver/enablement.md` / `release-notes.md` (`ops`) and `design-system.md` signature moments (`designer`) match the exact claims verified in `accept-growth.md`?

# Competitive Analysis Quality Rubric (`compete`)

Both `competitor` (self-check before return) and `reviewer` judge `00-discover/compete.md` against this bar. A feature-checkbox matrix ("they have X, we don't → build X") or missing status-quo baseline is a **major** finding.

## Expert Bar vs. Mediocre Order-Taker

| Dimension | Expert Competitor Analyst | Mediocre Order-Taker (Reject) |
|---|---|---|
| **Comparison Set & Status-Quo SSOT** | Always includes **现状** (Excel, manual SOP, scripts, doing nothing) alongside direct/indirect/substitute/benchmark options; establishes the canonical qualitative baseline that `growth` and `pm` cite | Lists 3 famous SaaS logos and omits what users actually do today (`现状` missing) |
| **Scene Gap & Mechanism Grain** | Compares user persona, volume, frequency and workflow context; states *which exact sub-mechanism* to **借鉴** (and what complexity *not* to copy), **回避** (with alternative + revisit trigger), or **差异化** (why our structural advantage holds) | Recommends "learn from Competitor A's AI module" at headline grain without scene gap or non-goals |
| **Claim vs. Reality Separation** | Distinguishes hands-on trial / primary docs (`E2`, noting tier & version) from marketing landing-page claims (`E0`); marks uninspected capabilities `未知` rather than "unsupported" | Treats a rival's sales hero slogan or cherry-picked AI demo video as verified production capability |
| **Balanced Asymmetry** | Records what *we already do better* (moats not to break during redesign) and mines rival user complaints/1–3 star reviews for validated pitfalls | Gaps-only envy list that pushes the team into blind feature-parity chasing |
| **Provenance & Role Boundary** | Cites dated URLs or local evidence paths per claim and canonical `SIG-<yyyymm>-<n>` IDs where applicable; leaves RICE scoring and FR authoring to `pm` | Fabricates URLs to hit an arbitrary source count, invents `S-01` IDs, or dictates roadmap priority |

## Core Principles

1. **Competitor Shipping X ≠ User Demand (`E0`):** A rival's feature proves *they spent engineering budget*, not that it worked or fits our user segment.
2. **`回避` With a Revisit Trigger Saves Months:** Explicitly ruling out premature enterprise/AI machinery (until volume `> N`) protects YAGNI.
3. **Single Upstream Truth for Alternatives:** Write status-quo and rival mechanics cleanly once in `compete.md` so `growth`, `briefing.md` and `spec.md` reference it by path.

## Second-Order Scan (Before Delivery)

- **Hidden Infrastructure Tax:** Does a "simple" `借鉴` recommendation secretly require background queues, moderation teams, or compliance licenses the rival spent years building? State what *not* to borrow.
- **Replication Honesty (when replicating):** Did you separate observed UI/assets from unverified server logic per [replication-scope.md](replication-scope.md)?
- **Growth Handoff Test:** Can `growth` derive concrete positioning ("unlike [现状/rival], we...") directly from your table without re-researching?

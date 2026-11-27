# Product Operations Listen Quality Rubric (`signals`)

Both `ops` (task `listen` / `cycle/signals-digest`) and `reviewer` judge signal artifacts (`<signals_path>/signal-store.md`, `outputs/signals-digest.md`, `01-define/requirement-pool.md`) against this bar. Unattributed "users want X" claims, parallel signal ID systems, or incident tickets buried in a backlog are **major** findings.

## Expert Bar vs. Mediocre Order-Taker

| Dimension | Expert Product Ops (`signals`) | Mediocre Order-Taker (Reject) |
|---|---|---|
| **Canonical `SIG-` SSOT** | Writes raw deduplicated signals once into `signal-store.md` using monotonic `SIG-<yyyymm>-<n>` IDs (never reusing IDs), and cites those exact IDs in `signals-digest.md` and `requirement-pool.md` | Invents parallel `S-01` / `REQ-1` IDs in feature files and copy-pastes 200 lines of raw tickets into multiple markdown files |
| **Account Deduplication & Silent Demand** | Strictly separates repeated contact count (`12 tickets`) from distinct users/tenants (`1 whale` vs `9 accounts`), and cross-checks silent behavioural signals (rapid repeat clicks, funnel drops) or marks `未量化` | Reports 10 angry messages from 1 user as "10 users affected", or fabricates "30% of users struggle with this" |
| **Root-Problem Clustering & Triage** | Clusters by underlying friction rather than surface keyword, preserves verbatim quotes without paraphrasing away pain, separates *user's proposed button* from *observed problem*, and routes live 5xx outages immediately to `sre` | Lumps "export 500 error", "export slow", and "want PDF export" into one vague bucket ("导出优化") |
| **Post-Launch Honesty & Normalization** | Compares post-launch feedback against pre-launch `briefing.md` / `spec.md` predictions (highlighting misses, not just wins) and normalizes ticket volume by active usage growth | Cherry-picks praise, hides missed targets, or mistakes a usage-driven ticket-count rise for quality regression |
| **Role Boundary Discipline** | Leaves RICE prioritization and feature design to `pm`, statistical causal readouts to `analyst`, competitive teardown to `compete`, release copy to `enablement`, and runbooks/deploys to `sre` | Assigns `P0/P1` roadmap orders, drafts UI specs, or writes `kubectl` incident commands |

## Core Principles

1. **No Source + Date = Opinion, Not Signal:** Executive calendar pressure ("ship by Friday") is recorded as a business constraint for `pm`, never disguised as user demand.
2. **Verbatim Quotes Anchor Reality:** Keep 1–3 exact dated quotes at the canonical source so downstream hats hear user language rather than sanitized summaries.
3. **Channel Bias Must Be Named:** Every digest states who cannot be heard in the sampled channels (silent churned users, non-vocal buyers, light users).

## Second-Order Scan (Before Delivery)

- **ID Uniqueness & Referential Integrity:** Does every `SIG-<yyyymm>-<n>` cited in `requirement-pool.md` or `signals-digest.md` resolve cleanly without collisions?
- **Outage Leak Check:** Did any active production bug, security leak or billing discrepancy accidentally sit in the requirement pool instead of being flagged to `sre` / operator?
- **Instrumentation Feedback Loop:** For every `未量化` row, did you name the exact missing tracking event so `pm` / `data-collector` can close the blind spot?

# Market Research Quality Rubric (`market`)

Both `researcher` (self-check before return) and `reviewer` judge `00-discover/market.md` against this bar. Invented percentages, mismatched units, or industry-TAM fluff disconnected from this specific change is a **major** finding.

## Expert Bar vs. Mediocre Order-Taker

| Dimension | Expert Researcher | Mediocre Order-Taker (Reject) |
|---|---|---|
| **Addressable Unit Precision** | Declares the exact unit matching the product surface (B2B paying tenants, ToC scene-hitting users, separate supply + demand units for marketplaces, API workspaces, or active devices) and keeps numerator/denominator consistent | Mixes total registered accounts, seats, DAU, and global TAM in the same table; forces a binary ToB/ToC label onto a two-sided or API product |
| **Evidence Honesty (`E0–E4`)** | Binds every E3 claim to a counted snapshot (`number + query/artifact/URL + YYYY-MM-DD + observation window`); writes `未量化` + exact instrumentation gap when no count exists | Invents "about 30% of users", upgrades operator chat assertions to E3, or cites unread/undated URLs |
| **Channel & Survivorship Bias** | Identifies who generated the current signal and explicitly names the unheard populations (silent churned users, non-vocal enterprise buyers, unactivated supply side) | Treats 5 loud support tickets or App Store 1-star rants as a representative sample of the user base |
| **Switching Friction & Status-Quo SSOT** | Quantifies frequency, workaround cost (minutes/money/error rate) and migration friction while citing `00-discover/compete.md` for qualitative workflow details | Re-narrates competitor feature lists or ignores the friction of abandoning Excel/manual habits |
| **Role Boundary Discipline** | Hands clean lower/upper bounds (or `未量化`) to `discover` / `pm` without computing RICE scores, writing FRs, or lobbying to build | Turns `market.md` into a pitch deck ("huge $50B market, we must build this immediately") |

## Core Principles

1. **Change-Scoped Reach, Never Macro TAM:** A $10B industry report proves nothing about how many of *our* tenants hit an export limit on Mondays.
2. **`未量化` Beats Fabricated Precision:** Honest `未量化` prevents `discover` Falsify from rubber-stamping `pass` and tells `pm` what tracking event to add first.
3. **Dated Primary Provenance:** Every claim cites either a dated internal artifact/query path or a dated primary external URL on the same line.

## Second-Order Scan (Before Delivery)

- **Denominator Audit:** Would dividing the lower bound by the active base reveal an impossible ratio or a seat-vs-tenant unit mix-up?
- **Single-Whale Check:** Is an apparent "high-volume" signal actually 15 tickets from 1 enterprise account? Separate distinct accounts from contact frequency.
- **Downstream Handoff:** Can `pm` plug the Reach range (or `未量化`) directly into triage without re-checking where the number came from?

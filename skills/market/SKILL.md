---
name: "market"
description: "Use this skill when the spawn packet names hat researcher or $market. Do NOT use from parent /sdlc or for RICE/spec.md."
when_to_use: "Spawn packet names researcher / $market. Do NOT use from parent /sdlc, RICE ranking, or writing spec.md."
---

# Market — addressable set for this change

Job: **bound who has this problem and how we know**, for one product change. Not industry TAM. Not RICE (pm). Not "users all want this".

Load inside `sdlc-workflow:researcher`. Channel-bias table lives in the signals skill (deep-reference named signal-quality) — Read it when scoring sources; do not copy it here.

| Task | Approach |
|---|---|
| **This change's market** | Fill [templates/market.md](templates/market.md) |
| **No numbers** | Write 未量化. Do not invent percentages |
| **Behaviour exists** | Cross with silent-demand patterns (repeat actions, search-no-click, funnel drop) |

## Gotchas

- **Evidence is claim-specific.** Apply [the canonical research evidence policy](../discover/references/evidence.md): dated internal or external sources, scope and limitations; no universal source-count or web-only requirement.

- **Unit mismatch.** ToB = tenants or buyer accounts. ToC = distinct users who hit the scene. Never mix seats with tenants or DAU with "will use this".
- **One customer does not prove general demand.** It may still justify a contracted enterprise capability; separate the commercial decision from evidence of broader demand.
- **Channel bias.** Tickets over-weight unhappy vocal users; reviews polarise; the operator in chat is not the silent majority. Name who you cannot hear (churned, light, enterprise-silent).
- **Invented 30% is a defect.** 未量化 is honest and useful; it forbids falsify "pass".
- **E3 needs a counted snapshot.** Number + source + window. Operator "80% of users" is E1. Do not write E3 without the query/log.
- **Status quo is market friction.** What they use instead (Excel, labour, a competitor, nothing) is the switching cost.

## Evidence grades (E0–E4)

Use [evidence.md](../discover/references/evidence.md). Bound observed and inferred populations separately; do not convert source count into confidence. You do not close falsify.

## Self-check

- [ ] Unit declared (tenant vs user)?
- [ ] Lower and upper bound **or** 未量化 (never a fake %)?
- [ ] Channel + who is unheard named?
- [ ] Status-quo alternative written?
- [ ] No RICE score, no FR, no "we should build"?
- [ ] E3 rows have a counted snapshot (else E1 / 未量化)?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [templates/market.md](templates/market.md) | Writing `00-discover/market.md` |

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.

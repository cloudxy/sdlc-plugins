---
name: "compete"
description: "Use this skill when the spawn packet names hat competitor or $compete. Do NOT use from parent /sdlc or for RICE/feature design."
when_to_use: "Spawn packet names competitor / $compete. Do NOT use from parent /sdlc, RICE ranking, or writing spec.md."
---

# Compete — snapshot for this change

Job: **borrow / avoid / differentiate** for one change, with scene gap and source grade. "They have it" is a list, not analysis.

Load inside `sdlc-workflow:competitor`. Long form (full battlecard) is `PLUGIN_ROOT/skills/signals/templates/competitor-analysis.md` — Read it when one row is not enough (L3/L4, new surface, differentiate-and-over-appetite). Default deliverable is the snapshot.

| Task | Approach |
|---|---|
| **This change vs others** | Fill [templates/snapshot.md](templates/snapshot.md) |
| **Copy request** | Still ask: do *our* users have the same problem? Same scene? |
| **No named rival** | Status quo (Excel / manual / unused) still fills the set |

## Gotchas

- **Evidence is claim-specific.** Apply [the canonical research evidence policy](../discover/references/evidence.md): dated internal or external sources, scope and limitations; no universal source-count or web-only requirement.

- **Status quo is always in the set.** Empty set without 现状 fails the gate.
- **A sales page supports what is advertised**, not proven performance. Record trial version, tier and date; absence from docs is unknown, not proof the competitor cannot do it.
- **Borrow at feature-point grain.** Say what you will not copy. Avoid needs an alternative + revisit trigger. Differentiate needs observed differences and defensibility assumptions; do not invent claims about what others cannot build.
- **Gaps-only lists cause blind chase.** Compare evidenced strengths and limitations; mark unverified cells unknown.
- **Do not RICE or pick the FR.** Pass the snapshot to discover / pm.

## Self-check

- [ ] Set includes 现状?
- [ ] One row for this change, not a full product matrix?
- [ ] Conclusion is borrow/avoid/differentiate with scene gap?
- [ ] Each claim has a source grade?
- [ ] No "we should build because they have it"?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [templates/snapshot.md](templates/snapshot.md) | Writing `00-discover/compete.md` |

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.

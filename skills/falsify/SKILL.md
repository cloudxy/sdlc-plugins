---
name: "falsify"
description: "Use only when the user types $falsify (deprecated alias of discover). Do NOT use from /sdlc or discover."
when_to_use: "Only the user typing $falsify. Deprecated: sunset 2026-12-31. Do NOT use from /sdlc or /sdlc-discover (discover applies the method itself), to write spec.md or to run post-launch experiments."
---

# Falsify — deprecated compatibility entry

**Deprecated; sunset 2026-12-31.** Use `sdlc-workflow:discover`: its [assumption-testing method](../discover/references/assumption-testing.md) owns the method and verdict criteria, and Step 1b of `/sdlc` applies it inside discover. This entry only keeps `$falsify` working until then. Evidence grades live in [discover’s evidence reference](../discover/references/evidence.md).

## Gotchas

Do not invent evidence or change failure criteria after seeing results. Do not duplicate the method here. Discovery validation does not prove production readiness; launch experiment analysis belongs to retro.

## Output

Update briefing § Falsify with assumptions, evidence, failure criteria and a scoped kill/narrow/bet/pass verdict. For a standalone invocation use discover's [assumptions template](../discover/templates/assumptions.md) and link it from briefing instead of copying it.

## Self-check

Confirm each load-bearing assumption has a test/evidence reference, uncertainty and an explicit decision; apply the canonical method’s full checks.

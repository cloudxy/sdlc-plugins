---
name: "falsify"
description: "Use this skill when /sdlc-discover or /sdlc Step 1b reaches Falsify, or $falsify. Do NOT use for spec.md or launch A/B."
when_to_use: "Discover Falsify or /sdlc Step 1b, or $falsify. Do NOT use to write spec.md or run post-launch experiments."
---

# Falsify — compatibility entry

Apply [discover’s assumption-testing method](../discover/references/assumption-testing.md). That file owns the method and verdict criteria; this entry preserves `$falsify` and existing calls. Evidence grades live in [discover’s evidence reference](../discover/references/evidence.md).

## Gotchas

Do not invent evidence or change failure criteria after seeing results. Do not duplicate the method here. Discovery validation does not prove production readiness; launch experiment analysis belongs to retro.

## Output

Update briefing § Falsify with assumptions, evidence, failure criteria and a scoped kill/narrow/bet/pass verdict. For a standalone invocation use [the assumptions template](templates/assumptions.md) and link it from briefing instead of copying it.

## Self-check

Confirm each load-bearing assumption has a test/evidence reference, uncertainty and an explicit decision; apply the canonical method’s full checks.

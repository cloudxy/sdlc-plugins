---
name: "falsify"
description: "Use this skill when /sdlc-discover or /sdlc Step 1b reaches Falsify, or $falsify. Do NOT use for spec.md or launch A/B."
when_to_use: "Discover Falsify or /sdlc Step 1b, or $falsify. Do NOT use to write spec.md or run post-launch experiments."
---

# Falsify — try to kill the change before spec

Job: **write load-bearing assumptions that can be false**, the cheapest test, and a verdict. Confirmation is not the goal. Launch A/B belongs to `retro` / analyst — not here.

Invoke from the discover window after survey + discuss. Do not invent evidence; cite market.md / compete.md / interview returns.

| Task | Approach |
|---|---|
| **Problem-layer** | Walk `prd-gwt` triage (no source / one customer / copy / future) against survey |
| **Solution-layer** | 2–4 assumptions on the chosen A/B/C |
| **No cheap test left** | Bet (Confidence ≤50% + named metric) or stop |

## Gotchas

- **"Users said they want it" is not a pass.** That is E1. **Pass** is legal only when every load-bearing row is ≥E2 and kill criteria did not fire. Unquantified cannot pass — only kill / narrow / bet.
- **Do not upgrade E1 to E3.** E3 is counted behaviour (number + source + window). Operator chat stays E1.
- **Kill criteria are written before results.** Do not relax them after a disappointing interview.
- **Unquantified market cannot "pass".** Only kill / narrow / bet.
- **Safety, permissions, consistency cannot be killed for appetite.** Narrow the surface; do not drop audit.
- **A/B in discovery is fake science.** Sample size and peeking rules live in experiment-design. Discovery uses cheaper rungs (probe, counts, 5 past-behaviour interviews, competitor reviews, fake door, logic prototype).

## Evidence grades

E0 rumour · E1 operator · E2 cited artifact · E3 counted behaviour · E4 registered test.

## Cheapest-test ladder (stop when killed)

1. Three-question probe / demand a ticket id  
2. Behaviour counts  
3. Five Mom-Test interviews / questionnaire return  
4. Competitor reviews + trial  
5. Fake door / waitlist (`prototype` FAKE branch)  
6. Logic prototype / wizard-of-oz  
7. Launch experiment — **forbidden here**; bets only reserve the metric

## Verdict

- **Kill** → `discovery.status: killed`. No pm.  
- **Narrow** → rewrite Claim, allow define on the smaller claim.  
- **Bet** → name the metric that define must use as north-star or driver.  
- **Pass** → every load-bearing row ≥E2 and kill criteria not triggered.

Write the table into `00-discover/briefing.md` § Falsify (template lives with discover). Optional copy: [templates/assumptions.md](templates/assumptions.md).

## Self-check

- [ ] 2–4 load-bearing rows, each one falsifiable sentence?
- [ ] Kill criteria written before results?
- [ ] Unquantified did not pass?
- [ ] Verdict filled? Bet has a metric name?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [templates/assumptions.md](templates/assumptions.md) | Standalone assumption table |

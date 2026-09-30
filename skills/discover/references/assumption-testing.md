# Falsify — try to kill the change before spec

Job: **write load-bearing assumptions that can be false**, the cheapest test, and a verdict. Confirmation is not the goal. Launch A/B belongs to `retro` / analyst — not here.

Invoke when the current discussion exposes load-bearing uncertainty. Use relevant research, existing artifacts or interview returns; a survey is not required for every bounded question. No existing evidence means an explicit hypothesis and learning step, not fabricated findings or automatic rejection.

| Task | Approach |
|---|---|
| **Problem-layer** | Walk `prd-gwt` triage (no source / one customer / copy / future) against survey |
| **Solution-layer** | load-bearing assumptions on the chosen A/B/C |
| **No cheap test left** | Bet (explicit uncertainty + named metric) or stop |

## Gotchas

- **"Users said they want it" is not a pass.** That is E1. **Pass** requires evidence relevant and strong enough for each load-bearing assumption, with predefined failure criteria not triggered. Merely attaching an E2 citation is insufficient. Unquantified cannot pass — only kill / narrow / bet.
- **Do not upgrade E1 to E3.** E3 is counted behaviour (number + source + window). Operator chat stays E1.
- **Kill criteria are written before results.** Do not relax them after a disappointing interview.
- **Unquantified market cannot "pass".** Only kill / narrow / bet.
- **Safety, permissions, consistency cannot be killed for appetite.** Narrow the surface; do not drop audit.
- **A/B in discovery is fake science.** Sample size and peeking rules live in experiment-design. Discovery uses cheaper rungs (probe, counts, targeted past-behaviour interviews, competitor reviews, fake door, logic prototype).

## Evidence grades

See [evidence.md](evidence.md), the sole definition of evidence labels. Grades do not by themselves establish validity.

## Cheapest-test ladder (stop when killed)

1. Three-question probe / demand a ticket id  
2. Behaviour counts  
3. Targeted past-behaviour interviews / questionnaire return  
4. Competitor reviews + trial  
5. Fake door / waitlist (`prototype` FAKE branch)  
6. Logic prototype / wizard-of-oz  
7. Launch experiment — **forbidden here**; bets only reserve the metric

## Verdict

Do not choose a verdict from missing evidence alone. When the scenario, load-bearing assumptions, investment boundary or bet metric is still unknown, leave the verdict pending and resolve the relevant gap. Direction approval can authorize continued exploration without authorizing a larger implementation bet. Define tests from the actual claim; do not prescribe generic interview counts or numerical kill thresholds before that context exists. Proposed criteria are not executed results or accepted decisions.

- **Kill** → `discovery.status: killed`. No pm.  
- **Narrow** → rewrite Claim, allow define on the smaller claim.  
- **Bet** → name the metric that define must use as north-star or driver.  
- **Pass** → scoped assumptions supported by relevant evidence and failure criteria not triggered; disclose what remains unknown.

Write the table into `00-discover/briefing.md` § Falsify (template lives with discover). Optional copy: [assumptions template](../templates/assumptions.md).

## Self-check

- [ ] Load-bearing rows, each one falsifiable sentence?
- [ ] Kill criteria written before results?
- [ ] Unquantified did not pass?
- [ ] Verdict filled? Bet has a metric name?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [assumptions template](../templates/assumptions.md) | Standalone assumption table |

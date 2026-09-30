# Discuss protocol — help needs take shape

Use this method when uncertainty affects the next action, including a small change or a later refinement. Some users know their needs but cannot express them; others form preferences through examples and tradeoffs. Treat your interpretation as revisable. Reuse settled decisions and investigate readable facts yourself. The manager keeps the conversation; a delegated specialist returns unresolved decisions with options and affected scope through the manager.

## Choose the next helpful move

Identify what is unclear: person/context, desired outcome, solution, constraint, acceptance, or supporting evidence. Delivery size and uncertainty are separate. A bounded question may need only a short exchange; it does not require a new discovery workspace or a market survey.

| Current signal | Helpful move | Guard against |
|---|---|---|
| Vague wish or abstract adjective | Ask for a recent concrete episode and the change the user hopes for | Converting “smart” into an AI feature list |
| “I don't know” / cannot recall an episode | Offer tentative scenarios, contrasting examples or a small sketch to react to | Repeating the same abstract question or demanding a completed brief |
| A requested feature with unclear purpose | Explore context and intended progress using JTBD; retain the original proposal | Assuming every user-proposed solution is wrong |
| No view of the possibilities | Show credible alternatives and relevant references, with tradeoffs | Inventing alternatives to meet a count or treating a competitor as demand evidence |
| All offered options rejected | Accept the correction, summarize what was ruled out and revise the problem frame | Repackaging or defending the same recommendation |
| Hard to imagine the experience | Walk one scenario with a storyboard, flow sketch or sample input/output | Building a full application just to clarify a concept |
| Conflicting goals or stakeholders | Make the tradeoff and decision owner explicit; use an actor/impact map if useful | Simulating stakeholder agreement |
| Behavior still ambiguous | Separate the rule, concrete examples and unanswered questions | Inventing an accepted outcome to complete GWT |
| Scope and behavior already authorized | Cite the decision and continue; ask only about consequential gaps | Reopening settled choices or requesting the same approval |

Usually focus a turn on one uncertainty that changes scope, reduces consequential risk or unlocks work. Related questions can be grouped when manageable. Dependency ordering helps select the next question; it is not a requirement to ask the entire available frontier or to finish in a fixed number of rounds. Wait for an answer only when dependent work needs it; continue independent investigation.

## Elicit, then offer something to react to

Start with an open opportunity to describe the situation. When that is difficult, change the representation rather than increasing the interrogation:

- Recent episode: “上一次发生时，你原本想完成什么，卡在哪一步？”
- Tentative interpretation: “目前我理解你更在意请求有人负责；这还只是我的理解。”
- Conversation starter: “省心可能是少录入、少漏跟进、少追人。哪一种接近你的经历？也可能都不是。”
- Concrete walkthrough: show one short example or sketch and invite corrections to the part that does not fit.

These are possible moves, not a mandatory sequence. Start with a small contrast the user can react to; do not turn starters into a catalogue or stack an additional fallback question before hearing the reaction. Expand when that reaction calls for it. Keep unfamiliar framework terminology out of the user's way. For a new idea without past examples, label imagined scenarios as hypothetical; do not fabricate history or interview answers.

The existing three-question probe remains useful where answers are missing: how it is done today, where it breaks, and what becomes possible afterwards. Current workaround cost is one value signal, not a universal value ceiling. JTBD/value-path concepts live in [product-shaping.md](../../prd-gwt/references/product-shaping.md); consult them when the purpose needs unpacking, not for every clear request.

## Options, recommendations and evidence

Distinguish **elicitation** from **decision support**. Conversation starters are disposable prompts, not a closed menu or a demand test. Let the user reject, combine or replace them. Avoid pushing a preferred solution before the problem is understood. When a consequential choice is ready, give a recommendation with its assumptions, benefits, costs/constraints and what would change it.

Use genuinely different alternatives where useful, including the user's proposal and the status quo when relevant. Identify references as inspected public examples, existing project behavior, or invented illustrations. Do not claim to have inspected an unavailable reference. A user's preference after seeing options can inform a decision, but does not establish market demand or solution effectiveness.

A small inline illustration can help the manager explain a choice. A delegated prototype or actual experiment uses the registered `designer/market/prototype` task and its learning question; accepted UI design still belongs to the design contract. No production code or full FR/GWT authoring in discovery.

## Keep understanding and decisions recoverable

Update the existing briefing/work brief rather than creating a new document each round. Keep:

- User statements with source/context; distinguish observation from interpretation using [evidence.md](evidence.md).
- Current understanding, hypotheses and unresolved questions. A goal or preferred solution can still be provisional.
- Decisions with authority/source and scope. Agreement on a direction is not validation of its promised effect; silence is not a decision.
- Material corrections: what changed, why, what remains valid, and affected requirements/consumers. Use existing Q-* / A-* / requirement IDs and version rules; do not silently overwrite a handed-off decision.

Resume from those records. Do not re-ask answered questions or re-propose rejected options without new information. If the user changes a detail, revisit its rule/examples; if a solution changes, revisit its tradeoffs; if the goal or audience changes, revisit the problem frame. Block affected consumers only. Learning during conversation is not automatically a definition failure.

## Ready for the next action

For the current slice, check shared understanding of who/context/outcome, scope and important constraints, observable success/failure examples appropriate to the next stage, and the source of consequential decisions. Load-bearing assumptions need relevant evidence or an explicit authorized bet with a bounded learning step. Unresolved questions name an owner or evidence source and their blocked scope.

Do not require all future unknowns to disappear. An accepted brief and authorization to continue are enough when they cover the next action. Scope acceptance and effectiveness evidence are separate: an authorized bounded bet can be ready while its effect remains unverified. If the current brief or sketch is unavailable, ask for its context without re-asking approval of the direction. If only part is ready, record that boundary and use scoped-work for independent ready work. An unanswered strategic question stays pending. Exploration-only ends with its result.

## Three interlocutors

| Who | Where | Output |
|---|---|---|
| Operator (this chat) | These rounds | Decisions, appetite, which surface first |
| Absent stakeholder (legal / CS / buyer) | Questionnaire file | Do not guess |
| Real user / tenant admin | Interview script the operator takes outside | No returned observation means no new evidence; apply evidence.md to actual returns |

## Interview script (operator takes out)

Ask past behaviour, not "would you use this":

- Last time this happened: when, what did you do, how long, who else was involved?
- What did you try that failed?
- In evidence-gathering interviews, collect the story before pitching solutions. If a concept is shown to elicit reactions, record that prompted context; do not present it as an unprompted need or measured demand.

## Questionnaire (async)

Write `00-discover/questionnaire-<slug>.md`: purpose, from/to, how answers will be used, one idea per question, answer stub, "why this matters" only when the question can be misread. Most-important-first. Closing catch-all.

## Method provenance

Adapted for this workflow, not a quota or a separate stage: [JTBD](https://www.christenseninstitute.org/theory/jobs-to-be-done/), [story-based interviews](https://www.producttalk.org/story-based-customer-interviews/), [conversation starters](https://www.designkit.org/methods/conversation-starters.html), [rapid prototyping](https://www.designkit.org/methods/rapid-prototyping.html), and [example mapping](https://cucumber.io/docs/bdd/example-mapping/). The [Double Diamond](https://www.designcouncil.org.uk/resources/framework-for-innovation/) supplies iterative problem/solution exploration. The existing mattpocock grilling dependency tree and Mom Test past-behavior questions remain useful; whole-frontier rounds are not required.

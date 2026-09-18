# Discuss protocol — grilling + scripts for people not in chat

Borrowed from mattpocock grilling (frontier rounds) and the Mom Test (past behaviour, no pitch).

## Grilling rounds

Map the work as a **design tree**. The **frontier** is every decision whose prerequisites are already settled. Ask the whole frontier in one round. A question that depends on an unanswered question in this round belongs later.

```
❓ **Q1** - **<title>**: <body; prefer choices>

➡️ <recommended answer>

---

❓ **Q2** - ...
```

Wait for answers. Recompute the frontier. Done when the frontier is empty **and** the human confirms shared understanding. Finding facts (survey files, repo) is yours; do not ask what you can Read.

## Three-question probe (Discuss-P)

Users state solutions. Never implement the stated solution without this:

1. How do you do this today? → workaround cost is the value ceiling
2. Where does it break?
3. If it were done, what would you do next? → real goal

Follow-ups: "方便" → where, how long; "其他系统都有" → what do you *do* there; "以后可能需要" → is there a scene now; "老板要求" → run the three questions on the boss's problem.

## Three interlocutors

| Who | Where | Output |
|---|---|---|
| Operator (this chat) | These rounds | Decisions, appetite, which surface first |
| Absent stakeholder (legal / CS / buyer) | Questionnaire file | Do not guess |
| Real user / tenant admin | Interview script the operator takes outside | Until it returns, related claims stay E1 |

## Interview script (operator takes out)

Ask past behaviour, not "would you use this":

- Last time this happened: when, what did you do, how long, who else was involved?
- What did you try that failed?
- Do not pitch A/B/C. If they volunteer a solution, still run the three questions.

## Questionnaire (async)

Write `00-discover/questionnaire-<slug>.md`: purpose, from/to, how answers will be used, one idea per question, answer stub, "why this matters" only when the question can be misread. Most-important-first. Closing catch-all.

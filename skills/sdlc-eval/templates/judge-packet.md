# Judge packet v2 (fill `<FOLDER>`; send nothing else)

```
## JUDGE PACKET v2
role: blind judge — fresh context, no stake in either output
folder: <FOLDER>            # e.g. …/iteration-3/design-contract-2/blind

1. Read <FOLDER>/rubric.json: task_prompt, reference_notes (what good looks like), criteria (id, criterion, weight),
   scale, judgment_schema, validate_command.
2. Inventory both sides first: `find <FOLDER>/A <FOLDER>/B -type f | sort` (sides have subfolders). Read every document.
   Open every image and look at it; judge visual work from the pictures, not from descriptions. An empty side scores 1.
3. A and B are separate folders. Before you credit a passage, check which folder it came from. Crediting one side with
   the other side's content is the most common judging error, and the validator rejects it.
4. Score A and B independently on each criterion, 1–5:
     1 missing or wrong · 2 superficial (the words are there, the substance is not) · 3 adequate with visible gaps
     4 strong: specific, evidenced, few gaps · 5 excellent: a senior practitioner would ship it as-is
   Each "why" is one line that carries evidence from THAT side: a verbatim quote in 「」 (at least 6 characters, copied
   exactly from a file on that side) or the path of an image on that side that you looked at (A/… or B/…).
5. Defects: when you verify a real defect — wrong against the task or inputs, an internal contradiction, a broken,
   overlapping, clipped or unreadable rendering, a required state or path that is missing — record it under "defects"
   with the criterion it affects and the file on that side. That criterion scores at most 3 for that side.
   Style preferences and typos are not defects.

Rules:
- Judge substance: reasoning, real alternatives, numbers, evidence, rendered results. Not length, file count,
  formatting or confident tone. More files is not better work.
- Keywords from the rubric appearing in an output are not evidence; check whether the thing was actually done.
- Do not guess which process produced A or B. Read nothing outside <FOLDER>. Do not browse the web.
- If both are poor, score both low; if both are excellent, score both high. "tie" is allowed.

Write exactly one file, <FOLDER>/judgment.json:
{
  "inventory": { "A": ["<every document on A, path relative to A/>"], "B": ["<every document on B>"] },
  "defects":   { "A": [{"criterion": "<id>", "file": "A/<path>", "defect": "<what and where>"}], "B": [] },
  "scores": {
    "A": { "<criterion_id>": {"score": <1-5>, "why": "<one line with 「a verbatim quote from A」 or A/<image path>>"}, ... },
    "B": { "<criterion_id>": {"score": <1-5>, "why": "<one line with 「a verbatim quote from B」 or B/<image path>>"}, ... }
  },
  "preference": "A" | "B" | "tie",
  "rationale": "<2–3 sentences on the decisive differences in substance>"
}
Every criterion id from rubric.json appears for both A and B.

Then run the validate_command from rubric.json. If it lists problems, fix them from the files: for a suspected swap,
re-read both sides and re-score that criterion from scratch; never move a quote to the other side just to pass.
Repeat until it prints ✓ (at most 3 rounds).
Return only: "judged <FOLDER>" — or "judged <FOLDER> — validate still failing: <first problem>".
```

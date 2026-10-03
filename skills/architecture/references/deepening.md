# Deepening survey — cycle / deepen-survey

<!-- 来源（派生，只作追溯）：改写自 mattpocock/skills@d81f3a1 的 skills/engineering/codebase-design（SKILL.md、DEEPENING.md）与 improve-codebase-architecture。已按本插件合同改写：报告写进周期目录，不写临时 HTML；候选先交人选择，再走 architecture 的常规任务。上游变更不自动同步。 -->

Use in a product cycle to find where the code is getting harder to change, before it turns into rework. The output is a list of candidates for a person to choose from; nothing is refactored here.

## Vocabulary

Use these words exactly in the report.

- **Module**: anything with an interface and an implementation (function, class, package, slice).
- **Interface**: everything a caller must know to use it correctly: types, invariants, ordering, error modes, configuration, performance.
- **Depth**: behavior a caller or test can exercise per unit of interface it must learn. Deep = a lot of behavior behind a small interface; shallow = interface nearly as complex as the implementation.
- **Seam**: the place where an interface lives and behavior can vary without editing callers.
- **Locality**: change, bugs and verification concentrate in one place. **Leverage**: one implementation serves many callers and tests.

Tests: the **deletion test** (delete the module; if complexity vanishes it was a pass-through, if it reappears across callers it earned its place); **the interface is the test surface** (callers and tests cross the same seam); **one adapter is a hypothetical seam, two adapters a real one**.

## Procedure

1. **Scope by evidence, not by reading everything.** Find hot spots from history (`git log --format= --name-only` over the cycle window, plus defect fixes and escapes recorded in `.sdlc/_outcomes/`). If the user named an area, start there. Read `domain-model.md` and the ADRs for the area first; do not re-suggest what an ADR rejected unless the friction is now real enough to reopen it, and say so.
2. **Look for friction** in the hot spots: one concept spread across many small modules; shallow interfaces; pure helpers extracted for testing while bugs hide in how they are called; coupled modules leaking across seams; code that is hard to test through its interface.
3. **Classify each candidate's dependencies**: in-process; local-substitutable (test stand-in exists); remote but owned (port + adapters); true external (injected port, mock adapter). The category decides how the deepened module would be tested.
4. **Write `outputs/deepening.md`.** Per candidate:
   - files;
   - the problem;
   - the direction in plain words;
   - the benefit in locality and leverage, and how tests would improve;
   - the dependency category;
   - recommendation strength: `strong`, `worth exploring` or `speculative`.

   End with the one you would tackle first and why.
5. **Stop at candidates.** Do not propose interfaces yet. A chosen candidate becomes ordinary architecture work (shape/contract or a refactor ticket) with its own decisions. A candidate the user rejects for a reason a future survey needs gets an ADR, so it is not re-suggested.

## Limits

This is a survey, not a rescue. It does not justify a sweeping rewrite or a refactor mixed into a fix, and a pleasant design is not evidence of value: rank candidates by recent change cost and recorded escapes.

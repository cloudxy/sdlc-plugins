# Design Quality Rubric (`design-contract`)

Both `designer` (self-check before return) and `reviewer` / `qc` (independent G-fresh and design QA) judge design deliverables against this rubric. Static prose without inspected rendered screenshots, or happy-path-only screens missing state/a11y contracts, is a **major** finding.

## Expert Bar vs. Mediocre Order-Taker

| Dimension | Expert Product Designer | Mediocre Order-Taker (Reject) |
|---|---|---|
| **Scope & Direction Choice** | Explicitly justifies `reuse`, `local-exploration` or `new-direction`; when exploring, renders structurally distinct clickable prototypes, inspects PNGs at real breakpoints, fixes visual defects before recommending, and ties the signature moment to Aha | Invents 3 colour swaps of one layout, falls into unexamined AI-default face clusters, or recommends a prototype with clipped text / horizontal overflow at `375px` |
| **Cognitive Load & Hierarchy** | Applies **Tesler's Law** (smart defaults absorb complexity), **Jakob's Law** (familiar workbench conventions), **Hick's Law** (1 primary CTA + progressive disclosure), **Miller's Law** (`5–7` item chunking), and **Gestalt** (proximity/whitespace over nested card-border soup) | Dumps every database field onto equal-weight cards; multiple competing primary buttons; nested `card-in-card` borders everywhere |
| **State Isomorphism (`UI = f(State)`)** | Distinguishes `in-flight loading` vs `arrived empty` vs `error` vs `permission unknown/denied`; preserves user form drafts on failure/back; defines optimistic rollback and **forward migration for hidden/deprecated cached client steps** | Flashes「暂无数据」while loading or failing; closes modals and wipes user input on `500`; leaves stale `localStorage` wizard steps active |
| **Latency & Physical Ergonomics** | Designs to **Doherty Threshold** (`<100ms` press feedback, `<400ms` flow, `>200ms` zero-CLS skeleton/dimmed refresh, `>10s` server-recoverable async + cancel) and **Fitts's Law** (`≥44×44px` targets, destructive actions physically separated from Save/Confirm) | Full-page spinner on every filter click; `24px` icon buttons; red Delete button flush next to Submit with no confirmation |
| **Tokens, Copy & WCAG AA** | Consumes semantic tokens only; audits actual foreground/background contrast pairs (`≥4.5:1` / `≥3:1`), second non-colour channel, Tab/Escape focus trap & return, icon `aria-label` copy, `prefers-reduced-motion`, and actionable `what happened + next step` copy | Hardcoded hex/px values, low-contrast grey secondary text, missing `:focus-visible`, or dead-end copy（「提交」「暂无数据」「出了点问题」） |
| **Build Design QA (`design-qa`)** | Captures running build at matching breakpoints/states, compares side-by-side with final prototype PNGs, verifies signature moment timing/motion, and ranks concrete visual/interaction regressions | Writes「实现基本符合设计」from reading source code or looking at one desktop happy-path screenshot |

## Core Principles

1. **Rendered Proof Over Prose:** A direction, edge state or QA sign-off is judged by inspected PNGs at real breakpoints, never by promising adjectives in Markdown.
2. **Complexity Belongs in Defaults, Not User Forms (Tesler):** Hide derivable knobs behind smart defaults and progressive disclosure while keeping one clear primary action per view.
3. **Authoritative State Honesty:** Never disguise loading, permission-unknown or network failure as empty state, and never let deprecated cached client steps fire silently after a UI change.

## Second-Order Scan (Before Delivery)

- **State & Refresh Torture Test:** What happens when the user edits half a form, submits into a `422`/`500`, refreshes mid-job, or upgrades from an older UI version with cached local state?
- **375px & Long-Content Stress:** Do CJK/German long labels, 0-item and 10,000-item counts, and mobile viewports keep the primary CTA, error recovery and navigation reachable without clipping?
- **Frontend Zero-Guess Test:** Can `frontend` port `02-shape/prototypes/final/` + `flows.md` + `edge-states.md` + `design-tokens.json` without inventing a single colour, breakpoint, disabled reason, or focus rule?

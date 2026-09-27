# Frontend — design contract to interactive reality

Job: **turn design contracts into interactive reality** — tokens over hardcoding, component library over one-off components, project-appropriate data/state handling.

| Task | Approach |
|---|---|
| **Implement a page/component** | Open the final prototype (`02-shape/prototypes/final/`) + story + tokens + edge-states → map its `data-component` IDs to components → implement → 9-dim self-check → build verify |
| **Edge states (stack-agnostic)** | Walk empty/loading/error/boundary/permission/offline from the design matrix first; library choice is downstream |
| **Responsive adaptation** | Breakpoint strategy → per-breakpoint layout → test at 375/768/1024/1440 |
| **Debug UI issue** | Screenshot → inspect DOM → trace to CSS/state → fix → re-screenshot |
| **Add a11y** | Semantic tags → ARIA → keyboard navigation → contrast check |

## Gotchas — verified lessons; check they match your stack

Use the current project framework, component library and authoritative build commands. The examples below do not mandate React, antd, npm or a two-app workspace. Native UI uses its device/preview/test tools.


- **Workspace packages consumed through build output go stale.** After editing a shared package's source, rebuild it (or point consumers at source) before running an app; a stale build caused a verified runtime crash.
- **ESM-only dependencies need test-transform exceptions.** Configure the test runner to transpile them, or every suite fails with "Cannot use import statement outside a module".
- **Fullwidth characters (`（）：`) adjacent to bare bash variables** cause bash 3.2 to parse them as part of the variable name. Use `${VAR}` always.
- **`status` is a read-only variable in zsh.** Don't use it as a variable name in build scripts.
- **An empty permission cache means "not loaded yet".** Refetch after a reload; never render it as "no permissions" (blank navigation) or as "all permissions" (privileged entries leak). Caches in localStorage outlive the session — clear on logout or version change.
- **Untrusted third-party text renders as text.** Never pass it through a markdown/HTML renderer; when the page moves, its XSS test moves with it.

## From the final prototype to code

The final prototype is the design target **in code**, not a picture. Screenshots of it are for reference only.

1. Open `02-shape/prototypes/final/` (HTML/CSS). List its `data-component` IDs: each becomes a real component — reuse the component library first, extract when reuse or consistency warrants it.
2. Its CSS variables are the tokens: map them to the project's token system; never copy literal values.
3. Every state it can show (`?state=empty|loading|error|…`) is a state you implement, with its copy verbatim.
4. Rebuild, do not paste: the prototype has fake data, no data layer and may skip semantics. Keep its layout and behaviour; write real components, real data fetching and accessible markup.
5. Prototype, `flows.md`, edge-states and spec disagree → stop and raise an open question to pm (behaviour) or designer (layout, copy). Do not pick one silently: that is how "the feature does not match" starts.
6. Where the design is silent (a hover state, a spacing between two blocks, an empty column), decide with the visual judgement in [frontend-design](../../../vendor/anthropic-skills/skills/frontend-design/SKILL.md) (packet `inputs`; upstream original) — within the tokens and the prototype's direction, never overriding them.

## Key decisions

### 9-dimension self-check (every component)

1. Spacing — tokens, not magic numbers
2. Color — tokens, no hardcoded hex
3. Font — token-defined families and sizes
4. Border radius / shadow — token consistency
5. Icons — the project’s established accessible icon system
6. Interaction states — hover/focus/disabled/loading all handled
7. **State completeness** — every edge-state from design covered (empty/loading/error/boundary/permission/offline)
8. Responsive — tested at mobile/tablet/desktop breakpoints
9. Accessibility — semantic tags, ARIA, keyboard navigation, contrast ratio

### Data fetching — React Query example where the project uses it

```jsx
// ✅ react-query with conditional polling
const { data, isLoading } = useQuery({
  queryKey: ['tasks', page, status],
  queryFn: () => fetchTasks(page, status),
  refetchInterval: (query) => {
    const active = query.state.data?.items.some(t => t.status === 'running');
    return active ? 3000 : false;  // stop when terminal
  },
});
```

Choose the existing framework’s data model; verify cancellation, stale responses, retry, polling shutdown and state consistency rather than requiring this library.

### Component library alignment

Extract a shared component when behavior and visual consistency are stable enough that the reuse benefit exceeds the abstraction and change cost. Repeated Card+Table+Search layouts are a signal to compare interfaces and states, not a fixed occurrence threshold. Keep variants local when their responsibilities are still diverging.

### Integration run (slice done definition)

1. Start the app (`app.start` in `sdlc.config.yaml`) against the real backend — not the mock.
2. Walk the ticket's journey steps as a user from a realistic starting state (new account, empty data, mobile width).
3. Screenshot each step: `bash PLUGIN_ROOT/scripts/ui-evidence.sh <url> 03-impl/screens/T-<n> 375,1440`; open the PNGs.
4. Compare with the final prototype at the same breakpoint and state (open both side by side): layout, hierarchy, the signature moment, state copy. Fix visible gaps now; record the rest.
5. Trigger at least empty, error and permission states; confirm tracking events fire.
6. Write `03-impl/T-<n>-integration.md` from the integration template.

## Handoff contract

| Direction | Content |
|---|---|
| **Input** | Ticket (journey slice + FR anchors) · spec §2 core value · **final prototype `02-shape/prototypes/final/` (code, component IDs, states)** · `flows.md` · edge-states matrix · tokens / `design-system.md` · API contracts + examples · `tracking.md` · frontend-design (visual judgement where the design is silent) |
| **Output** | Component implementation · 9-dim self-check report · build output (exit code) · evidence file · `T-n-integration.md` with screenshots |
| **Downstream** | `qa` (component + edge-states matrix for verification) · `qc` (self-check report as review input) |
| **Refuse** | Defining design tokens (→ designer) · implementing API endpoints (→ backend) · final quality verdict (→ qc) |

## Self-check

- [ ] Applicable project build/target checks exit 0?
- [ ] `check-frontend.sh` zero violations?
- [ ] 9 dimensions walked through?
- [ ] Every `data-component` in the final prototype maps to a component, and every prototype state is implemented?
- [ ] Edge-states matrix items covered?
- [ ] No hardcoded color/spacing values?
- [ ] Data/state handling follows the project and handles cancellation/stale responses?
- [ ] Routes have lazy/ErrorBoundary/404?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [frontend-design](../../../vendor/anthropic-skills/skills/frontend-design/SKILL.md) | Deciding visual details the design did not specify (upstream original; install with `bash vendor/install.sh`) |
| [edge-states-impl.md](ui/edge-states-impl.md) | Implementing a component with complex state (empty/loading/error/boundary) |
| [state-and-data.md](ui/state-and-data.md) | Deciding state ownership, data fetching patterns, or debugging re-render issues |
| [templates/impl-evidence.md](../templates/impl-evidence.md) | Implementation evidence (command + exit code) |

> Gotchas based on: `anthropics/skills@41bbe19` (docx SKILL.md footgun pattern — 'the model knows the API; these are the footguns') · verified incidents from a user project's history

# Direction and final prototypes

Design prototypes are **design deliverables**, not throwaway experiments. The `prototype` skill (throwaway, "skip polish", `00-discover/prototypes/`) answers one discovery question and is never used for design directions or handoff. Keep the two apart:

| Purpose | Owner / task | Path | Quality bar |
|---|---|---|---|
| Test one hypothesis in discovery | discover / falsify with `prototype` | `00-discover/prototypes/` | Throwaway; answers one question |
| Design direction | designer `explore` | `02-shape/prototypes/D<n>/` | Clickable main journey to the Aha moment, real copy, screenshots at the product's supported viewports/devices (375/1440 are web examples) with no visible defects |
| Final prototype (handoff) | designer `specify` | `02-shape/prototypes/final/` | The picked direction, every screen in `flows.md`, every state in `edge-states.md`, tokens only, component IDs |

## Direction prototypes (`explore`)

1. One folder per direction: `02-shape/prototypes/D1/index.html` (+ assets). Use isolated views of the existing stack/components when practical; plain HTML/CSS/JS is a web fallback. Native products use appropriate runnable preview sources and device/emulator captures. Record start commands and dependencies; stub external effects. Fake data must look like this product's real data.
2. Cover the main journey up to the Aha moment and the direction's signature moment. Other screens can be stubs, marked as stubs.
3. Real copy in the product's language. No lorem ipsum, "Button", "Title".
4. Screenshots: `bash PLUGIN_ROOT/scripts/ui-evidence.sh 02-shape/prototypes/D1/index.html 02-shape/prototypes/D1/shots 375,1440`, then Read every PNG. Record each screenshot in the 缺陷检查 table of `design-directions.md` (overlap, clipped or overflowing text, horizontal scroll at 375, alignment, contrast, placeholder content). Fix and recapture until the row is clean — a direction with a visible defect is not recommendable.
5. Cite the screenshots in `design-directions.md` by relative path. The gate checks that every cited image exists.

## Final prototype (`specify`)

The handoff that frontend builds against. It turns the picked direction into the exact target:

- **Every FR screen** in `flows.md` exists as a page or a view; navigation between them works.
- **Every state** in `edge-states.md` (empty, loading, error, partial, permission, overflow) is reachable, e.g. with a `?state=empty` switch, and has its real copy.
- **Tokens only:** colours, type, spacing and radii come from the design tokens / `design-system.md` (CSS variables). Shared design values use the canonical token source; layout-specific values need not become gratuitous global tokens. Do not manually duplicate a second token set in the prototype.
- **Component IDs:** mark reusable parts with `data-component="<id>"` so implementation, review and design QA refer to the same things.
- **Close to the real stack:** when the project has a component library or design tokens in code, build the final prototype with the same class names, token names and component boundaries, so frontend ports it instead of redrawing it.
- **Screenshots** of every screen × state at supported device/viewport sizes in `02-shape/prototypes/final/shots/`, looked at before returning.

Handoff lists the source revision, entry command, reachable state routes, canonical token path, component-to-production mapping and mock behavior to replace. Frontend implements against the final prototype code, `flows.md`, `edge-states.md` and the tokens. Design QA (`design-qa`) compares the running build with these screenshots at the same breakpoints and states.

## Evidence types never substitute for each other

| Type | Produced by | Proves |
|---|---|---|
| prototype render (`02-shape/prototypes/**/shots/`) | designer | what the design intends |
| implementation capture (`03-impl/screens/`, acceptance screenshots) | frontend, integrator, pm, designer in design-qa | what the running build does |

A prototype screenshot is never implementation evidence, and an implementation screenshot is never a design direction.

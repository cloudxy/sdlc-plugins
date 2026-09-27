---
name: "imagery"
description: "Use this skill when the user says /sdlc-grok or a packet lists imagery. Do NOT use in place of a prototype, direction or screenshot."
when_to_use: "Command /sdlc-grok (login / status / logout / probe), or a spawn packet whose imagery list is non-empty, or $imagery. Do NOT use for diagrams (svg-diagram + scripts/diagram), for UI implementation, or as acceptance evidence."
---

# Imagery — a generated image that carries information, and can be traced

Job: **produce the few bitmaps a design or a launch genuinely needs, and make each one traceable to a prompt, a model and the artifact that uses it.** The SVG diagram lane draws structure (flow, ER, architecture); this lane makes pictures. Most features need zero. An image that carries no information is decoration, and decoration is not a deliverable.

| Packet `kind` | Lands in | It carries | Who consumes it |
|---|---|---|---|
| `ref` | `02-shape/assets/refs/` | one visual-language probe during exploration | designer, while writing `design-directions.md` |
| `illustration` · `empty-state` | `02-shape/assets/generated/` | the meaning of an empty / error / onboarding moment | the final prototype, then frontend |
| `hero` | `02-shape/assets/generated/` | a brand-front surface's one memorable image | official site / landing page |
| `icon` | `02-shape/assets/generated/` | a family of icons or icon grounds | design system, then frontend |

## Three red lines

1. **A reference image is not a design direction.** A direction is prototype code plus its render. `check-sdlc.sh` ignores `assets/refs/` and `assets/generated/` when it demands rendered directions or walkthrough shots — pointing at a generated image where a real screenshot belongs is a gate violation, not a shortcut.
2. **A generated image is never a UI contract.** Frontend still ports the accepted `02-shape/prototypes/final/` code; it only consumes these files by path.
3. **Never generate a real person's likeness, another company's logo or mark, or a recognizable copy of a competitor's interface.** Where the image is used, say it is AI-generated and point at its evidence file.

## Authorization (mode: auth — this is what /sdlc-grok runs)

On hosts without plugin commands (Codex), `mode: auth` with login / status / logout / probe in the request is the same entry.

```
python3 PLUGIN_ROOT/scripts/grok/auth.py login     # once, by the human, in their own terminal
python3 PLUGIN_ROOT/scripts/grok/auth.py status    # logged in / expired / not logged in
python3 PLUGIN_ROOT/scripts/image/generate.py --probe   # can this account actually generate? (one cheap image)
python3 PLUGIN_ROOT/scripts/grok/auth.py logout    # revoke at xAI, delete the local credential
```

`login` is an OAuth 2.0 device flow against `auth.x.ai`: the script prints a URL and a code, the human approves in a browser with their SuperGrok / X Premium+ account, and a refreshable token lands in `~/.sdlc/grok/credentials.json` (0600, outside this repo and outside every project). Access tokens last ~15 minutes and refresh automatically; the refresh token rotates on every use.

- **No command prints a token**, and no token reaches an artifact, an evidence file or a chat message. A hat only ever learns *authorized* or *not authorized*.
- **A hat must not run `login`.** It is an interactive human action. If `status` says not authorized, stop and ask the operator to run `/sdlc-grok login` — do not ask them for a token, and do not put one in a file.
- **`probe` before trusting the lane.** xAI gates the OAuth API surface by subscription tier and answers `403` to some otherwise valid logins. On 403 the way forward is an API key: set `XAI_API_KEY` and `imagery.auth: api-key` in `sdlc.config.yaml`. The scripts treat both the same.
- The plugin never reads the host's own credentials. This authorization is the one the operator granted here.

## Generating (mode: packet — only when the packet's `imagery` lists the kind)

The project must opt in first: `imagery.enabled: true` in `sdlc.config.yaml` (it spends the operator's subscription quota, and `imagery.budget.max_per_feature` caps it).

```
python3 PLUGIN_ROOT/scripts/image/generate.py --root <feature_dir> \
  --kind empty-state --name empty-orders \
  --purpose "订单空态：说明还没有数据以及下一步做什么" \
  --declared-in 02-shape/edge-states.md --prompt-file <feature_dir>/prompts/empty-orders.txt \
  --aspect 4:3 --resolution 1k
python3 PLUGIN_ROOT/scripts/image/check.py --root <feature_dir>
```

Write the prompt to a file first — it is the reviewable part of this work, and it is stored verbatim in the evidence.

### Prompt discipline

Four parts, in this order. Anything vague here comes back as a default-looking image:

1. **Subject** — what is in the frame, and what it must communicate (the *purpose*, restated visually).
2. **Composition** — framing, where the focus sits, what negative space is for, whether copy will be laid over it (then leave room and keep contrast low there).
3. **Style anchors** — pull them from `<product_root>/design-system.md` and the chosen direction: the actual accent colour, the flat//painterly choice, line weight, warm or cool neutrals. Name the values, not adjectives.
4. **Exclusions** — `no text, no logo, no watermark, no UI chrome, no real people` unless one of those *is* the subject. Generated text in an image is almost always wrong and cannot be localized.

Then judge the result against the same anti-default anchors design uses ([design-contract's visual-direction](../design-contract/references/visual-direction.md)): if a similar product would have produced the same image, it is a default, not a decision. Regenerate with a sharper prompt rather than accepting it and moving on — and **look at the file** before referencing it.

## Evidence

`generate.py` writes `<feature>/evidence/images/<name>.json` — prompt verbatim, model, parameters, request id, `auth_mode`, the digest of every file and of the declaring artifact — plus one line per call in `evidence/images/ledger.jsonl`. Nobody writes these by hand.

`check.py` fails when: a file has no record · a digest no longer matches · the bytes are not a real image · the kind and the directory disagree · `purpose` is thin · the declaring artifact is missing, was edited after generation (**stale**) or never actually references the file · the prompt was hand-edited · anything credential-shaped appears in the evidence.

Edit the declaring artifact later and the image goes stale on purpose: re-look at it, then regenerate or re-declare.

## Gotchas

- **Generating instead of deciding.** An image cannot resolve a question the design has not answered; it will just make an undecided screen look finished.
- **Text baked into the image.** Generated lettering is misspelled, unlocalizable and unchangeable. Copy is copy, laid over the image.
- **Style adjectives instead of values.** "modern, clean, professional" produces the AI default face. Name the hex, the neutral's temperature, the line weight.
- **Referencing an image nobody looked at.** Read the file first: composition, clipping, contrast under the copy that will sit on it.
- **`n: 10` as exploration.** Ten near-identical images cost ten images of quota and decide nothing. Sharpen the prompt and generate one.
- **A hat trying to log in.** Authorization is the operator's interactive step. Not authorized → stop and say so; never ask for a token, never write one into a file.
- **Treating a 403 as a bug.** It usually means the subscription tier is not allowed on the OAuth API surface. Say so and name the API-key fallback.
- **Editing the declaring artifact afterwards** silently makes every image in it stale. Re-look, then regenerate or re-declare.

## Self-check before returning

- [ ] Could a reader say what each image is *for*, from `purpose` alone?
- [ ] Are the style anchors traceable to `design-system.md` / the picked direction, not invented here?
- [ ] Is every image referenced where it is declared, and labelled as AI-generated?
- [ ] No real likeness, no third-party mark, no competitor interface copy, no baked-in text?
- [ ] Did the directions, prototypes and acceptance artifacts keep their **real** renders and screenshots?
- [ ] `python3 PLUGIN_ROOT/scripts/image/check.py --root <feature_dir>` exits 0?

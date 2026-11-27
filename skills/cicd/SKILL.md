---
name: cicd
description: "Use this skill when the spawn packet asks to wire gates into CI or $cicd. Do NOT load in /sdlc or for incidents."
when_to_use: "Spawn packet asks to export gates into CI, or $cicd. Do NOT use from parent /sdlc, release checklists, or incidents."
---

# CI wiring — deterministic gates, changed-path routing, provenance & release pipelines

Procedure for exporting the project's **existing** deterministic gates into CI (`sre/deliver/ci` → `06-deliver/ci.md`, [templates/ci.md](templates/ci.md)). CI here is another runner of G-script, **not a new gate kind**: commands and exit semantics inherit 1:1 from `sdlc.config.yaml` and `check-sdlc.sh`.

## Registered task

`sre/deliver/ci` writes `06-deliver/ci.md` ([templates/ci.md](templates/ci.md)) with the gate-to-pipeline mapping, changed-path routing rules, touched CI files, immutable runner/toolchain digests, signing/SBOM posture, a real run URL/log (or an explicit unexecuted limitation), and `gates[]` artifact reuse conditions. Project `source_writes` authorizes scoped pipeline/config edits; it never implies deployment.

## Core wiring & Changed-Path Targeted CI Routing SOP

1. **Single source of gate truth & Non-Bypassable PR Status Checks (`sdlc.config.yaml` + `check-sdlc.sh`).** Map one CI step per configured gate, cheapest first (`lint → affected unit → contract-test → SAST → build → migration → check-sdlc`). Configure branch/merge protection so PR status checks covering affected **`lint + unit + contract-test + SAST`** are **strictly non-bypassable** (enforce for administrators too — explicitly forbid `"这次特殊先合"` manual/admin merge overrides and `|| true` / `continue-on-error` gate laundering). Where web or HTTP API surfaces exist, wire a post-deploy **Staging `DAST` hook** against the staging/ephemeral preview endpoint before production promotion.
2. **Resolve targeted local testing vs CI pipelines (Changed-Path Routing SOP).** Preserve local agent targeted-only execution: never fork gate commands between local agents and CI, and never force unrelated full-suite test runs on isolated doc/subpackage edits:
   - Keep canonical runner entrypoints in `sdlc.config.yaml` (or a repo test-impact script invoked by both local tasks and CI).
   - Compute `git diff --name-only <merge-base>...HEAD` in a fast **gate-router** step to derive affected modules, transitive callers, shared schemas/contracts, and active `.sdlc/<feature>/` directories.
   - **PR / feature push**: run affected-target `lint`, `unit`, `contract-test`, `SAST`, affected integration/E2E suites, and `--hat <done-stages>` `check-sdlc.sh` on touched active features.
   - **Foundational / shared-surface trigger & Staging DAST**: automatically widen scope when foundational paths change (`migrations/`, `auth/`, shared contracts/SDKs, lockfiles, container/CI configs), execute the **Staging `DAST` hook** on web/API staging deployments, and run release-candidate smoke/compatibility gates on release tags or scheduled integration sweeps.
3. **Monorepo path filters & required-check safety.** Path filters must follow the **transitive package graph** (editing `packages/contracts` triggers downstream `services/api` and `apps/web`, not `contracts` alone). Use a single non-bypassable aggregator status job (or explicit skipped-pass reporting) so GitHub/GitLab branch protection never deadlocks waiting on a path-filtered required job while still blocking any failed sub-gate.
4. **Active feature-dir discovery.** Select changed/active `.sdlc/<feature>/` trees and enforce only stages completed on feature branches and stages promised by `delivery_goal` on `main` — never fail historical archived or intentionally plan-only features for lacking build stages.
5. **Artifact signing, provenance & SBOM attestation.** Pin third-party CI actions and base images by immutable commit SHA / digest (never floating `@main` or `:latest`). For release builds, emit CycloneDX/SPDX **SBOM**, sign artifacts/containers (e.g. Sigstore Cosign OIDC provenance / SLSA build attestation), and bind uploaded `gates[]` fingerprint logs to the exact commit tree + lockfile + config + environment digest.
6. **Mobile, desktop & package release pipelines.** Separate PR verification (compile, targeted tests, ABI/semver check, dry-run packaging) from irreversible publication (App Store Connect / Play Console / notarized macOS DMG / Windows Authenticode / npm / PyPI / crates). Store signing keys/certificates strictly in ephemeral CI secret stores, verify **N-2** server API compatibility and minimum-version kill-switch readiness ([industry-delivery-sops.md](../impl-evidence/references/industry-delivery-sops.md)), and gate store/registry push behind explicit version tags + `qc` readiness approval.

## Gotchas

- **CI green ≠ review pass.** CI executes deterministic G-script only; G-fresh remains an independent `reviewer` spawn. Do not wire LLM auto-review into CI as a substitute for review or gates.
- **Commit SHA alone never justifies reusing an old CI green.** Reuse `gates[]` artifacts only when commit/tree, dirty state, lockfile/dependencies, `sdlc.config.yaml`, gate script version, target OS/arch and external fixture contracts all match.
- **Secrets by reference only.** Credentials, signing certs and tokens live in the CI secret vault / OIDC provider, never in `sdlc.config.yaml` or workflow scripts.

## Self-check

- [ ] Non-bypassable PR status checks enforce affected `lint + unit + contract-test + SAST` (admin/manual `"这次特殊先合"` bypasses disabled, untranslated exit codes, zero LLM auto-review substitutes), plus a Staging `DAST` hook where web/API surfaces exist?
- [ ] Local agent targeted-only execution preserved while CI changed-path / monorepo routing follows transitive dependencies and avoids branch-protection required-check deadlocks?
- [ ] `check-sdlc.sh` scopes to active features' completed stages on branches and `delivery_goal` stages on `main` (ignoring archived/plan-only specs)?
- [ ] Actions/runners pinned by digest/SHA, secrets referenced from vault/OIDC, and release artifacts emit SBOM + provenance signatures?
- [ ] Mobile/desktop/package publish steps separated from PR checks and gated behind release tags + readiness approval?
- [ ] `06-deliver/ci.md` ([templates/ci.md](templates/ci.md)) records mapping, routing, pinned versions, reuse rules, and real run URL/log (or explicit unexecuted limitation)?

## Templates & references

| File | Use when |
|---|---|
| [templates/ci.md](templates/ci.md) | Deliverable shape for `sre/deliver/ci` (`06-deliver/ci.md`) |
| [industry-delivery-sops.md](../impl-evidence/references/industry-delivery-sops.md) | Client binary signing, store rollout, semver/ABI & regulated supply-chain obligations |
| [references/role-quality.md](references/role-quality.md) | SRE CI/CD wiring excellence & review rubric |

# SRE CI/CD Wiring Excellence & Review Rubric

Apply alongside [cicd SKILL.md](../SKILL.md) when producing or reviewing `06-deliver/ci.md` and project CI workflow configurations.

## 1. Gate Truth & Exit Integrity

| Dimension | Excellence Bar | Reject (`major` / `blocker`) |
|---|---|---|
| Gate mapping | 1:1 steps invoking `sdlc.config.yaml` commands + `check-sdlc.sh`, ordered cheapest first (`lint → test → build → migration → check-sdlc`) | Forked inline commands that drift from `sdlc.config.yaml`, or invented gate kinds |
| Exit semantics | Raw exit codes passed through untranslated; `gates[]`-admissible logs uploaded as artifacts | Gate laundering (`|| true`, `continue-on-error`, or softening non-zero exits into warnings) |
| Review boundary | CI runs deterministic G-script checks only; G-fresh remains an independent `reviewer` spawn | Wiring LLM auto-review into CI as a substitute for independent review or gates |

## 2. Changed-Path Routing, Monorepo Safety & Feature Scoping

- **Changed-path targeted routing**: Reconciles targeted testing discipline with CI safety via a fast `gate-router` (`git diff --name-only <merge-base>...HEAD`): isolated package/doc PRs run affected targets and transitive consumers, while foundational edits (`migrations/`, `auth/`, shared contracts/SDKs, lockfiles, CI/toolchain configs) or release tags widen integration/smoke coverage automatically.
- **Zero branch-protection deadlocks**: Path-filtered monorepo jobs report through an always-executed summary gate job (or explicit neutral/skipped-pass status) so GitHub/GitLab required status checks never hang in `Pending` on untouched packages.
- **Lifecycle-aware `.sdlc/` checks**: Feature branches run `check-sdlc.sh --require --hat <done-stage>` for active features' completed stages; `main` checks active features against their declared `delivery_goal`, ignoring archived or intentionally plan-only features.

## 3. Supply-Chain Security, Client/Package Release & Fingerprint Reuse

- **Immutable pinning & attestation**: Pin runner images and third-party CI actions to immutable commit SHAs / digests (never mutable `@main` or `:latest`), inject secrets strictly via vault/OIDC references, and emit CycloneDX/SPDX SBOMs + cryptographic provenance signatures (Cosign / SLSA) on release artifacts.
- **Irreversible client & package publish gating**: Separate PR build/ABI/semver checks from irreversible store/registry publication (App Store / Play / notarized desktop binaries / `npm` / `PyPI` / `crates`), gating publish behind explicit release tags, N-2 API compatibility checks and `qc` readiness.
- **Strict `gates[]` reuse**: Reuse CI green logs only when commit/tree SHA, clean worktree state, lockfiles, `sdlc.config.yaml`, gate script version, target OS/arch and external fixtures all match; report unexecuted remote pipelines honestly rather than fabricating run URLs.

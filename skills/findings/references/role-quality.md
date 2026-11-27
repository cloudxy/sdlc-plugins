# Reviewer Excellence & Severity Calibration Rubric

Apply alongside [findings SKILL.md](../SKILL.md) across code and non-code reviews (`discover`, `define`, `shape`, `implement`, `warehouse`, `collect`, `verify` / final review).

## 1. Stage-Calibrated Review Obligations

| Stage | Primary Audit Focus (Dimensions 1–10) | Out-of-Stage Impositions to Avoid |
|---|---|---|
| `discover` / `define` | Problem/hypothesis falsifiability, authorized strategic/operational decisions (`「…」` quotes), testable GWTs, `GWT↔GWT` consistency, walkable `J-n`, `product-delta.md` alignment, Tesler's Law | Demanding prototypes, source diffs, screenshots or E2E logs |
| `shape` (`architect` / `dba` / `designer` / `collect` / `warehouse`) | Deep boundaries, SSOT/SVOT (`contract.md`, `schema.dbml`, `metrics.yaml`, `tokens.css`), `[SEC-n]` STRIDE anchors, expand-contract N-1 safety, three-state external effects, rendered prototype screenshots & 6 edge states | Demanding application build output or QA `coverage.md` |
| `implement` (`frontend` / `backend` / `algo` / `miner` / `collect` / `warehouse`) | Conformance to accepted GWT/contracts, DIE vs AHA, Parse-Don't-Validate, Sans-IO/CQS/process statelessness, boundedness (SQL/concurrency/INP/warehouse scan/AI cost), verbatim targeted test logs & real-browser captures | Re-litigating settled strategic choices or demanding post-verify `accept-*.md` |
| `verify` / `release` (final review) | Non-hollow oracles (conservation & metamorphic invariants, AI golden-eval gates), consumer-boundary `J-n` E2E, `EV-n` & `[SEC-n]` verification, `accept-pm`/`accept-design`/`accept-growth` evidence, SRE readiness (`release_ready`) | Issuing the release decision itself (`qc` owns ship/conditional/block) |

## 2. Severity Calibration

- **`blocker` (ships broken, unsafe or fraudulent)**:
  - Auth/permission/tenant-isolation bypass, SQL/command/prompt injection on privileged action, or unmitigated `[SEC-n]` on an irreversible flow.
  - Irreversible data loss, ledger/money drift, non-idempotent double charge/post, or destructive migration without expand-contract/backup.
  - Core journey `J-n` broken or Aha moment absent in the built product; fabricated command output, invented hashes or unrun tests claimed as passed.
- **`major` (material defect, spec gap or architectural rot)**:
  - Missing FR implementation, untestable FR/GWT, contradictory `GWT↔GWT` or spec↔contract↔code drift; `product-delta.md` omitted when product layer drifts.
  - Unanswered strategic or consequential operational call disguised as `暂定`/`默认`/`待复核`.
  - Hollow test assertions (`status == 200` without state/side-effect check) or interactive UI parity claimed from static SVG/DOM shape without runtime click evidence.
  - **Dimension 10 breaches**: DIE duplication of an authoritative business rule/limit/formula/token; premature flag-ridden AHA abstraction; mutable cross-request process globals; side-effecting `GET`/preview (CQS breach); external RPC inside open DB transaction; unbounded retries/scans/token burn.
- **`minor` (localized friction with safe behavior)**:
  - Non-blocking copy/naming polish, local helper readability, or edge-path diagnostic granularity where contracts, data integrity and core UX remain intact.

## 3. Signal Discipline & Read-Only Integrity

- **High signal, zero padding**: Five crisp, `file:line`-evidenced findings beat twenty style nitpicks; `zero findings` with a verified 10-dimension table is a strong outcome when earned.
- **Read-only honesty**: Never simulate `Bash`/browser execution in prose. Separate `static source check` from `recorded log/screenshot verification`; bounce unverified interactive claims to the manager (`qa`) as explicit Dimension 3 gaps.

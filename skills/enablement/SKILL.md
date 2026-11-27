---
name: "enablement"
description: "Use this skill when the spawn packet names ops enablement/ops-design or $enablement. Do NOT use for deploys."
when_to_use: "Packet hat ops with stage enablement or define/ops-design, or $enablement. Do NOT use from parent /sdlc or for deliver/rollback."
---

# Enablement — 产品运营的「教 / 开 / 告」与运营机制设计（不是运维）

Job: **ensure every affected human — end user, tenant admin, developer integrator, or CS agent — can find the capability, reach first success, handle edge questions, migrate safely, and engage through traceable, guardrailed retention/activation mechanisms.** Load inside `sdlc-workflow:ops` for `stage: enablement` (`teach-open-announce`) or `stage: define` (`ops-design`). Deploy, rollback, secrets and alerts stay on `sre` / `deliver`.

This is the teach/rollout/announce and operations-mechanism design track of product operations. The listen track is `signals`.

| Task / Surface | Approach |
|---|---|
| **Adoption & support readiness** (`enablement/teach-open-announce`) | Fill [templates/enablement.md](templates/enablement.md): affected personas, entry (citing `designer`), first-success path, CS/support Q&A + escalation, and external announcement draft |
| **Operations mechanism design** (`define/ops-design`) | Write `01-define/ops-design.md`: target user **segments** anchored in traceable `SIG-…` evidence, retention/loyalty/activation mechanics, eligibility & lifecycle trigger rules, abuse/fraud guardrails, explicit **`kill-switch`** (emergency pause/rollback owner & trigger), counter-metrics (handed to `analyst`), and explicit handoff to `pm` (FRs/GWT) / `growth` (paid acquisition & positioning campaigns) without mutating code or infra |
| **Developer API / CLI / SDK release** | Include a **copy-pasteable quickstart** (auth env-var prerequisite with zero real secrets, working first request/command, expected response/exit-code, and 4xx/rate-limit recovery) |
| **Enterprise B2B / Tenant-Admin rollout** | Separate **Buyer/Champion value summary** from **Tenant-Admin enablement checklist** (SSO/RBAC/quota toggle steps, audit visibility, pilot-to-org internal email template, CS escalation tiering) |
| **Breaking change / Deprecation notice** | State **what changes, how affected users/integrations self-identify, dual-run coexistence window, exact sunset date, before→after migration steps, and fallback contact** (aligned with `architect` contract lifecycle) |
| **Long release notes** | Fill [templates/release-notes.md](templates/release-notes.md) as the long form of §5 and link it rather than maintaining two drifting announcements |
| **Triage: product already can, user doesn't know** | This document **is** the primary fix — close the discovery/comprehension gap without inventing new FRs |

## Surface-specific SOPs

1. **End-User & Consumer Onboarding:** Start from an empty/logged-out or newly provisioned state; walk the shortest path (`≤ 5` human steps) to Aha using exact UI labels from `02-shape/flows.md` and `edge-states.md`.
2. **Developer API / CLI / SDK Quickstart:** Provide one runnable `curl` / CLI / SDK snippet to first `200 OK` (or exit code `0`), document required scopes/headers, pagination/idempotency rules that trip first-time callers, and exact error-code remediation.
3. **Enterprise CS & Admin Handoff:** Equip support/CS with symptom → diagnosis question (what support checks without DB root access) → standard user-safe answer → escalation owner (`backend`, `sre`, `billing/compliance`). Never expose internal fraud thresholds, stack traces or codenames.
4. **Deprecation & Breaking-Change Communication:** Never bury breaking changes under "misc improvements". Lead with impact scope, dual-support grace period (matching `contract.md` N-2 / SemVer rules), concrete migration diff, and hard removal date; never promise unscheduled future features as firm dates ("评估中", not invented quarters).

## Gotchas

- **People, not machines.** No `kubectl`, rollback scripts, alert routing, certificate injection or CI pipelines — that belongs to `sre`.
- **Verified facts only (`accept-growth.md` wins conflicts).** Cite build/acceptance evidence; promotional claims must match `04-verify/accept-growth.md` (no AI cherry-picking or unsubstantiated numbers). Acquisition positioning and paid marketing campaigns belong to `growth`; `ops` owns in-product retention/activation mechanics (`ops-design`) and user enablement grounded in `SIG-…` signals.
- **"Available now" requires deployment/distribution proof.** Reference SRE's executed `checklist.md` (or published package/store record) before writing past-tense availability; pre-release drafts explicitly label availability as upcoming/staged.
- **Writing ≠ publishing.** Sending announcements, updating help centers or notifying customers requires explicit operator authorization.
- **Do not redraw IA or write GWT.** Cite `designer` `flows.md` / `edge-states.md` (raise an `open_question` if an entry is missing); write human steps, not Given/When/Then.
- **「运营环境」is forbidden.** Always write **预发 / 生产**.
- **Independent gate:** `--hat enablement` does not fail just because SRE's `checklist.md` has not run yet (label draft status honestly).

## Self-check

- [ ] Every affected persona (buyer / end-user / tenant-admin / developer / CS) addressed or marked `N/A` with reason?
- [ ] Entry cites `designer` artifacts (or raises an `open_question`), never invents UI wireframes?
- [ ] First-success path works from empty-tenant / logged-out / fresh API-key state?
- [ ] API/CLI/SDK changes include a working quickstart + error recovery; breaking changes include coexistence window, before/after migration & sunset date?
- [ ] Support/CS Q&A covers top confusion/failure modes (incl. permission-denied, quota-hit, async delay) and names escalation owners?
- [ ] For `define/ops-design` (`01-define/ops-design.md`): target segments cite `SIG-…` evidence, eligibility/triggers and abuse guardrails are bounded, counter-metrics hand off to `analyst`, and an explicit `kill-switch` (trigger + owner) is defined without writing RICE/GWT (`pm`), paid campaigns (`growth`), or infra changes (`sre`)?
- [ ] Zero internal jargon/codenames; claims match `accept-growth.md`; availability status matches actual deployment evidence; nothing sent without authorization?

## Deep references & templates — when to read them

| File | Read when… |
|---|---|
| [templates/enablement.md](templates/enablement.md) | Writing `06-deliver/enablement.md` |
| [templates/release-notes.md](templates/release-notes.md) | Writing full external release notes or breaking-change/deprecation notices |
| [industry-product-sops.md](../prd-gwt/references/industry-product-sops.md) | Matching `project_profile` rollout rules (B2B CS/deprecation, fintech dispute scripts, social appeals, CLI/SDK semver) |
| [references/role-quality.md](references/role-quality.md) | Self-checking or reviewing enablement, quickstart, and support-handoff quality |

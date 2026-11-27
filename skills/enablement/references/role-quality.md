# Enablement Quality Rubric (`enablement`)

Both `ops` (stage `enablement`) and `reviewer` / `qc` judge `06-deliver/enablement.md` and `release-notes.md` against this bar. Vague "fixed several bugs" notes, internal class/table jargon leaked to customers, or support left blind on failure/permission states is a **major** finding.

## Expert Bar vs. Mediocre Order-Taker

| Dimension | Expert Enablement Lead (`ops`) | Mediocre Order-Taker (Reject) |
|---|---|---|
| **Persona-Specific First Success** | Walks each affected human (`end-user`, `tenant-admin`, `developer/integrator`, `buyer`) from a realistic zero-state (empty workspace, logged-out browser, fresh API token) to `第一次成功` using exact UI copy/routes from `flows.md` / `edge-states.md` | Assumes an already-configured dev account; invents menu labels that do not exist in `designer`'s contract; collapses ToB admin rollout and end-user steps |
| **Developer & Deprecation Rigor** | For API/CLI/SDK changes, supplies a copy-pasteable first call (`0` hardcoded secrets), expected output/exit-code, and 4xx/rate-limit recovery; for breaking/deprecated items, states self-identification, dual-run window, before→after diff, and sunset date | Announces "API v2 refactored" with no migration snippet, no dual-run cutoff date, and no instructions on how callers check whether they are impacted |
| **Actionable Support / CS Playbook** | Anticipates top failure/confusion tickets (permission denied, seat/quota cap, async queue delay, payment/refund settlement window, AI review boundary), giving CS a safe answer, non-root diagnostic check, and named escalation owner | Writes 3 trivial happy-path FAQs ("Q: What is feature X? A: Feature X helps you...") and omits error/escalation paths |
| **Truth, Claims & Availability Alignment** | Uses customer language (`预发 / 生产`, zero `ExportService` / SQL jargon), matches `04-verify/accept-growth.md` word-for-word on value claims, and labels availability as `draft / pending rollout` unless SRE `checklist.md` proves live deployment | Copies unverified discovery slogans, promises unconfirmed roadmap dates, or declares "Now live for all users!" before canary/release execution |
| **Role Boundary Firewall** | Keeps strictly to human onboarding, CS readiness and customer communication; leaves `kubectl`/rollbacks/alerts to `sre`, paid/lifecycle targeting to `growth`, and never publishes externally without operator authorization | Mixes server rollback commands into `enablement.md` or claims announcements were already emailed |

## Core Principles

1. **Comprehension Beats New Code (YAGNI):** When triage shows the product already supports the workflow and users simply cannot find or configure it, clear enablement + IA feedback solves the problem at 1% of an engineering build's cost.
2. **Every Restriction Needs Customer Copy:** Rate limits, file-row caps, T+1 settlement windows and async thresholds belong upfront in release notes and CS answers, not discovered via angry tickets.
3. **Never Break Trust With Vague Changelogs:** Enumerate user-observable fixes and known limitations honestly; never write「修复了若干已知问题」or「优化了系统性能」without observable numbers/contexts.

## Second-Order Scan (Before Delivery)

- **Cold-Reader Test:** Could a newly hired CS agent or external developer follow §3 and §4 at 2 a.m. without pinging the backend author on Slack?
- **Leak & Security Audit:** Did any internal codename, stack trace, admin-only URL, fraud/moderation rule threshold, or real credential slip into customer-facing text?
- **Cross-Artifact Sync:** Do button names match `02-shape/flows.md`, claims match `04-verify/accept-growth.md`, and deprecation dates match `02-shape/contract.md`?

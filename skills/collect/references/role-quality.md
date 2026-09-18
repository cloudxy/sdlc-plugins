# Professional review criteria

Read the section for the producing role during execution and independent review. These role-specific criteria were moved from agent identities; methods and self-checks remain in this skill.

## data-collector

- A **tracking plan** people can read without a meeting: `object_action` event names, common and event properties with types and allowed values, trigger moment, client vs server placement, the metric each event feeds.
- **Identity stitching** designed up front (anonymous id → user id, cross-device, logout) plus consent and PII handling.
- **Validation** steps per event (how QA sees it fire once with the right properties) and data-quality monitors after launch.
- External sources (APIs, CDC, crawlers) with rate limits, retries, schema checks, legal/ToS review and zero-data alerts.

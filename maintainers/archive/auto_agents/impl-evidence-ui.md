# auto_agents frontend pitfalls (verified)

Gate: item needs a test, a reproducing commit, or code-plus-runtime evidence from this session. Speculation stays out. Implementers read this plus SKILL.md Gotchas. Product gaps (missing pages, missing FRs) belong in diagnosis, not here.

---

## P-FE-01 shared package main points at dist

Symptom: CRA runtime throws `axios_1.default.create is not a function`. `npm run build` and Jest stay green. After editing `frontend/shared/src`, the apps still consume stale exports.

Cause: `@auto-agents/frontend-shared` `"main": "dist/index.js"`. webpack5 resolving CJS `__importDefault(require('axios'))` against axios ESM misses `default`. Source and dist can diverge for a long time.

Do this:

- Keep `frontend/shared/tsconfig.json` `"module": "ES2020"` (do not revert to `commonjs`).
- After shared source edits run `npm run build -w @auto-agents/frontend-shared` before starting an app.
- Jest `transformIgnorePatterns` must include `@auto-agents` so babel transpiles the ESM dist.

Evidence:

- commit `86a9ab5` `fix(shared): 产物改 ESM——修复 CRA webpack 下 axios CJS interop 运行时崩溃` (dev bundle checked: zero leftover `__importDefault(require('axios'))`).
- this session 2026-09-07: `src/index.ts` no longer exports `queryViewState`, `src/query/` is gone, `dist/index.js` still `export { queryViewState } from './query/state'`.

---

## P-FE-02 Jest must transpile antd, icons, and shared ESM

Symptom: every test fails with `Cannot use import statement outside a module`.

Cause: `@ant-design/icons`, antd v6, `@rc-component/*`, and the shared dist after P-FE-01 are ESM. Jest ignores `node_modules` by default.

Do this: keep both apps' `package.json`:

```
"transformIgnorePatterns": [
  "node_modules/(?!(@ant-design|antd|rc-|@rc-component|@auto-agents)/)"
]
```

Dropping `@auto-agents` recreates the failure after the ESM switch.

Evidence: commit `902de6d` added the antd exception; `86a9ab5` appended `@auto-agents`. This session: admin 13 passed, official 3 passed with that config.

---

## P-FE-03 empty permission cache is not "no perms" and not "open every write surface"

Two recurrence chains:

1. Sidebar looks fine after login; F5 leaves the Sider up with zero items.
2. Backend restart / permissions fetch failure makes the sidebar vanish again.

Cause: `cachedPermissions` is module memory. zustand persist restores token/user only. An empty array used to mean "user has no codes" in `filterMenu` (total filter-out). `bea13b5` fell back to the full menu, but `tenantOnly` lives on leaves, not groups, so a top-level filter still showed tenant-only leaves.

Do this:

- If authenticated and cache empty, refresh on mount (dedupe in-flight) and bump `revision` so React re-renders.
- logout must `clearCachedPermissions`.
- Empty-cache fallback must recurse `tenantOnly`. It must not treat `/newapi` `/llm` `/platform-ops` `/users` `/settings` as fallback-visible: that is the FR-06/07 leak, because `requireAdmin` (`role==='admin'`) lets a tenant company admin through.
- Do not "fix" this by telling people to clear localStorage.

Evidence:

- `8256ef2` F5 missing sidebar plus `usePermission.test.tsx` F5 auto-refresh case.
- `bea13b5` unreachable backend total-filter recurrence plus test for full-menu fallback.
- `fdeedfe` / F-T10-1 recursive leaf `tenantOnly` plus test that a platform admin with null tenant_id does not see member/usage leaves.
- this session: those four tests green.

---

## P-FE-04 unwrap the envelope exactly once

Symptom: list/success fields are undefined (empty tenant name on signup success), or Members create cannot read username. The page still looks like success.

Cause: `createApiClient` already returns `response.data` (the envelope). The service then `unwrap(envelope)` to the payload. A second `unwrap(r.data)` or `.then(r => r.data)` peels an extra layer.

Do this:

```ts
// service
api.post(path, body).then((r) => unwrap<T>(r))

// page
const result = await tenantSignup(values)  // already T; do not read .data again
```

Tests must mock interceptor semantics: `api.get` resolves `{ success, code, message, data }`, not an axios response.

Evidence:

- commit `e497004`: Members/skills used `unwrap(r.data)` while the interceptor already stripped axios; Members.test mocks the envelope.
- this session: `frontend/official/src/services/signup.ts` already `unwrap<SignupResult>`, `pages/Register.tsx` still peels `.data` again. No Register test, so it escaped. Copying Register will re-break.

---

## P-FE-05 map 422 occupancy and keep the form

Symptom: delete a member, create the same username again, click create — modal closes or nothing happens.

Cause: backend uniqueness includes soft-deleted rows and returns 422. The page used to ignore 422 and mixed antd field errors with API errors in one catch.

Do this: if `isFormValidateError(e)`, stay silent (fields already red); otherwise map the backend prefix to actionable copy; do not close the Modal; do not `resetFields`.

Evidence: `Members.test.tsx` F-02 422 name and email cases. This session: both green.

---

## P-FE-06 untrusted SKILL.md must stay a text node

Symptom: public detail using HTML/markdown renderers executes script/img onerror from third-party bodies.

Cause: the skills square already fetches public bodies; Wave 1 market detail will fetch more third-party SKILL.md. React text nodes escape; markdown libraries do not.

Do this: render `skill_md` as a text node (`pre` with `data-testid="skill-md"`). When retiring `/skills`, move this test to `/capabilities/:type/:slug`. Do not delete the case because the square is gone.

Evidence: `frontend/official/src/pages/SkillsSquare.test.tsx` XSS case — payload visible as text, no script node. This session: official 3 passed. spec T-27 / QA-05: Wave 1 must keep the cell.

---

## P-FE-07 jsdom missing APIs make antd 6 / react-router 7 tests flake or hang

Symptom: findBy 1s timeouts under parallel load, or Jest never exits.

Cause: jsdom has no MessageChannel / matchMedia / ResizeObserver / IntersectionObserver / scrollIntoView. rc-component form schedules on MessageChannel. Polyfilling with worker_threads MessageChannel leaves handles open and hangs Jest.

Do this: keep both apps' setupTests.ts: stub MessageChannel with setTimeout (not worker_threads); configure asyncUtilTimeout 8000; testTimeout 20000.

Evidence: comments in setupTests.ts (ticket 06 / 86a9ab5 flake fix). This session: admin tests ~55s all green, official ~11s all green.

---

## P-FE-08 antd v6 deprecated Alert message

Symptom: test stderr says Alert message is deprecated, use title instead. Suites still pass; CI logs fill with warnings.

Cause: antd 6 renamed Alert.message to title (same family as Spin.tip to description, Drawer.width to size). The repo still has many Alert message props.

Do this: new code uses title / description / size. Fix on touch; do not open a warnings-only mega ticket.

Evidence: this session frontend/admin npm test printed the deprecation stack from antd/lib/alert/Alert.js while Members.test ran (13 passed). Source grep: Alert plus message= still at least seven call sites.

---

Not filed this round (no independent evidence): fullwidth-adjacent bash variables, zsh readonly status, Drawer width runtime warning (not isolated in this session's test output).

#!/usr/bin/env bash
# check-sdlc.sh 夹具：SUMMARY 退出码、G-fresh 返工语义（r2 4A）、--hat H.1 合同、
# roles_skipped 精确 token（含 product-ops ≡ ops）、open_questions、appetite、
# 验证无矩阵、VAGUE、NFR MATRIX、NOSEC、enablement 结构；
# v4：产品层 PRODUCTCTX、CORE/JOURNEY/TRACKING、设计方向、DESIGNFIRST/ARCH、STRESS、INTEGRATION、
# J-n E2E 矩阵、E2E 闸门记录、三方验收 ACCEPT、WRITEBACK、accept 排位、--hat product、growth/launch、旧档兼容
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
CHK="$ROOT/scripts/check-sdlc.sh"
T=$(mktemp -d "${TMPDIR:-/tmp}/sdlc-check.XXXXXX")
trap 'rm -rf "$T"' EXIT
fail=0
assert_exit() {
  local want="$1" label="$2"
  shift 2
  bash "$CHK" "$@" >"$T/out" 2>&1
  local got=$?
  if [ "$got" -ne "$want" ]; then
    echo "FAIL $label: want exit $want got $got"
    cat "$T/out"
    fail=$((fail+1))
  else
    echo "ok   $label (exit $want)"
  fi
}
assert_tag() {
  grep -q "$1" "$T/out" || { echo "FAIL missing $1 tag"; cat "$T/out"; fail=$((fail+1)); }
}

# 1. 无泳道 → 恰好 1 条 NOLANE；SUMMARY 不得再 +1
mkdir -p "$T/nolan"
printf '# note\n' >"$T/nolan/note.md"
assert_exit 1 "NOLANE exit==1 not 2" --require "$T/nolan"
assert_tag 'SDLC-SUMMARY'

# 2.（翻转）current_hat=shape + last fresh=fail（无 stage 标记）→ 合法返工 exit 0
mkdir -p "$T/adv/01-define" "$T/adv/05-review"
cat >"$T/adv/state.yaml" <<'Y'
feature: t
lane: L3
appetite: 4h
current_hat: shape
hats_done: [define]
gates:
  - name: fresh-context
    kind: fresh-context
    result: fail
    blocker: 1
Y
echo '泳道：L3' >"$T/adv/01-define/spec.md"
echo findings >"$T/adv/05-review/findings.md"
assert_exit 0 "shape rework with fail is legal (flipped)" --require "$T/adv"

# 2b.（新）fail@define（有 stage 标记）但 current_hat=shape → HATADVANCE
mkdir -p "$T/adv2/01-define" "$T/adv2/05-review"
cat >"$T/adv2/state.yaml" <<'Y'
feature: t
lane: L3
appetite: 4h
current_hat: shape
hats_done: [define]
gates:
  - name: fresh-context
    kind: fresh-context
    stage: define
    result: fail
    blocker: 1
Y
echo '泳道：L3' >"$T/adv2/01-define/spec.md"
echo findings >"$T/adv2/05-review/findings.md"
assert_exit 1 "HATADVANCE fail@define but current=shape" --require "$T/adv2"
assert_tag HATADVANCE

# 2c.（legacy）current_hat=塑形（中文旧档，无 stage 标记）→ exit 0（双边 grep 认）
mkdir -p "$T/leg/01-define" "$T/leg/05-review"
cat >"$T/leg/state.yaml" <<'Y'
feature: t
lane: L3
appetite: 4h
current_hat: 塑形
hats_done: [定义]
gates:
  - name: fresh-context
    kind: fresh-context
    result: fail
    blocker: 1
Y
echo '泳道：L3' >"$T/leg/01-define/spec.md"
echo findings >"$T/leg/05-review/findings.md"
assert_exit 0 "legacy Chinese state still exit 0" --require "$T/leg"

# 3. current_hat=define + G-fresh fail → 不报 HATADVANCE（返工中）
mkdir -p "$T/rew/01-define" "$T/rew/05-review"
cat >"$T/rew/state.yaml" <<'Y'
feature: t
lane: L3
appetite: 4h
current_hat: define
hats_done: []
open_questions: [Q-VOICE]
gates:
  - name: fresh-context
    kind: fresh-context
    stage: define
    result: fail
Y
printf '泳道：L3\n| Q-VOICE | x | 待确认 |\n' >"$T/rew/01-define/spec.md"
echo findings >"$T/rew/05-review/findings.md"
assert_exit 0 "define+fail is rework not advance" --require "$T/rew"

# 4. spec 待确认 Q 未进 state
mkdir -p "$T/oq/01-define"
cat >"$T/oq/state.yaml" <<'Y'
feature: t
lane: L3
appetite: 4h
current_hat: define
hats_done: []
open_questions: []
Y
printf '泳道：L3\n| **Q-VOICE** | 首屏 | 待确认 |\n' >"$T/oq/01-define/spec.md"
assert_exit 1 "OPENQ" --require "$T/oq"
assert_tag OPENQ

# 5. appetite 8h vs Wave 0 人周
mkdir -p "$T/ap/01-define"
cat >"$T/ap/state.yaml" <<'Y'
feature: t
lane: L4
appetite: 8h
current_hat: define
hats_done: []
Y
printf '泳道：L4\nWave 0 为 2–4 人周\n' >"$T/ap/01-define/spec.md"
assert_exit 1 "APPETITE" --require "$T/ap"
assert_tag APPETITE

# 6. 验证帽完成但无 coverage.md（英文主词 grep）
mkdir -p "$T/mx/01-define" "$T/mx/03-impl"
cat >"$T/mx/state.yaml" <<'Y'
feature: t
lane: L3
appetite: 4h
current_hat: review
hats_done: [define, shape, implement, verify]
Y
echo '泳道：L3' >"$T/mx/01-define/spec.md"
assert_exit 1 "MATRIXMISS" --require "$T/mx"
assert_tag MATRIXMISS

# 7. fresh-context 无 findings.md
mkdir -p "$T/nf/01-define"
cat >"$T/nf/state.yaml" <<'Y'
feature: t
lane: L2
appetite: 4h
current_hat: define
hats_done: []
gates:
  - name: fresh-context
    kind: fresh-context
    stage: define
    result: fail
Y
echo '泳道：L2' >"$T/nf/01-define/spec.md"
assert_exit 1 "FINDINGS" --require "$T/nf"
assert_tag FINDINGS

# 8. --hat 用法：spawn 角色名 / 空值 / 未知 id → exit 64
mkdir -p "$T/usage/01-define"
cat >"$T/usage/state.yaml" <<'Y'
feature: t
lane: L2
appetite: 4h
current_hat: define
hats_done: []
Y
echo '泳道：L2' >"$T/usage/01-define/spec.md"
assert_exit 64 "--hat pm is a usage error" --hat pm "$T/usage"
assert_exit 64 "--hat bogus is a usage error" --hat bogus "$T/usage"
assert_exit 64 "--hat (empty) is a usage error" --require --hat "" "$T/usage"

# 9. --hat define：无 spec → HATMISS；legacy prd.md → DEPRECATED 警告但 exit 0
mkdir -p "$T/hm/01-define"
cat >"$T/hm/state.yaml" <<'Y'
feature: t
lane: L2
appetite: 4h
current_hat: define
hats_done: []
Y
assert_exit 1 "HATMISS define without spec" --hat define "$T/hm"
assert_tag HATMISS
mkdir -p "$T/hm2/01-define"
cat >"$T/hm2/state.yaml" <<'Y'
feature: t
lane: L2
appetite: 4h
current_hat: define
hats_done: []
Y
printf '泳道：L2\nFR-1 Given x When y Then z\n' >"$T/hm2/01-define/prd.md"
assert_exit 0 "--hat define warns on legacy prd.md" --hat define "$T/hm2"
grep -q 'DEPRECATED' "$T/out" || { echo "FAIL missing DEPRECATED tag"; fail=$((fail+1)); }

# 10. roles_skipped 单行精确 token：ops 跳过 signals；block-style 不认
mkdir -p "$T/skip"
cat >"$T/skip/state.yaml" <<'Y'
feature: t
lane: L2
appetite: 4h
current_hat: define
hats_done: []
roles_skipped: [architect, ops]
Y
assert_exit 0 "--hat signals skipped via roles_skipped [ops]" --hat signals "$T/skip"
mkdir -p "$T/skip2"
cat >"$T/skip2/state.yaml" <<'Y'
feature: t
lane: L2
appetite: 4h
current_hat: define
hats_done: []
roles_skipped:
  - ops
Y
assert_exit 1 "block-style roles_skipped is invalid (HATMISS)" --hat signals "$T/skip2"
assert_tag HATMISS

# 11. --hat dba 双工件 AND；--hat implement 证据 glob；--hat warehouse 精确路径
mkdir -p "$T/dba1/02-shape"
cat >"$T/dba1/state.yaml" <<'Y'
feature: t
lane: L3
appetite: 4h
current_hat: shape
hats_done: [define, shape]
Y
printf '泳道：L3\n' >"$T/dba1/02-shape/db-spec.md"
assert_exit 1 "--hat dba missing schema.dbml" --hat dba "$T/dba1"
assert_tag HATMISS
mkdir -p "$T/imp1/03-impl"
cat >"$T/imp1/state.yaml" <<'Y'
feature: t
lane: L1
current_hat: implement
hats_done: []
Y
printf 'note\n' >"$T/imp1/03-impl/T-1-evidence.md"
assert_exit 0 "--hat implement with evidence file" --hat implement "$T/imp1"
mkdir -p "$T/wh1"
cat >"$T/wh1/state.yaml" <<'Y'
feature: t
lane: L4
appetite: 4h
current_hat: shape
hats_done: [define, shape]
Y
printf 'id: m1\n' >"$T/wh1/metrics.yaml"
assert_exit 1 "--hat warehouse rejects root metrics.yaml" --hat warehouse "$T/wh1"
assert_tag HATMISS

# 12. --hat market / compete
mkdir -p "$T/mkt"
cat >"$T/mkt/state.yaml" <<'Y'
feature: t
lane: L2
appetite: 4h
current_hat: define
hats_done: []
Y
assert_exit 1 "--hat market missing market.md" --hat market "$T/mkt"
assert_tag HATMISS
mkdir -p "$T/mkt2/00-discover"
cat >"$T/mkt2/state.yaml" <<'Y'
feature: t
lane: L2
appetite: 4h
current_hat: define
hats_done: []
Y
echo market >"$T/mkt2/00-discover/market.md"
assert_exit 0 "--hat market with file" --hat market "$T/mkt2"

# 13. discovery.status=done 无 briefing → NODISCOVER
mkdir -p "$T/nd/01-define"
cat >"$T/nd/state.yaml" <<'Y'
feature: t
lane: L2
appetite: 4h
current_hat: define
hats_done: []
discovery:
  status: done
Y
printf '泳道：L2\n' >"$T/nd/01-define/spec.md"
assert_exit 1 "done without briefing is NODISCOVER" --require "$T/nd"
assert_tag NODISCOVER

# 14. OPENQOPEN: 待确认 Q 在 state 但未 answered，current_hat=shape
mkdir -p "$T/oq2/01-define" "$T/oq2/02-shape"
cat >"$T/oq2/state.yaml" <<'Y'
feature: t
lane: L2
appetite: 4h
current_hat: shape
hats_done: [define]
open_questions: [Q-VOICE]
Y
printf '泳道：L2\n| Q-VOICE | x | 待确认 |\n' >"$T/oq2/01-define/spec.md"
echo contract >"$T/oq2/02-shape/contract.md"
assert_exit 1 "OPENQOPEN unanswered Q at shape" --require "$T/oq2"
assert_tag OPENQOPEN

# 15. --hat enablement vs --hat deliver 互不绑架
mkdir -p "$T/en1/06-deliver"
cat >"$T/en1/state.yaml" <<'Y'
feature: t
lane: L3
appetite: 4h
current_hat: deliver
hats_done: [qc]
Y
echo checklist >"$T/en1/06-deliver/checklist.md"
assert_exit 0 "--hat deliver does not require enablement.md" --hat deliver "$T/en1"
assert_exit 1 "--hat enablement missing file" --hat enablement "$T/en1"
assert_tag HATMISS
printf '第一次成功：租户管理员打开座位管理\n## 客服 / CS 话术\n' >"$T/en1/06-deliver/enablement.md"
assert_exit 0 "--hat enablement with 客服+第一次成功" --hat enablement "$T/en1"
echo enablement >"$T/en1/06-deliver/enablement.md"
assert_exit 1 "--hat enablement missing 客服/第一次成功 is ENABLE" --hat enablement "$T/en1"
assert_tag ENABLE
mkdir -p "$T/en2/06-deliver"
cat >"$T/en2/state.yaml" <<'Y'
feature: t
lane: L3
appetite: 4h
current_hat: deliver
hats_done: [qc]
roles_skipped: [ops]
Y
assert_exit 0 "--hat enablement skipped via roles_skipped [ops]" --hat enablement "$T/en2"

# 16. VAGUE: 友好的 / gracefully in 验收标准
mkdir -p "$T/vg/01-define"
cat >"$T/vg/state.yaml" <<'Y'
feature: t
lane: L2
appetite: 4h
current_hat: define
hats_done: []
Y
printf '泳道：L2\n## 验收标准\nGiven x When y Then 友好的处理错误\n' >"$T/vg/01-define/spec.md"
assert_exit 1 "VAGUE 友好的" --require "$T/vg"
assert_tag VAGUE
mkdir -p "$T/vg2/01-define"
cat >"$T/vg2/state.yaml" <<'Y'
feature: t
lane: L2
appetite: 4h
current_hat: define
hats_done: []
Y
printf '泳道：L2\n## Acceptance\nGiven x When y Then handle errors gracefully\n' >"$T/vg2/01-define/spec.md"
assert_exit 1 "VAGUE gracefully" --require "$T/vg2"
assert_tag VAGUE

# 17. MATRIX NFR hole via check-matrix.py
mkdir -p "$T/nfr/01-define" "$T/nfr/04-verify"
cat >"$T/nfr/state.yaml" <<'Y'
feature: t
lane: L3
appetite: 4h
current_hat: verify
hats_done: [define]
Y
printf '泳道：L3\nFR-1 Given a When b Then c\nNFR-1 p95 < 500ms\n' >"$T/nfr/01-define/spec.md"
printf '泳道：L3\n| FR-1 | TC-1 |\n' >"$T/nfr/04-verify/coverage.md"
assert_exit 1 "MATRIX NFR hole" --hat verify "$T/nfr"
assert_tag MATRIX

# 18. NOSEC: q_security=yes, contract without [SEC-n]
mkdir -p "$T/sec/02-shape"
cat >"$T/sec/state.yaml" <<'Y'
feature: t
lane: L3
appetite: 4h
current_hat: shape
hats_done: [define]
q_security: yes
Y
printf '泳道：L3\nmodules only\n' >"$T/sec/02-shape/contract.md"
assert_exit 1 "NOSEC missing [SEC-n]" --hat shape "$T/sec"
assert_tag NOSEC
printf '泳道：L3\n[SEC-1] trust boundary B-1 spoofing → authn on export API → NFR-1\n' >"$T/sec/02-shape/contract.md"
assert_exit 0 "NOSEC pass with [SEC-1]" --hat shape "$T/sec"

# 19. product-ops skip alias for ops
mkdir -p "$T/po"
cat >"$T/po/state.yaml" <<'Y'
feature: t
lane: L2
appetite: 4h
current_hat: define
hats_done: []
roles_skipped: [product-ops]
Y
assert_exit 0 "--hat signals skipped via product-ops" --hat signals "$T/po"
mkdir -p "$T/po2/06-deliver"
cat >"$T/po2/state.yaml" <<'Y'
feature: t
lane: L3
appetite: 4h
current_hat: deliver
hats_done: [qc]
roles_skipped: [product-ops]
Y
assert_exit 0 "--hat enablement skipped via product-ops" --hat enablement "$T/po2"

# 20. canonical filename aliases (one-release DEPRECATED)
mkdir -p "$T/aliasv/04-verify" "$T/aliasv/01-define"
cat >"$T/aliasv/state.yaml" <<'Y'
feature: t
lane: L3
appetite: 4h
current_hat: verify
hats_done: [define]
Y
printf '泳道：L3\n' >"$T/aliasv/01-define/spec.md"
printf '泳道：L3\n| FR-1 | TC-1 |\n' >"$T/aliasv/04-verify/trace-matrix.md"
assert_exit 0 "--hat verify accepts legacy trace-matrix.md" --hat verify "$T/aliasv"
grep -q DEPRECATED "$T/out" || { echo "FAIL missing DEPRECATED tag"; cat "$T/out"; fail=$((fail+1)); }
mkdir -p "$T/aliasd/06-deliver"
cat >"$T/aliasd/state.yaml" <<'Y'
feature: t
lane: L3
appetite: 4h
current_hat: deliver
hats_done: [qc]
Y
printf '泳道：L3\n' >"$T/aliasd/06-deliver/release-checklist.md"
assert_exit 0 "--hat deliver accepts legacy release-checklist.md" --hat deliver "$T/aliasd"
grep -q DEPRECATED "$T/out" || { echo "FAIL missing DEPRECATED tag"; cat "$T/out"; fail=$((fail+1)); }

# 21. --report skips NOLANE/MATRIX on a half-built tree
mkdir -p "$T/rep/05-review"
printf '泳道：L2\n## Snapshot\n- a.md abc\nfindings\n' >"$T/rep/05-review/findings.md"
# no state.yaml, no spec — would NOLANE without --report
assert_exit 0 "--report skips NOLANE on half-built tree" --hat review --report "$T/rep"
mkdir -p "$T/rep2/05-review"
printf 'findings without snapshot\n' >"$T/rep2/05-review/findings.md"
assert_exit 1 "--report missing Snapshot is NOSNAP" --hat review --report "$T/rep2"
assert_tag NOSNAP

# 22. duplicate host_spawn
mkdir -p "$T/hs/01-define"
cat >"$T/hs/state.yaml" <<'Y'
feature: t
lane: L2
appetite: 4h
current_hat: define
hats_done: []
host_spawn:
  researcher:
    fallback: general-purpose
host_spawn: {}
Y
printf '泳道：L2\n' >"$T/hs/01-define/spec.md"
assert_exit 1 "duplicate host_spawn is HOSTSPAWN" --require "$T/hs"
assert_tag HOSTSPAWN

# 23. ROOTCAUSE: rework_rounds>=2 + evidence, no root_cause line
mkdir -p "$T/rc/03-impl" "$T/rc/01-define"
cat >"$T/rc/state.yaml" <<'Y'
feature: t
lane: L2
appetite: 4h
current_hat: implement
hats_done: [define]
rework_rounds: 2
Y
printf '泳道：L2\n' >"$T/rc/01-define/spec.md"
printf '泳道：L2\nevidence only\n' >"$T/rc/03-impl/T-1-evidence.md"
assert_exit 1 "rework>=2 without root_cause is ROOTCAUSE" --hat implement "$T/rc"
assert_tag ROOTCAUSE
printf '泳道：L2\nroot_cause: nil deref in parser\n' >"$T/rc/03-impl/T-1-evidence.md"
assert_exit 0 "rework>=2 with root_cause line" --hat implement "$T/rc"

# ======================= v4 gates (sdlc_version: 4) =======================
mk_v4() { # $1 = project dir name; creates a filled product layer + feature dir .sdlc/f
  local P="$T/$1"
  mkdir -p "$P/docs/product/data" "$P/.sdlc/f/01-define" "$P/.sdlc/f/02-shape/prototypes" "$P/.sdlc/f/03-impl" "$P/.sdlc/f/04-verify" "$P/.sdlc/f/05-review"
  printf 'product_root: docs/product\n' >"$P/sdlc.config.yaml"
  for f in strategy.md feature-map.md growth.md design-system.md architecture.md domain-model.md; do
    printf '# %s\nreal content\n' "$f" >"$P/docs/product/$f"
  done
  printf '| https://a.example/reviews | 2026-09-01 |\n| https://b.example/pricing | 2026-09-01 |\n| https://c.example/blog | 2026-09-02 |\n' >>"$P/docs/product/growth.md"
  mkdir -p "$P/docs/product/screens"
  printf 'png' >"$P/docs/product/screens/home-1440.png"
  printf '# design-system.md\nreal content\n![home](screens/home-1440.png)\n' >"$P/docs/product/design-system.md"
  printf 'Table users {\n  id bigint\n}\n' >"$P/docs/product/erd.dbml"
  printf 'events: []\n' >"$P/docs/product/data/tracking-plan.yaml"
  cat >"$P/.sdlc/f/state.yaml" <<Y
feature: f
sdlc_version: 4
product_root: docs/product
lane: L2
appetite: 1w
ui: yes
tracking: yes
current_hat: define
hats_done: []
Y
  printf '泳道：L2\n## 核心价值与 Aha 时刻\n首次导入后 30 秒看到第一份报告\n## 关键用户旅程\nJ-1 导入数据并看到报告\n' >"$P/.sdlc/f/01-define/spec.md"
  printf '泳道：L2\nEV-1 report_viewed\n' >"$P/.sdlc/f/01-define/tracking.md"
}

# 24. define: product layer unfilled → PRODUCTCTX; filled → pass; no 核心价值 → CORE; tracking yes without tracking.md → TRACKING
mk_v4 d1
F="$T/d1/.sdlc/f"
assert_exit 0 "v4 --hat define with filled product layer" --hat define "$F"
printf '<!-- sdlc:unfilled -->\n# strategy\n' >"$T/d1/docs/product/strategy.md"
assert_exit 1 "v4 --hat define with unfilled strategy is PRODUCTCTX" --hat define "$F"
assert_tag PRODUCTCTX
printf '# strategy\nreal\n' >"$T/d1/docs/product/strategy.md"
printf '泳道：L2\nJ-1 导入\n' >"$F/01-define/spec.md"
assert_exit 1 "v4 --hat define without 核心价值 is CORE" --hat define "$F"
assert_tag CORE
printf '泳道：L2\n## 核心价值与 Aha 时刻\nx\nJ-1 导入\n' >"$F/01-define/spec.md"
rm "$F/01-define/tracking.md"
assert_exit 1 "v4 tracking: yes without tracking.md is TRACKING" --hat define "$F"
assert_tag TRACKING

# 25. designer: 2 directions → DIRECTIONS; 3 + 选定 + screenshot → pass
mk_v4 g1
F="$T/g1/.sdlc/f"
sed -i.bak 's/^current_hat: define/current_hat: shape/' "$F/state.yaml" && rm -f "$F/state.yaml.bak"
printf '泳道：L2\n| 屏 | 空 |\n' >"$F/02-shape/edge-states.md"
for d in d1 d2 d3; do printf 'png' >"$F/02-shape/prototypes/$d-1440.png"; done
printf '泳道：L2\n| 参考 | https://a.example/x 2026-09-01 |\n| 参考 | https://b.example/y 2026-09-01 |\n| 参考 | https://c.example/z 2026-09-01 |\n## D1 卡片流\n![](prototypes/d1-1440.png)\n## D2 时间线\n' >"$F/02-shape/design-directions.md"
assert_exit 3 "v4 --hat designer with 2 directions, no pick, no defect check is DIRECTIONS x3" --hat designer "$F"
assert_tag DIRECTIONS
printf '泳道：L2\n| 参考 | https://a.example/x 2026-09-01 |\n| 参考 | https://b.example/y 2026-09-01 |\n| 参考 | https://c.example/z 2026-09-01 |\n## D1 卡片流\n![](prototypes/d1-1440.png)\n## D2 时间线\n![](prototypes/d2-1440.png)\n## D3 对话式\n![](prototypes/d3-1440.png)\n## 缺陷检查\n| prototypes/d2-1440.png | 无重叠截断 | 无 |\n选定：D2（picked_by: user）\n' >"$F/02-shape/design-directions.md"
assert_exit 0 "v4 --hat designer with 3 directions + pick + screenshots" --hat designer "$F"
rm "$F/02-shape/prototypes/d3-1440.png"
assert_exit 1 "v4 --hat designer: a direction screenshot that does not exist is DIRECTIONS (P02)" --hat designer "$F"
assert_tag DIRECTIONS

# 26. shape: ui yes without pick → DESIGNFIRST; contract without QAS/options → ARCH
mk_v4 s1
F="$T/s1/.sdlc/f"
printf '泳道：L2\nmodules only\n' >"$F/02-shape/contract.md"
assert_exit 3 "v4 --hat shape: no design pick + no QAS + no options" --hat shape "$F"
assert_tag DESIGNFIRST
assert_tag ARCH
printf '泳道：L2\n## 质量属性场景\nP95<300ms\n## 候选方案\nA / B\n' >"$F/02-shape/contract.md"
printf '泳道：L2\n## D1\n## D2\n## D3\n选定：D1\n' >"$F/02-shape/design-directions.md"
assert_exit 0 "v4 --hat shape with QAS, options and design pick" --hat shape "$F"

# 27. dba: db-spec without 路线压力测试 → STRESS
mk_v4 b1
F="$T/b1/.sdlc/f"
printf '泳道：L2\none row = one report\n' >"$F/02-shape/db-spec.md"
printf 'Table reports {}\n' >"$F/02-shape/schema.dbml"
assert_exit 1 "v4 --hat dba without roadmap stress test is STRESS" --hat dba "$F"
assert_tag STRESS

# 28. implement (ui yes): no integration file → INTEGRATION; with screenshot → pass
mk_v4 i1
F="$T/i1/.sdlc/f"
printf '泳道：L2\nnote\n' >"$F/03-impl/T-1-evidence.md"
assert_exit 1 "v4 --hat implement ui without integration is INTEGRATION" --hat implement "$F"
assert_tag INTEGRATION
printf '泳道：L2\nJ-1 walked against real API\n![](screens/j1-1440.png)\n' >"$F/03-impl/T-1-integration.md"
assert_exit 1 "v4 --hat implement: integration cites a screenshot that does not exist (P02)" --hat implement "$F"
assert_tag INTEGRATION
mkdir -p "$F/03-impl/screens" && printf 'png' >"$F/03-impl/screens/j1-1440.png"
assert_exit 0 "v4 --hat implement with integration screenshot" --hat implement "$F"

# 29. verify: J-1 without E2E row → MATRIX; no e2e gate → E2E; both fixed → pass
mk_v4 v1
F="$T/v1/.sdlc/f"
printf '泳道：L2\n| J-1 | TC-1 | 集成 |\n| EV-1 | TC-9 | 集成 |\n' >"$F/04-verify/coverage.md"
assert_exit 2 "v4 --hat verify: J without E2E + no e2e gate" --hat verify "$F"
assert_tag MATRIX
assert_tag E2E
printf '泳道：L2\n| J-1 | TC-1 | E2E |\n| EV-1 | TC-9 | 集成 |\n' >"$F/04-verify/coverage.md"
cat >>"$F/state.yaml" <<'Y'
gates:
  - name: lint
    kind: script
    result: pass
  - name: e2e
    kind: script
    result: pass
    exit_code: 0
Y
assert_exit 0 "v4 --hat verify with E2E row and e2e pass" --hat verify "$F"
mk_v4 v2
F="$T/v2/.sdlc/f"
printf '泳道：L2\n| J-1 | TC-1 | E2E |\n| EV-1 | TC-9 | 集成 |\n' >"$F/04-verify/coverage.md"
cat >>"$F/state.yaml" <<'Y'
gates:
  - name: e2e
    kind: script
    result: null
    reason: not configured
  - name: build
    kind: script
    result: pass
Y
assert_exit 1 "v4 e2e null followed by another pass gate is still E2E" --hat verify "$F"
assert_tag E2E

# 30. accept: missing files → HATMISS; pm 不通过 → ACCEPT; all pass → exit 0; growth skipped
mk_v4 a1
F="$T/a1/.sdlc/f"
assert_exit 3 "v4 --hat accept with no acceptance files" --hat accept "$F"
assert_tag HATMISS
mkdir -p "$F/03-impl/screens" "$F/04-verify/shots"
printf 'png' >"$F/03-impl/screens/j1.png"; printf 'png' >"$F/04-verify/shots/d2.png"
printf '泳道：L2\nJ-1 走查 ![](../03-impl/screens/j1.png)\n结论：不通过\n' >"$F/04-verify/accept-pm.md"
printf '泳道：L2\n对比原型 ![](shots/d2.png)\n结论：通过\n' >"$F/04-verify/accept-design.md"
printf '泳道：L2\n卖点核验\n结论：通过\n' >"$F/04-verify/accept-growth.md"
assert_exit 2 "v4 --hat accept with pm 不通过 (hat + global ACCEPT)" --hat accept "$F"
assert_tag ACCEPT
printf '泳道：L2\nJ-1 走查 ![](../03-impl/screens/j1.png)\n结论：通过\n' >"$F/04-verify/accept-pm.md"
assert_exit 0 "v4 --hat accept all 通过 with screenshots" --hat accept "$F"
rm "$F/04-verify/accept-growth.md"
printf 'roles_skipped: [growth]\n' >>"$F/state.yaml"
assert_exit 0 "v4 --hat accept skips growth via roles_skipped" --hat accept "$F"
printf '泳道：L2\n## 第 1 轮\n结论：不通过\n## 第 2 轮\nJ-1 走查 ![](../03-impl/screens/j1.png)\n结论：通过\n' >"$F/04-verify/accept-pm.md"
assert_exit 2 "v4 accept file with two different verdicts is ambiguous, not first-wins (P12)" --hat accept "$F"
assert_tag ACCEPT
printf '泳道：L2\nJ-1 走查 ![](../03-impl/screens/gone.png)\n结论：通过\n' >"$F/04-verify/accept-pm.md"
assert_exit 1 "v4 accept citing a screenshot that does not exist is ACCEPT (P04)" --hat accept "$F"
assert_tag ACCEPT

# 31. review (v4 L2): no product-delta → WRITEBACK; 无产品层变更 → pass; delta naming a missing file → WRITEBACK
mk_v4 r1
F="$T/r1/.sdlc/f"
printf '泳道：L2\n## Snapshot\nfindings\n' >"$F/05-review/findings.md"
assert_exit 1 "v4 --hat review without product-delta is WRITEBACK" --hat review "$F"
assert_tag WRITEBACK
printf '无产品层变更：纯文案修正\n' >"$F/product-delta.md"
assert_exit 0 "v4 --hat review with explicit no-change delta" --hat review "$F"
printf '| pm | feature-map.md | 旅程 | 新增 J-1 | spec |\n| growth | data/tags.yaml | 标签 | 新增 | x |\n' >"$F/product-delta.md"
assert_exit 1 "v4 delta naming a missing product file is WRITEBACK" --hat review "$F"
assert_tag WRITEBACK

# 32. HATADVANCE: fresh fail@implement but current_hat=accept
mk_v4 h1
F="$T/h1/.sdlc/f"
sed -i.bak 's/^current_hat: define/current_hat: accept/' "$F/state.yaml" && rm -f "$F/state.yaml.bak"
printf 'findings\n' >"$F/05-review/findings.md"
cat >>"$F/state.yaml" <<'Y'
gates:
  - name: fresh-context
    kind: fresh-context
    stage: implement
    result: fail
Y
assert_exit 1 "v4 HATADVANCE fail@implement but current=accept" --require "$F"
assert_tag HATADVANCE

# 33. --hat product: missing/unfilled → PRODUCTCTX; filled → pass
mk_v4 p1
assert_exit 0 "--hat product on a filled product layer" --hat product "$T/p1/docs/product"
rm "$T/p1/docs/product/domain-model.md"
printf '<!-- sdlc:unfilled -->\n' >"$T/p1/docs/product/architecture.md"
assert_exit 2 "--hat product missing domain-model + unfilled architecture" --hat product "$T/p1/docs/product"
assert_tag PRODUCTCTX

# 34. growth + launch hats
mk_v4 gr1
F="$T/gr1/.sdlc/f"
assert_exit 1 "--hat growth without 00-discover/growth.md" --hat growth "$F"
assert_tag HATMISS
mkdir -p "$F/00-discover" "$F/06-deliver"
printf '泳道：L2\n定位假设\n| 参考 | https://a.example/x 2026-09-01 |\n| 参考 | https://b.example/y 2026-09-01 |\n| 参考 | https://c.example/z 2026-09-01 |\n' >"$F/00-discover/growth.md"
assert_exit 0 "--hat growth with growth.md and filled product growth.md" --hat growth "$F"
printf '泳道：L3\n人群：近 7 天导入过数据但未查看报告\n渠道：站内信\n' >"$F/06-deliver/launch.md"
assert_exit 1 "--hat launch without holdout/guardrail is LAUNCH" --hat launch "$F"
assert_tag LAUNCH

# 35. legacy (no sdlc_version): v4 rules stay off
mkdir -p "$T/leg4/02-shape"
cat >"$T/leg4/state.yaml" <<'Y'
feature: t
lane: L3
appetite: 4h
ui: yes
current_hat: shape
hats_done: [define]
Y
printf '泳道：L3\n' >"$T/leg4/02-shape/edge-states.md"
assert_exit 0 "legacy --hat designer ignores v4 direction rules" --hat designer "$T/leg4"

# 36. product decisions: strategic 默认 / 默认已定 text / strategic 待确认 / 已确认 without the operator's words
mk_v4 dc1
PR="$T/dc1/docs/product"
printf '# strategy\n| id | 问题 | 类别 | 选项与推荐 | 状态 | 决定 |\n|---|---|---|---|---|---|\n| Q-PAYWALL | 首个付费墙 | 战略 | A 存储（推荐） | 默认 | |\n' >"$PR/strategy.md"
assert_exit 1 "--hat product: strategic decision marked 默认" --hat product "$PR"
assert_tag DEFAULTED
printf '# strategy\n| Q-PAYWALL | 首个付费墙 | 战略 | A 存储（推荐） | 待确认 | |\n' >"$PR/strategy.md"
assert_exit 1 "--hat product: strategic decision still 待确认" --hat product "$PR"
assert_tag DECISIONPENDING
printf '# strategy\n首个付费墙 = 结果存储〔默认已定·待复核〕\n' >"$PR/strategy.md"
assert_exit 1 "--hat product: 默认已定 in text" --hat product "$PR"
assert_tag DEFAULTED
printf '# strategy\n| **Q-PAYWALL** | 首个付费墙 | 战略 | A 存储（推荐） | 已确认 | 按推荐 |\n' >"$PR/strategy.md"
assert_exit 1 "--hat product: 已确认 without the operator's words" --hat product "$PR"
assert_tag DEFAULTED
printf '# strategy\n| Q-PAYWALL | 首个付费墙 | 战略 | A 存储（推荐） | 已确认 | 「按推荐，先墙存储」· 操作者 · 2026-09-18 |\n| Q-PAGE | 每页条数 | 运营 | 24（推荐） | 默认 | |\n' >"$PR/strategy.md"
printf '| 2026-09-17 | pm | Q1〔默认已定·待复核〕 |\n' >"$PR/CHANGELOG.md"
assert_exit 0 "--hat product: quoted answer + operational default; CHANGELOG history not scanned" --hat product "$PR"

# 37. feature decisions: a pending strategic Q may sit in define but blocks shape even if state says answered
mk_v4 dc2
F="$T/dc2/.sdlc/f"
printf '| Q-OPEN-GATE | 何时开闸 | 战略 | 验收后即开（推荐） | 待确认 | |\n| Q-SORT | 默认排序 | 运营 | 最新（推荐） | 默认 | |\n' >>"$F/01-define/spec.md"
printf 'open_questions: [{id: Q-OPEN-GATE, status: open}, {id: Q-SORT, status: answered}]\n' >>"$F/state.yaml"
assert_exit 0 "define may hold a pending strategic decision" --require "$F"
sed -i.bak 's/^current_hat: define/current_hat: shape/; s/Q-OPEN-GATE, status: open/Q-OPEN-GATE, status: answered/' "$F/state.yaml"
assert_exit 1 "strategic 待确认 in spec blocks shape" --require "$F"
assert_tag DECISIONPENDING
sed -i.bak 's/| 待确认 | |/| 已确认 | 「验收通过后再开，我来翻闸」· 操作者 · 2026-09-18 |/' "$F/01-define/spec.md"
assert_exit 0 "confirmed with the operator's words unblocks shape" --require "$F"
printf '首个付费墙〔默认已定·待复核〕\n' >>"$T/dc2/docs/product/strategy.md"
assert_exit 0 "product-layer default is a warning outside define" --require "$F"
assert_tag 'SDLC-DEFAULTED'
assert_exit 1 "product-layer default is red at --hat define" --hat define "$F"
assert_tag DEFAULTED
printf '按 pm 推荐：用户未应答，推荐默认采用\n' >"$F/01-define/notes.md"
assert_exit 1 "defaulted wording inside the feature is red" --require "$F"

# 38. PRODUCTUI: a filled design-system.md must cite a screenshot that exists
mk_v4 pu1
PR="$T/pu1/docs/product"
printf '# design-system.md\n颜色来自源码 tokens.ts [推断]\n' >"$PR/design-system.md"
assert_exit 1 "--hat product: design system without screenshots" --hat product "$PR"
assert_tag PRODUCTUI
printf '# design-system.md\n![home](screens/missing.png)\n' >"$PR/design-system.md"
assert_exit 1 "--hat product: design system citing a missing screenshot" --hat product "$PR"
assert_tag PRODUCTUI
mkdir -p "$T/pu1/.sdlc/_product/screens"
printf 'png' >"$T/pu1/.sdlc/_product/screens/admin-home-1440.png"
printf '# design-system.md\n![admin](.sdlc/_product/screens/admin-home-1440.png)\n' >"$PR/design-system.md"
assert_exit 0 "--hat product: screenshot resolved from the project root" --hat product "$PR"

# 39. SOURCES: research artifacts need URL + access date rows; only the user's research.offline waives it
mk_v4 so1
F="$T/so1/.sdlc/f"
mkdir -p "$F/00-discover"
printf '泳道：L2\n## 市场\n操作者口述：租户很多\n' >"$F/00-discover/market.md"
assert_exit 1 "v4 --hat market without web sources" --hat market "$F"
assert_tag SOURCES
printf '泳道：L2\n| 下界 | 1.2 万家 | https://stats.example/report 2026-09-10 | E3 |\n| 竞品价 | ¥99/月 | https://rival.example/pricing（2026-09-10） | E2 |\n| 抱怨 | 「导出太慢」 | https://forum.example/t/1 · 2026-09-11 | E2 |\n' >"$F/00-discover/market.md"
assert_exit 0 "v4 --hat market with three dated URLs" --hat market "$F"
printf '泳道：L2\n| 竞品 | https://rival.example（无日期） |\n' >"$F/00-discover/compete.md"
assert_exit 1 "URLs without an access date do not count" --hat compete "$F"
assert_tag SOURCES
printf 'product_root: docs/product\nresearch:\n  offline: true   # 内网环境，用户设置\n' >"$T/so1/sdlc.config.yaml"
assert_exit 0 "research.offline: true set by the user waives SOURCES" --hat compete "$F"
printf '# growth\n定位：内部采纳型产品，外部 URL 可省略\n' >"$T/so1/docs/product/growth.md"
assert_exit 0 "offline also waives the product growth.md sources" --hat product "$T/so1/docs/product"
printf 'product_root: docs/product\n' >"$T/so1/sdlc.config.yaml"
assert_exit 1 "product growth.md without sources" --hat product "$T/so1/docs/product"
assert_tag SOURCES

# 40. PRODUCTSIZE / REFS / STALE on the product layer
mk_v4 ps1
PR="$T/ps1/docs/product"
{ printf '# strategy\n'; i=0; while [ $i -lt 130 ]; do echo "line $i"; i=$((i+1)); done; } >"$PR/strategy.md"
assert_exit 0 "strategy.md over budget is a warning" --hat product "$PR"
assert_tag 'SDLC-PRODUCTSIZE'
{ printf '# strategy\n'; i=0; while [ $i -lt 260 ]; do echo "line $i"; i=$((i+1)); done; } >"$PR/strategy.md"
assert_exit 1 "strategy.md over twice the budget fails" --hat product "$PR"
assert_tag PRODUCTSIZE
printf '# strategy\n北极星：`metric:wact_tenants`。护栏 metric:export_fail_rate\n' >"$PR/strategy.md"
printf 'metrics:\n  - id: wact_tenants\n    name: 周活跃完成租户\n' >"$PR/data/metrics.yaml"
assert_exit 1 "metric reference without a definition is REFS" --hat product "$PR"
assert_tag REFS
printf 'metrics:\n  - id: wact_tenants\n  - id: export_fail_rate\n' >"$PR/data/metrics.yaml"
assert_exit 0 "defined metric references pass" --hat product "$PR"
printf '| 日期 | 功能 | 帽子 | 文件 | 变更摘要 |\n|---|---|---|---|---|\n| 2026-09-17 | /sdlc-product | growth | growth.md | 定位 |\n| 2026-09-18 | /sdlc-product | pm | strategy.md | 改北极星 |\n' >"$PR/CHANGELOG.md"
assert_exit 0 "upstream change after downstream write is a STALE warning" --hat product "$PR"
assert_tag 'SDLC-STALE'

# 41. unfilled marker: only a leading comment counts; prose that mentions the token is real content
mk_v4 um1
PR="$T/um1/docs/product"
printf '# architecture\n说明：模板顶部的 sdlc:unfilled 注释已删除，本文件为真实内容。\n' >"$PR/architecture.md"
printf '# domain\n`sdlc:unfilled` 是模板标记（见 product-layer.md）\n' >"$PR/domain-model.md"
assert_exit 0 "prose mentioning sdlc:unfilled is not a template" --hat product "$PR"
printf '<!-- sdlc:unfilled — architect 写入真实内容后删除本行 -->\n# architecture\n' >"$PR/architecture.md"
printf 'Table t {\n  id int\n}\n  // sdlc:unfilled\n' >"$PR/erd.dbml"
assert_exit 2 "leading comment markers (html and dbml) are templates" --hat product "$PR"
assert_tag PRODUCTCTX

# 40. P07 discovery killed：define 及之后不得继续；显式 reopened 后放行
mk_v4 k1
F="$T/k1/.sdlc/f"
printf 'discovery:\n  status: killed\n' >>"$F/state.yaml"
assert_exit 1 "discovery killed blocks define (P07)" --hat define "$F"
assert_tag NODISCOVER
printf '  reopened: {by: user, at: 2026-09-18, reason: 新证据}\n' >>"$F/state.yaml"
assert_exit 0 "discovery killed + reopened by the user may continue" --hat define "$F"

# 41. P08 空产品文件不是已填写的产品层
mk_v4 e1
: >"$T/e1/docs/product/strategy.md"
printf '   \n\n' >"$T/e1/docs/product/domain-model.md"
assert_exit 2 "empty / blank product files are PRODUCTCTX (P08)" --hat product "$T/e1/docs/product"
assert_tag PRODUCTCTX

# 42. P09b 子检查失败必须传到父闸门：check-explain 拒绝的执行计划不能被吞掉
mk_v4 x1
F="$T/x1/.sdlc/f"
printf 'product_root: docs/product\nextra_gates: [explain]\n' >"$T/x1/sdlc.config.yaml"
printf '| 1 | SIMPLE | orders | ALL | NULL | NULL | NULL | 10000 | 100 | Using temporary |\n' >"$F/explain.txt"
printf '泳道：L2\nnote\n' >"$F/03-impl/T-1-evidence.md"
mkdir -p "$F/03-impl/screens" && printf 'png' >"$F/03-impl/screens/j1.png"
printf '泳道：L2\n![](screens/j1.png)\n' >"$F/03-impl/T-1-integration.md"
assert_exit 1 "check-explain failure reaches the parent gate (P09b)" --hat implement "$F"
assert_tag EXPLAIN

# 43. P13 验收报告标题（Acceptance report）不触发需求 GWT 规则
mk_v4 h13
F="$T/h13/.sdlc/f"
mkdir -p "$F/03-impl/screens" && printf 'png' >"$F/03-impl/screens/j1.png"
for w in pm design growth; do printf '# Acceptance report\n泳道：L2\n![](../03-impl/screens/j1.png)\n结论：通过\n' >"$F/04-verify/accept-$w.md"; done
assert_exit 0 "acceptance report heading is not a requirement GWT section (P13)" --hat accept "$F"

# 44. C02 模板里「不写「默认已定」」的说明不是默认落地的决策
mk_v4 c02
F="$T/c02/.sdlc/f"
printf '泳道：L2\n## 核心价值与 Aha 时刻\nx\n## 关键用户旅程\nJ-1 导入\n说明：没回答不等于同意——不写「默认已定」。\n' >"$F/01-define/spec.md"
assert_exit 0 "instruction not to write 默认已定 is not DEFAULTED (C02)" --hat define "$F"
printf '泳道：L2\n## 核心价值与 Aha 时刻\nx\n## 关键用户旅程\nJ-1 导入\n定价：默认已定为 99 元\n' >"$F/01-define/spec.md"
assert_exit 1 "a decision written as 默认已定 is still DEFAULTED" --hat define "$F"
assert_tag DEFAULTED

# 45. C03 原样拷贝的模板（带 sdlc:unfilled）等于没交
mk_v4 c03
F="$T/c03/.sdlc/f"
cp "$ROOT/skills/prd-gwt/templates/spec.md" "$F/01-define/spec.md"
assert_exit 2 "a copied, unfilled spec template is HATMISS (C03)" --hat define "$F"
assert_tag HATMISS

# 46. DIAGRAM：功能目录里的图必须过绘图闸门（与 DBML 语义一致、svg-lint 零警告）
if [ -f "$ROOT/vendor/svg-diagram/assets/house-style.svg" ] && command -v node >/dev/null 2>&1; then
  mk_v4 dg
  F="$T/dg/.sdlc/f"
  mkdir -p "$F/02-shape/assets"
  printf 'Table users {\n  id bigint [pk]\n}\nTable orders {\n  id bigint [pk]\n  user_id bigint [ref: > users.id]\n}\n' >"$F/02-shape/schema.dbml"
  python3 - "$ROOT/vendor/svg-diagram/assets/house-style.svg" "$F/02-shape/assets/f-er.svg" <<'PY'
import re, sys
t = open(sys.argv[1]).read()
meta = '<metadata id="sdlc">{"type": "er", "owner": "dba", "sources": ["02-shape/schema.dbml"]}</metadata>'
t = re.sub(r"(<svg[^>]*>)", r"\1" + meta, t, count=1)
t = t.replace("</svg>", '<g data-sdlc-id="users"/><g data-sdlc-id="orders"/><g data-sdlc-id="orders.user_id->users.id"/></svg>')
open(sys.argv[2], "w").write(t)
PY
  assert_exit 0 "an ER diagram matching its DBML passes the stage gate" --hat define "$F"
  sed -i.bak 's#<g data-sdlc-id="orders.user_id->users.id"/>##' "$F/02-shape/assets/f-er.svg" && rm -f "$F/02-shape/assets/f-er.svg.bak"
  assert_exit 1 "an ER diagram missing a DBML relationship is DIAGRAM" --hat define "$F"
  assert_tag DIAGRAM
fi

if [ "$fail" -ne 0 ]; then
  echo "----------------------------------------"
  echo "test-check-sdlc: $fail failed"
  exit 1
fi
echo "----------------------------------------"
echo "test-check-sdlc: all passed"
exit 0

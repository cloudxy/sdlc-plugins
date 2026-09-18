#!/usr/bin/env bash
# ============================================================================
# check-sdlc.sh — SDLC 工件合规门禁（G-脚本，确定性判决）
# 用法：bash check-sdlc.sh [--require] [--hat <stage-id>] [--report] <feature 目录或 S 档文件>
#       bash check-sdlc.sh --stats [root]
# 退出码 = 违规数。默认：无工件则跳过（exit 0），不阻塞非流程改动。
# --require：跳过视为失败（编排器在帽子应交件之后用；skip ≠ pass）
# --hat <stage-id>：隐含 --require；按 H.1 必交路径表检查本帽工件。
# --report：/sdlc-review 报告模式。只验 findings.md + ## Snapshot；跳过 NOLANE/MATRIX/NOSEC 等泳道检查。
#   stage-id 来自 workflow/registry.json（spawn 角色名如 pm 非法）。
#   --hat product <product_root>：只验产品层文件（已填、无 sdlc:unfilled），不跑泳道检查。
#   v4：state.yaml 含 sdlc_version: 4 时启用产品层 / 设计方向 / 联调 / E2E / 三方验收 / 回写闸门；旧档不受影响。
#   未知/空 stage-id → 用法错误（exit 64）。skip 由 state.yaml roles_skipped
#   单行 flow 列表精确 token 决定（block-style 无效，见 H.1）。
#   `product-ops` ≡ `ops`（跳过别名，不是 spawn type）。
# ============================================================================
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
MATRIX_PY="$SCRIPT_DIR/../skills/coverage-matrix/scripts/check-matrix.py"
set -u
V=0
REQUIRE=0
HAT_GIVEN=0
HATID=""
REPORT=0
TMPF=$(mktemp 2>/dev/null || echo /tmp/_sdlc_$$.tmp)
trap 'rm -f "$TMPF"' EXIT
red() { printf "\033[0;31m✗ [SDLC-%s] %s\033[0m\n" "$1" "$2"; V=$((V+1)); }
grn() { printf "\033[0;32m✓ %s\033[0m\n" "$1"; }

VALID_HATS=$(python3 "$SCRIPT_DIR/workflow.py" stages) || exit 64
is_valid_hat() { case " $VALID_HATS " in *" $1 "*) return 0 ;; esac; return 1; }

FILTERED=()
while [ $# -gt 0 ]; do
  case "$1" in
    --require) REQUIRE=1 ;;
    --hat)
      HAT_GIVEN=1
      if [ $# -ge 2 ]; then HATID="$2"; shift; else HATID=""; fi
      ;;
    --report) REPORT=1 ;;
    *) FILTERED+=("$1") ;;
  esac
  shift
done
set -- "${FILTERED[@]+"${FILTERED[@]}"}"

# ---------- --stats：四度量汇总（泳道分布/闸门拦截/返工/耗时） ----------
if [ "${1:-}" = "--stats" ]; then
  trap "" PIPE
  ROOT="${2:-.sdlc}"
  echo "SDLC 四度量（${ROOT}）"
  echo "================================"
  declare -a LANE_C=(0 0 0 0 0); TOTAL=0; INTERCEPT=0; REWORK=0; DUR=0; DURN=0
  for st in $(find "$ROOT" -name state.yaml 2>/dev/null); do
    L=$(grep -m1 -E "^lane:" "$st" | grep -oE "L[0-4]" | tr -d L); [ -z "$L" ] && continue
    LANE_C[$L]=$((LANE_C[$L]+1)); TOTAL=$((TOTAL+1))
    FI=$(grep -m1 -oE "findings_total: [0-9]+" "$st" | grep -oE "[0-9]+$"); [ -n "$FI" ] && INTERCEPT=$((INTERCEPT+FI))
    RW=$(grep -m1 -oE "rework_rounds: [0-9]+" "$st" | grep -oE "[0-9]+$"); [ -n "$RW" ] && REWORK=$((REWORK+RW))
    DM=$(grep -m1 -oE "duration_min: [0-9]+" "$st" | grep -oE "[0-9]+$"); [ -n "$DM" ] && { DUR=$((DUR+DM)); DURN=$((DURN+1)); }
  done
  [ $TOTAL -eq 0 ] && { echo "无已记账 feature"; exit 0; }
  echo "泳道分布: L0=${LANE_C[0]} L1=${LANE_C[1]} L2=${LANE_C[2]} L3=${LANE_C[3]} L4=${LANE_C[4]}（共 ${TOTAL}）"
  echo "独立审查拦截: $INTERCEPT 个自审未发现问题"
  echo "返工轮次: $REWORK"
  [ $DURN -gt 0 ] && echo "平均耗时: $((DUR/DURN)) 分钟/票"
  echo "L3+ 占比: $(( (LANE_C[3]+LANE_C[4])*100/TOTAL ))%（>40% 判定过严）"
  exit 0
fi

# ---------- --hat 校验（隐含 --require；spawn 角色名非法） ----------
if [ "$HAT_GIVEN" = "1" ]; then
  REQUIRE=1
  if [ -z "$HATID" ] || ! is_valid_hat "$HATID"; then
    echo "用法错误: --hat 必须是 stage-id (合法值: ${VALID_HATS})。--hat pm 这类 spawn 角色名非法。" >&2
    exit 64
  fi
fi

TARGET="${1:-}"
if [ -z "$TARGET" ]; then echo "用法: check-sdlc.sh [--require] [--hat <stage-id>] [--report] <feature目录|S档文件> | --stats [root]"; exit 1; fi

# ---------- v4 决策闸（DEFAULTED / DECISIONPENDING） ----------
# 决策行 = 表格行里有 Q-* id、「类别」单元格（战略|运营）和「状态」单元格（待确认|已确认|默认）。
# 无类别单元格的旧表不参与判定。战略决策只能由操作者明确回答：没回答 ≠ 同意。
decision_rows() { # $@ = 文件 → file<TAB>id<TAB>类别<TAB>状态<TAB>有「原话」(1/0)
  [ $# -gt 0 ] || return 0
  awk -F'|' '
    /^[[:space:]]*\|/ {
      id=""; cls=""; stat=""; q=0
      for (i=2; i<NF; i++) {
        c=$i; gsub(/\*\*/, "", c); gsub(/^[[:space:]]+|[[:space:]]+$/, "", c)
        if (id=="" && c ~ /^Q-[A-Z][A-Z0-9-]*$/) id=c
        else if (c=="战略" || c=="运营") cls=c
        else if (c=="待确认" || c=="已确认" || c=="默认") stat=c
        if (index($i, "「") && index($i, "」")) q=1
      }
      if (id!="" && cls!="" && stat!="") printf "%s\t%s\t%s\t%s\t%d\n", FILENAME, id, cls, stat, q
    }' "$@" 2>/dev/null
}
check_defaulted() { # $1 = red|warn；其余 = 文件
  local mode="$1"; shift
  [ $# -gt 0 ] || return 0
  local df did dcls dstat dq msg hit hits
  while IFS="$(printf '\t')" read -r df did dcls dstat dq; do
    [ -n "$did" ] || continue
    msg=""
    if [ "$dcls" = "战略" ] && [ "$dstat" = "默认" ]; then
      msg="$df: $did 是战略决策却标「默认」（只能由操作者明确回答：写「待确认」+ 选项与推荐，问人并等待）"
    elif [ "$dstat" = "已确认" ] && [ "$dq" != "1" ]; then
      msg="$df: $did 标「已确认」但没有操作者原话「…」（写明谁、何时、怎么答的；没有回答就仍是待确认）"
    fi
    [ -n "$msg" ] || continue
    if [ "$mode" = "red" ]; then red DEFAULTED "$msg"; else printf "\033[0;33m⚠ [SDLC-DEFAULTED] %s\033[0m\n" "$msg"; fi
  done <<EOF
$(decision_rows "$@")
EOF
  hits=$(grep -HnE '默认已定|未(应答|回复|答复)[^|]{0,24}(默认|采用|推荐)' "$@" 2>/dev/null \
    | grep -vE '(不写|不要写|不得写|禁止写|别写|不能写|不要|不得|禁止)[[:space:]]*[「"“]?默认已定')  # 模板里禁止这样写的说明不是违规（C02）
  [ -n "$hits" ] || return 0
  local total
  total=$(printf '%s\n' "$hits" | grep -c .)
  while IFS= read -r hit; do
    msg="${hit}（用户没回答不等于同意：战略问题保持待确认并停下等人，不得按推荐默认落地）"
    if [ "$mode" = "red" ]; then red DEFAULTED "$msg"; else printf "\033[0;33m⚠ [SDLC-DEFAULTED] %s\033[0m\n" "$msg"; fi
  done <<EOF
$(printf '%s\n' "$hits" | head -3)
EOF
  [ "$total" -gt 3 ] && printf "  …默认落地的战略决策文本共 %s 处（只列前 3 处）\n" "$total"
  return 0
}
check_pending() { # $1 = 说明；其余 = 文件：战略决策仍待确认
  local why="$1"; shift
  [ $# -gt 0 ] || return 0
  local df did dcls dstat dq
  while IFS="$(printf '\t')" read -r df did dcls dstat dq; do
    [ -n "$did" ] || continue
    if [ "$dcls" = "战略" ] && [ "$dstat" = "待确认" ]; then
      red DECISIONPENDING "$df: 战略决策 $did 仍待确认 —— ${why}（把选项与推荐交给操作者并等待明确回答；这不是返工）"
    fi
  done <<EOF
$(decision_rows "$@")
EOF
}

is_unfilled() { # $1 = 文件：模板标记只认行首注释（<!-- / # / //），正文里提到这个词不算
  grep -qE '^[[:space:]]*(<!--|#|//)[[:space:]]*sdlc:unfilled' "$1" 2>/dev/null
}
research_offline() { # $1 = 起点目录：上溯找 sdlc.config.yaml；research.offline: true（只有用户能设）→ 0
  local d="$1" nd j=0
  while [ $j -lt 8 ]; do
    if [ -f "$d/sdlc.config.yaml" ]; then
      awk '/^research:/ { r=1; next } r && /^[^[:space:]#]/ { r=0 } r && /^[[:space:]]+offline:[[:space:]]*true([[:space:]]|#|$)/ { f=1 } END { exit f ? 0 : 1 }' "$d/sdlc.config.yaml"
      return $?
    fi
    nd=$(dirname "$d"); [ "$nd" = "$d" ] && break; d="$nd"; j=$((j+1))
  done
  return 1
}
need_sources() { # $1 = 文件；$2 = 最少条数；$3 = 标签。数「URL 与日期同一行」的不同 URL
  [ -f "$1" ] || return 0
  research_offline "$(cd "$(dirname "$1")" && pwd)" && return 0
  local n
  n=$(grep -E 'https?://' "$1" 2>/dev/null | grep -E '20[0-9]{2}-[0-9]{2}-[0-9]{2}' | grep -oE 'https?://[^[:space:]|)>」,，；;]+' | sed -E 's#[.。]+$##' | sort -u | wc -l | tr -d ' ')
  [ "${n:-0}" -ge "$2" ] || red SOURCES "$1: 网络来源 ${n:-0} 条，$3 需 ≥$2 条（同一行写 URL + 访问日期）。帽子有 WebSearch/WebFetch，包里写「不需要联网」不是理由；只有用户在 sdlc.config.yaml 设 research.offline: true 才豁免"
}
has_existing_image() { # $1 = md 文件：引用的 PNG/JPG/WebP 至少一张真实存在（相对文件目录，上溯到项目根）
  local f="$1" refs ref d nd j
  refs=$(grep -oE '[A-Za-z0-9_./~-]+\.(png|jpe?g|webp)' "$f" 2>/dev/null | sort -u)
  [ -n "$refs" ] || return 1
  while IFS= read -r ref; do
    case "$ref" in /*) [ -f "$ref" ] && return 0; continue ;; esac
    d=$(cd "$(dirname "$f")" && pwd); j=0
    while [ $j -lt 6 ]; do
      [ -f "$d/$ref" ] && return 0
      [ -f "$d/sdlc.config.yaml" ] && break
      nd=$(dirname "$d"); [ "$nd" = "$d" ] && break; d="$nd"; j=$((j+1))
    done
  done <<EOF
$refs
EOF
  return 1
}

missing_images() { # $1 = md 文件 → 打印引用了但不存在的图片；一张都没引用时打印 NONE
  local f="$1" refs ref d nd j found miss=""
  refs=$(grep -oE '[A-Za-z0-9_./~-]+\.(png|jpe?g|webp)' "$f" 2>/dev/null | sort -u)
  [ -n "$refs" ] || { echo NONE; return; }
  while IFS= read -r ref; do
    found=0
    case "$ref" in
      /*) [ -f "$ref" ] && found=1 ;;
      *) d=$(cd "$(dirname "$f")" && pwd); j=0
         while [ $j -lt 6 ]; do
           [ -f "$d/$ref" ] && { found=1; break; }
           [ -f "$d/sdlc.config.yaml" ] && break
           nd=$(dirname "$d"); [ "$nd" = "$d" ] && break; d="$nd"; j=$((j+1))
         done ;;
    esac
    [ "$found" -eq 1 ] || miss="$miss $ref"
  done <<EOF
$refs
EOF
  echo "${miss# }"
}
need_images() { # $1 = md 文件；$2 = 标签；$3 = 语境。截图必须真实存在：一张不引用、或引用了不存在的文件都算违规
  local m
  m=$(missing_images "$1")
  if [ "$m" = "NONE" ]; then red "$2" "$1: ${3}未引用截图"
  elif [ -n "$m" ]; then red "$2" "$1: 引用的截图不存在: ${m}（截图要真实拍下来，不能只写路径）"
  fi
}

# ---------- --hat product：产品层独立检查（/sdlc-product 用；不跑泳道检查） ----------
if [ "$HAT_GIVEN" = "1" ] && [ "$HATID" = "product" ]; then
  PRD="$TARGET"
  if [ ! -d "$PRD" ]; then
    red PRODUCTCTX "--hat product: 产品层目录 $PRD 不存在"
  else
    for pf in strategy.md feature-map.md architecture.md domain-model.md erd.dbml; do
      if [ ! -f "$PRD/$pf" ]; then red PRODUCTCTX "--hat product: 缺 $PRD/$pf"
      elif ! grep -q '[^[:space:]]' "$PRD/$pf" 2>/dev/null; then red PRODUCTCTX "--hat product: $PRD/$pf 是空文件（P08）"
      elif is_unfilled "$PRD/$pf"; then red PRODUCTCTX "--hat product: $PRD/$pf 仍是模板（含 sdlc:unfilled）"
      fi
    done
    for pf in growth.md design-system.md data/tracking-plan.yaml data/metrics.yaml data/tags.yaml; do
      if [ -f "$PRD/$pf" ] && is_unfilled "$PRD/$pf"; then
        printf "\033[0;33m⚠ [SDLC-PRODUCTOPT] %s 仍是模板（可选文件：该产品无此面时删掉文件并在 README 写明理由）\033[0m\n" "$PRD/$pf"
      fi
    done
    if [ -f "$PRD/growth.md" ] && ! is_unfilled "$PRD/growth.md"; then need_sources "$PRD/growth.md" 3 "--hat product growth.md"; fi
    if [ -f "$PRD/data-dictionary.md" ]; then
      python3 "$SCRIPT_DIR/data_dictionary.py" --product-root "$PRD" --check >/dev/null 2>&1 \
        || red PRODUCTCTX "$PRD/data-dictionary.md: 与 erd.dbml / domain-model.md / data/metrics.yaml 不一致（来源已变或被手改）——重新生成：python3 PLUGIN_ROOT/scripts/data_dictionary.py --product-root $PRD"
    fi
    DS="$PRD/design-system.md"
    if [ -f "$DS" ] && ! is_unfilled "$DS"; then
      has_existing_image "$DS" || red PRODUCTUI "$DS: 没有引用任何存在的截图——设计系统要从运行中的产品反推：按 app.start 启动，scripts/ui-evidence.sh 截图并引用 PNG（尚无界面的新产品引用原型截图；check_config.py --probe 查应用是否在跑）"
    fi
    PMD=$(find "$PRD" -name '*.md' -not -name 'CHANGELOG.md' 2>/dev/null)
    if [ -n "$PMD" ]; then
      check_defaulted red $PMD
      check_pending "产品层未完成（/sdlc-product 须拿到操作者回答后再收尾）" $PMD
    fi
    # PRODUCTSIZE：每次 spawn 都会整读产品层；超预算告警，超 2× 失败
    for spec in strategy.md:120 feature-map.md:200 growth.md:200 design-system.md:250 architecture.md:250 domain-model.md:300 README.md:60; do
      pf=${spec%%:*}; lim=${spec##*:}
      [ -f "$PRD/$pf" ] || continue
      nl=$(wc -l <"$PRD/$pf" | tr -d ' ')
      if [ "$nl" -gt $((lim * 2)) ]; then
        red PRODUCTSIZE "$PRD/$pf: ${nl} 行，超过 2× 预算 ${lim}（产品层只放长期成立的事实；功能细节回到功能工件）"
      elif [ "$nl" -gt "$lim" ]; then
        printf "\033[0;33m⚠ [SDLC-PRODUCTSIZE] %s: %s 行 > 预算 %s\033[0m\n" "$PRD/$pf" "$nl" "$lim"
      fi
    done
    # REFS：metric:/tag:/event: 引用必须在数据文件里有定义（数据文件已填时才查）
    for kind in metric:data/metrics.yaml:id tag:data/tags.yaml:id event:data/tracking-plan.yaml:event; do
      pre=${kind%%:*}; rest=${kind#*:}; yf=${rest%%:*}; key=${rest##*:}
      { [ -f "$PRD/$yf" ] && ! is_unfilled "$PRD/$yf"; } || continue
      [ -n "$PMD" ] || continue
      DEFS=$(grep -oE "^[[:space:]]*-?[[:space:]]*${key}:[[:space:]]*[\"']?[A-Za-z0-9_.-]+" "$PRD/$yf" 2>/dev/null | sed -E "s/.*${key}:[[:space:]]*[\"']?//" | sort -u)
      USED=$(grep -ohE "(^|[^A-Za-z0-9_])${pre}:[A-Za-z0-9_.-]+" $PMD 2>/dev/null | sed -E "s/^.*${pre}://; s/[.]+$//" | sort -u)
      for u in $USED; do
        printf '%s\n' "$DEFS" | grep -qxF "$u" || red REFS "$PRD: ${pre}:${u} 在 $yf 里没有定义（负责人补定义，或改成已有 id）"
      done
    done
    # STALE（告警）：按 CHANGELOG 行序，上游文件在下游最后一次写入之后又变了
    if [ -f "$PRD/CHANGELOG.md" ]; then
      STALE_OUT=$(awk -F'|' '
        BEGIN {
          deps["growth.md"]="strategy.md feature-map.md data/metrics.yaml data/tags.yaml"
          deps["design-system.md"]="strategy.md feature-map.md"
          deps["architecture.md"]="strategy.md"
          deps["domain-model.md"]="architecture.md feature-map.md"
          deps["data/tracking-plan.yaml"]="domain-model.md feature-map.md"
          deps["data/metrics.yaml"]="strategy.md data/tracking-plan.yaml"
          deps["data/tags.yaml"]="data/metrics.yaml"
          n = split("strategy.md feature-map.md growth.md design-system.md architecture.md domain-model.md data/tracking-plan.yaml data/metrics.yaml data/tags.yaml", files, " ")
        }
        /^[[:space:]]*\|/ && NF > 5 {
          for (i = 1; i <= n; i++) {
            f = files[i]; b = f; sub(/^data\//, "", b)
            if (index($5, f) > 0 || (b != f && index($5, b) > 0)) last[f] = NR
          }
        }
        END {
          for (d in deps) {
            if (!(d in last)) continue
            m = split(deps[d], ups, " ")
            for (k = 1; k <= m; k++) if ((ups[k] in last) && last[ups[k]] > last[d]) print d " ← " ups[k]
          }
        }' "$PRD/CHANGELOG.md" | sort)
      if [ -n "$STALE_OUT" ]; then
        while IFS= read -r sl; do
          printf "\033[0;33m⚠ [SDLC-STALE] %s（上游在下游最后一次写入之后又改了：重跑下游负责人，或在 progress 记录为何不受影响）\033[0m\n" "$sl"
        done <<EOF
$STALE_OUT
EOF
      fi
    fi
  fi
  echo "----------------------------------------"
  if [ $V -eq 0 ]; then grn "产品层检查通过"
  else printf "\033[0;31m✗ [SDLC-SUMMARY] 共 %s 处违规\033[0m\n" "$V"
  fi
  exit $V
fi
if [ ! -e "$TARGET" ]; then
  echo "check-sdlc: $TARGET 不存在，跳过"
  if [ "$REQUIRE" = "1" ]; then red SKIP "$TARGET 不存在（--require：跳过不能当放行）"; exit "$V"; fi
  exit 0
fi

# ---------- S 档单文件 / M+L 档目录统一收集工件 ----------
# 非流程工件豁免（基础设施文件：账本/说明/模板——不要求泳道声明与证据）
EXEMPT_RE='\.sdlc/(_lessons\.md|README\.md)$'

FILES=""
if [ -f "$TARGET" ]; then FILES="$TARGET"; ROOT="$(dirname "$TARGET")"
else
  ROOT="$TARGET"
  FILES=$(find "$TARGET" -name "*.md" -o -name "state.yaml" 2>/dev/null | grep -vE "$EXEMPT_RE" || true)
fi
if [ -z "$FILES" ]; then
  echo "check-sdlc: 无工件，跳过"
  if [ "$REQUIRE" = "1" ]; then red SKIP "无工件（--require：跳过不能当放行）"; exit "$V"; fi
  exit 0
fi

# Artifact locations are data; semantic checks below refer to generated shell variables.
python3 "$SCRIPT_DIR/workflow.py" artifact-paths > "$TMPF" || exit 64
while IFS=$'\t' read -r ART_ID ART_PATH; do
  printf -v "ART_${ART_ID}" '%s' "$ART_PATH"
done < "$TMPF"

ST="$ROOT/state.yaml"
[ -f "$ST" ] || ST="$TARGET"

# ---------- roles_skipped 精确 token（单行 flow 列表；block-style 无效） ----------
role_skipped() { # $1 = spawn_role token；读 state.yaml roles_skipped
  [ -f "$ST" ] || return 1
  LINE=$(grep -m1 -E '^roles_skipped:' "$ST" | sed -E 's/^roles_skipped:[[:space:]]*//; s/#.*$//; s/\[//g; s/\]//g')
  [ -n "$LINE" ] || return 1
  OLDIFS=$IFS; IFS=','
  for t in $LINE; do
    t=$(printf '%s' "$t" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
    [ "$t" = "$1" ] && { IFS=$OLDIFS; return 0; }
    # product-ops is a skip alias for spawn role ops (not a --hat / spawn type)
    if [ "$1" = "ops" ] && [ "$t" = "product-ops" ]; then
      IFS=$OLDIFS
      return 0
    fi
  done
  IFS=$OLDIFS
  return 1
}

q_security_yes() {
  [ -f "$ST" ] || return 1
  grep -qE '^q_security:[[:space:]]*yes' "$ST" && return 0
  grep -qE '^[[:space:]]*Q[234]:[[:space:]]*yes' "$ST" && return 0
  return 1
}

# ---------- v4 helpers（仅 sdlc_version>=4 生效） ----------
st_val() { # $1 = 顶层标量键
  [ -f "$ST" ] || return 0
  grep -m1 -E "^$1:" "$ST" | sed -E "s/^$1:[[:space:]]*//; s/[[:space:]]+#.*$//; s/[\"']//g; s/[[:space:]]+$//"
}
is_v4() { SV=$(st_val sdlc_version); case "$SV" in ''|*[!0-9]*) return 1 ;; esac; [ "$SV" -ge 4 ]; }
ui_yes() { [ "$(st_val ui)" = "yes" ]; }
tracking_yes() { [ "$(st_val tracking)" = "yes" ]; }
product_root_abs() {
  PR=$(st_val product_root)
  [ -n "$PR" ] || return 0
  case "$PR" in
    /*) printf '%s' "$PR"; return 0 ;;
  esac
  dd="$ROOT"; j=0
  while [ $j -lt 6 ]; do
    if [ -f "$dd/sdlc.config.yaml" ]; then printf '%s' "$dd/$PR"; return 0; fi
    nd=$(dirname "$dd"); [ "$nd" = "$dd" ] && break; dd="$nd"; j=$((j+1))
  done
  printf '%s' "$(cd "$ROOT/../.." 2>/dev/null && pwd)/$PR"
}
need_product() { # $1 = 产品层相对路径；$2 = 标签
  PRA=$(product_root_abs)
  if [ -z "$PRA" ]; then red PRODUCTCTX "$2: sdlc_version>=4 但 state.yaml 缺 product_root"; return; fi
  if [ ! -f "$PRA/$1" ]; then red PRODUCTCTX "$2: 缺产品层 $PRA/$1（负责人帽补齐，或先跑 /sdlc-product）"
  elif is_unfilled "$PRA/$1"; then red PRODUCTCTX "$2: 产品层 $PRA/$1 仍是模板（含 sdlc:unfilled）"
  fi
}
verdict_of() { # $1 = 验收文件 → 通过|有条件通过|不通过|歧义|空。出现多个不同结论时不取第一个（P12），判为歧义
  local all
  all=$(grep -oE '结论[:：][[:space:]]*(有条件通过|不通过|通过)' "$1" 2>/dev/null | sed -E 's/^结论[:：][[:space:]]*//' | sort -u)
  case "$(printf '%s\n' "$all" | grep -c .)" in
    0) echo "" ;;
    1) echo "$all" ;;
    *) echo "歧义" ;;
  esac
}
check_accept_file() { # $1 = 文件；$2 = 谁；$3 = 是否要求截图(1/0)
  [ -f "$1" ] || return 0 # presence is checked by the registry gate
  VD=$(verdict_of "$1")
  if [ -z "$VD" ]; then red ACCEPT "$1: 缺「结论：通过|有条件通过|不通过」"
  elif [ "$VD" = "歧义" ]; then red ACCEPT "$1: 出现多个不同的「结论：」，只保留当前这一轮的结论（历史轮次移到「历史」小节并改写措辞）"
  elif [ "$VD" = "不通过" ]; then red ACCEPT "$1: $2 验收不通过（按差距清单返工 implement 后重验）"
  fi
  if [ "$3" = "1" ]; then need_images "$1" ACCEPT "$2 验收（有界面的变更须在运行中的产品上走查）"; fi
}
e2e_passed() {
  [ -f "$ST" ] || return 1
  awk '
    /^[A-Za-z_]/ { hit=0 }
    /^[[:space:]]*-[[:space:]]/ { hit=0 }
    /name:[[:space:]]*e2e([[:space:],}]|$)/ { hit=1 }
    hit && /result:[[:space:]]*pass/ { ok=1 }
    END { exit ok?0:1 }
  ' "$ST"
}

# ---------- 0. --hat 必交路径表（H.1，脚本合同） ----------
if [ "$HAT_GIVEN" = "1" ]; then
  CONTRACT_ARGS=(--stage "$HATID" --root "$ROOT")
  for ROLE in $(python3 "$SCRIPT_DIR/workflow.py" roles); do
    role_skipped "$ROLE" && CONTRACT_ARGS+=(--skip "$ROLE")
  done
  ui_yes && CONTRACT_ARGS+=(--ui)
  python3 "$SCRIPT_DIR/workflow.py" check-stage "${CONTRACT_ARGS[@]}" > "$TMPF"
  CONTRACT_RC=$?
  [ "$CONTRACT_RC" -ge 2 ] && { red CONTRACT "cannot load stage contract"; exit 64; }
  while IFS=$'\t' read -r LEVEL CODE MESSAGE; do
    [ -z "$LEVEL" ] && continue
    if [ "$LEVEL" = error ]; then red "$CODE" "--hat $HATID: $MESSAGE"
    else printf '⚠ [SDLC-%s] %s\n' "$CODE" "$MESSAGE"; fi
  done < "$TMPF"
  case "$HATID" in
    market)
      is_v4 && ! role_skipped researcher && need_sources "$ROOT/${ART_market}" 3 "--hat market"
      ;;
    compete)
      is_v4 && ! role_skipped competitor && need_sources "$ROOT/${ART_compete}" 3 "--hat compete"
      ;;
    growth)
      if ! role_skipped growth; then
        is_v4 && need_product growth.md "--hat growth"
        is_v4 && need_sources "$ROOT/${ART_growth}" 3 "--hat growth"
      fi
      ;;
    launch)
      if ! role_skipped growth; then
        if [ -f "$ROOT/${ART_launch}" ]; then
          grep -qE '人群|分群|segment' "$ROOT/${ART_launch}" || red LAUNCH "$ROOT/06-deliver/launch.md: 缺目标人群/分群"
          grep -qE '渠道|channel' "$ROOT/${ART_launch}" || red LAUNCH "$ROOT/06-deliver/launch.md: 缺触达渠道"
          grep -qE '对照|holdout|A/B|护栏' "$ROOT/${ART_launch}" || red LAUNCH "$ROOT/06-deliver/launch.md: 缺对照组/护栏（投放即实验）"
        fi
      fi
      ;;
    accept)
      role_skipped pm || check_accept_file "$ROOT/${ART_accept_pm}" "pm" "$(ui_yes && echo 1 || echo 0)"
      if ui_yes && ! role_skipped designer; then check_accept_file "$ROOT/${ART_accept_designer}" "designer" 1; fi
      role_skipped growth || check_accept_file "$ROOT/${ART_accept_growth}" "growth" 0
      ;;
    define)
      if is_v4; then
        need_product strategy.md "--hat define"
        need_product feature-map.md "--hat define"
        PRA=$(product_root_abs)
        if [ -n "$PRA" ] && [ -d "$PRA" ]; then
          PMD=$(find "$PRA" -name '*.md' -not -name 'CHANGELOG.md' 2>/dev/null)
          [ -n "$PMD" ] && check_defaulted red $PMD
        fi
        SPECF=""
        for p in $(python3 "$SCRIPT_DIR/workflow.py" paths spec); do [ -f "$ROOT/$p" ] && SPECF="$ROOT/$p" && break; done
        if [ -n "$SPECF" ]; then
          grep -qE '核心价值|Aha' "$SPECF" || red CORE "$SPECF: 缺「核心价值与 Aha 时刻」（v4：先说清价值路径再写 FR）"
          if ui_yes; then grep -qE '\bJ-[0-9]+' "$SPECF" || red JOURNEY "$SPECF: ui: yes 但无关键用户旅程 J-n"; fi
          if tracking_yes; then
            [ -f "$ROOT/${ART_tracking}" ] || red TRACKING "--hat define: tracking: yes 但缺 01-define/tracking.md"
          else
            grep -qE '埋点[:：][[:space:]]*N/A' "$SPECF" || [ -f "$ROOT/${ART_tracking}" ] || red TRACKING "$SPECF: tracking 非 yes 时须写「埋点：N/A（理由）」"
          fi
        fi
      fi
      ;;
    signals)
      ;;
    shape)
      if is_v4 && ! role_skipped architect; then
        need_product architecture.md "--hat shape"
        if [ -f "$ROOT/${ART_contract}" ]; then
          grep -qE '质量属性|QAS' "$ROOT/${ART_contract}" || red ARCH "$ROOT/02-shape/contract.md: 缺质量属性场景（v4：方案由可量化场景驱动）"
          grep -qE '候选方案|备选方案' "$ROOT/${ART_contract}" || red ARCH "$ROOT/02-shape/contract.md: 缺候选方案对比（v4：没有单选项决策）"
        fi
        if ui_yes && ! role_skipped designer; then
          [ -f "$ROOT/${ART_directions}" ] && grep -qE '选定[:：][[:space:]]*D[0-9]+' "$ROOT/${ART_directions}" \
            || red DESIGNFIRST "--hat shape: ui: yes 但设计方向未选定（体验先于架构：designer explore → 人工选择 → specify）"
        fi
      fi
      ;;
    dba)
      role_skipped dba || {
        if is_v4; then
          need_product domain-model.md "--hat dba"
          need_product erd.dbml "--hat dba"
          [ -f "$ROOT/${ART_db_spec}" ] && { grep -qE '路线压力测试' "$ROOT/${ART_db_spec}" || red STRESS "$ROOT/02-shape/db-spec.md: 缺「路线压力测试」（v4：用 feature-map 的 Next/Later 验证可扩展性）"; }
        fi
      }
      ;;
    designer)
      if is_v4 && ! role_skipped designer; then
        DD="$ROOT/${ART_directions}"
        if [ ! -f "$DD" ]; then red HATMISS "--hat designer: 缺 02-shape/design-directions.md（≥3 个方向 + 选定）"
        else
          ND=$(grep -oE '^#+[[:space:]]*D[0-9]+' "$DD" | grep -oE 'D[0-9]+' | sort -u | wc -l | tr -d ' ')
          [ "${ND:-0}" -ge 3 ] || red DIRECTIONS "$DD: 设计方向 ${ND:-0} 个（v4 须 ≥3 个真正不同的方向，标题 ## D1 / ## D2 / ## D3）"
          grep -qE '选定[:：][[:space:]]*D[0-9]+' "$DD" || red DIRECTIONS "$DD: 缺「选定：D<n>」（人工选择后由 designer specify 记录）"
          need_images "$DD" DIRECTIONS "方向（没有渲染产物的方向不算方向）"
          grep -qE '缺陷检查' "$DD" || red DIRECTIONS "$DD: 缺「缺陷检查」（推荐前逐张看截图：重叠 / 截断 / 溢出 / 对齐 / 对比度 / 占位内容）"
          need_sources "$DD" 3 "--hat designer（参考表）"
        fi
        need_product design-system.md "--hat designer"
      fi
      ;;
    implement)
      if is_v4 && ui_yes; then
        if ls "$ROOT"/03-impl/*integration*.md >/dev/null 2>&1; then
          for IF in "$ROOT"/03-impl/*integration*.md; do
            need_images "$IF" INTEGRATION "联调记录（须在运行中的产品上走通切片并截图）"
          done
        else
          red INTEGRATION "--hat implement: ui: yes 但缺 03-impl/T-n-integration.md（前后端联调 + 截图）"
        fi
      fi
      ;;
    verify)
      if is_v4 && ui_yes; then
        e2e_passed || red E2E "$ST: ui: yes 但 gates[] 无 name: e2e 且 result: pass 的记录（有界面的变更 e2e 不得为 null）"
      fi
      ;;
    review)
      if is_v4 && [ "$REPORT" != "1" ]; then
        case "$(st_val lane)" in
          L2|L3|L4)
            DELTA="$ROOT/product-delta.md"
            if [ ! -f "$DELTA" ]; then
              red WRITEBACK "--hat review: 缺 product-delta.md（产品层回写记录；无变更写「无产品层变更：理由」）"
            elif ! grep -qE '无产品层变更[:：]' "$DELTA"; then
              PRA=$(product_root_abs)
              for pf in $(grep -oE '(strategy|feature-map|growth|design-system|architecture|domain-model)\.md|erd\.dbml|data/(tracking-plan|metrics|tags)\.yaml' "$DELTA" | sort -u); do
                [ -n "$PRA" ] && [ ! -f "$PRA/$pf" ] && red WRITEBACK "$DELTA: 记录了 $pf 的变更，但 $PRA/$pf 不存在"
              done
            fi
            ;;
        esac
      fi
      ;;
    qc)
      ;;
    deliver)
      : # presence handled by registry
      ;;
    enablement)
      if role_skipped ops; then
        :
      elif [ -f "$ROOT/${ART_enablement}" ]; then
        grep -qE '客服|第一次成功' "$ROOT/${ART_enablement}" || red ENABLE "$ROOT/06-deliver/enablement.md: 缺「客服」或「第一次成功」（教/开/告最低结构）"
      fi
      ;;
    retro)
      ;;
    warehouse)
      ;;
    collect)
      if is_v4 && ! role_skipped data-collector && [ -f "$ROOT/${ART_tracking_impl}" ]; then need_product data/tracking-plan.yaml "--hat collect"; fi
      ;;
  esac
fi

# ---------- --report：只验 findings + Snapshot，不跑泳道检查 ----------
if [ "$REPORT" = "1" ]; then
  FIND="$ROOT/${ART_findings}"
  [ -f "$FIND" ] || FIND=$(find "$ROOT" -name findings.md 2>/dev/null | head -1)
  if [ -z "$FIND" ] || [ ! -f "$FIND" ]; then
    red HATMISS "--report: 缺 05-review/findings.md"
  else
    grep -qE '^##[[:space:]]*Snapshot' "$FIND" || red NOSNAP "$FIND: 缺 ## Snapshot（报告模式不验 NOLANE/MATRIX/NOSEC）"
  fi
  echo "----------------------------------------"
  if [ $V -eq 0 ]; then grn "SDLC 报告模式通过（findings + Snapshot）"
  else printf "\033[0;31m✗ [SDLC-SUMMARY] 共 %s 处违规\033[0m\n" "$V"
  fi
  exit $V
fi

# ---------- 1. 泳道声明 ----------
LANE_DECLARED=0
for f in $FILES; do
  grep -qE "(泳道|lane)[:：]\s*L[0-4]" "$f" 2>/dev/null && LANE_DECLARED=1 && break
  [ -f "$ROOT/state.yaml" ] && grep -qE "^lane:\s*L[0-4]" "$ROOT/state.yaml" && LANE_DECLARED=1 && break
done
[ "$LANE_DECLARED" = "1" ] && grn "泳道声明" || red NOLANE "未声明泳道（工件头 '泳道：Ln' 或 state.yaml lane 字段）"

# ---------- 2. GWT 验收标准（L2+ 工件含验收段时校验） ----------
for f in $FILES; do
  case "$f" in */04-verify/*|*/05-review/*) continue ;; esac  # 验收/审查报告不是需求工件（P13）
  if grep -qiE "^#+[[:space:]]*(验收标准|Acceptance([[:space:]]+criteria)?)[[:space:]]*$" "$f" 2>/dev/null; then
    if ! grep -qE "Given|当.*时|假设" "$f" 2>/dev/null; then
      red GWT "$f: 验收标准缺 Given/When/Then 结构"
    fi
    # 不可测词
    UNTEST=$(grep -nE "(正确地|正确的|合理地|合理的|正常工作|应该没问题|友好的|快速的|适当的|尽可能|必要时|[Cc]orrectly|[Gg]racefully|[Ff]riendly)" "$f" 2>/dev/null | head -1)
    [ -n "$UNTEST" ] && red VAGUE "$f:$UNTEST 不可测词"
  fi
done

# ---------- 3. 自测证据：命令 + 退出码 + 证据-期望一致性（帽子感知） ----------
IMPL_DONE=1
ST_GLOBAL="$ROOT/state.yaml"
[ -f "$ST_GLOBAL" ] || ST_GLOBAL="$TARGET"
if [ -f "$ST_GLOBAL" ]; then
  grep -qE "hats_done:.*(implement|实现)" "$ST_GLOBAL" 2>/dev/null || IMPL_DONE=0
fi
for f in $FILES; do
  if grep -qE "^#+\s*(自测证据|evidence)" "$f" 2>/dev/null && [ "$IMPL_DONE" = "1" ]; then
    grep -qE "exit|退出码|Exit code|✅.*0$|\[0\]" "$f" || red EVID "$f: 自测证据缺退出码（'跑过了'不是证据）"
    BT='`'
    grep -qF "$BT$BT$BT" "$f" || red EVID "$f: 证据需原样输出块（三反引号围栏）"
    # EVIDMISMATCH：want 按 FR 号存（QA-1），证据区标题 FR-n（重锚（QA-4）
    if [ "$IMPL_DONE" = "1" ]; then
      awk '/^FR-[0-9]+[[:space:]]*(Given|假设)/ { cur=substr($0,1,index($0," ")-1); pend=1 }
           /Then/ && pend==1 { want[cur]=($0 ~ /退出码 0|exit code 0/) ? 0 : 1; pend=0 }
           /^FR-[0-9]+[（(]/ { n=index($0,"（"); if(n==0) n=index($0,"("); cur=substr($0,1,n-1) }
           /^exit code [0-9]+/ { if (want[cur]==0 && $0 !~ /exit code 0/) print FILENAME": " cur " 期望 0 但证据记录 " $0 }' "$f" > "$TMPF" 2>/dev/null || true
      while IFS= read -r bad; do
        red EVIDMISMATCH "${bad}（中间态证据禁入——重录终态输出）"
      done < "$TMPF"
    fi
  fi
done

# ---------- 4. state.yaml 必填字段 + 闸门三类记录 + null 显式化 ----------
if [ -f "$ST" ]; then
  for k in feature lane current_hat; do
    grep -qE "^${k}:.*\S" "$ST" || red STATE "$ST: 缺必填字段 $k"
  done
  grep -qE "^appetite:.*\S" "$ST" || grep -qE "^lane:\s*L[01]" "$ST" || red STATE "$ST: L2+ 必填 appetite"
  # null 闸门必须带 reason
  if grep -qE "result:\s*null" "$ST" && ! grep -qE "reason:" "$ST"; then
    red NULLGATE "$ST: 闸门 result:null 但缺 reason（静默跳过=漏洞）"
  fi
fi

# ---------- 5. 覆盖矩阵空洞（存在 coverage.md 时；优先 check-matrix.py 含 NFR） ----------
COV=$(find "$ROOT" -name "coverage.md" 2>/dev/null | head -1)
if [ -n "$COV" ]; then
  SPECS=$(find "$ROOT" \( -name "spec.md" -o -name "spec-s.md" -o -path "*01-define/tracking.md" \) 2>/dev/null)
  if [ -n "$SPECS" ] && [ -f "$MATRIX_PY" ] && command -v python3 >/dev/null 2>&1; then
    MOUT=$(python3 "$MATRIX_PY" "$COV" $SPECS 2>&1) || true
    while IFS= read -r line; do
      case "$line" in
        *'✗ [MATRIX]'*) red MATRIX "$COV: $line" ;;
      esac
    done <<EOF
$MOUT
EOF
  else
    for sf in $SPECS; do
      for fr in $(grep -oE "FR-[0-9]+" "$sf" 2>/dev/null | sort -u); do
        grep -q "$fr" "$COV" 2>/dev/null || red MATRIX "$COV: $fr 未出现在覆盖矩阵（空洞须补用例或标豁免）"
      done
    done
  fi
fi

# ---------- 5b. Q-security → contract.md 须有 [SEC-n] ----------
if q_security_yes; then
  CON=$(find "$ROOT" -name "contract.md" 2>/dev/null | head -1)
  if [ -n "$CON" ]; then
    grep -qE '\[SEC-[0-9]+\]' "$CON" || red NOSEC "$CON: Q-security=yes 但无 [SEC-n]（threat-model 须落在合同）"
  fi
fi

# ---------- 6. metrics.yaml 重复 id（L4） ----------
MET=$(find "$ROOT" -name "metrics.yaml" 2>/dev/null | head -1)
if [ -n "$MET" ]; then
  DUP=$(grep -E "^\s*-?\s*id:" "$MET" | sort | uniq -d)
  [ -n "$DUP" ] && red METDUP "$MET: 重复指标 id（${DUP}）—— 口径唯一事实源被破坏"
fi

# ---------- 7. 进度源 vs 工件（feat-four-pillars 2026-09-07 实锤） ----------
if [ -f "$ST" ]; then
  # current_hat 归一化到英文主词（中文 legacy 双边认；resume 时经理负责归一化写回）
  norm_hat() {
    case "$1" in
      信号|signals) echo signals ;;
      定义|define) echo define ;;
      采集|collect) echo collect ;;
      塑形|shape) echo shape ;;
      实现|implement) echo implement ;;
      验证|verify) echo verify ;;
      验收|accept) echo accept ;;
      审查|review) echo review ;;
      放行|qc) echo qc ;;
      交付|deliver) echo deliver ;;
      回顾|retro) echo retro ;;
      *) echo "$1" ;;
    esac
  }
  rank_of() { python3 "$SCRIPT_DIR/workflow.py" rank "$1"; }
  HAT=$(grep -m1 -E "^current_hat:" "$ST" | sed -E 's/^current_hat:[[:space:]]*//;s/["'\'']//g')
  NHAT=$(norm_hat "$HAT")
  # 最后一个 fresh-context gate：result 与 stage（stage 缺省=legacy 旧档）
  FAIL_STAGE=$(awk '
    /kind:[[:space:]]*fresh-context/ { in_fc=1; s=""; next }
    in_fc && /kind:/ { in_fc=0 }
    in_fc && /stage:[[:space:]]*[A-Za-z]/ { sub(/.*stage:[[:space:]]*/,""); s=$0 }
    in_fc && /result:[[:space:]]*(pass|fail)/ { r=$2; ls=s; lr=r; in_fc=0 }
    END { if (lr=="fail") print ls }
  ' "$ST")
  if [ -n "$FAIL_STAGE" ]; then
    NFAIL=$(norm_hat "$FAIL_STAGE")
    RH=$(rank_of "$NHAT"); RF=$(rank_of "$NFAIL")
    if [ "$RF" -eq 0 ]; then
      # legacy 旧档无 stage 标记：只在 current_hat 已越过全部生产阶段时红
      case "$NHAT" in
        accept|review|qc|deliver|retro)
          red HATADVANCE "$ST: 最近 G-fresh(fail) 禁止 current_hat=${HAT}（审查/放行/交付前不得推帽）"
          ;;
      esac
    elif [ "$RH" -gt "$RF" ]; then
      red HATADVANCE "$ST: 最近 G-fresh fail@${NFAIL} 但 current_hat=${HAT}（越级；应留在 ${NFAIL} 返工，HATADVANCE）"
    fi
  fi

  SPEC=$(find "$ROOT" -name spec.md -o -name spec-s.md 2>/dev/null | head -1)
  if [ -n "$SPEC" ]; then
    if grep -qE '^appetite:[[:space:]]*["'"'"']?8h' "$ST" && grep -qE 'Wave[[:space:]]*0|[0-9]+[[:space:]]*人周' "$SPEC"; then
      red APPETITE "$ST: appetite 仍是 8h，但 $SPEC 已按波/人周（进度源与 PRD 互相否定）"
    fi
    for q in $(grep '待确认' "$SPEC" | grep -oE 'Q-[A-Z][A-Z0-9-]+' | sort -u); do
      grep -qF "$q" "$ST" || red OPENQ "$ST: spec 待确认 $q 未写入 open_questions"
    done
    # OPENQOPEN: 待确认 Q 已记账但未 answered，且 current_hat 已过 define
    if [ "$(rank_of "$NHAT")" -gt 2 ]; then
      for q in $(grep '待确认' "$SPEC" | grep -oE 'Q-[A-Z][A-Z0-9-]+' | sort -u); do
        if grep -qE "${q}.*answered" "$ST"; then
          :
        else
          red OPENQOPEN "$ST: spec 待确认 $q 未 answered，禁止进入 ${HAT}"
        fi
      done
    fi
  fi

  # v4 决策：战略决策不得被默认；过 define（或 shape）仍待确认的战略决策禁止推帽
  if is_v4; then
    FMD=$(find "$ROOT" -name '*.md' -not -path '*/memory/*' 2>/dev/null)
    [ -n "$FMD" ] && check_defaulted red $FMD
    if [ "$HATID" != "define" ]; then
      PRA=$(product_root_abs)
      if [ -n "$PRA" ] && [ -d "$PRA" ]; then
        PMD=$(find "$PRA" -name '*.md' -not -name 'CHANGELOG.md' 2>/dev/null)
        [ -n "$PMD" ] && check_defaulted warn $PMD
      fi
    fi
    RK=$(rank_of "$NHAT")
    if [ "$RK" -gt 2 ] && [ -d "$ROOT/01-define" ]; then
      DMD=$(find "$ROOT/01-define" -name '*.md' 2>/dev/null)
      [ -n "$DMD" ] && check_pending "禁止进入 ${HAT}" $DMD
    fi
    if [ "$RK" -gt 3 ] && [ -d "$ROOT/02-shape" ]; then
      SMD=$(find "$ROOT/02-shape" -name '*.md' 2>/dev/null)
      [ -n "$SMD" ] && check_pending "禁止进入 ${HAT}" $SMD
    fi
  fi

  # 发现带：仅当 state 写了 discovery: 才判（无该键 = 旧档，不红）
  if grep -qE '^discovery:' "$ST"; then
    DSTAT=$(awk '
      $0 ~ /^discovery:/ { in_d=1; next }
      in_d && /^[^[:space:]]/ { in_d=0 }
      in_d && /status:/ { sub(/.*status:[[:space:]]*/,""); gsub(/["'\'']/,""); print $1; exit }
    ' "$ST")
    LANE=$(grep -m1 -E "^lane:" "$ST" | grep -oE "L[0-4]")
    case "$LANE" in
      L2|L3|L4)
        case "$DSTAT" in
          pending|"")
            if [ "$NHAT" = "define" ] || [ "$(rank_of "$NHAT")" -ge 2 ]; then
              red NODISCOVER "$ST: L2+ discovery.status=${DSTAT:-empty} 禁止 define/其后（须 done|skipped）"
            fi
            ;;
          killed)
            # 发现阶段结论是「不做」：必须显式重开（discovery.reopened: {by, at, reason}）才能继续（P07）
            REOPENED=$(awk '$0 ~ /^discovery:/ { d=1; next } d && /^[^[:space:]]/ { d=0 } d && /reopened:/ { print "y"; exit }' "$ST")
            if [ -z "$REOPENED" ] && { [ "$NHAT" = "define" ] || [ "$(rank_of "$NHAT")" -ge 2 ]; }; then
              red NODISCOVER "$ST: discovery.status=killed（发现阶段结论是不做），define 及之后不得继续；确需继续由用户决定并记录 discovery.reopened: {by, at, reason}"
            fi
            ;;
          done)
            BR=$(find "$ROOT" -path '*00-discover/briefing.md' 2>/dev/null | head -1)
            [ -n "$BR" ] || BR="$ROOT/00-discover/briefing.md"
            if [ ! -f "$BR" ]; then
              red NODISCOVER "$ST: discovery.status=done 但无 00-discover/briefing.md"
            else
              grep -qE '^##[[:space:]]+Compete' "$BR" || red NOCOMPETE "$BR: 缺 ## Compete"
              grep -qE '^##[[:space:]]+Market' "$BR" || red NOMARKET "$BR: 缺 ## Market"
              grep -qE '^##[[:space:]]+Falsify' "$BR" || red NOFALSIFY "$BR: 缺 ## Falsify"
              grep -qE '现状|status quo|Status quo' "$BR" || red NOCOMPETE "$BR: Compete 未写现状"
              grep -qE '杀死' "$BR" || red NOFALSIFY "$BR: Falsify 未写杀死条件"
              if is_v4 && ! role_skipped growth; then
                grep -qE '^##[[:space:]]+Growth' "$BR" || red NOGROWTH "$BR: 缺 ## Growth（定位与亮点假设；roles_skipped 含 growth 可跳）"
              fi
            fi
            ;;
        esac
        ;;
    esac
  fi

  if grep -qE 'hats_done:.*(verify|验证)' "$ST"; then
    [ -n "$MET" ] || true
    COV2=$(find "$ROOT" -name "coverage.md" 2>/dev/null | head -1)
    [ -n "$COV2" ] || red MATRIXMISS "$ST: hats_done 含 verify/验证 但无 coverage.md（MATRIX 段不会跑；绿闸 ≠ FR 覆盖）"
  fi

  if grep -qE 'kind:[[:space:]]*fresh-context' "$ST"; then
    FIND=$(find "$ROOT" -name findings.md 2>/dev/null | head -1)
    [ -n "$FIND" ] || red FINDINGS "$ST: 已记 fresh-context 但无 findings.md（审查结论必须落盘）"
  fi

  # DIAGRAM：功能目录里的每张图都要过绘图闸门（来源声明、安全、svg-lint 零警告、与来源的语义比对）
  if is_v4; then
    SVGS=$(find "$ROOT" -path '*/assets/*.svg' -not -path '*/shots/*' 2>/dev/null | sort)
    if [ -n "$SVGS" ]; then
      DOUT=$(printf '%s\n' "$SVGS" | tr '\n' '\0' | xargs -0 python3 "$SCRIPT_DIR/diagram/lint.py" --root "$ROOT" 2>&1)
      DCODE=$?
      while IFS= read -r line; do
        case "$line" in *'✗ [DIAGRAM-'*) red DIAGRAM "${line#*] }" ;; esac
      done <<EOF
$DOUT
EOF
      [ "$DCODE" -eq 2 ] && ! printf '%s' "$DOUT" | grep -q '✗ \[DIAGRAM-' && red DIAGRAM "diagram check could not run: ${DOUT}"
    fi
  fi

  # v4 ACCEPT：任何验收结论「不通过」都挡住整棵树，直到重新验收
  if is_v4; then
    for af in "$ROOT"/04-verify/accept-*.md; do
      [ -f "$af" ] || continue
      case "$(verdict_of "$af")" in
        不通过) red ACCEPT "$af: 验收不通过未关闭（返工 implement → 重跑 verify → 重新验收）" ;;
        歧义) red ACCEPT "$af: 验收结论有歧义（多个不同的「结论：」）" ;;
      esac
    done
    if grep -qE 'hats_done:.*accept' "$ST"; then
      [ -f "$ROOT/${ART_accept_pm}" ] || red ACCEPTMISS "$ST: hats_done 含 accept 但无 04-verify/accept-pm.md"
    fi
  fi

  # HOSTSPAWN：禁止同一文件写两次 host_spawn（后者覆盖前者，常见于模板 host_spawn: {}）
  HSCOUNT=$(grep -cE '^host_spawn:' "$ST" 2>/dev/null) || HSCOUNT=0
  [ "${HSCOUNT:-0}" -gt 1 ] && red HOSTSPAWN "$ST: host_spawn 出现 ${HSCOUNT} 次（YAML 后者覆盖前者；禁止再写 host_spawn: {}）"

  # ROOTCAUSE：同帽第二轮返工须在证据或 gates 里有 root_cause: 一行（不判对错）
  RW=$(grep -m1 -E '^rework_rounds:' "$ST" | grep -oE '[0-9]+' | head -1)
  RW=${RW:-0}
  if [ "$RW" -ge 2 ]; then
    HAS_EV=0
    ls "$ROOT"/03-impl/*evidence*.md >/dev/null 2>&1 && HAS_EV=1
    if [ "$HAS_EV" = "1" ]; then
      grep -qE '^[[:space:]]*root_cause:' "$ST" "$ROOT"/03-impl/*evidence*.md 2>/dev/null \
        || red ROOTCAUSE "$ST: rework_rounds>=2 但证据/gates 无 root_cause: 一行"
    fi
  fi
fi

# ---------- extra_gates：仅当项目 sdlc.config.yaml 显式点名（默认不跑，避免无后端票假红） ----------
CFG=""
d="$ROOT"
i=0
while [ $i -lt 6 ]; do
  if [ -f "$d/sdlc.config.yaml" ]; then CFG="$d/sdlc.config.yaml"; break; fi
  nd=$(dirname "$d")
  [ "$nd" = "$d" ] && break
  d="$nd"
  i=$((i+1))
done
if [ -n "$CFG" ]; then
  EG=$(grep -A6 -E '^extra_gates:' "$CFG" 2>/dev/null || true)
  if printf '%s\n' "$EG" | grep -qE 'layering'; then
    LAYER_PY="$SCRIPT_DIR/../skills/impl-evidence/scripts/check-layering.py"
    LR=$(grep -m1 -E '^layering_root:' "$CFG" | sed -E 's/^layering_root:[[:space:]]*//; s/#.*$//; s/["'\'']//g')
    LR=${LR:-backend}
    LPATH="$d/$LR"
    if [ -e "$LPATH" ] && [ -f "$LAYER_PY" ] && command -v python3 >/dev/null 2>&1; then
      LOUT=$(python3 "$LAYER_PY" "$LPATH" 2>&1) || true
      while IFS= read -r line; do
        case "$line" in
          *'✗ [LAYER]'*) red LAYERING "$line" ;;
        esac
      done <<EOF
$LOUT
EOF
    fi
  fi
  if printf '%s\n' "$EG" | grep -qE 'explain'; then
    EXPLAIN_PY="$SCRIPT_DIR/../skills/schema/scripts/check-explain.py"
    EXFILE=$(find "$ROOT" -name '*explain*' 2>/dev/null | head -1)
    if [ -n "$EXFILE" ] && [ -f "$EXPLAIN_PY" ] && command -v python3 >/dev/null 2>&1; then
      XOUT=$(python3 "$EXPLAIN_PY" "$EXFILE" 2>&1)
      XCODE=$?  # 不能写成 $(...) || true 再读 $?：那样永远是 0（P09b）
      [ "$XCODE" -ne 0 ] && red EXPLAIN "$EXFILE: check-explain.py exit $XCODE"
    fi
  fi
fi

echo "----------------------------------------"
if [ $V -eq 0 ]; then grn "SDLC 工件合规通过"
else printf "\033[0;31m✗ [SDLC-SUMMARY] 共 %s 处违规\033[0m\n" "$V"
fi
exit $V

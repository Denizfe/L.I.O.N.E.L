#!/usr/bin/env bash
# scripts/verify_memory.sh — G2's two DoD clauses that no machine can check on its own.
#
#     compose down && up  ->  memory survives
#     semantic recall     ->  a dissimilar query retrieves the stored fact
#
# Both need a running Qdrant, and the second needs the pinned embedding model in a warm
# cache. Neither can be a CI test: ADR-0007's guarantee is that the ordinary path works
# with the cable pulled, and a suite that started containers by default would break it.
# So this is opt-in, announced before it acts, and it says which embedder it used in
# every line — a persistence proof with a fixture embedder is a true statement about the
# STORE and says nothing about retrieval quality.
#
# THIS IS NOT A GATE AND NEVER WILL BE, for the same reason check_env.sh is not: it
# describes a host with a Docker daemon, and CI is not the host runtime (ADR-0002).
#
# EXIT CODES ARE A CONTRACT
#     0  the clauses checked here passed
#     1  a clause failed, or a precondition is missing (Qdrant down, model uncached)
#     2  this script or its helper is broken
#
# IT STOPS AND STARTS A CONTAINER. `docker compose down` removes lionel-memory and its
# network; the named volume `lionel_qdrant_storage` is NOT removed, which is the whole
# point of the test. Nothing else on the host is touched.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -x "$ROOT/.venv/Scripts/python.exe" ]]; then
  PY="$ROOT/.venv/Scripts/python.exe"          # Git Bash on Windows
elif [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
else
  PY="python3"
fi

if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
  R=$'\033[31m'; G=$'\033[32m'; Y=$'\033[33m'; D=$'\033[2m'; B=$'\033[1m'; Z=$'\033[0m'
else
  R=""; G=""; Y=""; D=""; B=""; Z=""
fi

COLLECTION="lionel_persistence_check"
failures=0
skipped=0

row() { printf '  %s%-5s%s %-12s %-10s %s\n' "$2" "$1" "$Z" "$3" "$4" "$5"; }

# Full strict mode, and `if !` for every capture. `out="$(cmd)"` under `set -e` aborts the
# script when cmd exits non-zero, BEFORE the next line can look at the result -- which is
# how check_env.sh once made `skip`, `fail` and `broken` all unreachable and left `pass` as
# the only outcome it could report (section 9.13). Every helper call here can exit non-zero
# on a real failure, so every one is guarded. The exit code is then discarded deliberately:
# the verdict is the first TSV field, and two sources of truth for "did it pass" is how
# they come to disagree.
#
# stderr is DISCARDED and only the LAST line of stdout is parsed. The first run of this
# script reported `FAIL write` while the helper had in fact succeeded: fastembed writes
# download progress to stderr, `2>&1` folded it into the captured output, and every TSV
# field shifted by one -- the verdict became a progress bar while the payload beside it
# was plainly a success. A driver whose report depends on whether a library felt chatty is
# the same defect arriving from a new direction.
helper() {
  local out=""
  if ! out="$("$PY" "$ROOT/scripts/_memory_live.py" "$@" 2>/dev/null | tail -n 1)"; then
    :   # a non-zero exit is a verdict, not an abort. The verdict is inside `out`.
  fi
  printf '%s' "$out"
}

echo
echo "${B}== memory verification — G2's live clauses${Z}"
echo "${D}   Qdrant: http://127.0.0.1:6333    compose: docker-compose.yml${Z}"
echo
echo "${Y}This starts and stops the lionel-memory container. The named volume is kept.${Z}"
echo

# ── 1. Qdrant answering ────────────────────────────────────────────────────────
res="$(helper reachable)"
verdict="${res%%$'\t'*}"; detail="${res#*$'\t'}"
if [[ "$verdict" != "pass" ]]; then
  row "FAIL" "$R" "qdrant" "no answer" "$detail"
  echo
  echo "  ${D}Start it with:  docker compose up -d qdrant${Z}"
  echo
  exit 1
fi
row "ok" "$G" "qdrant" "reachable" "$detail"

# ── 2. which embedder ──────────────────────────────────────────────────────────
res="$(helper embedder)"
verdict="${res%%$'\t'*}"; detail="${res#*$'\t'}"
if [[ "$verdict" == "pass" ]]; then
  row "ok" "$G" "embedder" "real model" "$detail"
  REAL_MODEL=1
else
  row "skip" "$Y" "embedder" "fixture" "$detail"
  REAL_MODEL=0
  skipped=$((skipped + 1))
fi

# ── 3. write, restart, read ────────────────────────────────────────────────────
"$PY" "$ROOT/scripts/_memory_live.py" drop "$COLLECTION" >/dev/null 2>&1 || true

res="$(helper write "$COLLECTION")"
verdict="${res%%$'\t'*}"; payload="${res#*$'\t'}"
if [[ "$verdict" != "pass" ]]; then
  row "FAIL" "$R" "write" "failed" "$payload"
  exit 1
fi
RID="${payload%%$'\t'*}"; tail="${payload#*$'\t'}"
WHICH="${tail%%$'\t'*}"; COUNT="${tail#*$'\t'}"
row "ok" "$G" "write" "stored" "${D}${RID} · ${WHICH} · ${COUNT} point(s)${Z}"

echo
echo "  ${D}docker compose down${Z}"
docker compose down >/dev/null 2>&1 || { row "BRK" "$R" "compose" "down failed" ""; exit 2; }
echo "  ${D}docker compose up -d qdrant${Z}"
docker compose up -d qdrant >/dev/null 2>&1 || { row "BRK" "$R" "compose" "up failed" ""; exit 2; }

# Wait on a real query, not on `healthy`. The healthcheck is a TCP probe and the port
# accepts connections slightly before the collections are loaded — docker-compose.yml says
# so where the probe is defined.
ready=0
for _ in $(seq 1 30); do
  res="$(helper reachable)"
  if [[ "${res%%$'\t'*}" == "pass" ]]; then ready=1; break; fi
  sleep 1
done
if [[ $ready -ne 1 ]]; then
  row "FAIL" "$R" "restart" "never ready" "Qdrant did not answer within 30s of coming back up"
  exit 1
fi
row "ok" "$G" "restart" "back up" "${D}container recreated, volume kept${Z}"

res="$(helper read "$COLLECTION" "$RID")"
verdict="${res%%$'\t'*}"; payload="${res#*$'\t'}"
if [[ "$verdict" != "pass" ]]; then
  row "FAIL" "$R" "persistence" "LOST" "$payload"
  failures=$((failures + 1))
else
  COUNT="${payload##*$'\t'}"
  row "ok" "$G" "persistence" "survived" "${D}same id, same text, same trust · ${COUNT} point(s)${Z}"
fi

"$PY" "$ROOT/scripts/_memory_live.py" drop "$COLLECTION" >/dev/null 2>&1 || true

# ── 4. semantic recall — v1.0's clause, carried forward verbatim ───────────────
# "a dissimilar query retrieves the stored fact -- keyword matching must fail it".
# The helper refuses to run if the query shares a single word with the target, so the
# second half is enforced rather than assumed.
SEM="lionel_semantic_check"
"$PY" "$ROOT/scripts/_memory_live.py" drop "$SEM" >/dev/null 2>&1 || true
res="$(helper semantic "$SEM")"
verdict="${res%%$'\t'*}"; payload="${res#*$'\t'}"
case "$verdict" in
  pass) TR="${payload%%$'\t'*}"; WORDS="${payload#*$'\t'}"
        row "ok" "$G" "semantic" "retrieved" "${D}${WORDS}${Z}"
        if [[ "$TR" == "tr:hit" ]]; then
          row "note" "$D" "  turkish" "also hit" "${D}a Turkish query reached the English fact — not asserted; all-MiniLM-L6-v2 is an English model${Z}"
        else
          row "note" "$D" "  turkish" "missed" "${D}expected: all-MiniLM-L6-v2 is an English model. Recorded for G6c${Z}"
        fi ;;
  skip) row "skip" "$Y" "semantic" "not run" "$payload"; skipped=$((skipped + 1)) ;;
  broken) row "BRK" "$R" "semantic" "broken" "$payload"; exit 2 ;;
  *) row "FAIL" "$R" "semantic" "failed" "${payload:-$res}"; failures=$((failures + 1)) ;;
esac
"$PY" "$ROOT/scripts/_memory_live.py" drop "$SEM" >/dev/null 2>&1 || true

echo
if [[ $failures -gt 0 ]]; then
  echo "  ${R}${B}FAIL${Z}  $failures clause(s) did not hold."
  echo
  exit 1
fi
echo "  ${G}${B}PASS${Z}  memory survives \`compose down && up\`, and a dissimilar query finds it."
if [[ $REAL_MODEL -eq 0 ]]; then
  echo "  ${Y}note${Z}  a FIXTURE embedder was used. That proves the STORE persists and says"
  echo "        nothing about retrieval quality. The semantic-recall clause is NOT"
  echo "        verified by this run."
fi
echo
exit 0

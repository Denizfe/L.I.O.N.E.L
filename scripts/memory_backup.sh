#!/usr/bin/env bash
# scripts/memory_backup.sh — the memory has a second copy, and restoring it is exercised.
#
#     create           snapshot every configured collection into backups/qdrant/
#     list             what is in backups/qdrant/, with its checksum re-verified
#     restore <file>   put a snapshot back, over the live collection
#     selftest         a full round-trip through a scratch collection, touching no real data
#
# WHY THIS EXISTS
#   MASTER_PLAN_v1 §2.6 required `scripts/memory_backup.sh` and MASTER_PLAN_v2's
#   migration table has no row for it — neither retained nor deleted, simply absent.
#   Phase2_Final_Signoff.md §6 carries that as a Major with no mitigation: from the moment
#   G2 closes, the project's memory has exactly one copy, and a single
#   `docker compose down -v` ends it. ADR-0038 reinstates the item; this is it.
#
# THIS IS NOT A GATE AND NEVER WILL BE, for the same reason check_env.sh and
# verify_memory.sh are not: it describes a host with a Docker daemon and a running Qdrant,
# and CI is not the host runtime (ADR-0002). Nothing here runs in a workflow.
#
# EXIT CODES ARE A CONTRACT
#     0  the operation succeeded
#     1  it failed, or a precondition is missing (Qdrant down, no such file)
#     2  this script or its helper is broken
#
# WHAT IT WRITES, AND WHAT THAT MEANS
#   backups/qdrant/<collection>-<id>.snapshot plus a .sha256 beside it. `backups/` is
#   gitignored and MUST stay that way: a snapshot is a verbatim copy of everything the
#   assistant has ever been told, unencrypted, and ADR-0007's local-only guarantee is the
#   only thing protecting it. Do not sync this directory anywhere without an ADR saying
#   where. `tests/unit/test_memory_backup.py` asserts the ignore rule, because it is the
#   one property here that is a security property rather than a convenience.
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

DEST="$ROOT/backups/qdrant"
KEEP="${LIONEL_BACKUP_KEEP:-7}"
HELPER="$ROOT/scripts/_memory_snapshot.py"

row() { printf '  %s%-5s%s %-16s %-10s %s\n' "$2" "$1" "$Z" "$3" "$4" "$5"; }

# The scratch directory `selftest` works in. Global rather than `local`, because the EXIT
# trap that removes it runs after the function has returned, where a `local` no longer
# exists — under `set -u` that turned a passing selftest into `tmp: unbound variable` and a
# non-zero exit, which is a green run reporting itself as a failure.
SELFTEST_TMP=""

# Every capture is guarded with `if !`. Under `set -e` a bare `out="$(cmd)"` aborts the
# script before the next line can read the verdict — which is how check_env.sh once made
# `fail` unreachable and left `pass` as the only outcome it could report
# (Architecture_Freeze.md §9.13). The exit code is then discarded deliberately: the verdict
# is the first TSV field, and two sources of truth for "did it pass" is how they disagree.
#
# stderr is DISCARDED and only the LAST line of stdout is parsed, for the reason
# verify_memory.sh gives at the same place: a library that feels chatty on stderr shifts
# every TSV field by one, and the verdict becomes a progress bar.
helper() {
  local out=""
  if ! out="$("$PY" "$HELPER" "$@" 2>/dev/null | tail -n 1)"; then
    :
  fi
  printf '%s' "$out"
}

helper_all() {
  local out=""
  if ! out="$("$PY" "$HELPER" "$@" 2>/dev/null)"; then
    :
  fi
  printf '%s' "$out"
}

human() {
  local n="$1"
  if   [[ "$n" -ge 1073741824 ]]; then printf '%d.%d GB' $((n / 1073741824)) $(((n % 1073741824) * 10 / 1073741824))
  elif [[ "$n" -ge 1048576 ]];    then printf '%d.%d MB' $((n / 1048576))    $(((n % 1048576) * 10 / 1048576))
  elif [[ "$n" -ge 1024 ]];       then printf '%d.%d kB' $((n / 1024))       $(((n % 1024) * 10 / 1024))
  else                                 printf '%d B' "$n"
  fi
}

banner() {
  echo
  echo "${B}== memory backup — $1${Z}"
  echo "${D}   Qdrant: http://127.0.0.1:6333    into: backups/qdrant/    keep: ${KEEP}${Z}"
  echo
}

usage() {
  sed -n '2,9p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  echo
}

# -- create --------------------------------------------------------------------------
# Prunes to $KEEP per collection AFTER a successful write, never before: a retention
# policy that deletes the old copy first is a policy that loses everything on the one run
# where the new copy fails.
prune() {
  local collection="$1" n=0 f
  while IFS= read -r f; do
    n=$((n + 1))
    if [[ $n -gt $KEEP ]]; then
      rm -f -- "$f" "$f.sha256"
      row "prune" "$D" "$collection" "removed" "${D}$(basename "$f")${Z}"
    fi
  done < <(ls -1t "$DEST/$collection"-*.snapshot 2>/dev/null || true)
}

do_create() {
  banner "create"
  local listing verdict name points made=0
  listing="$(helper_all collections)"
  if [[ -z "$listing" ]]; then
    row "BRK" "$R" "helper" "no output" "$HELPER printed nothing"
    exit 2
  fi

  while IFS=$'\t' read -r verdict name points; do
    [[ -z "$verdict" ]] && continue
    case "$verdict" in
      pass)
        local res path digest bytes
        res="$(helper create "$name" "$DEST")"
        if [[ "${res%%$'\t'*}" != "pass" ]]; then
          row "FAIL" "$R" "$name" "no snapshot" "${res#*$'\t'}"
          exit 1
        fi
        res="${res#*$'\t'}"; path="${res%%$'\t'*}"
        res="${res#*$'\t'}"; digest="${res%%$'\t'*}"
        res="${res#*$'\t'}"; bytes="${res%%$'\t'*}"
        row "ok" "$G" "$name" "$(human "$bytes")" "${D}$(basename "$path") · ${points} point(s) · sha256:${digest:0:12}${Z}"
        prune "$name"
        made=$((made + 1))
        ;;
      skip)   row "skip" "$Y" "$name" "absent" "${D}${points}${Z}" ;;
      fail)   row "FAIL" "$R" "qdrant" "no answer" "$name"
              echo
              echo "  ${D}Start it with:  docker compose up -d qdrant${Z}"
              echo
              exit 1 ;;
      *)      row "BRK" "$R" "helper" "$verdict" "$name"; exit 2 ;;
    esac
  done <<< "$listing"

  echo
  if [[ $made -eq 0 ]]; then
    echo "  ${Y}${B}NONE${Z}  Qdrant is up and holds no configured collection yet. Nothing to back up."
    echo
    exit 0
  fi
  echo "  ${G}${B}PASS${Z}  ${made} collection(s) copied to backups/qdrant/, checksummed beside each file."
  echo "  ${D}Restoring is exercised by \`bash scripts/memory_backup.sh selftest\`, not assumed.${Z}"
  echo
}

# -- list ----------------------------------------------------------------------------
# Re-verifies each checksum rather than printing the sidecar back. An unverified list of
# backups tells you a file exists, which was never the question.
do_list() {
  banner "list"
  local f found=0 bad=0 recorded res actual bytes
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    found=$((found + 1))
    if [[ -f "$f.sha256" ]]; then
      recorded="$(cut -d' ' -f1 < "$f.sha256")"
      res="$(helper sha256 "$f")"
      if [[ "${res%%$'\t'*}" != "pass" ]]; then
        row "BRK" "$R" "sha256" "unreadable" "${res#*$'\t'}"
        exit 2
      fi
      res="${res#*$'\t'}"; actual="${res%%$'\t'*}"; bytes="${res#*$'\t'}"
      if [[ "$recorded" == "$actual" ]]; then
        row "ok" "$G" "snapshot" "$(human "$bytes")" "${D}$(basename "$f") · sha256 verified${Z}"
      else
        row "FAIL" "$R" "corrupt" "mismatch" "$(basename "$f")"
        bad=$((bad + 1))
      fi
    else
      row "warn" "$Y" "unverified" "no sha256" "$(basename "$f")"
      bad=$((bad + 1))
    fi
  done < <(ls -1t "$DEST"/*.snapshot 2>/dev/null || true)

  echo
  if [[ $found -eq 0 ]]; then
    echo "  ${Y}${B}EMPTY${Z}  no snapshots in backups/qdrant/. Run \`bash scripts/memory_backup.sh create\`."
    echo
    exit 1
  fi
  if [[ $bad -gt 0 ]]; then
    echo "  ${R}${B}FAIL${Z}  ${bad} of ${found} snapshot(s) could not be verified."
    echo
    exit 1
  fi
  echo "  ${G}${B}PASS${Z}  ${found} snapshot(s), every checksum re-computed and matching."
  echo
}

# -- restore -------------------------------------------------------------------------
# Destructive and says so. The collection name is derived from the filename rather than
# guessed, and can be overridden — restoring into a NEW name is how you inspect a backup
# without betting the live collection on it.
do_restore() {
  local file="${1:-}" collection="${2:-}" confirmed="${LIONEL_BACKUP_YES:-0}"
  if [[ -z "$file" ]]; then
    echo "  ${R}usage:${Z} bash scripts/memory_backup.sh restore <file.snapshot> [collection]"
    exit 2
  fi
  if [[ ! -f "$file" ]]; then
    echo "  ${R}no such file:${Z} $file"
    exit 1
  fi
  if [[ -z "$collection" ]]; then
    collection="$(basename "$file")"
    collection="${collection%%-*}"
  fi

  banner "restore"
  echo "  ${Y}This REPLACES the collection \`${collection}\` with the contents of${Z}"
  echo "  ${Y}$(basename "$file"). Anything stored since that snapshot is lost.${Z}"
  echo
  if [[ "$confirmed" != "1" ]]; then
    if [[ -t 0 ]]; then
      read -r -p "  Type the collection name to confirm: " answer
      if [[ "$answer" != "$collection" ]]; then
        echo "  ${D}not confirmed — nothing was changed${Z}"
        echo
        exit 1
      fi
    else
      echo "  ${R}refused:${Z} not a terminal and LIONEL_BACKUP_YES is not 1."
      echo "  ${D}An unattended restore over live memory needs to be asked for in as many words.${Z}"
      echo
      exit 1
    fi
  fi

  local before res
  before="$(helper points "$collection")"
  if [[ "${before%%$'\t'*}" == "pass" ]]; then
    row "note" "$D" "$collection" "holds" "${D}${before#*$'\t'} point(s) — about to be replaced${Z}"
  else
    row "note" "$D" "$collection" "absent" "${D}it will be created by the restore${Z}"
  fi

  res="$(helper restore "$collection" "$file")"
  if [[ "${res%%$'\t'*}" != "pass" ]]; then
    row "FAIL" "$R" "restore" "refused" "${res#*$'\t'}"
    echo
    exit 1
  fi
  row "ok" "$G" "$collection" "restored" "${D}${res#*$'\t'} point(s)${Z}"
  echo
  echo "  ${G}${B}PASS${Z}  \`${collection}\` now holds what the snapshot held."
  echo
}

# -- selftest ------------------------------------------------------------------------
# The clause that matters. A backup nobody has restored is a file, not a backup, and the
# first restore anybody tries is otherwise the one performed under pressure with the live
# collection already gone. This round-trips a REAL snapshot of a REAL collection into a
# scratch name, compares the point counts, and drops the scratch — so it exercises the
# restore path in full while betting nothing.
do_selftest() {
  banner "selftest"
  local listing verdict name points source="" expected=0
  listing="$(helper_all collections)"
  while IFS=$'\t' read -r verdict name points; do
    if [[ "$verdict" == "pass" && -z "$source" ]]; then source="$name"; expected="$points"; fi
    if [[ "$verdict" == "fail" ]]; then
      row "FAIL" "$R" "qdrant" "no answer" "$name"
      echo
      echo "  ${D}Start it with:  docker compose up -d qdrant${Z}"
      echo
      exit 1
    fi
  done <<< "$listing"

  if [[ -z "$source" ]]; then
    row "skip" "$Y" "selftest" "no data" "no configured collection exists yet — nothing to round-trip"
    echo
    exit 1
  fi
  row "ok" "$G" "source" "$source" "${D}${expected} point(s)${Z}"

  local scratch="lionel_restore_check" res path
  SELFTEST_TMP="$(mktemp -d)"
  trap 'rm -rf -- "${SELFTEST_TMP:-}"; "$PY" "$HELPER" drop lionel_restore_check >/dev/null 2>&1 || true' EXIT

  res="$(helper create "$source" "$SELFTEST_TMP")"
  if [[ "${res%%$'\t'*}" != "pass" ]]; then
    row "FAIL" "$R" "snapshot" "failed" "${res#*$'\t'}"
    exit 1
  fi
  res="${res#*$'\t'}"; path="${res%%$'\t'*}"
  row "ok" "$G" "snapshot" "taken" "${D}$(basename "$path")${Z}"

  "$PY" "$HELPER" drop "$scratch" >/dev/null 2>&1 || true
  res="$(helper restore "$scratch" "$path")"
  if [[ "${res%%$'\t'*}" != "pass" ]]; then
    row "FAIL" "$R" "restore" "refused" "${res#*$'\t'}"
    exit 1
  fi
  local restored="${res#*$'\t'}"
  if [[ "$restored" != "$expected" ]]; then
    row "FAIL" "$R" "round-trip" "count differs" "source held ${expected}, the restore holds ${restored}"
    exit 1
  fi

  # The count is the weak half. Two collections agree on it whenever the wrong snapshot
  # happens to be the same size, which is exactly the mistake a directory of dated files
  # invites. The digest is over the sorted point ids, so agreeing means holding the same
  # records rather than the same number of them.
  local d_src d_dst
  d_src="$(helper digest "$source")"
  d_dst="$(helper digest "$scratch")"
  if [[ "${d_src%%$'\t'*}" != "pass" || "${d_dst%%$'\t'*}" != "pass" ]]; then
    row "BRK" "$R" "digest" "unreadable" "${d_src} / ${d_dst}"
    exit 2
  fi
  d_src="${d_src#*$'\t'}"; d_src="${d_src%%$'\t'*}"
  d_dst="${d_dst#*$'\t'}"; d_dst="${d_dst%%$'\t'*}"
  if [[ "$d_src" != "$d_dst" ]]; then
    row "FAIL" "$R" "round-trip" "ids differ" "same count, different records — sha256:${d_src:0:12} vs sha256:${d_dst:0:12}"
    exit 1
  fi
  row "ok" "$G" "round-trip" "identical" "${D}${restored} point(s), same ids · sha256:${d_src:0:12} · scratch dropped${Z}"

  echo
  echo "  ${G}${B}PASS${Z}  a snapshot of \`${source}\` restores to the same records, not merely the same count."
  echo "  ${D}The live collection was never written to.${Z}"
  echo
}

case "${1:-create}" in
  create)   do_create ;;
  list)     do_list ;;
  restore)  shift; do_restore "$@" ;;
  selftest) do_selftest ;;
  -h|--help|help) usage ;;
  *) echo "  unknown command: ${1}"; usage; exit 2 ;;
esac
exit 0

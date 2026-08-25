#!/usr/bin/env bash
# scripts/check_env.sh — the host tooling preflight.
#
# MASTER_PLAN_v1 §1.1 is a six-row table a human was told to check by hand before
# Phase 1 began, and MASTER_PLAN_v2 Phase 1 carries it forward word for word:
# "the tooling preflight table, the Git Bash hazard rules". This runs it.
#
# WHY IT IS NOT A GATE
#     It describes the HOST, and CI is not the host runtime (ADR-0002). A gate that
#     went red because a laptop lacked VS Build Tools would be asserting something
#     about the wrong machine. So this is a script an operator runs, and its table
#     lives in ci/policy/policy.yaml under `preflight` — one registry, read here and
#     shape-checked by tests/unit/test_preflight.py, so the table cannot drift from
#     the thing that executes it.
#
# EXIT CODES — the same contract every gate obeys (CI_Architecture §4):
#     0   every tool required now is present and new enough
#     1   the ENVIRONMENT is wrong — something required is missing or too old
#     2   the PREFLIGHT is broken — policy.yaml is unreadable or has no table
#     Never collapse 1 and 2. "Install node" and "fix this script" are different jobs.
#
# OFFLINE BY DEFAULT
#     Nothing here touches the network unless --live is passed, and --live says so
#     before it starts. ADR-0007's guarantee is that the ordinary path works with the
#     cable pulled; a preflight that quietly dialled out would be the first thing to
#     break it.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

POLICY="ci/policy/policy.yaml"
LIVE=0
for arg in "$@"; do
  case "$arg" in
    --live) LIVE=1 ;;
    -h|--help)
      echo "usage: bash scripts/check_env.sh [--live]"
      echo "  --live   also run the checks that need the network or a credential"
      exit 0 ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
  G=$'\033[32m'; R=$'\033[31m'; Y=$'\033[33m'; D=$'\033[2m'; Z=$'\033[0m'
else
  G=""; R=""; Y=""; D=""; Z=""
fi

blocking_failures=0
later_missing=0

row() { printf '  %s%-5s%s %-10s %-12s %s\n' "$2" "$1" "$Z" "$3" "$4" "$5"; }

echo
echo "== preflight — host tooling for L.I.O.N.E.L"
echo "   table: $POLICY -> preflight    host: $(uname -s 2>/dev/null || echo unknown)"
echo

# ---- Phase 0: bootstrap, in pure bash ----------------------------------------
# Everything below needs python3 and pyyaml to read the table. That is not a
# circular dependency, it is the floor: these two ARE the minimum, so failing to
# find them is a real and complete answer rather than an inability to answer.
if ! command -v python3 >/dev/null 2>&1; then
  row "MISS" "$R" "python3" "-" "not on PATH. Every gate and script needs it."
  echo
  echo "  ${R}environment incomplete${Z} — install Python 3.11+ and re-run."
  echo "  On Windows do NOT rely on the bare interpreter name: it resolves to the"
  echo "  Microsoft Store stub, which exits 9009 and opens the Store instead"
  echo "  (MASTER_PLAN_v1 §2). Use python3, or let uv own the interpreter."
  exit 1
fi
if ! python3 -c 'import yaml' >/dev/null 2>&1; then
  row "MISS" "$R" "pyyaml" "-" "cannot read the table without it."
  echo
  echo "  ${R}environment incomplete${Z} — run \`uv sync --extra ci\` and re-run."
  exit 1
fi
if [[ ! -f "$POLICY" ]]; then
  echo "  ${R}BROKEN${Z}  $POLICY is missing; the preflight has no table to run."
  exit 2
fi

# ---- Phase 1: the tool table -------------------------------------------------
if ! TOOLS="$(python3 "$ROOT/scripts/_preflight_table.py" tools 2>/dev/null)"; then
  echo "  ${R}BROKEN${Z}  $POLICY has no usable \`preflight.tools\` table."
  echo "          This script and that section ship together; one without the other"
  echo "          is a preflight that cannot say what it is checking."
  exit 2
fi

echo "  ${D}tools${Z}"
while IFS=$'\t' read -r id minimum probe extract required_at why; do
  [[ -z "$id" ]] && continue
  out="$($probe 2>&1 || true)"
  found="$(printf '%s' "$out" | grep -oE "$extract" | head -1 || true)"

  if [[ -z "$found" ]]; then
    if [[ "$required_at" == "now" ]]; then
      row "MISS" "$R" "$id" ">= $minimum" "$why"
      blocking_failures=$((blocking_failures + 1))
    else
      row "later" "$Y" "$id" ">= $minimum" "needed at $required_at — $why"
      later_missing=$((later_missing + 1))
    fi
    continue
  fi

  if printf '%s\n%s\n' "$minimum" "$found" | sort -V -C; then
    row "ok" "$G" "$id" "$found" "$D>= $minimum$Z"
  elif [[ "$required_at" == "now" ]]; then
    row "OLD" "$R" "$id" "$found" "below the $minimum floor — $why"
    blocking_failures=$((blocking_failures + 1))
  else
    row "later" "$Y" "$id" "$found" "below $minimum, needed at $required_at"
    later_missing=$((later_missing + 1))
  fi
done <<< "$TOOLS"

# ---- Phase 2: the python packages the gates import ---------------------------
echo
echo "  ${D}Python packages${Z}"
PKGS="$(python3 "$ROOT/scripts/_preflight_table.py" packages)"
while IFS=$'\t' read -r mod dist required_at why; do
  [[ -z "$mod" ]] && continue
  if python3 -c "import $mod" >/dev/null 2>&1; then
    row "ok" "$G" "$dist" "importable" "$D$mod$Z"
  elif [[ "$required_at" == "now" ]]; then
    row "MISS" "$R" "$dist" "-" "$why"
    blocking_failures=$((blocking_failures + 1))
  else
    row "later" "$Y" "$dist" "-" "needed at $required_at"
    later_missing=$((later_missing + 1))
  fi
done <<< "$PKGS"

# ---- Phase 3: host paths the capability registry declares --------------------
# The filesystem capability is handed exactly one allowed root and cannot escape
# it. That root is an ABSOLUTE HOST PATH, so no gate and no portable test can say
# whether it exists — CI checks out somewhere else entirely. This is the only place
# the question can be asked, and asking it found the answer "no": the registry
# pointed at Desktop/L.I.O.N.E.L while the repository lived in Projects/.
echo
echo "  ${D}declared host paths${Z}"
ROOTS="$(python3 "$ROOT/scripts/_preflight_table.py" roots)"
if [[ -z "$ROOTS" ]]; then
  row "ok" "$G" "roots" "none" "${D}no capability declares a host path${Z}"
else
  here="$(pwd -W 2>/dev/null || pwd)"
  while IFS=$'\t' read -r name path; do
    [[ -z "$name" ]] && continue
    if [[ ! -d "$path" ]]; then
      row "MISS" "$R" "$name" "no such dir" "declared root does not exist: $path"
      blocking_failures=$((blocking_failures + 1))
    else
      there="$(cd "$path" && { pwd -W 2>/dev/null || pwd; })"
      if [[ "$there" != "$here" ]]; then
        row "WARN" "$Y" "$name" "elsewhere" "root is $path, not this checkout"
      else
        row "ok" "$G" "$name" "this repo" "${D}$path${Z}"
      fi
    fi
  done <<< "$ROOTS"
fi

# ---- Phase 4: the Git Bash hazard table --------------------------------------
# MASTER_PLAN_v1 §2 opens with: "These bite on every phase. Encoding them once here
# prevents four separate debugging sessions." They were encoded once, in prose, in a
# plan that was later superseded — and nobody opens a superseded plan while setting a
# machine up. Four of the seven are now gate rules; one is checked here; the last two
# describe what a person types at a terminal and can only be printed. So they are
# printed, at the one moment the operator can act on them.
echo
echo "  ${D}Git Bash hazards (MASTER_PLAN_v1 §2)${Z}"
while IFS=$'\t' read -r hid enforced rule; do
  [[ -z "$hid" ]] && continue
  case "$enforced" in
    operator)  row "read" "$Y" "$hid" "operator" "$rule" ;;
    check_env) : ;;   # executed below, reported there
    *)         row "gate" "$G" "$hid" "$enforced" "${D}enforced on every push${Z}" ;;
  esac
done <<< "$(python3 "$ROOT/scripts/_preflight_table.py" hazards)"

# HAZ-DOCKER-BACKEND, executed. `docker --version` answers about the CLI and says
# nothing about whether a daemon is running — this preflight reported a green Docker
# row on a machine where nothing could actually be launched.
backend="$(python3 "$ROOT/scripts/_preflight_table.py" docker-backend)"
case "${backend%%$'\t'*}" in
  wsl2)
    row "ok" "$G" "HAZ-DOCKER-BACKEND" "wsl2" "${D}${backend#*$'\t'}${Z}" ;;
  other)
    row "WARN" "$Y" "HAZ-DOCKER-BACKEND" "not wsl2" \
        "Hyper-V backend: unreliable bind-mount performance on the Qdrant volume at G2" ;;
  *)
    row "WARN" "$Y" "HAZ-DOCKER-BACKEND" "no daemon" \
        "docker CLI is installed but no daemon answers; nothing can be launched" ;;
esac

# ---- Phase 5: live checks, opt-in --------------------------------------------
echo
echo "  ${D}live checks${Z}"
if [[ "$LIVE" -eq 0 ]]; then
  python3 "$ROOT/scripts/_preflight_table.py" live
  echo "  ${D}re-run with --live to execute these. They reach the network.${Z}"
else
  echo "  ${Y}--live given: the two checks below WILL reach the network.${Z}"

  # Both handshakes run inside _preflight_table.py, not as a shell pipeline. The
  # pipeline version looked right and could not pass: `printf ... | server` closes
  # stdin the moment printf finishes, and a server that reads EOF as "the client
  # hung up" tears the session down before writing a byte of response. See the
  # MCPClient docstring — the GitHub check reported "no login" for every input,
  # including a valid credential.
  #
  # Each command prints one TAB-separated line: <verdict>\t<detail>.
  #   pass    the clause is satisfied
  #   fail    it is not, and the detail says which half
  #   skip    it could not be attempted, and the detail says what to do
  #   broken  the check itself could not run — exit 2, not 1
  live_check() {
    local label="$1" out verdict detail rc
    out="$(PYTHONPATH="$ROOT/src" python3 "$ROOT/scripts/_preflight_table.py" "$2" 2>&1)"
    rc=$?
    verdict="${out%%$'\t'*}"; detail="${out#*$'\t'}"
    case "$verdict" in
      pass)   row "ok"   "$G" "$label" "verified" "${D}${detail}${Z}" ;;
      skip)   row "skip" "$Y" "$label" "not run"  "$detail" ;;
      broken) row "BRK"  "$R" "$label" "broken"   "$detail"; exit 2 ;;
      *)      row "FAIL" "$R" "$label" "failed"   "${detail:-$out}"
              blocking_failures=$((blocking_failures + 1)) ;;
    esac
    return 0
  }

  live_check "filesystem" live-filesystem

  # "Start Docker Desktop" and "issue a new token" are different jobs, so the
  # daemon is checked first rather than letting a dead daemon surface as a
  # credential failure.
  if [[ "${backend%%$'\t'*}" == "unreachable" ]]; then
    row "skip" "$Y" "github" "not run" "no Docker daemon — start Docker Desktop and re-run"
  else
    live_check "github" live-github
  fi
fi

# ---- Verdict -----------------------------------------------------------------
echo
if [[ "$blocking_failures" -gt 0 ]]; then
  echo "  ${R}FAIL${Z}  $blocking_failures required item(s) missing. The environment is not ready."
  exit 1
fi
if [[ "$later_missing" -gt 0 ]]; then
  echo "  ${G}PASS${Z}  everything required now is present."
  echo "  ${Y}note${Z}  $later_missing item(s) are needed at a later gate, not yet."
else
  echo "  ${G}PASS${Z}  every row in the preflight table is satisfied."
fi
exit 0

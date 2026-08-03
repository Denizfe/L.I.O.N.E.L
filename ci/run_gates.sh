#!/usr/bin/env bash
# ci/run_gates.sh — run one gate, or all of them.
#
#   bash ci/run_gates.sh              # every gate, summary at the end
#   bash ci/run_gates.sh architecture # one gate
#   bash ci/run_gates.sh --list
#
# EXIT CODES  0 pass · 1 policy violation · 2 a gate itself is broken
# Every gate is standalone: `python3 ci/gates/gate_<name>.py` works on its own.
# No gate depends on another, so a failure never cascades into misleading noise.

# ci-policy: allow SH-STRICT — this runner MUST survive non-zero gate exits in order to
# collect a summary; `set -e` would abort on the first failing gate and hide the rest.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GATES="$HERE/gates"
export PYTHONPATH="$GATES:${PYTHONPATH:-}"

ORDER=(structure adr contracts jsonschema protobuf artifacts docker-digests
       no-latest no-pending no-todo secrets licenses markdown dependencies
       shell architecture l0-conformance)

name_to_file() { echo "$GATES/gate_$(echo "$1" | tr '-' '_').py"; }

if [[ "${1:-}" == "--list" ]]; then
  for g in "${ORDER[@]}"; do printf '  %-16s %s\n' "$g" "$(name_to_file "$g")"; done; exit 0
fi

run_one() {
  local f; f="$(name_to_file "$1")"
  [[ -f "$f" ]] || { echo "no such gate: $1"; return 2; }
  python3 "$f"
}

if [[ $# -ge 1 ]]; then run_one "$1"; exit $?; fi

declare -a PASSED=() FAILED=() BROKEN=()
for g in "${ORDER[@]}"; do
  run_one "$g"
  case $? in
    0) PASSED+=("$g") ;;
    1) FAILED+=("$g") ;;
    *) BROKEN+=("$g") ;;
  esac
done

echo "════════════════════════════════════════════════════════════"
echo "  CI POLICY SUMMARY"
echo "════════════════════════════════════════════════════════════"
printf '  passed     %2d  %s\n' "${#PASSED[@]}" "${PASSED[*]:-—}"
printf '  violations %2d  %s\n' "${#FAILED[@]}" "${FAILED[*]:-—}"
printf '  broken     %2d  %s\n' "${#BROKEN[@]}" "${BROKEN[*]:-—}"
echo
if (( ${#BROKEN[@]} )); then
  echo "  A gate could not run. That is a broken gate, not a passing repository."
  exit 2
fi
(( ${#FAILED[@]} )) && exit 1
exit 0

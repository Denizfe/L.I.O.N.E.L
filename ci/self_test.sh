#!/usr/bin/env bash
# ci/self_test.sh — do the gates actually catch anything?
#
# ci-policy: allow SH-STRICT — must survive non-zero exits from the gates it is
# deliberately provoking; `set -e` would abort on the first (expected) failure.
#
# A gate that passes a clean repository but would miss a real violation is decoration.
# This plants a known violation, asserts the matching gate rejects it, and restores.
# It is the only test that answers "is this pipeline load-bearing?"

set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export NO_COLOR=1 PYTHONPATH="$ROOT/ci/gates"

pass=0; fail=0
declare -a RESTORE=()
cleanup() { for c in "${RESTORE[@]}"; do eval "$c"; done; }
trap cleanup EXIT

# expect_violation <gate> <rule-substring> <description>
expect_violation() {
  local gate="$1" rule="$2" desc="$3"
  local out; out="$(python3 "ci/gates/gate_$(echo "$gate" | tr '-' '_').py" 2>&1)"
  local rc=$?
  if [[ $rc -eq 1 && "$out" == *"$rule"* ]]; then
    printf '  \033[32mok\033[0m    %-16s catches %s\n' "$gate" "$desc"; ((pass++))
  else
    printf '  \033[31mFAIL\033[0m  %-16s did NOT catch %s (exit %s)\n' "$gate" "$desc" "$rc"; ((fail++))
  fi
}

echo
echo "══ gate self-test — planting known violations"
echo

# 1. Secret scanning. AUD-C02 REMEDIATION:
#    The credential is GENERATED from sample_parts in policy.yaml and planted in a
#    TEMP TREE OUTSIDE THE REPOSITORY. No matching literal exists in any repo file,
#    so gate_secrets needs no path exclusion in order for this test to pass.
#    The gate is pointed at the temp tree with --root.
SECRET_TMP="$(mktemp -d)"
RESTORE+=("rm -rf '$SECRET_TMP'")
mkdir -p "$SECRET_TMP/config"
PYTHONPATH="$ROOT/ci/gates" python3 - "$SECRET_TMP/config/planted.yaml" <<'PYGEN'
import sys, yaml, pathlib
pol = yaml.safe_load(open(pathlib.Path(__file__).parent / "ci/policy/policy.yaml")) \
      if False else yaml.safe_load(open("ci/policy/policy.yaml"))
aws = next(p for p in pol["secrets"]["patterns"] if p["id"] == "SEC-AWS")
pathlib.Path(sys.argv[1]).write_text("aws_key: " + "".join(aws["sample_parts"]) + "\n")
PYGEN
out="$(python3 ci/gates/gate_secrets.py --root "$SECRET_TMP" 2>&1)"; rc=$?
if [[ $rc -eq 1 && "$out" == *"SEC-AWS"* ]]; then
  printf '  \033[32mok\033[0m    %-16s catches %s\n' "secrets" "a generated AWS key (planted outside the repo)"; ((pass++))
else
  printf '  \033[31mFAIL\033[0m  %-16s did NOT catch %s (exit %s)\n' "secrets" "a generated AWS key" "$rc"; ((fail++))
fi
rm -rf "$SECRET_TMP"

# 1b. The regexes themselves must be exercised, not merely present.
out="$(python3 ci/gates/gate_secrets.py --verify-patterns-only 2>&1)"; rc=$?
if [[ $rc -eq 0 && "$out" == *"pattern self-tests"* ]]; then
  printf '  \033[32mok\033[0m    %-16s %s\n' "secrets" "regex self-test: every pattern matches its sample and rejects its near-miss"; ((pass++))
else
  printf '  \033[31mFAIL\033[0m  %-16s regex self-test failed (exit %s)\n' "secrets" "$rc"; ((fail++))
fi

# 2. Mutable image tags.
printf 'image: qdrant/qdrant:latest\n' > config/_selftest.yaml
RESTORE+=("rm -f '$ROOT/config/_selftest.yaml'")
expect_violation no-latest "DOCKER-002" "a :latest tag"
rm -f config/_selftest.yaml

# 3. Placeholder pins.
printf 'sha256: PENDING\n' > config/_selftest.yaml
expect_violation no-pending "PLACEHOLDER-001" "a PENDING placeholder"
rm -f config/_selftest.yaml

# 4. ADR-0011: the shell capability must never come back.
mkdir -p src/lionel/capabilities/shell
RESTORE+=("rmdir '$ROOT/src/lionel/capabilities/shell' 2>/dev/null || true")
expect_violation architecture "ARCH-001" "a resurrected shell capability"
rmdir src/lionel/capabilities/shell

# 5. Phase 0 forbids runtime code.
printf 'x = 1\n' > src/lionel/_selftest.py
RESTORE+=("rm -f '$ROOT/src/lionel/_selftest.py'")
expect_violation structure "STRUCT-004" "runtime code during Phase 0"
rm -f src/lionel/_selftest.py

# 6. Unregistered TODO.
printf '# TODO: unregistered\n' > scripts/_selftest.sh
RESTORE+=("rm -f '$ROOT/scripts/_selftest.sh'")
expect_violation no-todo "TODO-001" "an unregistered TODO"
rm -f scripts/_selftest.sh

# 7. Shell strict mode.
printf '#!/usr/bin/env bash\necho hi\n' > scripts/_selftest.sh
expect_violation shell "SH-STRICT" "a script without strict mode"
rm -f scripts/_selftest.sh

# 8. Broken internal doc link.
printf '# t\n\n[x](does-not-exist.md)\n' > docs/_selftest.md
RESTORE+=("rm -f '$ROOT/docs/_selftest.md'")
expect_violation markdown "MD-LINK" "a broken internal link"
rm -f docs/_selftest.md

# Cleanup must be verified, not assumed. A self-test that leaves its planted
# violations behind turns every subsequent run red for the wrong reason — and the
# first person to see it will "fix" the gate rather than the litter.
leftover=0
for f in config/_selftest.toml config/_selftest.yaml src/lionel/_selftest.py \
         scripts/_selftest.sh docs/_selftest.md; do
  [[ -e "$f" ]] && { printf '  \033[31mFAIL\033[0m  self-test litter not removed: %s\n' "$f"; leftover=1; }
done
[[ -d src/lionel/capabilities/shell ]] && { echo "  FAIL  self-test litter: src/lionel/capabilities/shell"; leftover=1; }
(( leftover )) && { echo; echo "  Planted files survived cleanup. Remove them before re-running."; exit 1; }

echo
if (( fail )); then
  printf '  \033[31mSELF-TEST FAIL\033[0m  %d/%d gates did not catch their planted violation\n\n' "$fail" "$((pass+fail))"
  echo "  A gate that cannot catch a violation is decoration. Fix the gate."
  exit 1
fi
printf '  \033[32mSELF-TEST PASS\033[0m  %d/%d planted violations caught\n\n' "$pass" "$pass"

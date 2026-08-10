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

# Five of the plants below go into files that ARE the architecture (Architecture_Freeze.md
# §2). Each restores itself, but "restores itself" is a claim, and this suite exists
# because claims about tests are worth less than tests. Snapshot the checksum now and
# assert it at the end: if any plant survives, the number moves.
arch_checksum() { python3 scripts/architecture_checksum.py 2>/dev/null | grep -oE 'sha256:[0-9a-f]{64}' | head -1; }
CHECKSUM_BEFORE="$(arch_checksum)"
cleanup() { for c in "${RESTORE[@]}"; do eval "$c"; done; }
trap cleanup EXIT

# plant_in <path> — back a file up byte-exactly before planting in it, and register the
# restore. Use for any file that must come back unchanged, and ALWAYS for the five paths
# inside the architecture checksum set (docs/decisions/ADR-*.md, contracts/**,
# config/**/*.toml, config/*.json, ci/policy/policy.yaml, artifacts.lock.yaml). A plant
# left behind there does not merely litter — it moves the architecture checksum, and the
# next reader sees an unexplained architecture change rather than a broken test.
# Echoes the backup path; pass it to `unplant`.
plant_in() {
  local f="$1" b; b="$(mktemp)"
  cp "$f" "$b"
  RESTORE+=("[[ -f '$b' ]] && cp '$b' '$ROOT/$f'; rm -f '$b'")
  printf '%s' "$b"
}
unplant() { cp "$2" "$1"; rm -f "$2"; }

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
# selftest-covers: secrets — asserted by hand rather than through expect_violation,
# because the credential is GENERATED and planted OUTSIDE the repository and the gate is
# pointed at it with --root. gate-coverage reads this pragma; see its module docstring.
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

# 9. L0 offline conformance — the keystone gate. Finding M1: it enforces 8 invariants
#    and 18 rules and had no standing regression protection, so a change could silently
#    disarm the autonomy guarantee (ADR-0007) and every run would stay green.
#
#    Unlike the tests above, this one mutates a file that is IN the architecture
#    checksum set (config/**/*.toml). It is restored from a byte-exact backup and the
#    restoration is verified below — a self-test that leaves this file altered would
#    move the architecture checksum and read as an unexplained architecture change.
L0_CFG="config/tiers/l0.toml"
L0_BAK="$(mktemp)"
cp "$L0_CFG" "$L0_BAK"
# Guarded: the happy path restores and deletes the backup below, so by the time the
# EXIT trap runs there is normally nothing left to do. This entry exists for the path
# where the script dies mid-test with the violation still planted.
RESTORE+=("[[ -f '$L0_BAK' ]] && cp '$L0_BAK' '$ROOT/$L0_CFG'; rm -f '$L0_BAK'")
sed -i 's/^network_allowed = false/network_allowed = true/' "$L0_CFG"
if ! grep -q '^network_allowed = true' "$L0_CFG"; then
  printf '  \033[31mFAIL\033[0m  %-16s could not plant the violation (l0.toml changed shape?)\n' "l0-conformance"
  ((fail++))
else
  expect_violation l0-conformance "L0-OFFLINE-002" "L0 declaring network_allowed = true"
fi
cp "$L0_BAK" "$L0_CFG"; rm -f "$L0_BAK"

# ── 10–17: the eight gates that had never rejected anything ────────────────────────
# At the 1.0.0 freeze the suite covered 9 of 17 gates. CI_Architecture.md §7 step 6 has
# always said a gate that has never rejected anything is unproven; nothing enforced it,
# so eight gates went unproven for the whole of Phase 0. `gate-coverage` now enforces it,
# and these are the assertions that satisfy it.

# 10. The ADR set is complete and contiguous.
cat > docs/decisions/ADR-9999-selftest.md <<'ADRX'
# ADR-9999: self-test plant

| | |
|---|---|
| Status | **Accepted** |
ADRX
RESTORE+=("rm -f '$ROOT/docs/decisions/ADR-9999-selftest.md'")
expect_violation adr "ADR-001" "an ADR count that no longer matches policy"
rm -f docs/decisions/ADR-9999-selftest.md

# 11. Contract metadata. Every schema declares who owns it and what plane it is on;
#     without that a contract has no reviewer and no blast radius.
cat > contracts/core/v1/_selftest.schema.json <<'SCHEMA'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://lionel.local/schemas/core/v1/_selftest.schema.json",
  "title": "selftest",
  "type": "object"
}
SCHEMA
RESTORE+=("rm -f '$ROOT/contracts/core/v1/_selftest.schema.json'")
expect_violation contracts "CONTRACT-001" "a contract with no x-lionel block"
rm -f contracts/core/v1/_selftest.schema.json

# 12. Examples must satisfy the schema they illustrate. An example that does not is the
#     one a consumer copies.
cat > contracts/core/v1/_selftest.schema.json <<'SCHEMA'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://lionel.local/schemas/core/v1/_selftest.schema.json",
  "title": "selftest",
  "type": "object",
  "required": ["a"],
  "properties": { "a": { "type": "string" } },
  "examples": [ { "a": 123 } ],
  "x-lionel": {
    "version": "1.0.0", "adr": "ADR-0027", "stability": "provisional",
    "plane": "internal", "owner": "platform", "producer": "platform",
    "consumers": ["platform"],
    "compatibility": { "since": "1.0.0", "breaking_changes": [], "notes": "self-test plant" }
  }
}
SCHEMA
expect_violation jsonschema "JSON-004" "an example that fails its own schema"
rm -f contracts/core/v1/_selftest.schema.json

# 13. Protobuf must compile. A .proto that does not is a data plane that does not exist.
cat > contracts/grpc/v1/_selftest.proto <<'PROTO'
syntax = "proto3";
package lionel.selftest.v1;
message Broken { string a = ; }
PROTO
RESTORE+=("rm -f '$ROOT/contracts/grpc/v1/_selftest.proto'")
expect_violation protobuf "PROTO-001" "a .proto that does not compile"
rm -f contracts/grpc/v1/_selftest.proto

# 14. Unresolved artifacts block the gate (ADR-0013). This one mutates a checksum-set
#     file — see plant_in.
ART_BAK="$(plant_in artifacts.lock.yaml)"
sed -i '0,/status: RESOLVED/s//status: UNRESOLVED/' artifacts.lock.yaml
expect_violation artifacts "ART-000" "an unresolved artifact in the lockfile"
unplant artifacts.lock.yaml "$ART_BAK"

# 15. Image references in runnable config must be digest-pinned, not merely non-`:latest`.
#     A specific tag still points wherever the registry decides tomorrow.
printf 'image: qdrant/qdrant:v1.9.0\n' > config/_selftest.yaml
expect_violation docker-digests "DOCKER-006" "a tagged image with no digest"
rm -f config/_selftest.yaml

# 16. An unrecognised licence has not been assessed, and unassessed is not permissive.
LIC_BAK="$(plant_in artifacts.lock.yaml)"
sed -i '0,/^    license: MIT$/s//    license: Frobnicate-9.9/' artifacts.lock.yaml
expect_violation licenses "LIC-004" "a licence that is on no allowlist"
unplant artifacts.lock.yaml "$LIC_BAK"

# 17. Unbounded dependency (ADR-0013): a rebuild months later resolves a different tree.
DEP_BAK="$(plant_in pyproject.toml)"
sed -i 's|^dependencies = \[|dependencies = [\n    "unbounded-selftest-package",|' pyproject.toml
expect_violation dependencies "DEP-001" "a dependency with no version bound"
unplant pyproject.toml "$DEP_BAK"

# ── 18–20: the meta-gates (ADR-0030) ───────────────────────────────────────────────
# These check the pipeline rather than the repository, so they are the ones most likely
# to be quietly wrong: nothing else in CI would notice.

# 18. Architecture checksum. `config/**/*.toml` is inside the checksum set, so a new file
#     there changes both the policy group's membership and the checksum. This is the
#     failure that went undetected for eight days when *.proto was unpinned in
#     .gitattributes and a Windows clone hashed CRLF.
printf 'selftest = true\n' > config/_selftest.toml
expect_violation checksum "CHECKSUM-001" "a change to the architecture checksum set"
rm -f config/_selftest.toml

# 19. Generated documents. Both say "regenerate rather than hand-edit"; this proves the
#     gate notices when someone does the opposite.
GEN_BAK="$(plant_in CI_Inventory.md)"
printf '\nhand-edited line the generator would never produce\n' >> CI_Inventory.md
expect_violation generated-docs "GEN-001" "a hand-edited generated document"
unplant CI_Inventory.md "$GEN_BAK"

# 20. Gate coverage itself. The plant goes into a COPY of this script: bash reads a script
#     incrementally as it executes, so editing the running file could change the behaviour
#     of the test doing the editing. The gate takes --suite for exactly this, the same way
#     gate_secrets takes --root.
# selftest-covers: gate-coverage — asserted inline against a doctored copy of this suite.
COV_TMP="$(mktemp -d)"
RESTORE+=("rm -rf '$COV_TMP'")
grep -v 'expect_violation structure' ci/self_test.sh > "$COV_TMP/self_test.sh"
out="$(python3 ci/gates/gate_gate_coverage.py --suite "$COV_TMP/self_test.sh" 2>&1)"; rc=$?
if [[ $rc -eq 1 && "$out" == *"COV-001"* && "$out" == *"structure"* ]]; then
  printf '  \033[32mok\033[0m    %-16s catches %s\n' "gate-coverage" "a gate whose planted violation was deleted"; ((pass++))
else
  printf '  \033[31mFAIL\033[0m  %-16s did NOT catch %s (exit %s)\n' "gate-coverage" "a deleted assertion" "$rc"; ((fail++))
fi
rm -rf "$COV_TMP"

# Cleanup must be verified, not assumed. A self-test that leaves its planted
# violations behind turns every subsequent run red for the wrong reason — and the
# first person to see it will "fix" the gate rather than the litter.
leftover=0
for f in config/_selftest.toml config/_selftest.yaml src/lionel/_selftest.py \
         scripts/_selftest.sh docs/_selftest.md \
         docs/decisions/ADR-9999-selftest.md \
         contracts/core/v1/_selftest.schema.json contracts/grpc/v1/_selftest.proto; do
  [[ -e "$f" ]] && { printf '  \033[31mFAIL\033[0m  self-test litter not removed: %s\n' "$f"; leftover=1; }
done
[[ -d src/lionel/capabilities/shell ]] && { echo "  FAIL  self-test litter: src/lionel/capabilities/shell"; leftover=1; }
grep -q '^network_allowed = false' config/tiers/l0.toml || {
  echo "  FAIL  config/tiers/l0.toml was not restored — L0 still reads network_allowed = true"; leftover=1; }
(( leftover )) && { echo; echo "  Planted files survived cleanup. Remove them before re-running."; exit 1; }

echo
if (( fail )); then
  printf '  \033[31mSELF-TEST FAIL\033[0m  %d/%d gates did not catch their planted violation\n\n' "$fail" "$((pass+fail))"
  echo "  A gate that cannot catch a violation is decoration. Fix the gate."
  exit 1
fi
# The suite must leave the architecture byte-identical. A plant that survives in the
# checksum set does not merely litter: it silently changes what Architecture_Freeze.md §2
# describes, and the next person to recompute sees an architecture change with no commit
# behind it. The litter check above lists files it knows about; this catches the ones it
# does not — including in-place edits, which leave no file to look for.
CHECKSUM_AFTER="$(arch_checksum)"
if [[ -n "$CHECKSUM_BEFORE" && "$CHECKSUM_BEFORE" != "$CHECKSUM_AFTER" ]]; then
  printf '  \033[31mSELF-TEST FAIL\033[0m  the suite changed the architecture checksum\n'
  printf '        before  %s\n        after   %s\n\n' "$CHECKSUM_BEFORE" "$CHECKSUM_AFTER"
  echo "  A plant inside the checksum set was not restored. Find it before trusting this run."
  exit 1
fi
printf '  \033[32mSELF-TEST PASS\033[0m  %d/%d planted violations caught\n' "$pass" "$pass"
printf '                    architecture checksum unchanged — %s\n\n' "${CHECKSUM_AFTER:-unavailable}"

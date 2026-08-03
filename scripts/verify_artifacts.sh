#!/usr/bin/env bash
# scripts/verify_artifacts.sh — convenience wrapper for the artifact policy gate.
#
# This script used to carry its own copy of the artifact rules. It no longer does.
# ci/gates/gate_artifacts.py is the single source of truth, and duplicating policy
# across two files is how the two quietly disagree — at which point neither can be
# trusted and the disagreement is discovered during an incident.
#
# Kept because `bash scripts/verify_artifacts.sh` is in muscle memory and referenced
# from ADR-0013 and Artifact_Verification_Report.md.
#
# EXIT CODES  0 pass · 1 policy violation · 2 the gate itself is broken

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$HERE/ci/run_gates.sh" artifacts

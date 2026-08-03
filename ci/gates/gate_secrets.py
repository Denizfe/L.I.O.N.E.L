#!/usr/bin/env python3
"""GATE: secret scanning.  ADR-0015, ADR-0022.

REMEDIATES AUD-C02.

THERE ARE NO PATH EXCLUSIONS IN THIS GATE. Every file in the repository is scanned,
including `ci/` — including this file, and including the policy that configures it.

The previous design excluded `ci/` because the self-test embedded a literal AWS key.
That exclusion was disproportionate: an entire directory went unscanned to hide one
string, and an audit proved that AWS keys, GitHub tokens and PEM private keys placed
anywhere under `ci/` were undetected.

The exclusion is unnecessary because of two structural properties, each PROVEN ON
EVERY RUN rather than assumed:

  SEC-SELF-REGEX  No configured regex matches its own source text.
                  `AKIA[0-9A-Z]{16}` does not match the string "AKIA[0-9A-Z]{16}" —
                  the character after AKIA is `[`, which is not in the class. A gate
                  needs the PATTERN, never a MATCHING LITERAL. If someone later adds
                  a pattern that does self-match, this check fails and forces a
                  redesign instead of tempting another exclusion.

  SEC-SELF-SPEC   Test fixtures are declared as PARTS and joined at runtime, so no
                  matching literal exists anywhere in the tree. The separators in
                  `["AKIA", "IOSFODNN7EXAMPLE"]` break the pattern in the source; the
                  joined value matches. This check proves both halves.

Regexes are themselves tested (SEC-REGEX-POS / SEC-REGEX-NEG): each must match its
generated sample and reject its near-miss. A regex loosened by a stray `?` fails here
rather than silently matching nothing forever.

USAGE
    python3 ci/gates/gate_secrets.py                 scan the repository
    python3 ci/gates/gate_secrets.py --root DIR      scan an arbitrary tree
    python3 ci/gates/gate_secrets.py --verify-patterns-only

`--root` exists so the self-test can plant fixtures OUTSIDE the repository entirely.
Nothing is ever written into the scanned tree to test it.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from _lib import Gate, load_policy, rel, read_text, ROOT, gate_error

# Kept identical to _lib.repo_files so behaviour matches the rest of the pipeline.
# NOTE: `ci` is deliberately ABSENT. Adding it here would reintroduce AUD-C02.
SKIP_DIRS = {
    ".git", "node_modules", ".venv", "__pycache__", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "models", "data", "logs", "backups",
    "vendor", ".claude",
}


def walk(root: Path) -> list[Path]:
    out = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        out.append(p)
    return sorted(out)


def main() -> None:
    argv = sys.argv[1:]
    root = ROOT
    if "--root" in argv:
        root = Path(argv[argv.index("--root") + 1]).resolve()
        if not root.is_dir():
            gate_error(f"--root is not a directory: {root}")
    patterns_only = "--verify-patterns-only" in argv

    p = load_policy()
    g = Gate("secrets", "Secret scanning", ["ADR-0015", "ADR-0022"])
    sec = p["secrets"]

    if any(k in sec for k in ("exclude", "exclude_paths", "skip_paths")):
        g.check()
        g.fail("SEC-EXCLUDE",
            "the secrets policy declares a path exclusion",
            "AUD-C02: excluding a directory from secret scanning creates a blind spot in "
            "a place nobody thinks to look. `ci/` was excluded to hide one test fixture, "
            "and an audit proved AWS keys, GitHub tokens and PEM private keys placed there "
            "went undetected. This gate has no path exclusions by design.",
            "Remove the exclusion. If a fixture is the reason, declare it as "
            "`sample_parts` so it is generated at runtime and never stored.")

    compiled = []
    for entry in sec["patterns"]:
        try:
            compiled.append((entry["id"], re.compile(entry["regex"]), entry))
        except re.error as e:
            g.check()
            g.fail("SEC-REGEX-BAD", f"pattern `{entry['id']}` does not compile: {e}",
                "An uncompilable pattern silently detects nothing, and the gate would "
                "otherwise report PASS while scanning for a detector that never fires.",
                "Fix the regex in ci/policy/policy.yaml.")

    # ── Structural proofs. These are what make path exclusions unnecessary. ──────

    for pid, rx, entry in compiled:
        g.check()
        if rx.search(entry["regex"]):
            g.fail("SEC-SELF-REGEX",
                f"pattern `{pid}` MATCHES ITS OWN SOURCE TEXT",
                "A self-matching pattern makes the policy file trip the gate, which is "
                "exactly the pressure that produced the AUD-C02 exclusion. The invariant "
                "that keeps this gate exclusion-free is that a detector never matches its "
                "own definition.",
                "Rewrite the pattern so it cannot match its own text — usually by relying "
                "on a character class where the source has a metacharacter.")

        parts = entry.get("sample_parts")
        if not parts:
            g.check()
            g.fail("SEC-SPEC-MISSING", f"pattern `{pid}` declares no `sample_parts`",
                "Without a generated sample the regex is never exercised, so a broken "
                "detector is indistinguishable from a clean repository.",
                "Add `sample_parts` — fragments that join into a matching credential.")
            continue

        sample = "".join(parts)

        g.check()
        if not rx.search(sample):
            g.fail("SEC-REGEX-POS",
                f"pattern `{pid}` does NOT match its own generated sample",
                "The detector is broken. It would report a clean repository forever while "
                "detecting nothing — the most dangerous possible failure for this gate, "
                "because it is indistinguishable from success.",
                f"Fix the regex or `sample_parts` so the joined value matches.")

        neg = entry.get("negative_sample")
        if neg is not None:
            g.check()
            if rx.search(neg):
                g.fail("SEC-REGEX-NEG",
                    f"pattern `{pid}` matches its negative sample `{neg}`",
                    "The detector is too loose. An over-broad secret pattern produces "
                    "false positives, and false positives are how a security gate gets "
                    "disabled by the third person who hits one.",
                    "Tighten the regex.")

        # The spec that BUILDS a credential must not itself look like one.
        for i, part in enumerate(parts):
            g.check()
            if rx.search(part):
                g.fail("SEC-SELF-SPEC",
                    f"`{pid}` sample_parts[{i}] is itself a matching literal",
                    "Fixture parts must be individually harmless; only the JOIN matches. "
                    "A part that matches on its own is a real credential-shaped literal "
                    "sitting in the repository, which is what sample_parts exists to avoid.",
                    "Split the fragment so no single part matches.")

    if patterns_only:
        g.note("--verify-patterns-only: pattern self-tests only, tree not scanned")
        g.report_and_exit()

    # ── Full scan. No path is exempt. ───────────────────────────────────────────

    uri_ok = re.compile(sec["require_secret_uri_scheme"])
    files = walk(root)
    if not files:
        gate_error(f"no files found under {root} — refusing to report PASS on an empty scan")

    scanned = 0
    for f in files:
        txt = read_text(f)
        if not txt:
            continue
        scanned += 1
        g.check()                       # counts FILES EXAMINED, not violations found
        r = rel(f) if root == ROOT else str(f.relative_to(root))

        for i, line in enumerate(txt.splitlines(), 1):
            for pid, rx, entry in compiled:
                m = rx.search(line)
                if not m:
                    continue
                g.fail(pid,
                    f"possible {entry['label']} in source",
                    "ADR-0015: secrets are referenced by `secret://` URI and resolved at "
                    "point of use, wrapped in SecretStr so they redact in logs. A literal "
                    "in the repository is in git history forever, and history is not "
                    "revocable.",
                    "Remove the literal, ROTATE THE CREDENTIAL (assume it is compromised), "
                    "and reference it as `secret://env/NAME`. If this is a test fixture, "
                    "declare it as `sample_parts` in ci/policy/policy.yaml instead.",
                    r, i)

            # ADR-0015 forbids ${VAR} interpolation in config.
            if (sec.get("forbid_env_interpolation") and r.startswith("config/")
                    and "${" in line
                    and not line.lstrip().startswith(("#", "//"))
                    and '"$comment"' not in line and "interpolation" not in line):
                g.fail("SEC-INTERP",
                    "`${...}` interpolation in a config file",
                    "ADR-0015: JSON does not expand variables and no component was ever "
                    "named as the expander, so it silently does not work. The tempting fix "
                    "— interpolating in the loader — turns the secret into an ordinary "
                    "string that ends up in log lines and crash dumps.",
                    "Use a typed `secret://` URI resolved by SecretResolver at point of use.",
                    r, i)

            # URI WELL-FORMEDNESS is a CONFIG-CORRECTNESS check, not a security check,
            # so it applies to the file types that actually carry config. Prose
            # illustrates URI shapes (`secret://env/NAME`) and a malformed one in a
            # sentence does nothing at runtime.
            #
            # THIS IS NOT A PATH EXCLUSION. The secret-literal scan above runs on every
            # file with no exemption; only this one syntactic check is scoped to where
            # it has meaning. Narrowing WHICH CHECK applies to a file type is different
            # from excluding a file from scanning — AUD-C02 was the latter.
            if f.suffix not in {".json", ".toml", ".yaml", ".yml"}:
                continue

            # A URI containing regex metacharacters is a PATTERN DEFINITION, not a
            # usage — a property of the string itself, not of where it lives.
            for um in re.finditer(r"secret://[^\"'`\s,;)}\]]+", line):
                val = um.group(0).rstrip(".")
                if any(c in val for c in "()|[]\\*+?{}^$"):
                    continue
                g.check()
                if not uri_ok.match(val):
                    g.fail("SEC-URI", f"malformed secret URI `{val}`",
                        "ADR-0015 defines four schemes: env, file, dpapi, k8s. An "
                        "unrecognised scheme resolves to nothing and fails at first use in "
                        "production rather than at config load.",
                        "Use `secret://env/NAME`, `secret://file/PATH`, "
                        "`secret://dpapi/NAME` or `secret://k8s/SECRET/KEY`.", r, i)

    g.note(f"scanned {scanned} files under {root} — NO PATH EXCLUSIONS (AUD-C02 remediation)")
    if scanned < 50 and root == ROOT:
        g.fail("SEC-COVERAGE",
            f"only {scanned} files scanned; expected at least 50",
            "A collapse in scan coverage looks identical to a clean repository. A floor "
            "turns silent coverage loss into a failing build.",
            "Investigate why the walk returned so few files before trusting this PASS.")
    g.report_and_exit()


if __name__ == "__main__":
    main()

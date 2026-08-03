#!/usr/bin/env python3
"""GATE: shell script policy.  ADR-0011, ADR-0014."""
import re
from _lib import Gate, load_policy, repo_files, rel, read_text

def main():
    p = load_policy(); g = Gate("shell", "Shell script policy", ["ADR-0011", "ADR-0014"])
    cfg = p["shell"]
    pats = [(x["id"], re.compile(x["regex"]), x["why"]) for x in cfg["forbid_patterns"]]

    # ci/self_test.sh deliberately writes non-strict scripts as fixtures.
    scripts = [f for f in repo_files(include={".sh"}) if not rel(f).startswith("ci/self_test")]
    if not scripts:
        g.note("no shell scripts found")

    for f in scripts:
        r, txt = rel(f), read_text(f)
        g.check()

        # Inline pragma: `# ci-policy: allow SH-STRICT — <reason>`. A reason is mandatory;
        # an exemption without one is a silently lowered standard.
        pragma = re.search(r"#\s*ci-policy:\s*allow\s+(\S+)\s+[—-]\s*(.+)", txt)
        if pragma:
            g.note(f"{r}: {pragma.group(1)} exempted — {pragma.group(2).strip()}")

        if cfg.get("require_strict_mode") and not (pragma and pragma.group(1) == "SH-STRICT"):
            # Scan the whole file: a long header comment can push `set -euo` well past
            # the first few lines, and a 15-line window produced false positives.
            if not re.search(r"^\s*set\s+-euo\s+pipefail", txt, re.M):
                g.fail("SH-STRICT",
                    "missing `set -euo pipefail`",
                    "Without -e a failing command is ignored and the script continues into an "
                    "inconsistent state; without -u a typo'd variable expands to empty and "
                    "silently does the wrong thing; without -o pipefail a failure mid-pipe is "
                    "masked by a successful tail.",
                    "Add `set -euo pipefail` near the top of the script.", r, 1)

        if cfg.get("require_lf_endings") and "\r\n" in txt:
            g.fail("SH-CRLF",
                "CRLF line endings",
                "A CRLF-terminated .sh fails on Linux with the cryptic `\\r: command not found`. "
                "This is the single most common Windows/Git Bash trap and .gitattributes exists "
                "to prevent it.",
                "Ensure `*.sh text eol=lf` in .gitattributes and re-checkout the file.", r)

        for i, line in enumerate(txt.splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            for pid, rx, why in pats:
                if rx.search(line):
                    g.fail(pid, f"forbidden shell pattern `{rx.pattern}`", why,
                        "Rewrite without it. If the intent is to fetch and run something, "
                        "download, verify a pinned checksum (ADR-0013), then execute.", r, i)

    # ADR-0011 is structural: no shell execution may exist in the capability surface.
    for f in repo_files(include={".py", ".json", ".yaml", ".toml"}):
        r = rel(f)
        if not (r.startswith("src/lionel/capabilities") or r.startswith("config/")):
            continue
        for i, line in enumerate(read_text(f).splitlines(), 1):
            if re.search(r"\b(shell=True|subprocess\.(call|run|Popen).*shell|os\.system|run_command)\b", line):
                g.check()
                g.fail("SH-ADR0011",
                    "shell execution in the capability surface",
                    "ADR-0011 abolished arbitrary shell execution. An allowlist gates the verb "
                    "and leaves the arguments open; with L.I.O.N.E.L reading untrusted documents, "
                    "injected text would become code execution on Efe's primary machine.",
                    "Express the capability as a typed tool over a closed set of values. If it "
                    "cannot be expressed that way, it does not become a tool.", r, i)
    g.check(1)
    g.report_and_exit()

if __name__ == "__main__": main()

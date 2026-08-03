#!/usr/bin/env python3
"""GATE: forbidden mutable image tags.  ADR-0013."""
import re, sys
from _lib import Gate, load_policy, repo_files, rel, read_text

def main():
    p = load_policy(); g = Gate("no-latest", "Forbidden mutable image tags", ["ADR-0013"])
    forbid = p["docker"]["forbid_tags"]
    # An image reference that also carries @sha256: is pinned; the tag is then advisory.
    ref = re.compile(r"([A-Za-z0-9._\-/]+):(" + "|".join(map(re.escape, forbid)) + r")\b")
    for f in repo_files(include={".yaml", ".yml", ".json", ".toml", ".sh", ".env", ""}):
        # .md excluded by design: gates police executable config, not prose that
        # documents a rejected practice (MASTER_PLAN_v2 §3 quotes `:latest`).
        # `ci/` excluded: gates and their self-test necessarily CONTAIN the strings
        # they hunt. Flagging them would invite weakening the pattern, which is how
        # a gate quietly stops catching real violations.
        if rel(f).startswith(("docs/", "ci/")):
            continue
        for i, line in enumerate(read_text(f).splitlines(), 1):
            for m in ref.finditer(line):
                if "@sha256:" in line:
                    continue
                if line.lstrip().startswith(("#", "//")):
                    continue
                g.check()
                g.fail("DOCKER-002",
                    f"mutable tag `:{m.group(2)}` on `{m.group(1)}`",
                    "ADR-0013: a tag is a movable pointer. `:latest` today and `:latest` next "
                    "month can be different images, so a build pinned by tag is not reproducible.",
                    f"Resolve the digest (`docker buildx imagetools inspect {m.group(1)}:<version>`) "
                    "and reference `@sha256:…`. Record it in artifacts.lock.yaml.",
                    rel(f), i)
    g.check(1)
    g.report_and_exit()

if __name__ == "__main__": main()

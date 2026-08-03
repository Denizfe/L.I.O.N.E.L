#!/usr/bin/env python3
"""GATE: every Docker image reference pinned by immutable digest.  ADR-0013."""
import re
from _lib import Gate, load_policy, repo_files, rel, read_text, ROOT, load_yaml

IMG = re.compile(r"\b((?:[a-z0-9\-.]+(?:\.[a-z]{2,}|:\d+)/)?[a-z0-9][a-z0-9._\-/]*)"
                 r"(?::([A-Za-z0-9._\-]+))?(@sha256:[0-9a-f]{64})?\b")
LIKELY = re.compile(r"(ghcr\.io/|docker\.io/|quay\.io/|qdrant/|ollama/|"
                    r"image:\s*|FROM\s+|imagetools inspect\s+)")

def main():
    p = load_policy(); g = Gate("docker-digests", "Docker image digest pinning", ["ADR-0013", "ADR-0020"])
    cfg = p["docker"]
    dig = re.compile(cfg["digest_pattern"])

    # 1. Every digest recorded anywhere must be well formed.
    # .md excluded: prose necessarily abbreviates digests (`sha256:0bd98fa7…5286`).
    # Gates police what runs; documentation about what runs is a different concern.
    for f in repo_files(include={".yaml", ".yml", ".json", ".toml", ".sh"}):
        for i, line in enumerate(read_text(f).splitlines(), 1):
            for m in re.finditer(r"sha256:[0-9a-zA-Z\-]+", line):
                g.check()
                if not dig.match(m.group(0)) and "UNRESOLVED" not in line:
                    g.fail("DOCKER-001", f"malformed digest `{m.group(0)}`",
                        "An OCI digest is sha256 followed by exactly 64 lowercase hex. Anything "
                        "else will not resolve and fails at pull time, in whatever environment "
                        "happens to run first.",
                        "Re-read the digest from `docker buildx imagetools inspect`.",
                        rel(f), i)

    # 2. Every image in the lockfile must carry a digest, or be an honest UNRESOLVED.
    lock = ROOT / "artifacts.lock.yaml"
    if lock.exists():
        d = load_yaml(lock)
        for name, img in (d.get("images") or {}).items():
            g.check()
            if img.get("status") == "RESOLVED":
                if not img.get("digest"):
                    g.fail("DOCKER-003", f"image `{name}` is RESOLVED without a digest",
                        "ADR-0013: only a digest is a pin. A tag is a movable pointer, so an "
                        "image referenced by tag is not reproducible.",
                        "Add `digest: sha256:…` from `docker buildx imagetools inspect`.",
                        "artifacts.lock.yaml")
                elif not dig.match(str(img["digest"])):
                    g.fail("DOCKER-004", f"image `{name}` digest malformed",
                        "Must be sha256:<64 lowercase hex>.", "Re-read the digest.",
                        "artifacts.lock.yaml")
                if img.get("pull_as") and "@sha256:" not in str(img["pull_as"]):
                    g.fail("DOCKER-005", f"image `{name}` `pull_as` is not digest-pinned",
                        "`pull_as` is what actually gets executed. Pinning the record but pulling "
                        "the tag makes the lockfile decorative.",
                        "Write `pull_as: repo@sha256:…`.", "artifacts.lock.yaml")
            elif img.get("status") == "UNRESOLVED":
                g.note(f"image `{name}` UNRESOLVED — owned by the artifacts gate, not this one.")

    # 3. Any image reference in runnable config must be digest-pinned.
    for f in repo_files(include={".yaml", ".yml", ".json", ".sh"}):
        r = rel(f)
        if not r.startswith(("config/", "deploy/", "scripts/", ".github/")):
            continue
        for i, line in enumerate(read_text(f).splitlines(), 1):
            if not LIKELY.search(line) or line.lstrip().startswith("#"):
                continue
            if "sha256:" in line or "UNRESOLVED" in line:
                continue
            for m in IMG.finditer(line):
                repo_, tag, digest = m.groups()
                if not tag or "/" not in repo_ or digest:
                    continue
                g.check()
                g.fail("DOCKER-006", f"image `{repo_}:{tag}` referenced without a digest",
                    "ADR-0013: tags are mutable. An image pulled by tag in CI or a manifest is "
                    "not the image that was reviewed.",
                    f"Pin it: `{repo_}@sha256:…` and record it in artifacts.lock.yaml.", r, i)
    g.check(1)
    g.report_and_exit()

if __name__ == "__main__": main()

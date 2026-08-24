"""ADR-0027 layer 2 — what the runtime launches is what the lockfile pinned. ADR-0013.

MASTER_PLAN_v2 §10, Gate G1: *"pinned GitHub MCP image digest verified."*

WHAT "VERIFIED" HAS TO MEAN HERE
    Not "a digest is present" — the gates already prove that. `docker-digests` fails any
    image reference without an `@sha256:`, and `artifacts` fails an unresolved lockfile
    entry. Both look at one file at a time.

    The failure neither can see is **disagreement between two files that are each
    internally valid**: `artifacts.lock.yaml` pins one digest, `config/capabilities.registry.json`
    launches another, and every gate stays green while the running system is not the
    reviewed system. That is what this checks.

    It is not hypothetical in shape. This repository has already had one defect of exactly
    that kind — the architecture checksum recorded in `Architecture_Freeze.md` §2 disagreed
    with what a clean clone computed for eight days, because nothing compared the two.

WHAT THIS DOES NOT DO
    It does not contact a registry. The digest's correspondence to a real image was
    established once, by hand, and recorded in `artifacts.lock.yaml` with the command that
    produced it — `docker buildx imagetools inspect`. Re-checking that in a test suite would
    need the network, and ADR-0007's guarantee would not survive a test suite that cannot
    run offline. Risk R-A16 ("fabricated hash undetected until Phase 6") is the accepted
    residue of that choice, and it is accepted with a reason rather than overlooked.
"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

DIGEST = re.compile(r"(?P<ref>[a-z0-9./-]+)@(?P<digest>sha256:[0-9a-f]{64})")


def _registry_images() -> dict[str, str]:
    """Every `ref@sha256:...` the capability registry would actually launch."""
    doc = json.loads((ROOT / "config" / "capabilities.registry.json").read_text(encoding="utf-8"))
    found: dict[str, str] = {}
    for name, spec in doc.get("capabilities", {}).items():
        for arg in spec.get("args", []) or []:
            m = DIGEST.fullmatch(str(arg))
            if m:
                found[m.group("ref")] = m.group("digest")
    return found


@unittest.skipIf(yaml is None, "pyyaml not installed (pyproject `ci` extra)")
class TestPinnedImages(unittest.TestCase):
    def setUp(self):
        self.lock = yaml.safe_load((ROOT / "artifacts.lock.yaml").read_text(encoding="utf-8"))
        self.registry_images = _registry_images()

    def _lock_entries(self):
        """Lockfile entries carrying a `ref` and a `digest`, whatever the section shape."""
        out = {}

        def walk(node):
            if isinstance(node, dict):
                ref, digest = node.get("ref"), node.get("digest")
                if isinstance(ref, str) and isinstance(digest, str) and digest.startswith("sha256:"):
                    out[ref] = digest
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(self.lock)
        return out

    def test_the_registry_launches_at_least_one_pinned_image(self):
        """Guards against the test passing because it found nothing to compare."""
        self.assertTrue(self.registry_images,
                        "no digest-pinned image found in the capability registry; this test "
                        "would otherwise pass by having nothing to check")

    def test_github_mcp_is_pinned_and_matches_the_lockfile(self):
        """The G1 DoD clause."""
        ref = "ghcr.io/github/github-mcp-server"
        self.assertIn(ref, self.registry_images,
                      "the github capability does not launch a digest-pinned image")
        locked = self._lock_entries()
        self.assertIn(ref, locked, f"{ref} is not in artifacts.lock.yaml")
        self.assertEqual(
            self.registry_images[ref], locked[ref],
            f"{ref}: the registry launches {self.registry_images[ref]} but the lockfile "
            f"pins {locked[ref]}. Both files are internally valid and every gate stays "
            f"green, which is exactly why this is the check that has to exist.")

    def test_every_registry_image_agrees_with_the_lockfile(self):
        locked = self._lock_entries()
        for ref, digest in self.registry_images.items():
            with self.subTest(image=ref):
                self.assertIn(ref, locked,
                              f"{ref} is launched but never pinned in artifacts.lock.yaml "
                              f"(ADR-0013)")
                self.assertEqual(digest, locked[ref])

    def test_pull_as_agrees_with_ref_and_digest(self):
        """`pull_as` is a convenience field, and a convenience field that drifts is a trap."""
        def walk(node):
            if isinstance(node, dict):
                pull_as = node.get("pull_as")
                ref, digest = node.get("ref"), node.get("digest")
                if isinstance(pull_as, str) and isinstance(ref, str) and isinstance(digest, str):
                    self.assertEqual(pull_as, f"{ref}@{digest}",
                                     f"pull_as does not match ref@digest for {ref}")
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(self.lock)


if __name__ == "__main__":
    unittest.main()

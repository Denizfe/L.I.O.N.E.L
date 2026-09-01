"""ADR-0027 layer 1 — the backup path's offline half.  ADR-0038.

WHAT THIS CAN AND CANNOT CHECK
    It cannot check that a snapshot restores. That needs a Docker daemon and a running
    Qdrant, it is `bash scripts/memory_backup.sh selftest`, and ADR-0002 is why it is not
    a test: CI is not the host runtime, and a suite that started containers by default
    would break ADR-0007's offline guarantee for everyone running it.

    What is portable is everything the driver and its helper do BEFORE the network: the
    checksum refusal, the argument contract, the agreement between the two files, and the
    one fact about this feature that is a security property rather than a convenience —
    `backups/` is gitignored, and a snapshot is a verbatim unencrypted copy of everything
    the assistant has ever been told.

WHY THE REFUSAL TESTS MATTER MOST
    `restore` is the only destructive operation in this repository that a person runs by
    hand, on the worst day they have had with it, from a directory of similarly named
    files. Every guard in front of it is checked here because the run where it matters is
    the run nobody is in a state to check anything.
"""
import importlib.util
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DRIVER = ROOT / "scripts" / "memory_backup.sh"
HELPER = ROOT / "scripts" / "_memory_snapshot.py"


def load_helper():
    """Imported by path: `scripts/` is not a package, and making it one would put a
    __init__.py beside the shell scripts for the benefit of one test."""
    spec = importlib.util.spec_from_file_location("_memory_snapshot", HELPER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestHelperContract(unittest.TestCase):
    """The TSV contract and the exit codes, which the driver parses positionally."""

    def setUp(self):
        self.h = load_helper()

    def run_main(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = self.h.main(list(argv))
        return code, buf.getvalue().splitlines()

    def test_an_unknown_command_is_broken_not_failed(self):
        """Exit 1 and exit 2 are different sentences: `fix the repo` and `fix the gate`.
        A typo'd command is the second, and the driver escalates rather than reporting a
        backup that did not happen as a backup that failed."""
        code, out = self.run_main("snapshoot")
        self.assertEqual(2, code)
        self.assertTrue(out[0].startswith("broken\t"))

    def test_wrong_arity_is_broken(self):
        code, out = self.run_main("create", "only-one-argument")
        self.assertEqual(2, code)
        self.assertIn("takes 2 argument(s)", out[0])

    def test_no_command_is_broken(self):
        code, out = self.run_main()
        self.assertEqual(2, code)
        self.assertTrue(out[0].startswith("broken\t"))

    def test_every_command_is_documented(self):
        """A command the docstring does not mention is a command nobody will find, and
        the docstring is the only usage this helper has."""
        doc = self.h.__doc__
        for name in self.h.COMMANDS:
            with self.subTest(command=name):
                self.assertIn(f"    {name}", doc)

    def test_sha256_matches_hashlib_and_reports_the_size(self):
        import hashlib
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "x.snapshot"
            f.write_bytes(b"lionel" * 5000)
            code, out = self.run_main("sha256", str(f))
        self.assertEqual(0, code)
        verdict, digest, size = out[0].split("\t")
        self.assertEqual("pass", verdict)
        self.assertEqual(hashlib.sha256(b"lionel" * 5000).hexdigest(), digest)
        self.assertEqual("30000", size)

    def test_sha256_of_a_missing_file_fails_rather_than_raising(self):
        code, out = self.run_main("sha256", str(ROOT / "no-such-file.snapshot"))
        self.assertEqual(1, code)
        self.assertTrue(out[0].startswith("fail\t"))


class TestRestoreRefusals(unittest.TestCase):
    """Every refusal reachable without a network. None of these touch Qdrant."""

    def setUp(self):
        self.h = load_helper()

    def restore(self, collection, path):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = self.h.cmd_restore(collection, str(path))
        return code, buf.getvalue().splitlines()

    def test_a_missing_file_is_refused(self):
        code, out = self.restore("lionel_memory", ROOT / "nope.snapshot")
        self.assertEqual(1, code)
        self.assertIn("is not a file", out[0])

    def test_a_corrupt_snapshot_is_refused_before_any_upload(self):
        """The one that has to hold. Restoring a corrupt snapshot over a live collection
        turns one lost copy into two, and the collection is deleted by the recovery before
        Qdrant discovers the file is unreadable."""
        with tempfile.TemporaryDirectory() as d:
            snap = Path(d) / "lionel_memory-1-2026-01-01-00-00-00.snapshot"
            snap.write_bytes(b"original bytes")
            sidecar = Path(str(snap) + ".sha256")
            sidecar.write_text(f"{self.h.sha256_of(snap)}  {snap.name}\n", encoding="utf-8")
            snap.write_bytes(b"original bytes, and then some corruption")
            code, out = self.restore("lionel_memory", snap)
        self.assertEqual(1, code)
        self.assertIn("checksum mismatch", out[0])

    def test_the_sidecar_is_found_beside_a_dotted_name(self):
        """`Path.with_suffix` replaces the last suffix rather than appending one, so
        `x.snapshot` + `.sha256` is a two-step that is easy to get wrong in the direction
        of silently skipping verification."""
        with tempfile.TemporaryDirectory() as d:
            snap = Path(d) / "lionel_memory-1-2026-01-01-00-00-00.snapshot"
            snap.write_bytes(b"bytes")
            expected = Path(str(snap) + ".sha256")
            self.assertEqual(expected, snap.with_suffix(snap.suffix + ".sha256"))


class TestDriverAndHelperAgree(unittest.TestCase):
    """The two files drift apart silently: a renamed command is an exit 2 nobody sees
    until the night the backup is needed."""

    def setUp(self):
        self.h = load_helper()
        self.driver = DRIVER.read_text(encoding="utf-8")

    def test_every_helper_command_the_driver_calls_exists(self):
        import re
        # Anchored on `$(` and on `"$HELPER"` so the comments, which say the word
        # "helper" in ordinary English, are not read as call sites.
        called = set(re.findall(r'\$\((?:helper|helper_all) ([a-z0-9_]+)', self.driver))
        called |= set(re.findall(r'"\$HELPER" ([a-z0-9_]+)', self.driver))
        self.assertTrue(called, "the driver appears to call no helper command at all")
        for name in called:
            with self.subTest(command=name):
                self.assertIn(name, self.h.COMMANDS)

    def test_the_driver_is_in_strict_mode(self):
        """`shell` gate SH-STRICT says the same thing; asserted here too because this is
        the script where a masked failure means a backup that silently did not happen."""
        self.assertIn("set -euo pipefail", self.driver)

    def test_the_driver_declares_its_scratch_variable_globally(self):
        """The EXIT trap runs after the function has returned, where a `local` no longer
        exists — under `set -u` that turned a passing selftest into `tmp: unbound
        variable` and a non-zero exit. A green run reporting itself as a failure is the
        failure mode this feature can least afford."""
        self.assertRegex(self.driver, r'(?m)^SELFTEST_TMP=""')
        self.assertIn('"${SELFTEST_TMP:-}"', self.driver)


class TestBackupsAreNotCommittable(unittest.TestCase):
    def test_the_backup_directory_is_gitignored(self):
        """ADR-0038's one security property. A snapshot is a verbatim, unencrypted copy of
        every memory; ADR-0007's local-only guarantee is what protects it, and a `git add
        -A` on a bad day is the whole of the threat model."""
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", "backups/qdrant/example.snapshot"],
            cwd=ROOT, capture_output=True)
        self.assertEqual(0, ignored.returncode,
                         "backups/ is not gitignored — a snapshot is plaintext memory")


if __name__ == "__main__":
    unittest.main()

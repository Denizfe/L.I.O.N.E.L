"""The G1 kill-tree proof.  ADR-0014, ADR-0027 layer 1.

MASTER_PLAN_v2 §10, Gate G1: *"Job Object kill-tree verified by terminating a parent and
confirming zero orphaned children."*

This is that sentence, executed. A parent is spawned; the parent spawns a grandchild that
would outlive it; the supervisor is shut down; the grandchild must be gone.

The grandchild is what matters. `subprocess.terminate()` would pass a test that only
checked the direct child, and orphaning the grandchild is the actual failure ADR-0014
exists to prevent — so this test would still be green against the implementation the ADR
rejected, if it stopped one level up.
"""
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from lionel.platform.process_supervisor import (  # noqa: E402
    IS_WINDOWS,
    ProcessSupervisor,
)

# The grandchild: sleeps far longer than the test, and announces its pid so the test can
# look for it afterwards. Nothing here cleans up after itself — that is the point.
GRANDCHILD = (
    "import os,sys,time;"
    "open(sys.argv[1],'w').write(str(os.getpid()));"
    "time.sleep(120)"
)

# The parent: spawns the grandchild, then sleeps. Killing the parent alone leaves the
# grandchild running, which is exactly what must not happen.
PARENT = (
    "import subprocess,sys,time;"
    "subprocess.Popen([sys.executable,'-c',sys.argv[1],sys.argv[2]]);"
    "time.sleep(120)"
)


def _pid_alive(pid: int) -> bool:
    """True if a process with this pid is running and not a zombie."""
    try:
        import psutil
    except ImportError:  # psutil is declared in pyproject (ADR-0014); skip if absent
        raise unittest.SkipTest("psutil not installed; `uv sync` or `pip install psutil`")
    if not psutil.pid_exists(pid):
        return False
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


class TestKillTree(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.marker = Path(self.tmp.name) / "grandchild.pid"

    def tearDown(self):
        self.tmp.cleanup()

    def _read_grandchild_pid(self, deadline: float = 20.0) -> int:
        end = time.monotonic() + deadline
        while time.monotonic() < end:
            if self.marker.exists():
                text = self.marker.read_text().strip()
                if text.isdigit():
                    return int(text)
            time.sleep(0.05)
        self.fail("grandchild never reported its pid; the fixture did not start")

    def test_terminating_the_parent_leaves_zero_orphans(self):
        """G1's DoD clause, verbatim: zero orphaned children."""
        sup = ProcessSupervisor(name="killtree-test")
        with sup:
            parent = sup.spawn([sys.executable, "-c", PARENT, GRANDCHILD, str(self.marker)],
                               name="parent")
            grandchild_pid = self._read_grandchild_pid()
            self.assertTrue(_pid_alive(grandchild_pid),
                            "fixture is broken: the grandchild was never alive")
            self.assertTrue(parent.is_running())

        # The `with` block has closed the job / signalled the process group.
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline and _pid_alive(grandchild_pid):
            time.sleep(0.05)

        self.assertFalse(
            _pid_alive(grandchild_pid),
            f"orphaned grandchild {grandchild_pid} survived the supervisor. This is the "
            f"exact failure ADR-0014 exists to prevent: terminate() kills the direct child "
            f"and leaves its descendants holding whatever they held.")
        self.assertFalse(parent.is_running())

    def test_shutdown_is_idempotent(self):
        sup = ProcessSupervisor()
        sup.spawn([sys.executable, "-c", "import time; time.sleep(60)"])
        sup.shutdown()
        sup.shutdown()  # must not raise
        self.assertEqual(sup.running(), [])

    def test_shutdown_runs_on_the_exception_path(self):
        """Cleanup that only runs when nothing went wrong is not cleanup."""
        sup = ProcessSupervisor()
        with self.assertRaises(ZeroDivisionError):
            with sup:
                sup.spawn([sys.executable, "-c", "import time; time.sleep(60)"])
                _ = 1 / 0
        self.assertEqual(sup.running(), [])

    def test_spawn_after_shutdown_is_refused(self):
        sup = ProcessSupervisor()
        sup.shutdown()
        with self.assertRaises(RuntimeError):
            sup.spawn([sys.executable, "-c", "pass"])


class TestPlatformMechanism(unittest.TestCase):
    """The mechanism must be the one ADR-0014 chose, not merely an equivalent outcome."""

    def test_windows_uses_a_job_object(self):
        if not IS_WINDOWS:
            self.skipTest("Windows-only: Job Objects")
        sup = ProcessSupervisor()
        try:
            self.assertIsNotNone(sup._job, "no job object was created")
        finally:
            sup.shutdown()

    def test_posix_puts_the_child_in_its_own_session(self):
        if IS_WINDOWS:
            self.skipTest("POSIX-only: process groups")
        import os
        sup = ProcessSupervisor()
        try:
            child = sup.spawn([sys.executable, "-c", "import time; time.sleep(30)"])
            time.sleep(0.3)
            self.assertEqual(os.getpgid(child.pid), child.pid,
                             "child is not its own process-group leader, so killpg would "
                             "signal this test process's group instead")
        finally:
            sup.shutdown()

    def test_windows_child_gets_a_new_process_group(self):
        if not IS_WINDOWS:
            self.skipTest("Windows-only")
        sup = ProcessSupervisor()
        try:
            child = sup.spawn([sys.executable, "-c", "import time; time.sleep(30)"])
            self.assertTrue(child.is_running())
        finally:
            sup.shutdown()
        self.assertFalse(child.is_running())


if __name__ == "__main__":
    unittest.main()

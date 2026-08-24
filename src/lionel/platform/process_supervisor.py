"""Child-process lifetime, with a kill-tree the OS enforces.  ADR-0014.

THE FAILURE THIS EXISTS TO PREVENT
    `subprocess.terminate()` kills the direct child and orphans its grandchildren. That is
    not an edge case for this project — an MCP server launched over stdio typically spawns
    a language runtime, which spawns workers. Kill the middle and the workers keep the
    microphone, the port, or the model file, and the next run fails with something that
    looks nothing like the actual cause.

    ADR-0014 rejected `psutil` recursive kill for the same reason it rejects most cleanup
    code: it is racy. A child spawned between enumeration and kill survives. The fix has to
    come from the kernel.

THE MECHANISM
    Windows   A Job Object with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE. Every descendant
              inherits the job, and closing the handle kills all of them — guaranteed by
              the OS, not by this file.
    POSIX     A new session (`setsid`) per supervised child, killed by process group.
              Same interface, for CI and for cluster containers.

    ADR-0014's structural half matters more and is not implemented here, because it is not
    code: *prefer HTTP-transport MCP servers over stdio wherever the server supports it.*
    The best-handled subprocess is the one that does not exist. This module is for the rest.

THE RESIDUAL RACE, STATED PLAINLY
    On Windows the process is created and then assigned to the job. A grandchild spawned in
    the microseconds between those two calls would not be in the job. Closing that window
    needs CREATE_SUSPENDED plus ResumeThread on the primary thread handle, and
    `subprocess.Popen` does not expose that handle — reaching it means pywin32 or
    reimplementing CreateProcess through ctypes, which is a larger decision than G1 needs.

    The window is bounded and small, it is documented here rather than discovered later,
    and `spawn()` accepts `assign_first=False` only so a test can widen it deliberately.
    If it ever matters, the fix is a named ADR amendment, not a quiet rewrite.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from typing import Sequence

__all__ = ["ProcessSupervisor", "SupervisedProcess", "KillTreeUnavailable"]

IS_WINDOWS = sys.platform == "win32"


class KillTreeUnavailable(RuntimeError):
    """The OS refused to give us a kill-tree primitive.

    Raised rather than degraded. A supervisor that silently falls back to
    `terminate()` would report success while leaving exactly the orphans ADR-0014 is
    about, and the G1 DoD — *zero orphaned children* — would pass by not being tested.
    """


@dataclass
class SupervisedProcess:
    """One supervised child. `popen` is exposed for stdio; lifetime belongs to the supervisor."""
    name: str
    popen: subprocess.Popen
    _job_handle: int | None = field(default=None, repr=False)

    @property
    def pid(self) -> int:
        return self.popen.pid

    def is_running(self) -> bool:
        return self.popen.poll() is None


# ── Windows Job Object plumbing (ctypes; no pywin32) ────────────────────────────────
if IS_WINDOWS:  # pragma: no cover - exercised on the windows CI job
    import ctypes
    from ctypes import wintypes

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    JobObjectExtendedLimitInformation = 9
    PROCESS_SET_QUOTA = 0x0100
    PROCESS_TERMINATE = 0x0001

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [("ReadOperationCount", ctypes.c_ulonglong),
                    ("WriteOperationCount", ctypes.c_ulonglong),
                    ("OtherOperationCount", ctypes.c_ulonglong),
                    ("ReadTransferCount", ctypes.c_ulonglong),
                    ("WriteTransferCount", ctypes.c_ulonglong),
                    ("OtherTransferCount", ctypes.c_ulonglong)]

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
                    ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
                    ("LimitFlags", wintypes.DWORD),
                    ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t),
                    ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.POINTER(ctypes.c_ulong)),
                    ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                    ("IoInfo", IO_COUNTERS),
                    ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    def _create_kill_on_close_job() -> int:
        _kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        handle = _kernel32.CreateJobObjectW(None, None)
        if not handle:
            raise KillTreeUnavailable(
                f"CreateJobObject failed (error {ctypes.get_last_error()}). Without a job "
                f"object there is no OS-enforced kill-tree on Windows, and ADR-0014 does "
                f"not permit falling back to terminate()."
            )
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not _kernel32.SetInformationJobObject(
                handle, JobObjectExtendedLimitInformation,
                ctypes.byref(info), ctypes.sizeof(info)):
            err = ctypes.get_last_error()
            _kernel32.CloseHandle(handle)
            raise KillTreeUnavailable(
                f"SetInformationJobObject failed (error {err}). The job exists but would "
                f"not kill its processes on close, which is the only property we wanted."
            )
        return handle

    def _assign(handle: int, pid: int) -> None:
        _kernel32.OpenProcess.restype = wintypes.HANDLE
        proc = _kernel32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, False, pid)
        if not proc:
            raise KillTreeUnavailable(
                f"OpenProcess({pid}) failed (error {ctypes.get_last_error()})")
        try:
            if not _kernel32.AssignProcessToJobObject(handle, proc):
                raise KillTreeUnavailable(
                    f"AssignProcessToJobObject failed for pid {pid} "
                    f"(error {ctypes.get_last_error()})")
        finally:
            _kernel32.CloseHandle(proc)

    def _close_job(handle: int) -> None:
        _kernel32.CloseHandle(handle)


class ProcessSupervisor:
    """Spawns and reliably kills process trees.

    Use as a context manager: leaving the block terminates everything, including on the
    exception path. That ordering is the point — cleanup that only runs on the happy path
    is cleanup that never runs when it matters.
    """

    def __init__(self, name: str = "lionel") -> None:
        self.name = name
        self._children: list[SupervisedProcess] = []
        self._lock = threading.Lock()
        self._job: int | None = _create_kill_on_close_job() if IS_WINDOWS else None
        self._closed = False

    # -- lifecycle ---------------------------------------------------------------
    def __enter__(self) -> "ProcessSupervisor":
        return self

    def __exit__(self, *exc) -> None:
        self.shutdown()

    def spawn(self, argv: Sequence[str], *, name: str | None = None,
              assign_first: bool = True, **popen_kwargs) -> SupervisedProcess:
        """Start a child inside the kill-tree.

        `assign_first=False` exists only so a test can widen the Windows assignment race
        described in this module's docstring. Production callers leave it alone.
        """
        if self._closed:
            raise RuntimeError("supervisor is shut down; create a new one")

        kwargs = dict(popen_kwargs)
        if IS_WINDOWS:
            # CREATE_NEW_PROCESS_GROUP gives us signal control (ADR-0014); without it a
            # CTRL_BREAK would hit our own process group as well.
            kwargs["creationflags"] = (kwargs.get("creationflags", 0)
                                       | subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            # A new session means the child and every descendant share one process-group
            # id we can signal in a single call, with no enumeration and no race.
            kwargs["start_new_session"] = True

        popen = subprocess.Popen(list(argv), **kwargs)
        if IS_WINDOWS and assign_first and self._job is not None:
            try:
                _assign(self._job, popen.pid)
            except KillTreeUnavailable:
                popen.kill()
                raise

        child = SupervisedProcess(name=name or argv[0], popen=popen, _job_handle=self._job)
        with self._lock:
            self._children.append(child)
        return child

    def shutdown(self, timeout: float = 5.0) -> None:
        """Kill every supervised tree. Idempotent, and safe to call from a finally block."""
        if self._closed:
            return
        self._closed = True

        if IS_WINDOWS:
            # Closing the job handle kills every process in it. Nothing here enumerates
            # anything, so nothing here can race a newly spawned grandchild.
            if self._job is not None:
                _close_job(self._job)
                self._job = None
        else:
            with self._lock:
                children = list(self._children)
            for child in children:
                if child.popen.poll() is not None:
                    continue
                try:
                    pgid = os.getpgid(child.pid)
                except (ProcessLookupError, PermissionError):
                    continue
                for sig in (signal.SIGTERM, signal.SIGKILL):
                    try:
                        os.killpg(pgid, sig)
                    except ProcessLookupError:
                        break
                    try:
                        child.popen.wait(timeout=timeout if sig == signal.SIGTERM else 1.0)
                        break
                    except subprocess.TimeoutExpired:
                        continue

        with self._lock:
            for child in self._children:
                try:
                    child.popen.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    pass
            self._children.clear()

    # -- inspection --------------------------------------------------------------
    @property
    def children(self) -> list[SupervisedProcess]:
        with self._lock:
            return list(self._children)

    def running(self) -> list[SupervisedProcess]:
        return [c for c in self.children if c.is_running()]

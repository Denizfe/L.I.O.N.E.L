# ADR-0014: ProcessSupervisor on Windows Job Objects

| | |
|---|---|
| Status | **Accepted** |
| Date | 2026-08-02 |
| Phase | 1 |
| Related | [ADR-0003](ADR-0003-mcp-first-capability-model.md), [ADR-0025](ADR-0025-cancellation-backpressure.md) |

## Context

MCP servers over stdio are child processes. On Windows, the POSIX assumptions most
subprocess code carries are wrong:

- **No process groups.** `os.killpg` does not exist. Terminating a parent leaves
  grandchildren running — `npx` spawning `node` is the common case, and the orphan holds
  the port.
- **Pipe-buffer deadlock.** A child that fills a pipe while the parent is not reading
  blocks forever.
- **asyncio needs `ProactorEventLoop`** for subprocess pipes; the selector loop does not
  support them on Windows.
- **`MAX_PATH` 260** unless long paths are enabled.
- **Ctrl+C semantics differ**; `CREATE_NEW_PROCESS_GROUP` is required for `CTRL_BREAK_EVENT`.

At L0 there may be six or more stdio servers running. Orphans accumulate across restarts
until something fails to bind.

## Decision

Two parts. The structural one matters more.

### Structural — spawn fewer processes

**Prefer HTTP-transport MCP servers over stdio wherever the server supports it.** The
best-handled subprocess is the one that does not exist. At L1+ this happens naturally as
services move into the cluster; at L0 it applies wherever a server offers the option.

### Tactical — supervise the rest

A `ProcessSupervisor` abstraction in `platform/process_supervisor/`:

- **Windows Job Objects** with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` — the only reliable
  kill-tree on Windows. Children die with the job, guaranteed by the OS.
- `CREATE_NEW_PROCESS_GROUP` for signal control.
- Non-blocking stdio with dedicated reader tasks; never block on a pipe.
- `ProactorEventLoop` selected explicitly at startup on Windows.
- Long-path awareness; paths validated at config load, not at spawn.
- Health checks and restart-with-backoff per supervised process.
- POSIX implementation behind the same interface, for CI and cluster containers.

## Consequences

### Positive
- Zero orphaned processes, enforced by the OS rather than by cleanup code.
- Cancellation ([ADR-0025](ADR-0025-cancellation-backpressure.md)) has a reliable primitive
  for subprocess termination.
- Windows/POSIX difference is contained in one module.

### Negative / Costs
- Job Objects require `pywin32` or `ctypes` — a platform-specific dependency, isolated.
- Supervision logic is genuinely fiddly and needs its own tests.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| `subprocess.terminate()` | Kills the direct child only. Orphans grandchildren — the actual failure mode |
| `psutil` recursive kill | Racy: a child spawned between enumeration and kill survives |
| `taskkill /T /F` | Shell-out, no error handling, and violates the spirit of ADR-0011 |
| HTTP transport for everything | Not all servers support it; forcing it would exclude useful third-party servers |

## Verification

Gate **G1**. Terminating a supervised parent leaves **zero orphaned children**, verified by
process enumeration after kill.

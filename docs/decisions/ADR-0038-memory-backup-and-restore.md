# ADR-0038: Memory has a second copy, and the restore is exercised rather than assumed

| | |
|---|---|
| Status | **Accepted** — Efe, 2026-09-01. In force |
| Date | 2026-09-01 |
| Phase | 2 |
| Related | [ADR-0004](ADR-0004-qdrant-in-docker.md), [ADR-0007](ADR-0007-degradation-ladder.md), [ADR-0010](ADR-0010-memory-service.md), [ADR-0013](ADR-0013-artifact-pinning.md), [ADR-0036](ADR-0036-memory-client-and-embedding-runtime.md) |

## Context

`MASTER_PLAN_v1.md` §2.6 — its Definition of Done for Phase 2 — listed one item that has
no successor anywhere:

> - [ ] `scripts/memory_backup.sh` produces a snapshot in `backups/` via the Qdrant snapshot API

`MASTER_PLAN_v2.md` rewrote the phase plan and carries a migration table saying, for each
v1.0 item, whether it was retained or deleted and why. **That table has no row for this
one.** It was not judged unnecessary and it was not deferred; it stopped being written
down. `Phase2_Final_Signoff.md` §6 records it as a **Major with no mitigation**, and §7
puts it to Efe as the one thing worth weighing before signing:

> §6's first row is a Major with no mitigation: there is no way to back up or restore
> memory. It does not block G2's DoD, because v2 does not carry that item forward. It does
> mean that from the moment G2 closes, the project's memory has a single copy.

The exposure is not theoretical and it is not slow. `docker-compose.yml` keeps memory in a
named volume, `lionel_qdrant_storage`, precisely so that `docker compose down && up`
preserves it — which `scripts/verify_memory.sh` proves on every run. The command one
character away from that, `docker compose down -v`, removes the volume. It is the command
people reach for when a container misbehaves, it prints nothing alarming, and after it
there is nothing to restore from.

**And durable memory is by construction the part that was worth keeping.** ADR-0010 splits
the store in two: `lionel_episodic` expires on a TTL, and `lionel_memory` does not expire at
all. Everything in the durable collection is there because something decided it should
outlive the conversation it came from. It is also, uniquely in this system, **not
reproducible**: the ADRs can be re-read, the models can be re-downloaded, `uv.lock` can
rebuild the environment. What Efe told the assistant six months ago exists in one place.

**A backup nobody has restored is a file.** This is the failure shape G2 already found four
times, stated in `Phase2_Final_Signoff.md` §1: every one of the four defects was *in
something that had been reviewed, frozen, and never executed*. A snapshot path with no
exercised restore would be the fifth instance of it, written the same week the other four
were closed.

## Decision

**Reinstate `scripts/memory_backup.sh`, and make the restore path a thing that is run
rather than a thing that is documented.**

1. **`scripts/memory_backup.sh` with four subcommands** — `create`, `list`, `restore`,
   `selftest` — driving `scripts/_memory_snapshot.py`, which speaks the Qdrant snapshot
   REST API. The split follows `verify_memory.sh` / `_memory_live.py` for the reason given
   there: two quoting regimes must not fight over the same backslashes.
2. **The host copy is the backup.** Qdrant writes snapshots inside `/qdrant/snapshots`,
   which is in the same named volume as the data — a copy that only lives there does not
   survive the one command this ADR exists to survive. `create` downloads the snapshot to
   `backups/qdrant/`, checksums it, and then deletes the server-side copy so the volume does
   not grow by a full copy of memory on every run.
3. **Every snapshot gets a `.sha256` beside it, and `restore` refuses on mismatch.** Not a
   warning. A recovery deletes the collection before it discovers the file is unreadable,
   so restoring a corrupt snapshot over live data turns one lost copy into two.
4. **`restore` is destructive and asks.** It requires the collection name typed back at a
   terminal, or `LIONEL_BACKUP_YES=1` set deliberately. With neither, and no tty, it
   refuses.
5. **`selftest` round-trips a real snapshot of a real collection into a scratch collection**
   (`lionel_restore_check`), compares a **sha256 over the sorted point ids** — not merely
   the point count — drops the scratch, and never writes to the live collection. This is
   the clause that distinguishes this ADR from the sentence in v1.0's plan.
6. **Retention is `LIONEL_BACKUP_KEEP`, default 7, pruned after a successful write** and
   never before. A retention policy that deletes the old copy first loses everything on the
   one run where the new copy fails.
7. **`backups/` stays gitignored, and that is a security property rather than tidiness.** A
   snapshot is a verbatim, unencrypted copy of everything the assistant has ever been told.
   ADR-0007's local-only guarantee is what protects it. Syncing that directory anywhere
   needs its own ADR.

**No new dependency.** `qdrant-client` is already declared by ADR-0036; the download and the
multipart upload use `urllib` from the standard library.

**This is not a gate and never will be**, for the reason `check_env.sh` and
`verify_memory.sh` are not: it describes a host with a Docker daemon and a running Qdrant,
and CI is not the host runtime (ADR-0002). Nothing here runs in a workflow.

**Scheduling is explicitly out of scope.** Nothing runs this on a timer, and this ADR does
not pretend otherwise — see Consequences.

## Consequences

**What gets better.** `Phase2_Final_Signoff.md` §6's first row acquires a mitigation, and
the sentence "from the moment G2 closes, the project's memory has a single copy" stops being
true. A disaster drill exists that can be run in under a minute, on the host, before it is
needed rather than during.

**What this costs.**

- **A backup is a second copy of the most sensitive data in the project, in a directory
  nothing watches.** Encryption at rest is not addressed here and would need its own ADR;
  what is addressed is that the directory is gitignored and that this ADR says out loud
  what is in it.
- **Nothing schedules it.** `create` runs when a person runs it, so the residual risk is not
  "no backup exists" but "the newest backup is as old as the last time anyone remembered".
  That is a strictly smaller risk than the one this closes, and it is the same shape as
  R-A20 — nothing forces the preflight to run either, and nothing can. It belongs in the
  risk register rather than in a cron job nobody reviewed.
- **`selftest` takes a real snapshot every time it runs**, which on a large collection is
  real disk and real seconds. It writes to a temporary directory and removes it.
- **The point-id digest proves the same records, not the same vectors.** Two collections
  with identical ids and corrupted vectors would agree. Checking the vectors would mean
  reading every one of them out over HTTP; the ids are what a restore of the *wrong
  snapshot* — the realistic mistake, in a directory of similarly named dated files — gets
  wrong first.

**What this does not change.** No contract moves, no schema moves, no stable surface moves.
The Memory Service does not learn about backups: this is an operator tool that talks to
Qdrant, not a capability, and nothing in `src/lionel/` imports it.

## Alternatives Rejected

**Leave it out, as MASTER_PLAN_v2 effectively did.** The argument for it is real — v2
deleted scope deliberately and this repository's failure mode is doing more than was
decided. It is rejected because the deletion was not a decision: the migration table records
a reason for every other dropped item and has no row for this one. An item that vanished
without an argument has not been argued against.

**A bind mount and a filesystem copy of the volume.** Simpler, and it dodges the snapshot
API entirely. Rejected twice over: `docker-compose.yml` uses a named volume specifically to
avoid the MSYS path-rewriting hazard (`HAZ-HOST-MOUNT`) and the NTFS I/O penalty, and a
file-level copy of a live storage directory is not a consistent snapshot — Qdrant's own API
exists because the answer to "can I just copy the files" is no.

**Restore by mounting the snapshot into the container and recovering from a local path.**
Fewer bytes over the wire than a multipart upload. Rejected: it requires `docker cp` with a
container-side absolute path, which is exactly `SH-MSYS-DOCKER` — Git Bash rewrites
`/qdrant/snapshots` into a Windows path before Docker sees it, and the failure is silent.
The upload endpoint has no such hazard.

**Compare point counts in `selftest` and stop there.** It was the first implementation.
Rejected once written down: a count is the property a restore of the wrong snapshot is most
likely to *share*, and a directory of dated files from the same collection is a machine for
producing that mistake.

**Schedule it — a cron entry, a Task Scheduler job, a `restart: unless-stopped` sidecar.**
Rejected for this ADR, not forever. Every version of it adds something that runs unattended
on Efe's primary machine and writes unencrypted memory to disk on a timer, which is a
decision about retention and about disk, not a detail of this one. Recorded as the residual
above.

## Verification

Delivered with this ADR:

| | |
|---|---|
| `scripts/memory_backup.sh` | `create` · `list` · `restore` · `selftest`, exit codes 0/1/2 as everywhere else |
| `scripts/_memory_snapshot.py` | `collections` `sha256` `points` `digest` `drop` `create` `restore`, TSV only |
| `tests/unit/test_memory_backup.py` | 13 assertions, ADR-0027 layer 1: the TSV and exit-code contract, every refusal reachable without a network, the driver/helper agreement, and that `backups/` is gitignored |

Witnessed on the host, 2026-09-01, against the digest-pinned Qdrant:

| What was run | What happened |
|---|---|
| `memory_backup.sh create` | `lionel_memory` copied to `backups/qdrant/`, 144.0 kB, sha256 written beside it, server-side copy removed |
| `memory_backup.sh selftest` | round-trip into `lionel_restore_check`: same count **and** the same point-id digest, scratch dropped, live collection untouched |
| **the disaster drill** | `lionel_memory` **deleted outright**, then restored from the snapshot — the point-id digest before the delete and after the restore are the same string |
| a corrupted snapshot | refused: `checksum mismatch: recorded 5bc5eaf923f1, file is 5977533cf7f9`, before any upload |
| `restore` with no tty and no `LIONEL_BACKUP_YES` | refused: *"an unattended restore over live memory needs to be asked for in as many words"* |
| Qdrant stopped | `create` exits 1 and says `Start it with: docker compose up -d qdrant`; `list` still verifies every checksum, because it needs no container |
| `LIONEL_BACKUP_KEEP=1` | the older snapshot and its sidecar pruned, after the new one was written |

Gate **G2+1**, which is where `Phase2_Final_Signoff.md` §6 assigned the item. It does not
change G2's Definition of Done and does not affect whether G2 can be signed.

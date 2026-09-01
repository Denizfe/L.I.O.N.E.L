# Phase 2 — Final Sign-off

| | |
|---|---|
| Gate | **G2 — Memory Service** |
| Date | Prepared 2026-08-28 · §6 and §8 updated 2026-09-01, when ADR-0038 closed the first open item |
| Architecture at preparation | **1.18.0** · `sha256:1d8a33c7efc4c046be4ce2211f846ae112ff1c7b0e6165cb413b3c66b95928ef` — 1.17.1 when first prepared |
| | *A dated fact, not a current-state claim — §8 carries the numbers that must stay true, and it is registered with `doc-claims` for as long as this document is unsigned* |
| Scope | MASTER_PLAN_v2 §10 Phase 2, plus the two v1.0 clauses it carries forward by name, plus U1 and U2 |
| Method | Each clause traced to an artefact — a named test, a gate rule, or a witnessed run. Not to a sentence |
| **VERDICT** | **Prepared, unsigned.** §7 is Efe's, and only Efe's |

---

## 1. Executive summary

**Seven DoD clauses. Seven have an artefact.** Five are checked by something that runs
without a human. Two — persistence across a container restart, and semantic recall through
the real embedding model — can only be checked on a host with a Docker daemon, and both were
witnessed on 2026-08-28.

G1's sign-off found the same defect shape three times and asked Efe to accept the residual
knowingly. G2 found it four more times, and the shape sharpened: **every one of the four was
in something that had been reviewed, frozen, and never executed.**

| | What it said | What was true |
|---|---|---|
| `artifacts.lock.yaml` | the embedding pin is verified because the model is "cached by fastembed" | `fastembed` appeared once in the repository — in that sentence. No ADR chose it, `pyproject.toml` did not declare it, `uv.lock` did not contain it. 26 days |
| `memory-record.schema.json` | `text` has `minLength: 1`; `redacted` means "its text is cleared" | Both cannot hold. A tombstone was a record the record contract rejected, on the one path both schemas call mandatory |
| `DEP-002` | "two HTTP clients is drift, not choice" | It read `pyproject.toml` only. Accepting ADR-0036 put `requests` in `uv.lock` via `fastembed`, and every gate stayed green |
| `QdrantBackend` | implements `VectorBackend` | It could not store a conforming record. Qdrant point ids must be an integer or a UUID; the contract pins them to a ULID |

The first three are closed — ADR-0036, ADR-0037, `DEP-003`. The fourth was a bug and is
fixed. **What none of them had in common with G1's three is a gate that could have caught
them**; what they do have in common is that running the thing found them in minutes.

---

## 2. MASTER_PLAN_v2 §10 Phase 2 — the five clauses

| # | Clause | State | Artefact |
|---|---|---|---|
| 1 | `forget(id)` **provably** removes a memory from retrieval | **Met** | `tests/unit/test_memory_service.py::TestForget`, 5 cases. The text is cleared, the vector leaves the backend, and the tombstone remains — asserted separately, because a delete that left no tombstone would make `forget` true only until the next consolidation run |
| 2 | Near-duplicate ingestion is deduplicated | **Met** | `TestDeduplication`, 4 cases. The fold keeps the higher importance; dedup does not cross `kind`, because a decision and an episodic note may say the same thing and have different expiries |
| 3 | Episodic decay observed under an **accelerated clock** | **Met** | `TestDecayUnderAnAcceleratedClock`, 4 cases. The clock is injected, which is the difference between a test and a thirty-day wait. Durable memory is asserted **not** to expire after 3650 simulated days |
| 4 | Re-index against a second embedding model completes **without data loss** | **Met** | `TestReindex`, 3 cases. Possible only because `embedding_model` is stored per record — the contract calls the alternative *"unrecoverable data loss disguised as gradually worsening recall"*. A redacted record is asserted not to be resurrected by the re-index |
| 5 | Direct `qdrant-store` is **absent** from the exposed capability surface | **Met** | `tests/unit/test_memory.py::TestCapabilitySurface`, and `config/capabilities.registry.json` carries the note by name. ADR-0010 removed it because exposing it makes every caller a memory-policy author |

---

## 3. The two v1.0 clauses MASTER_PLAN_v2 carries forward by name

Both need a running Qdrant. Neither can be a CI test: ADR-0007's guarantee is that the
ordinary path works with the cable pulled, and a suite that started containers by default
would break it. So they live in `scripts/verify_memory.sh`, opt-in and announced.

| # | Clause | State | Artefact |
|---|---|---|---|
| 6 | **Persistence proof** — `compose down && up` → the stored memory is still retrievable | **Met — by hand, and only by hand** | Witnessed 2026-08-28. Same id, same text, **same trust**. §4 |
| 7 | Semantically **dissimilar** query retrieves the stored fact — *"keyword-matching would fail this; vector search must not"* | **Met — by hand, with the real model** | Witnessed 2026-08-28 through `all-MiniLM-L6-v2`. The helper **refuses to run** if the query shares one word with the target. §4 |

### v1.0's other four Phase 2 items

MASTER_PLAN_v2 §11.2's migration table names what v1.0 content was retained, superseded or
deleted. It has a row for the compose sketch, the two-collection split and the capability
registry. **It has no row for `scripts/memory_backup.sh`.** That is not a decision recorded
either way; it is an omission, and this document is where it stops being invisible. §6.

| v1.0 item | State |
|---|---|
| `docker compose ps` reports `lionel-memory` **healthy** | **Met.** `docker compose ps` → `Up (healthy)` |
| `curl localhost:6333/healthz` returns success | **Met.** `healthz=200`, `readyz=200` |
| Ports respond on `127.0.0.1` but **not** on the LAN IP | **Met, and it is the most security-relevant line here.** `http://192.168.1.7:6333/healthz` → connection refused (curl exit 7), while `127.0.0.1` answers 200. The `127.0.0.1:` prefixes in `docker-compose.yml` are load-bearing: without them Docker publishes on `0.0.0.0` and an unauthenticated store holding everything the assistant has been told is reachable from the LAN |
| `scripts/memory_backup.sh` snapshots to `backups/` | **Not met, and not carried forward by v2.** Recorded in §6 rather than quietly dropped |

---

## 4. The clauses with no automated artefact

`scripts/verify_memory.sh` starts and stops a container. It says which embedder it used in
every line, because **a persistence proof with a fixture embedder is a true statement about
the store and says nothing about retrieval quality** — and the fixture exists, in
`scripts/_memory_live.py`, deliberately outside `src/lionel/`.

**Run on the host 2026-08-28 21:17 UTC, immediately before this document was finalised:**

```
ok    qdrant       reachable  Qdrant answering at http://127.0.0.1:6333
ok    embedder     real model the pinned model is cached and loads — sentence-transformers/all-MiniLM-L6-v2
ok    write        stored     01M153QXE0VVE48X1RQ1J564W4 · fastembed · 1 point(s)

  docker compose down
  docker compose up -d qdrant
ok    restart      back up    container recreated, volume kept
ok    persistence  survived   same id, same text, same trust · 1 point(s)
ok    semantic     retrieved  0 words shared with the target; 2 shared with a distractor ['it', 'with']
note    turkish    also hit   a Turkish query reached the English fact

PASS  memory survives `compose down && up`, and a dissimilar query finds it.
```

### Why this run counts

**The driver was observed failing, twice, in ways that matter.**

| Break | What it reported |
|---|---|
| Qdrant stopped | `FAIL qdrant no answer — [WinError 10061] the target machine actively refused it`, with the command that fixes it |
| `docker compose down -v` — the named volume **destroyed** | `record not found after restart; collection holds 0 point(s)` |

The second is the one that makes clause 6 evidence rather than decoration. Without it, a
green line could mean the record never left process memory. With it, the green line means
**the named volume carried it**.

**Keyword matching is refused, not assumed.** Clause 7's second half — *"keyword-matching
would fail this"* — is enforced by the helper, which exits `broken` if the query shares a
single word with the target. The query shares two words (`it`, `with`) with *distractors*,
which is reported rather than refused: it makes keyword matching actively wrong rather than
merely empty, which is a stronger demonstration of the clause than silence would be.

**A Turkish query also reached the English fact.** Reported, never asserted.
`all-MiniLM-L6-v2` is an English model and was never claimed to be otherwise; ADR-0018 chose
a multilingual STT precisely because model multilinguality is not assumed here. It is
recorded for G6c as an observation, not relied on as a property.

**What Efe is asked to accept:** clauses 6 and 7 rest on a run, witnessed once, on one
machine, through a driver proven capable of reporting its own failure. It is re-runnable in
one command. It is not, and cannot be, continuously verified — the same residual as G1's
clause 5, and the same risk, **R-A20**.

---

## 5. U1 and U2 — the universal exit criteria

**U1 — L0 conformance.** `l0-conformance` passes on every push, and nothing in this phase
weakened it: `qdrant-client` and `fastembed` are lazily imported, so the offline path does
not touch them, and `tests/unit/test_memory.py`'s twenty-four cases all run with neither
package installed. That is not a convenience — a suite that needed them present could not
test their absence, which is the failure L0 is about.

**U2 — security gate: the threat-model delta for the surface this phase added.**

| Added surface | Assessment |
|---|---|
| A container listening on `6333`/`6334` | Loopback-only, **verified against the LAN IP**, not merely configured. An unauthenticated vector store holding everything the assistant has been told is the highest-value target this project has yet created |
| Memory as a persistence path for injected content | **Trust does not launder.** A record keeps its ingestion trust forever, and `recall` returns the minimum trust across results as `trust_floor` for the caller to fold into the turn. `TestTrustDoesNotLaunder` asserts all three parts. Storing a hostile document and recalling it a day later must not upgrade it — memory is the obvious way round ADR-0012, and this is the structural answer |
| An empty recall | Returns `trust_floor: operator`, not the weakest level. Zero results introduce no content, and a floor that downgraded on every miss would make trust decay by accident |
| A model fetched from the network on first use | `fastembed` caches outside the repository. The pin is model-id plus a **dimension assertion at startup**, so substitution is a refusal to start rather than gradually worsening recall. Cold cache with no network is a named error, not an empty recall |
| `requests`, transitively | `forbid_packages` names it. `DEP-003` now reads `uv.lock`, and the exemption records `pulled_by`, `why`, `owner` and a route out. Nothing in `src/lionel/` imports it; `httpx` remains the client this repository's own code calls |
| `docker compose down -v` | Destroys the volume and every memory in it. Used deliberately in falsification; **there is no backup path to restore from**, which is §6's first row and the reason it is a Major |

---

## 6. Open items that do not block G2

| | Severity | Owner |
|---|---|---|
| **~~No backup path exists.~~ Closed 2026-09-01 by ADR-0038.** v1.0's Phase 2 DoD required `scripts/memory_backup.sh` snapshotting to `backups/` via the Qdrant snapshot API. MASTER_PLAN_v2's migration table had **no row for it** — neither retained nor deleted, simply absent. The item is reinstated: `create` · `list` · `restore` · `selftest`, checksummed snapshots, a restore that refuses a corrupt file, and a round-trip compared on point ids rather than on a count. The disaster drill — the durable collection deleted outright and restored — was witnessed on the host on 2026-09-01. **The residual is that nothing schedules it**: the newest backup is as old as the last time anyone remembered, which is the same shape as R-A20 | ~~Major~~ **Minor** | memory · operator |
| **Turkish TTS is personal-use only.** `tr_TR-dfki-medium` is CC-BY-NC-SA-4.0 and is the only Turkish voice. Blocks distribution, not Phase 2. R-A15 | Major | sensory · G6c |
| **A host fact cannot be checked from CI.** Clauses 6 and 7 are witnessed runs. Mitigated by `verify_memory.sh`; the residual is that nothing forces it to run. R-A20 | Moderate | platform · G3 |
| **A schema's prose and its examples can disagree, and nothing notices.** `memory-record.schema.json` described a cleared text, exemplified a `"[redacted]"` placeholder, and permitted only the second. The `jsonschema` gate compares an example to its schema, never to the sentence beside it. ADR-0037 fixed the instance; the class is open | Moderate | architecture |
| **Consolidation is a stub with a real shape.** `consolidate()` joins source texts rather than summarising them — there is no brain until G3. The supersession trail, the redaction exclusion and the trust floor are all real and tested; only the summary is naive | Minor | memory · G3 |
| **ADR-0029 rule 1 has no gate.** Append-only is enforced by a `PreToolUse` hook that sees `Edit`/`Write` but not `sed` through `Bash` | Minor | architecture |
| **Prose claims about file contents are unchecked.** `doc-quotes` closed the fenced-block half (ADR-0035). A sentence is not a fenced block | Minor | architecture |

---

## 7. Sign-off

**Not signed.** `Architecture_Freeze.md` §5 gives this signature to Efe and to nobody else,
and a document that signed itself would be the exact failure the seven rows above exist to
rule out.

To sign, replace this section:

```
| Signed | Efe · YYYY-MM-DD |
| Verdict | PASS — G2 closed, Phase 3 (Brain Gateway, G3) may begin |
| Architecture at signing | <version> · <checksum> |
```

and move this document from `doc_claims.documents` to `doc_claims.out_of_scope`, which is
what stops §8 tracking the present.

Before signing, one command is worth re-running on the host, because clauses 6 and 7 are the
only ones no machine will re-check on its own:

```bash
docker compose up -d qdrant
bash scripts/verify_memory.sh
```

Expect `ok persistence survived`, `ok semantic retrieved`, and **no** `skip` on the embedder
row. A `skip` there means the fixture embedder was used, and the verdict says in as many
words that the semantic clause is then **not** verified by that run.

**One thing to weigh before signing, which is not a precondition.** §6's first row was a
Major with no mitigation: there was no way to back up or restore memory. It did not block
G2's DoD, because v2 does not carry that item forward. It did mean that from the moment G2
closes, the project's memory would have a single copy.

**Closed on 2026-09-01, before signing rather than after.** ADR-0038 reinstates
`scripts/memory_backup.sh`, and the restore is exercised rather than documented — see §6's
first row for what was witnessed. Nothing about G2's Definition of Done changed; what
changed is that signing it no longer starts a period in which memory has one copy.

---

## 8. State at sign-off

**23 gates, 150 rules, 27 workflow jobs.** Self-test 32/32, gate coverage 23/23.
**38 ADRs**, 0 ADRs pending. 217 tests, 1 skipped (a POSIX-only kill-tree case).
`ci/policy/policy.yaml` holds 21 configuration sections.

```
contracts   27 JSON Schemas + 3 protobuf · 5 planes
checksum    sha256:1d8a33c7efc4… · 79 files · verified from a clean clone
memory      VectorBackend port · Qdrant adapter · 384-dim pin asserted at startup
container   qdrant/qdrant@sha256:0bd98fa7… · loopback-only · named volume
backup      memory_backup.sh · snapshot + sha256 · restore exercised on point ids (ADR-0038)
```

**This section is written in the phrasing `doc-claims` reads, and registered.** G1's
sign-off stated the same counts in an aligned block that matched no pattern, sat unsigned
across four versions, and went stale inside itself — `Architecture_Freeze.md` §9.19 records
it. A state block that cannot be checked is a state block that will be wrong, and the fix
is not to be more careful. `doc_claims.documents` now names this section, so every push
compares these numbers against the pipeline.

**On signing, this document moves to `doc_claims.out_of_scope`** and the numbers stop
tracking the present, exactly as `Phase0_Final_Signoff.md` and `Phase1_Final_Signoff.md`
have. A signed sign-off is a dated record; refreshing one is editing the archive.

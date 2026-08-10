# GHCR Image Digest — Engineering Justification

**AUD-M01 · `ghcr.io/github/github-mcp-server`**

| | |
|---|---|
| Date | 2026-08-03 |
| Objective | Obtain the immutable OCI image digest by any reproducible method |
| Methods attempted | **11**, across two sessions |
| **Outcome** | **The OCI image digest remains unobtainable in this environment** |
| **But** | A **fully reproducible tier-A alternative was discovered** and is documented below |
| Blocker classification | **TEMPORARY** — confirmed, and the constraint is narrower than previously understood |
| Lockfile | `status: UNRESOLVED` **unchanged**; alternatives block corrected |
| Artifacts gate | **still red** — re-run confirms `ART-000`, 1 violation across 16 checks |

---

## 1. Summary

I could not obtain the OCI manifest digest. The reason is unchanged and unambiguous: **GHCR
requires an `Authorization: Bearer` header on the manifest endpoint, and no header-capable
HTTP client is available in this environment.**

That is the same wall as before, and eleven methods now confirm it.

**However, the picture has changed materially.** GitHub's release API now publishes a
**SHA-256 `digest` for every release asset**, and release `v1.1.2` is flagged
`"immutable": true`. The official prebuilt binaries are therefore **tier-A,
primary-published, and pinnable right now** — with digests already retrieved and recorded.

This means the previous framing was wrong in one respect worth correcting: the lockfile
stated *"the Docker image is the only maintained distribution."* **It is not.** That
understatement made the blocker look harder than it is.

**What I did not do:** switch the artifact. Moving from a container image to a native binary
changes how the capability launches, removes the Docker Desktop dependency on the Windows
host, and touches ADR-0014 process supervision. That is an architecture decision requiring
your approval and an ADR — not something to slip into a lockfile while resolving a blocker.

---

## 2. Every method attempted

| # | Method | Result | Why it failed |
|---|---|---|---|
| 1 | `GET ghcr.io/v2/github/github-mcp-server/manifests/latest` | ❌ empty | 401 — no `Authorization` header |
| 2 | `GET ghcr.io/v2/.../manifests/v1.1.2` (explicit tag) | ❌ empty | Same |
| 3 | `GET ghcr.io/token?scope=repository:github/github-mcp-server:pull` | ⚠️ **token returned** | Token obtained; **cannot be used** — no way to set a request header |
| 4 | Token as `?access_token=` query parameter | ❌ empty | GHCR rejects; OCI spec requires the header |
| 5 | `GET ghcr.io/v2/.../tags/list?access_token=…` | ❌ empty | Same |
| 6 | Docker Hub `mcp/github-mcp-server` | ❌ empty | No official mirror in Docker's MCP namespace |
| 7 | Docker Hub `/v2/namespaces/mcp/repositories/…` | ❌ empty | Same |
| 8 | **Docker Hub search** `github-mcp-server` | ⚠️ **347k results, 10 inspected** | **All third-party forks.** See §3 |
| 9 | `api.github.com/orgs/github/packages/container/…/versions` | ❌ empty | Org package API requires authentication |
| 10 | `api.github.com/users/github/packages/container/…/versions` | ❌ empty | Same |
| 11 | Local registry tooling — `docker`, `crane`, `skopeo`, `regctl`, `podman`, `oras` | ❌ none installed | And each is an HTTP client, so prohibited here regardless |

**Method 3 is the precise shape of the wall.** An anonymous pull token *is* obtainable:

```
GET https://ghcr.io/token?scope=repository:github/github-mcp-server:pull&service=ghcr.io
  → {"token":"djE6Z2l0aHViL2dpdGh1Yi1tY3Atc2VydmVyOjE3ODU2NzEzNTk1MzI1MzA3Mzk="}
```

The credential is in hand. **The only missing capability is the ability to attach it to a
request.** That is a property of the tooling in this session, not of GHCR, not of GitHub,
and not of the artifact.

---

## 3. Third-party mirrors exist and must not be used

Docker Hub search returned ten `*/github-mcp-server` repositories with real pull counts:

```
hspedro/github-mcp-server        2,375 pulls   "Fork from official Github adding streamable transport"
0xshariq/github-mcp-server       1,069 pulls
autonomyx/github-mcp-server      1,057 pulls
hyeong8465/github-mcp-server       879 pulls
vakkineni449/github-mcp-server     403 pulls   "Fork ... with only PR tooling capabilities"
…
```

**Every one is a different artifact built by an unknown party**, and two openly describe
themselves as modified forks.

Pinning any of them would satisfy the gate and violate ADR-0013's explicit rule:

> *"Never substitute one artifact's digest for another's, even when sizes look close."*

This is the Kokoro trap in a more dangerous form. There, the wrong candidate was 155 bytes
different and still the same project. Here the candidates are **different builds by
different people**, one of which openly alters the transport layer. A lockfile pinning
`hspedro/github-mcp-server` would verify perfectly forever against software GitHub never
published.

**Recorded as a rejected substitution.** The existence of convenient wrong answers is why
the rule exists.

---

## 4. The discovery: official binaries are pinnable today

`GET api.github.com/repos/github/github-mcp-server/releases/latest` returns **v1.1.2** with
`"immutable": true` and a populated `digest` on every asset:

| Asset | SHA-256 | Bytes |
|---|---|---|
| `github-mcp-server_Linux_x86_64.tar.gz` | `221bb1e5b14cd298405e0e126686aabf32f1d9222d9537115e806a8fa8722f55` | 7,286,675 |
| `github-mcp-server_Linux_arm64.tar.gz` | `4dc735016e1910ca9269cbfe3d77f5699e39068f4a9555dce0bd753a48fd45ab` | 6,665,767 |
| `github-mcp-server_Windows_x86_64.zip` | `9ef5fafcebc8e21c702e05acd2919d88955d02a98c58d815580bb501d8d4c980` | 7,457,939 |
| `github-mcp-server_Windows_arm64.zip` | `258ad2694bbeb9dc8b8c63078d861b729095e5fda726500e4197eacb698a023c` | 6,733,175 |
| `github-mcp-server_1.1.2_checksums.txt` | `5272cecc9b9ac0435238a82ed0ef964c987da99943c562695208f15a27bd48b4` | 824 |

### Why this qualifies as tier A

1. **Primary-published.** The digests come from GitHub's own API for GitHub's own repository
   — not a mirror, not a third party.
2. **Immutable release.** `"immutable": true` means the assets cannot be replaced under the
   tag. This is a stronger guarantee than the Kokoro release, which predates both the
   `digest` field and immutability.
3. **Independently corroborated.** The release ships a `checksums.txt` whose *own* digest is
   API-published. Verifying that file against its digest, then verifying each binary against
   its contents, gives **two independent chains to the same values** — the same corroboration
   standard that earned tier C for the openWakeWord preprocessors, here on top of tier A.

### It would also improve the Windows story

The current design requires **Docker Desktop on the Windows host** to run a single
capability. A native `github-mcp-server_Windows_x86_64.exe` removes that dependency
entirely — relevant to ADR-0002 (Windows host) and ADR-0014 (process supervision), where
one fewer container runtime is one fewer thing to supervise.

---

## 5. Why I did not adopt it

Switching the artifact from an OCI image to a native binary changes:

| | Now | If switched |
|---|---|---|
| Launch | `docker run -i --rm … ghcr.io/…` | native executable, stdio |
| Windows host dependency | Docker Desktop required | **none** |
| Process supervision | container lifecycle | ADR-0014 `ProcessSupervisor` + Job Objects |
| Registry config | `command: docker` + `args` | `command: <path>` |
| Cluster deployment (ADR-0020) | image is directly usable | needs packaging into an image anyway |

That is an **architecture decision**, not a lockfile fix. Every prior round in this project
has held the line that a source change requires an ADR — ADR-0017 was amended when Kokoro's
source moved, and ADR-0013 gained an amendment for the sourcing rule. Making this change
silently, while resolving a blocker that was inconvenient, is precisely the pattern the G0
audit warned about.

**The decision is yours. The evidence is now complete enough to make it in five minutes.**

---

## 6. What was changed

Only `artifacts.lock.yaml`, and only the record — not the status.

| Field | Change |
|---|---|
| `alternatives` | Added **alternative 5** with all five digests, release version, immutability flag, and the corroboration chain |
| `alternatives[3].note` | Marked "superseded in practice" — building from source needs a Go toolchain; prebuilt binaries need nothing |
| `note` | **Corrected** the false claim that the Docker image is the only maintained distribution |
| `record_correction` | New field stating explicitly that this corrects a factual understatement and **does not resolve the blocker** |
| `status` | **UNCHANGED — `UNRESOLVED`** |
| `verification.tier` | **UNCHANGED — E** |
| `meta.resolved` / `meta.unresolved` | **UNCHANGED — 12 / 1** |

**No other file was modified.** No ADR, no gate, no policy, no registry.

---

## 7. Gate re-run

```
$ bash ci/run_gates.sh artifacts

  ✗ ART-000  1 artifact(s) unresolved
      at    artifacts.lock.yaml
      why   ADR-0013: G0 cannot be signed off while any artifact is unpinned.

  FAIL  1 violation(s) across 16 checks
```

**Still red, correctly.** The record improved; the blocker did not clear. A gate that went
green because the documentation got better would be worthless.

---

## 8. Resolution paths, ranked

| # | Path | Effort | Tier | Needs approval |
|---|---|---|---|---|
| **1** | `docker buildx imagetools inspect ghcr.io/github/github-mcp-server:v1.1.2` on your machine | **one command** | A | No — keeps current architecture |
| **2** | `crane digest ghcr.io/github/github-mcp-server:v1.1.2` | one command, no daemon | A | No |
| **3** | **Adopt the prebuilt binary** (digests above, already retrieved) | ~15 min + ADR | **A** | **Yes** — architecture change |
| 4 | Build from source, pin the commit | moderate, needs Go | A | Yes |
| 5 | Disable the capability at L0 | zero | n/a | No — but leaves G1 blocked |

**Recommendation: path 1.** It is one command, requires no approval, changes no
architecture, and resolves AUD-M01 outright. Path 3 is genuinely attractive on the Windows
story and should be considered on its own merits — **but not as a way to clear a blocker.**

> Use the explicit tag `v1.1.2`. `:latest` is mutable and `no-latest` (DOCKER-002) would
> reject it.

---

## 9. Classification, re-confirmed

**TEMPORARY.** Unchanged, and now better evidenced.

Nothing about GHCR, GitHub, or the artifact is defective. GHCR implements the OCI
distribution spec exactly as written; the token endpoint works; the artifact is published
and current. **The sole constraint is that this session's HTTP client cannot set a request
header.** Any machine with `docker`, `crane`, `skopeo`, or `curl` resolves it immediately.

Contrast a genuinely **PERMANENT** blocker, as documented elsewhere in this project:
XTTS-v2's licence, where the licensor dissolved in January 2024 and no counterparty exists
to negotiate with. That cannot be fixed by changing machines. This can.

---

## 10. Honest statement of what remains unknown

- **I did not obtain the image digest.** Everything above is either a negative result or a
  different artifact. Nothing here should be read as having resolved AUD-M01.
- **I did not verify the binary digests by downloading.** They are API-published, which is
  tier A by this project's own definition, but no file was fetched and hashed locally.
- **I did not fetch `checksums.txt`.** The corroboration chain in §4 is available in
  principle; I could not retrieve the file to confirm its contents match the per-asset
  digests. That confirmation should happen at adoption time.
- **v1.1.2 is `latest` today.** If you pin it, pin the version string, and re-check that the
  digests still match at adoption — the release is immutable, but my read of it is a
  point-in-time snapshot from 2026-08-03.

---

*`GHCR_Digest_Justification.md` is a new file. `artifacts.lock.yaml` was edited only as
described in §6. AUD-M01 remains OPEN and continues to block G0.*

# L.I.O.N.E.L — Master Execution Plan

**Local Intelligent Operations & NaturalEthereal Liaison**

| Field | Value |
|---|---|
| Document | `MASTER_PLAN.md` (v1.0 — blueprint, pre-execution) |
| Project root | `C:\Users\deniz\Desktop\L.I.O.N.E.L` |
| Host OS | Windows + Git Bash (MSYS2) |
| Container runtime | Docker Desktop (WSL2 backend) |
| Author | Lead AI Systems Architect |
| Owner / approver | Efe |
| Status | **AWAITING APPROVAL TO EXECUTE PHASE 1** |

---

## 0. Architectural Position

L.I.O.N.E.L is not a chatbot with a microphone bolted on. It is a **host process** that owns a reasoning loop and speaks MCP to every capability it has. Everything L.I.O.N.E.L can *do* — read files, recall memories, query GitHub, inspect hardware, speak — arrives through the same protocol boundary. That single decision is what makes the system extensible without refactors: adding a skill never means touching the core loop.

```
                       ┌──────────────────────────────┐
   mic ──► wake ──► VAD ──► whisper.cpp ──► TEXT      │
                       │                               │
                       │      ┌──────────────────┐     │
                       └─────►│  LIONEL HOST     │     │
                              │  (MCP client)    │     │
                              │  ┌────────────┐  │     │
                              │  │  BRAIN     │  │     │  swappable provider
                              │  │  adapter   │  │     │  (Claude API | Ollama | llama.cpp)
                              │  └────────────┘  │     │
                              └───┬───┬───┬───┬──┘     │
                    stdio/http    │   │   │   │        │
              ┌──────────────┬────┘   │   │   └────┐   │
              ▼              ▼        ▼   ▼        ▼   │
        filesystem      github    qdrant   FastMCP skills
          (MCP)          (MCP)    (MCP)    (system/shell/media)
                                    │
                              ┌─────▼─────┐
                              │  Qdrant   │  Docker :6333
                              │  vectors  │
                              └───────────┘
                              │
   speaker ◄── Kokoro-TTS ◄── TEXT
```

**Layer contract:** the sensory layer (Phase 4) knows nothing about the brain. The brain knows nothing about which MCP servers exist. The MCP servers know nothing about who is calling them. Each phase below closes one horizontal band of that diagram and is independently testable.

### 0.1 Confirmed architectural decisions

| ID | Decision | Rationale |
|---|---|---|
| ADR-0001 | **Hybrid, swappable brain adapter** | A `BrainProvider` ABC with `anthropic`, `ollama`, and `llamacpp` implementations selected by config. Develop against the Claude API (best tool-calling reliability, fastest iteration), then flip to Ollama for genuinely offline runs — without rewriting the host loop. No vendor lock-in, and the offline claim stays testable. |
| ADR-0002 | **Project root is `C:\Users\deniz\Desktop\L.I.O.N.E.L`** | Supersedes the `C:\Users\efe\...` path in the original project instructions, which is stale. All absolute paths in this plan use the corrected root. |
| ADR-0003 | **MCP-first capability model** | Every capability is an MCP server, including first-party ones we write ourselves in FastMCP. No "internal" backdoor APIs into the host. |
| ADR-0004 | **Qdrant runs in Docker, never embedded** | Persistent named volume, survives host restarts, matches any future migration to a remote cluster with a URL change only. |

---

## 1. Repository Layout (target state, end of Phase 4)

```
C:\Users\deniz\Desktop\L.I.O.N.E.L\
├── .git/
├── .gitattributes                 # forces LF; prevents CRLF corruption of .sh files
├── .gitignore
├── .env                           # SECRETS — gitignored, never committed
├── .env.example                   # committed template, no real values
├── .python-version                # pins 3.11 for uv
├── README.md
├── MASTER_PLAN.md                 # this document
├── docker-compose.yml             # Qdrant service
├── pyproject.toml                 # uv-managed dependency manifest
├── uv.lock
│
├── config/
│   ├── mcp.servers.json           # canonical MCP server registry for the host
│   ├── lionel.toml                # runtime config: brain provider, audio devices, wake word
│   └── logging.yaml
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── RUNBOOK.md                 # "it broke at 2am" recovery procedures
│   └── decisions/
│       ├── ADR-0001-brain-adapter.md
│       └── ADR-0002-...
│
├── scripts/                       # ALL Git Bash compatible
│   ├── check_env.sh               # preflight: node/python/docker/uv/git versions
│   ├── bootstrap.sh               # one-shot first-time setup
│   ├── memory_up.sh               # docker compose up -d qdrant + health wait
│   ├── memory_down.sh
│   ├── memory_backup.sh           # Qdrant snapshot to ./backups
│   ├── fetch_models.sh            # whisper + kokoro + wakeword model download
│   ├── build_whisper.sh
│   └── run_lionel.sh              # main entrypoint
│
├── src/lionel/
│   ├── __init__.py
│   ├── __main__.py                # python -m lionel
│   ├── config.py                  # pydantic-settings; loads lionel.toml + .env
│   ├── host/
│   │   ├── registry.py            # reads config/mcp.servers.json, spawns/connects servers
│   │   ├── client.py              # MCP client session manager (stdio + http)
│   │   └── loop.py                # the agent loop: perceive → think → act → speak
│   ├── brain/
│   │   ├── base.py                # BrainProvider ABC  ← ADR-0001
│   │   ├── factory.py
│   │   └── providers/
│   │       ├── anthropic_provider.py
│   │       ├── ollama_provider.py
│   │       └── llamacpp_provider.py
│   ├── memory/
│   │   ├── qdrant_bridge.py       # thin wrapper over the qdrant MCP tools
│   │   └── policy.py              # what is worth remembering, and for how long
│   ├── skills/                    # FIRST-PARTY FastMCP SERVERS
│   │   ├── system_server.py       # CPU/GPU/RAM/disk/battery telemetry
│   │   ├── shell_server.py        # allowlisted command execution
│   │   └── media_server.py        # audio device control, volume, playback
│   ├── sensory/
│   │   ├── audio_io.py            # sounddevice ring buffer, device enumeration
│   │   ├── wake.py                # openWakeWord (ONNX)
│   │   ├── vad.py                 # silero-vad endpointing
│   │   ├── stt.py                 # whisper.cpp subprocess / binding
│   │   ├── tts.py                 # kokoro-onnx synthesis + streaming playback
│   │   └── pipeline.py            # full-duplex orchestration, barge-in
│   └── utils/
│       ├── logging.py
│       └── paths.py               # single source of truth for Windows path handling
│
├── vendor/
│   └── whisper.cpp/               # git submodule, pinned tag
│
├── models/                        # GITIGNORED — large binaries
│   ├── whisper/ggml-base.en.bin
│   ├── kokoro/kokoro-v1.0.onnx
│   ├── kokoro/voices-v1.0.bin
│   └── wakeword/hey_lionel.onnx
│
├── data/qdrant/                   # GITIGNORED — Docker named-volume mirror
├── logs/                          # GITIGNORED
├── backups/                       # GITIGNORED
└── tests/
    ├── test_phase1_env.py
    ├── test_phase2_memory.py
    ├── test_phase3_skills.py
    └── test_phase4_sensory.py
```

---

## 2. Global Git Bash / Windows Rules

These bite on every phase. Encoding them once here prevents four separate debugging sessions.

| Hazard | Rule |
|---|---|
| **MSYS path mangling** — Git Bash rewrites `/qdrant/storage` into `C:/Program Files/Git/qdrant/storage` before Docker ever sees it | Prefix Docker commands containing container-side absolute paths with `MSYS_NO_PATHCONV=1`, or double the leading slash: `//qdrant/storage` |
| **Host paths in volume mounts** | Use `$(pwd -W)` to emit a Windows-native path, or rely on `docker-compose.yml` relative paths (Compose handles translation itself) — the reason we prefer Compose over raw `docker run` |
| **CRLF corruption of shell scripts** | `.gitattributes` with `*.sh text eol=lf` — a CRLF-terminated `.sh` fails with a cryptic `\r: command not found` |
| **Interactive TTY** | Prefix with `winpty` for anything that prompts (e.g. `winpty docker exec -it ...`) |
| **`python` resolves to a Microsoft Store stub** | Never call bare `python`. Use `uv run` for everything; `uv` owns the interpreter |
| **Backslashes in `.env`** | Always write forward slashes in config values: `C:/Users/deniz/...`. Python and Docker both accept them; Bash won't eat them as escapes |
| **Docker Desktop backend** | Must be WSL2, not Hyper-V — required for reliable bind-mount performance on the Qdrant volume |

---

# PHASE 1 — Environment, Workspace & Core MCP Initialization

**Goal:** a versioned, reproducible skeleton where an MCP client can already read/write the project and talk to GitHub. Nothing intelligent yet — this phase exists so every later phase has somewhere safe to land.

**Est. effort:** 1 session

### 1.1 Preflight — tooling to verify or install

| Tool | Minimum | Verify (Git Bash) | Why |
|---|---|---|---|
| Git | 2.40+ | `git --version` | Versioning + submodule for whisper.cpp |
| Node.js | 20 LTS | `node -v && npx -v` | Runs the filesystem MCP server via `npx` |
| Python | 3.11.x | `py -3.11 --version` | 3.11 is the sweet spot: onnxruntime + torch wheels all exist |
| uv | 0.5+ | `uv --version` | Dependency + venv manager; `uvx` runs MCP servers without installing |
| Docker Desktop | current | `docker version && docker compose version` | Qdrant, GitHub MCP server |
| VS Build Tools | 2022, "Desktop dev with C++" | `where cl.exe` in Dev Prompt | Required in Phase 4 to compile whisper.cpp |

Install `uv` if absent:

```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# restart Git Bash, then:
uv --version
```

### 1.2 Files created in this phase

```
.gitignore  .gitattributes  .env.example  .python-version
README.md   config/mcp.servers.json
scripts/check_env.sh   scripts/bootstrap.sh
docs/ARCHITECTURE.md   docs/decisions/ADR-0001-brain-adapter.md
src/lionel/__init__.py  src/lionel/utils/paths.py
tests/test_phase1_env.py
```

### 1.3 Commands

```bash
cd /c/Users/deniz/Desktop/L.I.O.N.E.L

# --- scaffold ---
mkdir -p config docs/decisions scripts src/lionel/{host,brain/providers,memory,skills,sensory,utils} \
         vendor models/{whisper,kokoro,wakeword} data/qdrant logs backups tests

# --- version control ---
git init -b main
git config core.autocrlf false      # .gitattributes is authoritative
printf '*.sh text eol=lf\n*.py text eol=lf\n* text=auto\n' > .gitattributes

# --- python toolchain ---
echo "3.11" > .python-version
uv python install 3.11

# --- verify the filesystem MCP server resolves & starts ---
npx -y @modelcontextprotocol/server-filesystem "C:/Users/deniz/Desktop/L.I.O.N.E.L" --help

# --- pull the official GitHub MCP server image (npm package is dead as of Apr 2025) ---
docker pull ghcr.io/github/github-mcp-server

# --- gate check ---
bash scripts/check_env.sh
```

### 1.4 `config/mcp.servers.json` — shape

```jsonc
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem",
               "C:/Users/deniz/Desktop/L.I.O.N.E.L"]
    },
    "github": {
      "command": "docker",
      "args": ["run", "-i", "--rm",
               "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
               "ghcr.io/github/github-mcp-server"],
      "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PAT}" }
    }
  }
}
```

> **Scope note.** The filesystem server is passed exactly one allowed root. It cannot escape it. This is deliberate — L.I.O.N.E.L should not be able to touch `C:\Windows` because a prompt went sideways.

> **Token hygiene.** `GITHUB_PAT` lives in `.env` only. Use a **fine-grained** PAT scoped to the L.I.O.N.E.L repository with `contents: read/write`, `metadata: read`, `pull_requests: write` — nothing else, no org-wide access.

### 1.5 Definition of Done — Phase 1

- [ ] `scripts/check_env.sh` exits `0` and prints a green row for all six tools
- [ ] `git log --oneline` shows exactly one commit, `[LIONEL-CORE] Phase 1: project scaffold` — **created only after Efe approves**
- [ ] `git status --porcelain` is clean; `.env` does **not** appear (proves `.gitignore` works)
- [ ] Filesystem MCP server starts, lists the project root, and **refuses** a read of `C:/Windows/System32/drivers/etc/hosts`
- [ ] GitHub MCP container starts and authenticates: a `get_me` call returns Efe's login
- [ ] `docs/decisions/ADR-0001-brain-adapter.md` exists and is committed
- [ ] Every `.sh` in `scripts/` has LF endings — verify with `file scripts/*.sh | grep -c CRLF` returning `0`

**Rollback:** `rm -rf .git` and re-run. Phase 1 creates no external state.

---

# PHASE 2 — Memory Architecture (Qdrant + mcp-server-qdrant)

**Goal:** L.I.O.N.E.L gains persistent semantic recall. Facts survive process death, machine reboot, and container recreation.

**Est. effort:** 1 session

### 2.1 Dependencies

| Component | Delivery | Notes |
|---|---|---|
| Qdrant | `qdrant/qdrant:latest` Docker image | Ports **6333** (REST/UI) and **6334** (gRPC) |
| `mcp-server-qdrant` | `uvx mcp-server-qdrant` | Official Qdrant MCP server; no install step, `uvx` fetches per-run |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` via FastEmbed | 384-dim, CPU-fast, downloads on first use. **Pin this** — changing it later invalidates every stored vector |

### 2.2 `docker-compose.yml`

```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: lionel-memory
    restart: unless-stopped
    ports:
      - "127.0.0.1:6333:6333"   # bound to loopback — not exposed to the LAN
      - "127.0.0.1:6334:6334"
    volumes:
      - qdrant_storage:/qdrant/storage
    environment:
      QDRANT__SERVICE__ENABLE_TLS: "false"
      QDRANT__LOG_LEVEL: "INFO"
    healthcheck:
      test: ["CMD-SHELL", "bash -c ':> /dev/tcp/127.0.0.1/6333' || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  qdrant_storage:
```

Using a **named volume** rather than a bind mount is intentional: it dodges the MSYS path-mangling class of bug entirely, and Docker Desktop's WSL2 backend gives named volumes much better I/O than a bind mount onto NTFS.

### 2.3 Commands

```bash
cd /c/Users/deniz/Desktop/L.I.O.N.E.L

docker compose up -d qdrant
docker compose ps                                    # expect: healthy

curl -s http://localhost:6333/healthz                # -> "healthz check passed"
curl -s http://localhost:6333/collections | jq .     # -> empty result list
# Dashboard: http://localhost:6333/dashboard

# smoke-test the MCP server standalone before wiring it into the host
QDRANT_URL="http://localhost:6333" \
COLLECTION_NAME="lionel_memory" \
EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2" \
uvx mcp-server-qdrant
```

### 2.4 Registry entry appended to `config/mcp.servers.json`

```jsonc
"qdrant": {
  "command": "uvx",
  "args": ["mcp-server-qdrant"],
  "env": {
    "QDRANT_URL": "http://localhost:6333",
    "COLLECTION_NAME": "lionel_memory",
    "EMBEDDING_MODEL": "sentence-transformers/all-MiniLM-L6-v2",
    "TOOL_STORE_DESCRIPTION": "Store an architectural decision, user preference, or durable fact in L.I.O.N.E.L's long-term memory. Include the 'why', not just the 'what'.",
    "TOOL_FIND_DESCRIPTION": "Recall prior architectural decisions, preferences, or facts from L.I.O.N.E.L's long-term memory before answering questions about past work."
  }
}
```

> **Naming correction worth flagging.** The project instructions refer to `qdrant-store-memory` / `qdrant-find-memories`. The server's actual tool names are **`qdrant-store`** and **`qdrant-find`**; what's customizable is their *descriptions*, via the two env vars above. Tool descriptions are the highest-leverage knob here — they are the only thing the brain reads when deciding whether to reach for memory, so they are written as instructions, not labels.

### 2.5 Memory schema

Two collections, separated because they have different retention rules:

| Collection | Contents | Retention |
|---|---|---|
| `lionel_memory` | Durable facts, user preferences, architectural decisions | Permanent, manually curated |
| `lionel_episodic` | Conversation turns, task outcomes | Rolling window, pruned by `memory/policy.py` |

Payload convention on every point: `{ "text", "kind", "source", "created_at", "confidence" }`.

### 2.6 Definition of Done — Phase 2

- [ ] `docker compose ps` reports `lionel-memory` as **healthy**
- [ ] `curl localhost:6333/healthz` returns success
- [ ] Round-trip test: store *"L.I.O.N.E.L uses a hybrid swappable brain adapter, per ADR-0001"* via `qdrant-store`, then a **semantically dissimilar** query — "how do we pick which LLM runs the agent?" — retrieves it. Keyword-matching would fail this; vector search must not
- [ ] **Persistence proof:** `docker compose down && docker compose up -d` → the stored memory is still retrievable. This is the test that actually matters
- [ ] `scripts/memory_backup.sh` produces a snapshot in `backups/` via the Qdrant snapshot API
- [ ] Ports respond on `127.0.0.1` but **not** on the machine's LAN IP

**Rollback:** `docker compose down -v` destroys the volume and returns to Phase 1 state.

---

# PHASE 3 — Hardware & API Integration (Python venv + FastMCP Skills)

**Goal:** L.I.O.N.E.L gets hands and a brain. First-party FastMCP servers give it real capabilities; the provider adapter makes the reasoning engine swappable per ADR-0001.

**Est. effort:** 2–3 sessions

### 3.1 Dependencies (`pyproject.toml`, managed by `uv`)

```toml
[project]
name = "lionel"
requires-python = ">=3.11,<3.12"
dependencies = [
  "fastmcp>=2.0",           # skill servers
  "mcp>=1.2",               # client side of the host loop
  "pydantic>=2.9",
  "pydantic-settings>=2.6",
  "httpx>=0.27",
  "anthropic>=0.40",        # brain provider: API
  "ollama>=0.4",            # brain provider: local
  "qdrant-client>=1.12",
  "psutil>=6.0",            # system telemetry skill
  "structlog>=24.4",
  "typer>=0.15",
]

[project.optional-dependencies]
sensory = [                 # installed in Phase 4
  "sounddevice>=0.5",
  "numpy>=1.26",
  "soundfile>=0.12",
  "onnxruntime>=1.19",
  "openwakeword>=0.6",
  "kokoro-onnx>=0.4",
  "silero-vad>=5.1",
]
dev = ["pytest>=8.3", "pytest-asyncio>=0.24", "ruff>=0.8", "mypy>=1.13"]
```

```bash
cd /c/Users/deniz/Desktop/L.I.O.N.E.L
uv venv --python 3.11
uv sync                     # resolves + writes uv.lock
uv run python -c "import fastmcp, psutil; print('ok')"
```

> **Why `uv` and not `pip`/`venv`.** `uv.lock` makes the environment reproducible from a clean machine, and `uvx` is already how we run `mcp-server-qdrant`. One tool for interpreters, dependencies, and ephemeral server execution.

### 3.2 The brain adapter — ADR-0001 made concrete

```
brain/base.py       BrainProvider ABC:
                      async def complete(messages, tools) -> BrainResponse
                      async def stream(messages, tools) -> AsyncIterator[Delta]
                      property supports_native_tools: bool

brain/providers/anthropic_provider.py   native tool-use blocks
brain/providers/ollama_provider.py      native tool calling where the model supports it,
                                        JSON-schema prompt fallback where it doesn't
brain/providers/llamacpp_provider.py    OpenAI-compatible /v1/chat/completions

brain/factory.py    reads config/lionel.toml -> [brain] provider = "anthropic" | "ollama" | "llamacpp"
```

The whole point of the ABC is that `host/loop.py` imports `BrainProvider` and nothing else. Swapping engines is a one-line config edit, and the same conversation transcript can be replayed against both providers to compare tool-calling fidelity — which is how we'll know whether the fully-offline path is actually good enough.

### 3.3 FastMCP skill servers

| Server | Tools | Guardrail |
|---|---|---|
| `system_server.py` | `get_cpu_load`, `get_memory_usage`, `get_disk_usage`, `get_gpu_status`, `get_battery`, `list_processes` | Read-only. Cannot kill processes |
| `shell_server.py` | `run_command` | **Allowlist only**, defined in `lionel.toml`. No shell interpolation, `subprocess` with `shell=False`, hard timeout, output truncation |
| `media_server.py` | `list_audio_devices`, `set_output_volume`, `play_file` | Bounded to enumerated devices |

Each server runs over **stdio** and is registered in `config/mcp.servers.json` as `uv run python -m lionel.skills.system_server`.

`shell_server.py` is the sharpest edge in the entire project. An agent with unconstrained shell access on a Windows host is a liability, not a feature. The allowlist is a hard requirement, not a v2 nicety.

### 3.4 Commands

```bash
# develop a skill server against the MCP Inspector
uv run fastmcp dev src/lionel/skills/system_server.py

# run it as the host would
uv run python -m lionel.skills.system_server

# full host loop, one-shot text mode (no audio yet)
uv run python -m lionel --once "What is my current CPU load and free disk space?"
```

### 3.5 Definition of Done — Phase 3

- [ ] `uv sync` reproduces the environment from `uv.lock` on a clean checkout
- [ ] MCP Inspector lists every tool from all three skill servers with correct schemas
- [ ] `python -m lionel --once "check my CPU and disk"` produces a **real tool call** — verified in the trace log, not inferred from a plausible-sounding answer
- [ ] The same prompt succeeds under `provider = "anthropic"` **and** `provider = "ollama"`, with results side-by-side in `docs/decisions/ADR-0001-brain-adapter.md`
- [ ] `shell_server` **refuses** a non-allowlisted command (`rm -rf /`, `format c:`) and logs the refusal
- [ ] The host writes a durable fact to `qdrant-store` at the end of a session and recalls it on the next boot — Phases 2 and 3 proven wired together
- [ ] `pytest tests/test_phase3_skills.py` green; `ruff check` and `mypy src/` clean

---

# PHASE 4 — Sensory Layers (Kokoro-TTS, whisper.cpp, openWakeWord)

**Goal:** L.I.O.N.E.L listens for its name, understands speech, and answers out loud — all locally, no network.

**Est. effort:** 3–4 sessions. This is the highest-risk phase; native compilation and audio device handling are where Windows fights back.

### 4.1 whisper.cpp — speech recognition

```bash
cd /c/Users/deniz/Desktop/L.I.O.N.E.L
git submodule add https://github.com/ggml-org/whisper.cpp vendor/whisper.cpp
cd vendor/whisper.cpp
git checkout <pinned-tag>          # never track master; ggml ABI moves fast

# CPU build
cmake -B build
cmake --build build --config Release -j

# NVIDIA build (requires CUDA Toolkit; do CPU first, prove it, then optimize)
# cmake -B build -DGGML_CUDA=1
# cmake --build build --config Release -j

# model download — .cmd variant on Windows, .sh assumes a Unix environment
cmd //c "models\\download-ggml-model.cmd base.en"

# verify
./build/bin/Release/whisper-cli.exe -m models/ggml-base.en.bin -f samples/jfk.wav
```

Binary lands at `vendor/whisper.cpp/build/bin/Release/whisper-cli.exe`. Model selection: start `base.en` (fast, ~140MB, good enough for commands); upgrade to `large-v3-turbo` if accuracy on your accent and mic disappoints. Measure before upgrading — a larger model that adds 1.5s of latency to every utterance is a worse assistant even if the transcript is prettier.

**Build must run from a "Developer Command Prompt for VS 2022"** so `cl.exe` and the Windows SDK are on `PATH`. `scripts/build_whisper.sh` will shell out via `cmd //c` to source `vcvars64.bat` first, keeping the Git Bash entrypoint intact.

### 4.2 Kokoro-TTS — speech synthesis

82M-parameter ONNX model. Runs comfortably on CPU, near-real-time, no GPU required.

```bash
uv add --optional sensory kokoro-onnx soundfile

# models are NOT in the pip package — fetch separately into models/kokoro/
#   kokoro-v1.0.onnx   (~330MB)
#   voices-v1.0.bin
bash scripts/fetch_models.sh
```

`sensory/tts.py` synthesizes to a numpy array at 24 kHz and streams to `sounddevice` **sentence by sentence**, so L.I.O.N.E.L starts speaking while the brain is still generating. Waiting for a full paragraph before the first phoneme is what makes local assistants feel dead.

### 4.3 openWakeWord — always-on trigger

```bash
uv add --optional sensory openwakeword onnxruntime
```

> **Windows constraint:** openWakeWord installs **onnxruntime only** on Windows — modern `tflite-runtime` has no Windows support. Every model must therefore be loaded with `inference_framework="onnx"`. Passing a `.tflite` model will fail at runtime.

Two-step plan:

1. **Bootstrap** with a pretrained model (`hey_jarvis`) to prove the audio pipeline end-to-end. Don't block the pipeline on model training.
2. **Train** a custom `"Hey Lionel"` ONNX model from synthetic TTS data (~45 min on GPU) once the pipeline works. Tune the detection threshold against a recorded false-activation set — an assistant that wakes to the TV is worse than one that needs saying twice.

### 4.4 The full-duplex pipeline

```
sounddevice ring buffer (16 kHz mono, 80 ms frames)
        │
        ├──► openWakeWord ──── score > threshold ──┐
        │                                          ▼
        └──► silero-vad ◄──────────── capture window opens
                 │  speech end detected (400 ms trailing silence)
                 ▼
          write WAV to temp ──► whisper-cli.exe ──► transcript
                                                        │
                                                        ▼
                                        host/loop.py (brain + MCP tools)
                                                        │
                                             sentence-chunked stream
                                                        ▼
                                        kokoro-onnx ──► sounddevice playback
                                                        │
                              barge-in: wake word during playback → abort, re-listen
```

**Latency budget** — the number that determines whether this feels alive:

| Stage | Target |
|---|---|
| Wake detection | < 100 ms |
| VAD endpointing | 400 ms trailing silence |
| whisper.cpp `base.en`, 5 s utterance | < 800 ms |
| Brain first token | < 1200 ms |
| Kokoro first audio | < 300 ms |
| **Wake → first spoken word** | **< 2.5 s** |

### 4.5 Definition of Done — Phase 4

- [ ] `whisper-cli.exe` transcribes `samples/jfk.wav` correctly
- [ ] Microphone enumeration works; `audio_io.py` captures 16 kHz mono without dropouts over a 10-minute soak
- [ ] Wake word fires reliably at conversational volume from 3 m, and produces **zero** false activations across 30 minutes of podcast audio
- [ ] Kokoro speaks a test sentence through the default output device with no clipping or artifacts
- [ ] **Full loop, no keyboard:** say *"Hey Lionel, how much disk space do I have left?"* → hear a spoken answer containing the real number from `system_server`. This single test exercises all four phases at once
- [ ] Barge-in works: speaking the wake word mid-response aborts playback within 300 ms
- [ ] Measured wake→speech latency is under 2.5 s and recorded in `docs/RUNBOOK.md`
- [ ] **Airplane-mode test:** disconnect the network, set `provider = "ollama"`, repeat the full loop. If this passes, "fully local and autonomous" is a fact rather than a claim

---

## 5. Phase Gates

No phase begins until the prior phase's Definition of Done is fully checked and Efe has signed off.

| Gate | Blocks | Hard requirement |
|---|---|---|
| G1 → Phase 2 | Memory work | Filesystem + GitHub MCP both responding; repo clean |
| G2 → Phase 3 | Skills work | Qdrant survives a container restart with data intact |
| G3 → Phase 4 | Sensory work | Text-mode agent completes a real tool call on both brain providers |
| G4 → v1.0 | Release | Voice loop passes offline |

## 6. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | whisper.cpp CUDA build fails on Windows (common — CUDA/MSVC version mismatch) | High | Med | Ship CPU build first; treat CUDA as an optimization, never a blocker |
| R2 | Local model tool-calling is unreliable vs. the API | High | High | ADR-0001 exists precisely for this. Measure both at G3; if Ollama fails, we know early and can pick a better-tuned model |
| R3 | Wake word false activations make the agent unusable | Med | High | Threshold tuning against a recorded negative set; custom model trained on Efe's actual voice |
| R4 | Embedding model swap silently invalidates stored vectors | Med | High | Pin `EMBEDDING_MODEL` in config; any change requires a documented full re-index |
| R5 | Audio device changes (headphones plugged in) crash the stream | Med | Med | Device-change callback + stream restart in `audio_io.py` |
| R6 | Shell skill abused by prompt injection through a document the agent reads | Low | Critical | Hard allowlist, `shell=False`, no interpolation. Untrusted text never reaches a shell |
| R7 | Secrets committed to git | Low | Critical | `.gitignore` verified at G1; pre-commit secret scan added in Phase 3 |

---

## 7. Working Method

### 7.1 `<thought>` tags

Before any non-trivial module — a FastMCP skill server, the brain adapter, the STT/TTS pipeline — I will open a `<thought>` block and work through:

- the file hierarchy and where the new code belongs
- interface and data-flow design, and what the module deliberately does *not* know about
- alternatives considered and why they lost
- failure modes and the guardrails for each

Everything outside those tags stays clean and professional: the decision, the code, the command to run. The `<thought>` block is where the reasoning is visible and auditable; the response is where the answer lives. If the thinking is boring, the tags won't appear — they're for real design forks, not ceremony.

### 7.2 Project memory

Every architectural decision, library choice, and rejected alternative gets written to Qdrant via `qdrant-store` the moment it's made — the "why", not just the "what". When we return to a module weeks later, I query `qdrant-find` **before** proposing changes, so we don't relitigate settled decisions or silently contradict them. This is why Phase 2 sits so early in the plan: from G2 onward, the project remembers itself.

### 7.3 GitHub — the golden rule

> **I will never `commit` or `push` autonomously.**

The workflow is fixed:

1. I write and stage the code.
2. I present the diff and a proposed commit message to Efe.
3. **Efe explicitly approves.**
4. Only then do I commit, with the `[LIONEL-CORE]` prefix.

No exceptions, no "this one was trivial", no bundling an unapproved change into an approved commit. If I ever appear to have committed without asking, treat it as a bug and revert it.

Commit format:

```
[LIONEL-CORE] Phase 2: Qdrant memory service + MCP registry entry

- docker-compose.yml with named volume and healthcheck
- config/mcp.servers.json: qdrant server with custom tool descriptions
- scripts/memory_{up,down,backup}.sh
```

---

## 8. Immediate Next Action

**Phase 1, Step 1:** create the directory tree, `.gitignore`, `.gitattributes`, `.env.example`, `config/mcp.servers.json`, `scripts/check_env.sh`, and `docs/decisions/ADR-0001-brain-adapter.md` under `C:\Users\deniz\Desktop\L.I.O.N.E.L` via the `filesystem` MCP tool — then run `scripts/check_env.sh` and report the preflight table before touching anything else.

**Awaiting Efe's approval to proceed.**

#!/usr/bin/env bash
# scripts/resolve_artifacts.sh — close out the UNRESOLVED entries in artifacts.lock.toml
#
# ADR-0013.  Run this ON EFE'S MACHINE, in Git Bash.  It downloads the five artifacts whose
# upstreams publish no digest, computes SHA-256 locally, and prints TOML ready to paste.
#
# WHY THIS SCRIPT EXISTS
#   Six of eleven artifacts were pinned from upstream-published digests (Hugging Face LFS
#   object ids, an OCI registry manifest, a git commit).  The remaining five have no
#   published hash anywhere:
#     - Kokoro's GitHub release assets predate the API digest field  -> digest: null
#     - openWakeWord v0.6.0 removed its model assets entirely (PR #50)
#     - GHCR will not serve a manifest without a bearer token
#   Those must be hashed locally.  This is trust-on-first-use: the FIRST download is
#   trusted, every subsequent one is verified.  It is weaker than an upstream-published
#   hash, and artifacts.lock.toml records that difference in `sha256_provenance` rather
#   than pretending the two are equivalent.
#
# WHAT IT WILL NOT DO
#   It will not invent a hash.  If a download fails, the entry stays UNRESOLVED and G0
#   stays blocked.  A fabricated checksum is worse than an absent one because it looks
#   verified.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/models"
mkdir -p "$OUT"/{kokoro,wakeword}

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
ok()   { printf '   \033[32mok\033[0m   %s\n' "$*"; }
warn() { printf '   \033[33mwarn\033[0m %s\n' "$*"; }
die()  { printf '   \033[31mFAIL\033[0m %s\n' "$*" >&2; exit 1; }

need() { command -v "$1" >/dev/null 2>&1 || die "missing required tool: $1"; }
need curl; need sha256sum

# expected_size guards against a truncated download producing a stable-but-wrong hash,
# which would then be committed and enforced forever.
fetch_and_hash() {
  local key="$1" url="$2" dest="$3" expect_bytes="$4"
  say "$key"
  if [ -f "$dest" ]; then
    ok "already present, not re-downloading: $dest"
  else
    printf '   downloading %s\n' "$url"
    curl -fL --retry 3 --progress-bar -o "$dest.part" "$url" || die "download failed: $url"
    mv "$dest.part" "$dest"
  fi
  local got_bytes; got_bytes=$(stat -c%s "$dest" 2>/dev/null || stat -f%z "$dest")
  if [ -n "$expect_bytes" ] && [ "$got_bytes" != "$expect_bytes" ]; then
    die "size mismatch for $key: expected $expect_bytes, got $got_bytes (truncated or upstream changed — DO NOT record this hash)"
  fi
  local h; h=$(sha256sum "$dest" | cut -d' ' -f1)
  ok "bytes  = $got_bytes"
  ok "sha256 = $h"
  printf '%s\t%s\t%s\n' "$key" "$h" "$got_bytes" >> "$ROOT/.resolved.tsv"
}

: > "$ROOT/.resolved.tsv"

# ── 1 & 2.  Kokoro (GitHub release assets, digest: null) ──────────────────────
fetch_and_hash models.kokoro_v1 \
  "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx" \
  "$OUT/kokoro/kokoro-v1.0.onnx" 325532387

fetch_and_hash models.kokoro_voices \
  "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin" \
  "$OUT/kokoro/voices-v1.0.bin" 28214398

# ── 3 & 4.  openWakeWord (assets removed from releases; fetched by the library) ─
say "models.wake_bootstrap + models.wake_preprocessors"
if command -v uv >/dev/null 2>&1; then
  uv run --with openwakeword python -c "
import openwakeword.utils as u, pathlib
d = pathlib.Path(r'''$OUT/wakeword''')
d.mkdir(parents=True, exist_ok=True)
u.download_models(target_directory=str(d))
print('downloaded to', d)
"
  for f in "$OUT"/wakeword/*.onnx; do
    [ -e "$f" ] || { warn "no .onnx files landed — check openwakeword version"; break; }
    printf '   %-34s %s\n' "$(basename "$f")" "$(sha256sum "$f" | cut -d' ' -f1)"
    printf 'wakeword/%s\t%s\t%s\n' "$(basename "$f")" \
      "$(sha256sum "$f" | cut -d' ' -f1)" "$(stat -c%s "$f")" >> "$ROOT/.resolved.tsv"
  done
  ok "melspectrogram.onnx and embedding_model.onnx must both appear above — without them no wake model runs"
else
  warn "uv not found; skipping. Install uv, then re-run."
fi

# ── 5.  GHCR image digest (needs the token exchange docker does for us) ────────
say "images.github_mcp"
if command -v docker >/dev/null 2>&1; then
  docker buildx imagetools inspect ghcr.io/github/github-mcp-server 2>/dev/null \
    | grep -iE '^(Name|Digest):' || warn "inspect failed — is Docker Desktop running?"
  ok "record the index Digest AND pick a version tag; :latest is mutable and must not be pinned"
else
  warn "docker not found; skipping."
fi

say "SUMMARY"
if [ -s "$ROOT/.resolved.tsv" ]; then
  column -t "$ROOT/.resolved.tsv" 2>/dev/null || cat "$ROOT/.resolved.tsv"
  printf '\nPaste these into artifacts.lock.toml as:\n'
  printf '    sha256 = "<hash>"\n    sha256_provenance = "local-tofu"\n'
  printf '    status = "RESOLVED"      # and delete the blocker/resolution keys\n'
  printf '\nThen update [meta] resolved/unresolved counts and re-run:\n'
  printf '    bash scripts/verify_artifacts.sh\n'
else
  die "nothing resolved"
fi

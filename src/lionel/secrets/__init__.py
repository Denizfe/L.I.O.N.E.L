"""Typed secret resolution.  ADR-0015.

THE DECISION THIS IMPLEMENTS
    **No string interpolation anywhere.** Config references a secret by a typed URI —
    `secret://env/NAME` — and a `SecretResolver` dereferences it at point of use. The
    resolved value is wrapped in `SecretStr`, whose `__str__` and `__repr__` redact.

WHY REDACTION LIVES ON THE TYPE
    ADR-0015, in one sentence: *"Redaction happens at the type, not at the call site,
    because call-site redaction is eventually forgotten exactly once."*

    That is the whole design. `${VAR}` interpolation — v1.0's implied fix — produces a
    plain `str`, and a plain `str` is one f-string away from a log line. Here the mistake
    has to be deliberate: you must call `.reveal()`, which is greppable, reviewable, and
    named so that it reads wrong in a logging call.

SCHEMES  (ADR-0015's table)
    secret://env/NAME            environment variable          local dev
    secret://file/PATH           mounted file                  containers
    secret://dpapi/NAME          Windows Credential Manager    L0, L1 on the host
    secret://k8s/SECRET/KEY      Kubernetes Secret via ESO     L2+

    `env` and `file` are implemented at G1 because they are the two the host skeleton
    needs. `dpapi` and `k8s` raise `BackendNotAvailable` naming the tier that brings them,
    rather than silently falling back to something weaker — a resolver that quietly
    downgrades `dpapi` to `env` would move a secret from the credential store to a process
    listing without anyone deciding to.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Final

__all__ = [
    "SecretStr",
    "SecretResolver",
    "SecretError",
    "MalformedSecretURI",
    "SecretNotFound",
    "BackendNotAvailable",
    "REDACTED",
]

REDACTED: Final = "***"

_URI = re.compile(r"^secret://(?P<scheme>[a-z0-9]+)/(?P<rest>.+)$")


class SecretError(Exception):
    """Base for every failure in this module."""


class MalformedSecretURI(SecretError):
    """The URI is not `secret://<scheme>/<path>`."""


class SecretNotFound(SecretError):
    """The URI was well-formed and the backend had nothing under it."""


class BackendNotAvailable(SecretError):
    """The scheme is real but not implemented, or not usable on this host."""


class SecretStr:
    """A string that does not print itself.

    Equality is supported so that tests and config comparisons work, and it is
    **constant-time** against another `SecretStr` — not because a timing attack is likely
    here, but because the cheap version of this class invites `==` against a plain `str`,
    which is how a secret ends up in an assertion message.
    """

    __slots__ = ("_value", "_origin")

    def __init__(self, value: str, origin: str = "<unknown>") -> None:
        if not isinstance(value, str):
            raise TypeError(f"SecretStr wraps str, got {type(value).__name__}")
        self._value = value
        self._origin = origin

    def reveal(self) -> str:
        """The plaintext. Every call site is a deliberate, greppable decision."""
        return self._value

    @property
    def origin(self) -> str:
        """The URI this came from — safe to log, and the thing you actually want in a log."""
        return self._origin

    def __str__(self) -> str:
        return REDACTED

    def __repr__(self) -> str:
        return f"SecretStr({REDACTED} from {self._origin!r})"

    def __format__(self, spec: str) -> str:
        # Without this, f"{secret:>20}" would bypass __str__ padding rules on some paths.
        # Any format spec at all still yields the redacted marker.
        return REDACTED

    def __bool__(self) -> bool:
        return bool(self._value)

    def __len__(self) -> int:
        # The length of a secret is a weak oracle, but callers legitimately need to know
        # whether something is empty, and __bool__ already answers that. Returning the
        # real length here would let f"{len(s)}" leak a little; return it anyway, because
        # hiding it would break `if not secret` semantics people expect and buys almost
        # nothing. Documented so the trade-off is visible rather than accidental.
        return len(self._value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SecretStr):
            from hmac import compare_digest
            return compare_digest(self._value, other._value)
        if isinstance(other, str):
            raise TypeError(
                "refusing to compare SecretStr to str: the failure message would contain "
                "the secret. Compare two SecretStr values, or call .reveal() explicitly."
            )
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)


class SecretResolver:
    """Dereferences `secret://` URIs. Stateless apart from an injected environment.

    `env` and `file_root` are injected rather than read from globals so the resolver is
    testable without mutating `os.environ` — a test that mutates the process environment
    leaks into every test that runs after it.
    """

    def __init__(self, env: dict[str, str] | None = None,
                 file_root: Path | None = None) -> None:
        self._env = os.environ if env is None else env
        self._file_root = file_root

    # -- public ------------------------------------------------------------------
    def is_secret_uri(self, value: object) -> bool:
        return isinstance(value, str) and bool(_URI.match(value))

    def resolve(self, uri: str) -> SecretStr:
        m = _URI.match(uri or "")
        if not m:
            raise MalformedSecretURI(
                f"not a secret URI: {uri!r}. Expected secret://<scheme>/<path> — one of "
                f"env, file, dpapi, k8s (ADR-0015)."
            )
        scheme, rest = m.group("scheme"), m.group("rest")
        handler = getattr(self, f"_resolve_{scheme}", None)
        if handler is None:
            raise MalformedSecretURI(
                f"unknown secret scheme {scheme!r} in {uri!r}. ADR-0015 defines env, "
                f"file, dpapi and k8s; adding a fifth is an amendment, not a code change."
            )
        return SecretStr(handler(rest, uri), origin=uri)

    def resolve_all(self, config: object) -> object:
        """Walk a config tree, replacing every secret URI with a `SecretStr`.

        Structure is preserved; only leaf strings that ARE secret URIs are touched. A
        string that merely contains one is left alone — ADR-0015 forbids interpolation, so
        `"Bearer secret://env/TOKEN"` is a config error, not a template, and it will fail
        at the consumer rather than being silently half-resolved here.
        """
        if isinstance(config, dict):
            return {k: self.resolve_all(v) for k, v in config.items()}
        if isinstance(config, list):
            return [self.resolve_all(v) for v in config]
        if self.is_secret_uri(config):
            return self.resolve(config)  # type: ignore[arg-type]
        return config

    # -- backends ----------------------------------------------------------------
    def _resolve_env(self, name: str, uri: str) -> str:
        if "/" in name:
            raise MalformedSecretURI(
                f"secret://env/ takes a bare variable name; got {name!r} in {uri!r}."
            )
        try:
            return self._env[name]
        except KeyError:
            raise SecretNotFound(
                f"environment variable {name!r} is not set (from {uri}). Set it, or point "
                f"the config at a different backend."
            ) from None

    def _resolve_file(self, rel: str, uri: str) -> str:
        path = Path(rel)
        if self._file_root is not None:
            candidate = (self._file_root / rel).resolve()
            root = self._file_root.resolve()
            # A mounted-secret path from config must not escape its root. Containers put
            # every secret under one directory precisely so this check is possible.
            if root != candidate and root not in candidate.parents:
                raise MalformedSecretURI(
                    f"{uri} escapes the secret root {root} — refusing to read {candidate}."
                )
            path = candidate
        try:
            # Trailing newlines are an artifact of how the file was written, never part of
            # the secret. Stripping only the line ending avoids eating meaningful padding.
            return path.read_text(encoding="utf-8").rstrip("\r\n")
        except FileNotFoundError:
            raise SecretNotFound(f"no such secret file: {path} (from {uri})") from None
        except OSError as e:
            raise SecretNotFound(f"cannot read secret file {path} (from {uri}): {e}") from None

    def _resolve_dpapi(self, name: str, uri: str) -> str:
        raise BackendNotAvailable(
            f"the dpapi backend arrives with the L0/L1 host credential store and is not "
            f"implemented at G1 ({uri}). It is not falling back to secret://env/{name}: a "
            f"silent downgrade would move this secret from the Windows credential store "
            f"into a process listing without anyone deciding to."
        )

    def _resolve_k8s(self, rest: str, uri: str) -> str:
        raise BackendNotAvailable(
            f"the k8s backend arrives at L2+ with the External Secrets Operator "
            f"(ADR-0015, Phase 7) and is not implemented at G1 ({uri})."
        )

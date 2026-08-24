"""Unit tests for lionel.secrets.  ADR-0015, ADR-0027 layer 1.

Runner is `unittest` from the standard library, deliberately. ADR-0027 defines five test
LAYERS and names no runner; pytest would be a new dependency, and Architecture_Freeze.md §4
requires an ADR and Efe's approval for one. `unittest` costs nothing and the layer
boundaries are what the ADR actually decided.

    python3 -m unittest discover -s tests -t . -v
"""
import os
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from lionel.secrets import (  # noqa: E402
    REDACTED,
    BackendNotAvailable,
    MalformedSecretURI,
    SecretNotFound,
    SecretResolver,
    SecretStr,
)

PLAINTEXT = "correct-horse-battery-staple"


class TestSecretStrRedacts(unittest.TestCase):
    """The G1 DoD phrase is 'its value redacts in log output'. These are that clause."""

    def setUp(self):
        self.s = SecretStr(PLAINTEXT, origin="secret://env/TEST")

    def test_str_redacts(self):
        self.assertEqual(str(self.s), REDACTED)
        self.assertNotIn(PLAINTEXT, str(self.s))

    def test_repr_redacts_but_keeps_the_origin(self):
        r = repr(self.s)
        self.assertNotIn(PLAINTEXT, r)
        self.assertIn("secret://env/TEST", r)

    def test_fstring_redacts(self):
        self.assertNotIn(PLAINTEXT, f"token={self.s}")

    def test_format_spec_cannot_bypass_redaction(self):
        # f"{s:>40}" takes a different path through the formatting machinery than f"{s}".
        self.assertNotIn(PLAINTEXT, f"{self.s:>40}")
        self.assertNotIn(PLAINTEXT, "{:s}".format(self.s))

    def test_percent_formatting_redacts(self):
        self.assertNotIn(PLAINTEXT, "token=%s" % (self.s,))

    def test_logging_call_redacts(self):
        """The failure this ADR exists to prevent, exercised through real logging."""
        import io
        import logging
        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        log = logging.getLogger("lionel.test.secrets")
        log.handlers = [handler]
        log.propagate = False
        log.setLevel(logging.INFO)
        log.info("resolved %s", self.s)
        log.info(f"interpolated {self.s}")
        handler.flush()
        self.assertNotIn(PLAINTEXT, buf.getvalue())
        self.assertIn(REDACTED, buf.getvalue())

    def test_reveal_is_the_only_way_out(self):
        self.assertEqual(self.s.reveal(), PLAINTEXT)

    def test_comparison_to_plain_str_is_refused(self):
        # Not a convenience refusal: assertEqual against a str would print the secret in
        # the failure message, which is a leak that only happens when something is already
        # going wrong.
        with self.assertRaises(TypeError):
            _ = self.s == PLAINTEXT

    def test_equality_between_secrets(self):
        self.assertEqual(self.s, SecretStr(PLAINTEXT))
        self.assertNotEqual(self.s, SecretStr("something-else"))

    def test_rejects_non_str(self):
        with self.assertRaises(TypeError):
            SecretStr(b"bytes")  # type: ignore[arg-type]


class TestEnvBackend(unittest.TestCase):
    def setUp(self):
        self.r = SecretResolver(env={"TOKEN": PLAINTEXT})

    def test_resolves(self):
        self.assertEqual(self.r.resolve("secret://env/TOKEN").reveal(), PLAINTEXT)

    def test_origin_is_recorded(self):
        self.assertEqual(self.r.resolve("secret://env/TOKEN").origin, "secret://env/TOKEN")

    def test_missing_variable_names_itself(self):
        with self.assertRaises(SecretNotFound) as cm:
            self.r.resolve("secret://env/ABSENT")
        self.assertIn("ABSENT", str(cm.exception))

    def test_does_not_touch_the_process_environment(self):
        self.assertNotIn("TOKEN", os.environ)


class TestFileBackend(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "token").write_text(PLAINTEXT + "\n", encoding="utf-8")
        self.r = SecretResolver(file_root=self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_resolves_and_strips_the_trailing_newline(self):
        self.assertEqual(self.r.resolve("secret://file/token").reveal(), PLAINTEXT)

    def test_missing_file(self):
        with self.assertRaises(SecretNotFound):
            self.r.resolve("secret://file/absent")

    def test_path_traversal_is_refused(self):
        with self.assertRaises(MalformedSecretURI):
            self.r.resolve("secret://file/../../etc/passwd")


class TestUnimplementedBackends(unittest.TestCase):
    """Not-yet-implemented must fail loudly. A silent downgrade is the dangerous outcome."""

    def setUp(self):
        self.r = SecretResolver(env={"NAME": "from-env"})

    def test_dpapi_refuses_rather_than_falling_back(self):
        with self.assertRaises(BackendNotAvailable) as cm:
            self.r.resolve("secret://dpapi/NAME")
        self.assertNotIn("from-env", str(cm.exception))

    def test_k8s_refuses(self):
        with self.assertRaises(BackendNotAvailable):
            self.r.resolve("secret://k8s/lionel/token")


class TestURIParsing(unittest.TestCase):
    def setUp(self):
        self.r = SecretResolver(env={})

    def test_rejects_non_uri(self):
        for bad in ("", "TOKEN", "env/TOKEN", "secret:/env/TOKEN", "http://x/y",
                    "secret://env", "secret://"):
            with self.subTest(uri=bad), self.assertRaises(MalformedSecretURI):
                self.r.resolve(bad)

    def test_rejects_unknown_scheme(self):
        with self.assertRaises(MalformedSecretURI):
            self.r.resolve("secret://vault/kv/token")

    def test_is_secret_uri(self):
        self.assertTrue(self.r.is_secret_uri("secret://env/A"))
        self.assertFalse(self.r.is_secret_uri("Bearer secret://env/A"))
        self.assertFalse(self.r.is_secret_uri(None))


class TestResolveAll(unittest.TestCase):
    def setUp(self):
        self.r = SecretResolver(env={"TOKEN": PLAINTEXT})

    def test_walks_nested_config(self):
        cfg = {"brain": {"url": "http://localhost:11434",
                         "api_key": "secret://env/TOKEN"},
               "list": ["plain", "secret://env/TOKEN"]}
        out = self.r.resolve_all(cfg)
        self.assertIsInstance(out["brain"]["api_key"], SecretStr)
        self.assertIsInstance(out["list"][1], SecretStr)
        self.assertEqual(out["brain"]["url"], "http://localhost:11434")
        self.assertEqual(out["list"][0], "plain")

    def test_interpolation_is_not_a_feature(self):
        """ADR-0015 forbids interpolation, so an embedded URI stays a plain string.

        It then fails at the consumer, which is the right place: half-resolving it here
        would reintroduce exactly the `${VAR}` behaviour the ADR rejected.
        """
        out = self.r.resolve_all({"header": "Bearer secret://env/TOKEN"})
        self.assertIsInstance(out["header"], str)
        self.assertNotIsInstance(out["header"], SecretStr)


if __name__ == "__main__":
    unittest.main()

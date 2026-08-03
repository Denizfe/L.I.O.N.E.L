#!/usr/bin/env python3
"""GATE: protobuf compile + field-number hygiene.  ADR-0028."""
import subprocess, sys, tempfile, os, re
from pathlib import Path
from _lib import Gate, ROOT, rel, read_text, gate_error

def main():
    g = Gate("protobuf", "Protobuf validation", ["ADR-0028", "ADR-0006"])
    d = ROOT / "contracts" / "grpc" / "v1"
    protos = sorted(d.glob("*.proto"))
    if not protos:
        gate_error("no .proto files under contracts/grpc/v1")

    try:
        import grpc_tools.protoc  # noqa
        from google.protobuf import descriptor_pb2
    except ImportError as e:
        gate_error("grpcio-tools not installed", f"pip install grpcio-tools  ({e})")

    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "desc")
        r = subprocess.run(
            [sys.executable, "-m", "grpc_tools.protoc", f"-I{d}", f"--descriptor_set_out={out}",
             *[p.name for p in protos]],
            capture_output=True, text=True, cwd=d)
        g.check()
        if r.returncode != 0:
            for line in (r.stderr or "").strip().splitlines():
                m = re.match(r"^(\S+?):(\d+):(\d+):\s*(.+)$", line)
                g.fail("PROTO-001", m.group(4) if m else line,
                    "A .proto that does not compile cannot generate stubs, so the data plane has "
                    "no wire format. ADR-0006 depends on protobuf being the media transport.",
                    "Fix the error. A common cause: referencing a message defined in a sibling "
                    "file without importing it — and importing across services would break the "
                    "dependency tree, so move the shared type to common.proto instead.",
                    f"contracts/grpc/v1/{m.group(1)}" if m else None,
                    int(m.group(2)) if m else None)
            g.report_and_exit()

        fds = descriptor_pb2.FileDescriptorSet()
        fds.ParseFromString(Path(out).read_bytes())

        for f in fds.file:
            r_ = f"contracts/grpc/v1/{f.name}"
            for msg in f.message_type:
                g.check()
                nums = [fl.number for fl in msg.field]
                if len(nums) != len(set(nums)):
                    dup = [n for n in set(nums) if nums.count(n) > 1]
                    g.fail("PROTO-002", f"duplicate field number(s) {dup} in `{msg.name}`",
                        "Reusing a field number silently reinterprets old bytes as a new meaning. "
                        "It does not error — it lies. This is the worst failure mode protobuf offers.",
                        "Give the new field a fresh number and `reserved` the old one permanently.", r_)
            for en in f.enum_type:
                g.check()
                if en.value and en.value[0].number != 0:
                    g.fail("PROTO-003", f"enum `{en.name}` does not reserve 0",
                        "proto3 treats 0 as the default for an unset field. Without an explicit "
                        "UNSPECIFIED at 0, an omitted field is indistinguishable from a real value, "
                        "and consumers cannot safely treat unknown enum values as 'unset'.",
                        f"Add `{en.name.upper()}_UNSPECIFIED = 0;` as the first value.", r_)

        # The dependency graph must stay a tree: a TTS service must not depend on STT.
        deps = {f.name: list(f.dependency) for f in fds.file}
        for name, ds in deps.items():
            for dep in ds:
                if dep != "common.proto" and name != "common.proto":
                    g.check()
                    g.fail("PROTO-004", f"`{name}` imports `{dep}`",
                        "Service protos must depend only on common.proto. A TTS service that "
                        "imports the STT proto acquires a dependency on a service it never calls, "
                        "and the graph stops being a tree.",
                        "Move the shared type into common.proto.", f"contracts/grpc/v1/{name}")

        g.note(f"{len(fds.file)} files · "
               f"{sum(len(f.message_type) for f in fds.file)} messages · "
               f"{sum(len(f.enum_type) for f in fds.file)} enums")
    g.report_and_exit()

if __name__ == "__main__": main()

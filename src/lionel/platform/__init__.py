"""Platform-specific plumbing, isolated so the rest of the codebase can ignore it.

ADR-0002 and ADR-0014: Windows + Git Bash is the host runtime, not a developer
convenience. The Windows/POSIX difference is contained in this package by design — a
caller that branches on `sys.platform` outside here is a bug, for the same reason
ADR-0001 forbids callers branching on provider name.
"""

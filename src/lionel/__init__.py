"""L.I.O.N.E.L — a local-first voice assistant with an offline autonomy guarantee.

Phase 1 (Gate G1): the host runtime skeleton and control plane. There is deliberately no
feature code here yet — MASTER_PLAN_v2 §10 puts memory at G2, the brain at G3 and the
sensory stack at G6.

Everything under this package is constrained by the contracts frozen in Phase 0. The
architecture checksum in Architecture_Freeze.md §2 covers those contracts; it does not
cover this package, because implementation conforming to a frozen contract is exactly the
work §4 permits without an ADR. Changing a contract is the part that needs one.
"""

__version__ = "0.1.0"

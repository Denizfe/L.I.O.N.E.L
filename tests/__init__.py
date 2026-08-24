"""Test suites, one package per ADR-0027 layer.

These are packages rather than bare directories so that `unittest discover` can import
them. Runner: the standard library.

    python3 -m unittest discover -s tests -t .

ADR-0027 names five LAYERS and no runner. pytest would be a new dependency, and
Architecture_Freeze.md §4 requires an ADR and Efe's approval for one — so if this suite
ever outgrows `unittest`, that is an ADR, not a `pip install`.
"""

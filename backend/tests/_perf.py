"""Shared helper for timing-sensitive tests (not collected — no ``test_`` prefix).

Coverage.py instruments every line, which inflates wall-clock time several-fold. Tests that assert
an ABSOLUTE timing bound (e.g. "this op takes < 1 ms") are therefore unreliable under ``pytest --cov``
and should be skipped there — the behaviour they guard is unchanged, only the timing measurement is
distorted. Behaviour/ratio assertions don't need this.
"""


def under_coverage() -> bool:
    """True iff coverage.py is actively measuring this run."""
    try:
        import coverage
        return coverage.Coverage.current() is not None
    except Exception:
        return False

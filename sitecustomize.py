"""Interpreter-startup shim: make `sqlite3` resolvable on a CPython built without it.

The CPython used here (3.11.4 at /usr/local/bin, shared with the sister project wb-mqtt-bridge) is
compiled WITHOUT the stdlib `_sqlite3` extension. `coverage.py` imports `sqlite3` at module load
(when the pytest-cov plugin is registered, before any conftest runs), so the alias MUST be in place
at interpreter startup — which is what `sitecustomize` gives us (Python imports it during site init,
before pytest/coverage load). We alias the self-contained `pysqlite3` (from `pysqlite3-binary`) onto
the `sqlite3` name.

This file is the committed source of truth. It is also COPIED into the venv's site-packages so the
interpreter auto-imports it (a repo-root sitecustomize is NOT on sys.path at site-init time). See
`scripts/install_sqlite_shim.sh`, run after creating/recreating the venv.
"""

import sys

try:
    import sqlite3  # noqa: F401
    sqlite3.connect(":memory:").close()
except (ImportError, AttributeError):
    try:
        import pysqlite3  # type: ignore
        sys.modules["sqlite3"] = pysqlite3
        sys.modules["sqlite3.dbapi2"] = pysqlite3.dbapi2
    except ImportError:
        sys.stderr.write(
            "WARNING: neither stdlib sqlite3 nor pysqlite3 is available; "
            "coverage and any sqlite-backed code will fail.\n"
        )

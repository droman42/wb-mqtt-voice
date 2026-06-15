#!/usr/bin/env bash
# Install the sqlite3-via-pysqlite3 startup shim into the active venv's site-packages.
#
# The runtime CPython here is built without the stdlib `_sqlite3` extension, which coverage.py
# needs. `sitecustomize.py` (committed at the repo root) aliases the self-contained `pysqlite3`
# onto `sqlite3` at interpreter startup — but only a sitecustomize ON sys.path at site-init time is
# auto-imported, i.e. one inside site-packages. This copies it there.
#
# Run once after `uv venv` / `uv sync` recreates the venv:
#     bash scripts/install_sqlite_shim.sh
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
src="$root/sitecustomize.py"
sp="$("$root/.venv/bin/python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"

cp "$src" "$sp/sitecustomize.py"
echo "installed sqlite shim → $sp/sitecustomize.py"
"$root/.venv/bin/python" -c "import sqlite3; print('sqlite3 resolves to:', sqlite3.__name__, '| version', sqlite3.sqlite_version)"

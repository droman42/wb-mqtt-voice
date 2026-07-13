"""
Irene Voice Assistant Version Information

Central version definition for the entire project. Everything derives from here: `pyproject.toml`
reads it via `version = {attr = ...}`, FastAPI's `info.version`, `/health`, and `CoreConfig.version`.

Why 0.5.x and not 15.x (REL-4): the old `15.0.0` claimed fourteen prior major releases of this
codebase, and there were none — the only tags this repo ever carried are `8.1` (inherited 2023
upstream history) and `v12-final`. Under semver:

  * MAJOR 0 — the public API is not frozen, which is true and about to be truer: the package is
    being renamed and its loader/logging extracted into a shared commons.
  * MINOR 5 — the fifth design generation. Under 0.x the minor field IS the breaking axis, so a new
    design generation lands exactly where semver already expects a breaking change.
  * PATCH  — backwards-compatible fixes, and nothing else. The "15th iteration counting the
    ancestors we were inspired by" is a lineage fact; it lives in the CHANGELOG and README, where a
    reader will understand it and no version resolver will misread it.

1.0.0 belongs to the rename, under a package name with its own version namespace.
"""

__version__ = "0.5.2"
__version_info__ = (0, 5, 2)

# The architecture generation this codebase implements — the "V15 components" of the old logs.
# Deliberately NOT derived from __version__: it counts redesigns, not releases. It happens to equal
# the minor today (see above), and that is the point rather than a coincidence.
ARCH_GENERATION = 5

# Legacy compatibility
VERSION = __version__

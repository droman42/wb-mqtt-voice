"""Output delivery layer (ARCH-15 PR-2 / io_architecture §3-§4).

The symmetric twin of `irene/inputs/`: concrete output adapters (PR-3+) and the `OutputManager`
that registers them, routes results to them by modality (D-2), and applies the §3.1 capability
negotiation. This is a *delivery* layer — it depends inward on `irene.core` and the domain, and
nothing in `core`/`config`/`components`/`utils` may import it (enforced by import-linter).
"""

from .manager import OutputManager

__all__ = ["OutputManager"]

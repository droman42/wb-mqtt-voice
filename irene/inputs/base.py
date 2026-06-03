"""
Input adapter-side shared types.

ARCH-11 / S1: the input PORT and its value type were consolidated into
`irene/core/interfaces/input.py` (`InputPort` + `InputData`), so `core` depends
on the abstraction inward instead of reaching out to `inputs.base`. This module
now holds only the adapter-side exception shared by the concrete inputs.

Adapters import the port directly from the port layer:
    from ..core.interfaces.input import InputPort, InputData
"""


class ComponentNotAvailable(Exception):
    """Exception raised when a required component is not available"""
    pass

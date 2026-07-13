"""Satellite room-node clients (ARCH-36, design `docs/design/python_satellite.md`).

The device side of the `/ws/audio` (uplink) and `/ws/audio/reply` (downlink) wire contracts —
the same protocol the ESP32 firmware implements. The uplink core is adapted from locveil-eval'
proven `ws_audio_provider`; there is NO runtime dependency on the test framework.
"""

from .link import SatelliteLink, SatelliteReplyClient

__all__ = ["SatelliteLink", "SatelliteReplyClient"]

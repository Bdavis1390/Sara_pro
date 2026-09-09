"""Worldshepherd SARA local administration service."""

__version__ = "0.1.0"

# Bootstrap Sentinel assurance hardening at package initialization so callers
# cannot obtain the preserved legacy module before its P1-sensitive state
# transitions have been replaced by the bounded hardening overlay.
from . import infrastructure_assurance as _sentinel_assurance_hardening  # noqa: F401,E402

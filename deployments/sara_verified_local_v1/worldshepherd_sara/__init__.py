"""Worldshepherd SARA local administration service.

Sentinel authoritative custody is intentionally not imported at package
initialization. Production Sentinel entrypoints use the isolated custody client;
legacy/synthetic assurance modules must be imported explicitly by synthetic
validation tooling and are not an authority boundary.
"""

__version__ = "0.1.0"

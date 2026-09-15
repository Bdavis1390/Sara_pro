"""Runtime provenance helpers for bounded BAROS research evidence.

NON-CLINICAL. Provenance strengthens reproducibility and auditability; it does
not promote software evidence into physical, clinical, or regulatory evidence.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from importlib import metadata
from typing import Iterable


DEFAULT_DISTRIBUTIONS = ("numpy", "numba", "pydicom", "pymedphys", "pytest")


def installed_versions(distributions: Iterable[str] = DEFAULT_DISTRIBUTIONS) -> dict[str, str]:
    """Return exact installed distribution versions, marking absent packages explicitly."""
    versions: dict[str, str] = {}
    for name in sorted({str(item).strip() for item in distributions if str(item).strip()}):
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "NOT_INSTALLED"
    return versions


def runtime_provenance(distributions: Iterable[str] = DEFAULT_DISTRIBUTIONS) -> dict[str, object]:
    """Capture a deterministic process-level software-environment fingerprint."""
    payload: dict[str, object] = {
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
            "executable_version_info": list(sys.version_info[:5]),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "distributions": installed_versions(distributions),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    payload["environment_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload

#!/usr/bin/env python3
"""Load the governed Worldshepherd research-source registry into SARA.

Uses only the Python standard library. The SARA admin token is read from
SARA_ADMIN_TOKEN and is never written to disk or logged by this script.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib import error, request

ROOT = Path(__file__).resolve().parent
REGISTRY_PATH = ROOT / "research_source_registry_v1.json"
BASE_URL = os.getenv("SARA_BASE_URL", "http://127.0.0.1:9530").rstrip("/")
ADMIN_TOKEN = os.getenv("SARA_ADMIN_TOKEN", "").strip()


def fail(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def call(method: str, path: str, payload: dict | None = None) -> dict:
    if not ADMIN_TOKEN:
        fail("SARA_ADMIN_TOKEN is not set")

    data = None
    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}",
        "Accept": "application/json",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(
        f"{BASE_URL}{path}", data=data, headers=headers, method=method
    )
    try:
        with request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        fail(f"SARA returned HTTP {exc.code}: {body}")
    except error.URLError as exc:
        fail(f"Unable to reach SARA at {BASE_URL}: {exc.reason}")


def main() -> None:
    if not REGISTRY_PATH.exists():
        fail(f"Registry file not found: {REGISTRY_PATH}")

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    sources = registry.get("sources")
    if not isinstance(sources, list) or not sources:
        fail("Registry contains no sources")

    source_ids = [item.get("source_id") for item in sources if isinstance(item, dict)]
    if len(source_ids) != len(set(source_ids)):
        fail("Duplicate source_id detected")

    patch = {
        "values": {
            "research_source_registry": registry,
        }
    }
    result = call("PATCH", "/admin/registry", patch)

    stored = result.get("registry", {}).get("research_source_registry", {})
    stored_sources = stored.get("sources", []) if isinstance(stored, dict) else []
    if len(stored_sources) != len(sources):
        fail(
            f"Verification failed: expected {len(sources)} sources, "
            f"SARA returned {len(stored_sources)}"
        )

    print(
        f"Loaded {len(sources)} governed research sources into SARA "
        f"at {BASE_URL}."
    )
    print("SARA should also contain a registry_patched audit event for this change.")


if __name__ == "__main__":
    main()

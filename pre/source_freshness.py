#!/usr/bin/env python3
"""Worldshepherd PRE official opportunity-source freshness monitor.

This monitor verifies that allowlisted official opportunity surfaces are
reachable now and records a digest of the retrieved public content. It does not
claim every opportunity is discovered, that copied/indexed records are legally
official over agency originals, or that any opportunity is suitable/winnable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import ssl
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SOURCES = [
    {
        "id": "sam-contract-opportunities",
        "url": "https://sam.gov/opportunities",
        "official_domain": "sam.gov",
        "expected_any": ["Contract Opportunities", "Search Contract Opportunities"],
        "authority_note": "Official U.S. System for Award Management contract-opportunities surface.",
    },
    {
        "id": "sbir-open-topics",
        "url": "https://www.sbir.gov/topics?status=Open",
        "official_domain": "sbir.gov",
        "expected_any": ["Funding Opportunities", "Search Open Topics"],
        "authority_note": "Official SBA SBIR/STTR discovery surface; individual topic pages warn users to verify agency originals.",
    },
    {
        "id": "diu-open-solicitations",
        "url": "https://www.diu.mil/work-with-us/open-solicitations",
        "official_domain": "diu.mil",
        "expected_any": ["Open Solicitations", "open solicitations", "Currently, there are no opportunities open"],
        "authority_note": "Official Defense Innovation Unit commercial-solicitation surface.",
    },
    {
        "id": "darpa-opportunities",
        "url": "https://www.darpa.mil/work-with-us/opportunities",
        "official_domain": "darpa.mil",
        "expected_any": ["R&D Opportunities", "Search our Opportunities", "Explore Open Opportunities"],
        "authority_note": "Official DARPA R&D-opportunities surface.",
    },
    {
        "id": "grants-search",
        "url": "https://www.grants.gov/grants/search-grants.html",
        "official_domain": "grants.gov",
        "expected_any": ["Search funding opportunities", "Search Grants", "Opportunities"],
        "authority_note": "Official Grants.gov federal funding-opportunity search surface.",
    },
]

USER_AGENT = "Worldshepherd-PRE-Freshness/1.0 (+evidence-controlled public-source monitor)"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fetch_source(source: dict, timeout_s: int = 30) -> dict:
    started = time.monotonic()
    req = Request(
        source["url"],
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.5",
        },
        method="GET",
    )
    result = {
        "id": source["id"],
        "requested_url": source["url"],
        "official_domain": source["official_domain"],
        "authority_note": source["authority_note"],
        "retrieved_at_utc": utc_now(),
    }
    try:
        context = ssl.create_default_context()
        with urlopen(req, timeout=timeout_s, context=context) as response:
            body = response.read(8_000_000)
            status = getattr(response, "status", 200)
            final_url = response.geturl()
            headers = {k.lower(): v for k, v in response.headers.items()}
        text = body.decode("utf-8", errors="replace")
        keyword_hits = [token for token in source["expected_any"] if token.lower() in text.lower()]
        result.update(
            {
                "ok": 200 <= status < 400 and bool(keyword_hits),
                "http_status": status,
                "final_url": final_url,
                "content_type": headers.get("content-type"),
                "etag": headers.get("etag"),
                "last_modified": headers.get("last-modified"),
                "content_length_bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "expected_keyword_hits": keyword_hits,
                "elapsed_ms": round((time.monotonic() - started) * 1000, 3),
            }
        )
    except HTTPError as exc:
        result.update(
            {
                "ok": False,
                "http_status": exc.code,
                "error": f"HTTPError: {exc}",
                "elapsed_ms": round((time.monotonic() - started) * 1000, 3),
            }
        )
    except (URLError, TimeoutError, OSError) as exc:
        result.update(
            {
                "ok": False,
                "http_status": None,
                "error": f"{type(exc).__name__}: {exc}",
                "elapsed_ms": round((time.monotonic() - started) * 1000, 3),
            }
        )
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="pre/evidence/source-freshness-report.json")
    ap.add_argument("--timeout", type=int, default=30)
    args = ap.parse_args()

    results = [fetch_source(source, timeout_s=args.timeout) for source in SOURCES]
    report = {
        "schema": "WS-PRE-SOURCE-FRESHNESS-V1",
        "evidence_class": "LIVE_PUBLIC_SOURCE_CHECK",
        "generated_at_utc": utc_now(),
        "source_count": len(results),
        "passing_source_count": sum(1 for x in results if x.get("ok")),
        "all_sources_pass": all(x.get("ok") for x in results),
        "sources": results,
        "claims_boundary": (
            "This report establishes current reachability and content provenance for the allowlisted official public opportunity surfaces only. "
            "It does not prove exhaustive market coverage, opportunity eligibility, bid suitability, award probability, agency endorsement, or that a secondary index supersedes an originating agency solicitation."
        ),
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["all_sources_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

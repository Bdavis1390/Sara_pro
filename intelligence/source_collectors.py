#!/usr/bin/env python3
"""Bounded public-source collectors for the Worldshepherd research database.

Supported initial adapters:
- U.S. Census Bureau Data API
- Data.gov Catalog API v4
- U.S. Bureau of Labor Statistics Public Data API v2
- Library of Congress loc.gov JSON API
- National Archives Catalog API v2 (LIVE QUERY ONLY; never persisted here)
- Smithsonian Open Access API

All collectors use HTTPS, bounded response sizes, explicit timeouts, provenance
metadata, and environment variables for credentials. API keys are never written
to the research database.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any
from urllib import error, parse, request

from research_db import DEFAULT_DB, DEFAULT_REGISTRY, ResearchDB, ResearchRecord

COLLECTOR_VERSION = "worldshepherd-tier1-collectors/1.0"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
TIMEOUT_SECONDS = 30
USER_AGENT = "Worldshepherd-Research/1.0 (+governed-local-ingestion)"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"required environment variable {name} is not set")
    return value


def redact(text: str, secrets: list[str]) -> str:
    result = text
    for secret in secrets:
        if secret:
            result = result.replace(secret, "[REDACTED]")
    return result


def fetch_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    secrets: list[str] | None = None,
) -> Any:
    if not url.startswith("https://"):
        raise ValueError("collector requests must use HTTPS")
    body = None
    merged_headers = {
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
        **(headers or {}),
    }
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        merged_headers["Content-Type"] = "application/json"
    req = request.Request(url, data=body, headers=merged_headers, method=method)
    try:
        with request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_RESPONSE_BYTES:
                raise RuntimeError("upstream response exceeds collector size limit")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise RuntimeError("upstream response exceeds collector size limit")
            return json.loads(raw.decode("utf-8"))
    except (error.HTTPError, error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        message = redact(str(exc), secrets or [])
        raise RuntimeError(f"collector request failed: {message}") from exc


def datagov_search(query: str, api_key: str, per_page: int = 10, org_slug: str = "") -> list[ResearchRecord]:
    params: dict[str, str | int] = {"q": query, "per_page": max(1, min(per_page, 100))}
    if org_slug:
        params["org_slug"] = org_slug
    url = "https://api.gsa.gov/technology/datagov/v4/search?" + parse.urlencode(params)
    data = fetch_json(url, headers={"X-Api-Key": api_key}, secrets=[api_key])
    records: list[ResearchRecord] = []
    for item in data.get("results", []) if isinstance(data, dict) else []:
        if not isinstance(item, dict):
            continue
        dcat = item.get("dcat") if isinstance(item.get("dcat"), dict) else {}
        upstream_id = str(item.get("identifier") or item.get("slug") or "").strip()
        if not upstream_id:
            upstream_id = hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest()
        canonical_url = str(
            dcat.get("landingPage")
            or item.get("landingPage")
            or item.get("harvest_record")
            or "https://data.gov/"
        )
        rights = str(dcat.get("rights") or dcat.get("license") or "")
        records.append(
            ResearchRecord(
                source_id="WS-SRC-USADATA",
                upstream_id=upstream_id,
                title=str(item.get("title") or dcat.get("title") or upstream_id),
                canonical_url=canonical_url,
                query_text=query,
                observed_at=now(),
                payload=item,
                validation_label="Official Data.gov catalog metadata; validate originating agency dataset",
                rights_label=rights,
                ttl_days=30,
                collector_version=COLLECTOR_VERSION,
            )
        )
    return records


def loc_search(query: str, rows: int = 10) -> list[ResearchRecord]:
    params = {"q": query, "fo": "json", "c": max(1, min(rows, 100))}
    url = "https://www.loc.gov/search/?" + parse.urlencode(params)
    data = fetch_json(url)
    records: list[ResearchRecord] = []
    for item in data.get("results", []) if isinstance(data, dict) else []:
        if not isinstance(item, dict):
            continue
        upstream_id = str(item.get("id") or item.get("url") or "").strip()
        if not upstream_id:
            upstream_id = hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest()
        rights = item.get("rights")
        if isinstance(rights, list):
            rights_label = "; ".join(str(value) for value in rights)
        else:
            rights_label = str(rights or "")
        records.append(
            ResearchRecord(
                source_id="WS-SRC-LOC",
                upstream_id=upstream_id,
                title=str(item.get("title") or upstream_id),
                canonical_url=str(item.get("url") or item.get("id") or "https://www.loc.gov/"),
                query_text=query,
                observed_at=now(),
                payload=item,
                validation_label="Official Library of Congress collection metadata; item-level provenance retained",
                rights_label=rights_label,
                ttl_days=365,
                collector_version=COLLECTOR_VERSION,
            )
        )
    return records


def nara_live_search(query: str, api_key: str, rows: int = 10) -> Any:
    """Query NARA without persistent ingestion.

    NARA's current Catalog API terms state that content returned by the API
    should not be cached or stored. This adapter therefore returns the live
    response only. The ResearchDB persistence gate for WS-SRC-NARA must remain
    disabled.
    """

    params = {"q": query, "limit": max(1, min(rows, 100))}
    url = "https://catalog.archives.gov/api/v2/records/search?" + parse.urlencode(params)
    return fetch_json(
        url,
        headers={"Content-Type": "application/json", "x-api-key": api_key},
        secrets=[api_key],
    )


def smithsonian_search(query: str, api_key: str, rows: int = 10) -> list[ResearchRecord]:
    params = {
        "q": query,
        "start": 0,
        "rows": max(1, min(rows, 100)),
        "api_key": api_key,
    }
    url = "https://api.si.edu/openaccess/api/v1.0/search?" + parse.urlencode(params)
    data = fetch_json(url, secrets=[api_key])
    response = data.get("response", {}) if isinstance(data, dict) else {}
    items = response.get("rows", []) if isinstance(response, dict) else []
    records: list[ResearchRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        upstream_id = str(item.get("id") or item.get("url") or "").strip()
        if not upstream_id:
            upstream_id = hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest()
        content = item.get("content") if isinstance(item.get("content"), dict) else {}
        descriptive = content.get("descriptiveNonRepeating") if isinstance(content, dict) else {}
        if not isinstance(descriptive, dict):
            descriptive = {}
        usage = descriptive.get("metadata_usage")
        rights_label = ""
        if isinstance(usage, dict):
            rights_label = str(usage.get("access") or "")
        records.append(
            ResearchRecord(
                source_id="WS-SRC-SMITHSONIAN",
                upstream_id=upstream_id,
                title=str(item.get("title") or upstream_id),
                canonical_url=str(descriptive.get("record_link") or item.get("url") or "https://www.si.edu/"),
                query_text=query,
                observed_at=now(),
                payload=item,
                validation_label="Smithsonian collection metadata; preserve object identifier and item-level rights",
                rights_label=rights_label,
                ttl_days=365,
                collector_version=COLLECTOR_VERSION,
            )
        )
    return records


def bls_series(series_ids: list[str], start_year: int | None = None, end_year: int | None = None, registration_key: str = "") -> list[ResearchRecord]:
    if not series_ids:
        raise ValueError("at least one BLS series ID is required")
    payload: dict[str, Any] = {"seriesid": series_ids}
    if start_year is not None:
        payload["startyear"] = str(start_year)
    if end_year is not None:
        payload["endyear"] = str(end_year)
    if registration_key:
        payload["registrationkey"] = registration_key
    data = fetch_json(
        "https://api.bls.gov/publicAPI/v2/timeseries/data/",
        method="POST",
        payload=payload,
        secrets=[registration_key],
    )
    results = data.get("Results", {}) if isinstance(data, dict) else {}
    series = results.get("series", []) if isinstance(results, dict) else []
    query_text = ",".join(series_ids)
    records: list[ResearchRecord] = []
    for item in series:
        if not isinstance(item, dict):
            continue
        series_id = str(item.get("seriesID") or "").strip()
        if not series_id:
            continue
        records.append(
            ResearchRecord(
                source_id="WS-SRC-DOL",
                upstream_id=series_id,
                title=f"BLS series {series_id}",
                canonical_url=f"https://api.bls.gov/publicAPI/v2/timeseries/data/{parse.quote(series_id)}",
                query_text=query_text,
                observed_at=now(),
                payload=item,
                validation_label="Official U.S. Bureau of Labor Statistics published time-series data",
                rights_label="U.S. government statistical data",
                ttl_days=60,
                collector_version=COLLECTOR_VERSION,
            )
        )
    return records


def census_query(year: int, dataset: str, variables: str, geography: str, api_key: str) -> list[ResearchRecord]:
    clean_dataset = dataset.strip("/")
    params = {"get": variables, "for": geography, "key": api_key}
    base = f"https://api.census.gov/data/{year}/{clean_dataset}"
    url = base + "?" + parse.urlencode(params)
    data = fetch_json(url, secrets=[api_key])
    query_without_secret = {
        "year": year,
        "dataset": clean_dataset,
        "get": variables,
        "for": geography,
    }
    upstream_id = hashlib.sha256(
        json.dumps(query_without_secret, sort_keys=True).encode("utf-8")
    ).hexdigest()
    canonical = base + "?" + parse.urlencode({"get": variables, "for": geography})
    return [
        ResearchRecord(
            source_id="WS-SRC-CENSUS",
            upstream_id=upstream_id,
            title=f"Census {year}/{clean_dataset}: {variables} for {geography}",
            canonical_url=canonical,
            query_text=json.dumps(query_without_secret, sort_keys=True),
            observed_at=now(),
            payload=data,
            validation_label="Official U.S. Census Bureau Data API response",
            rights_label="U.S. government statistical data",
            ttl_days=120,
            collector_version=COLLECTOR_VERSION,
        )
    ]


def ingest(db_path: str, records: list[ResearchRecord]) -> dict[str, Any]:
    with ResearchDB(db_path) as db:
        if db.stats()["sources"] == 0:
            db.load_registry(DEFAULT_REGISTRY)
        inserted, duplicates = db.ingest_many(records)
        return {"received": len(records), "inserted": inserted, "duplicates": duplicates, **db.stats()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Worldshepherd Tier-1 research collectors")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--no-ingest", action="store_true", help="print normalized results instead of writing SQLite")
    sub = parser.add_subparsers(dest="source", required=True)

    datagov = sub.add_parser("datagov")
    datagov.add_argument("query")
    datagov.add_argument("--per-page", type=int, default=10)
    datagov.add_argument("--org-slug", default="")

    loc = sub.add_parser("loc")
    loc.add_argument("query")
    loc.add_argument("--rows", type=int, default=10)

    nara = sub.add_parser("nara")
    nara.add_argument("query")
    nara.add_argument("--rows", type=int, default=10)

    smithsonian = sub.add_parser("smithsonian")
    smithsonian.add_argument("query")
    smithsonian.add_argument("--rows", type=int, default=10)

    bls = sub.add_parser("bls")
    bls.add_argument("series", nargs="+")
    bls.add_argument("--start-year", type=int)
    bls.add_argument("--end-year", type=int)

    census = sub.add_parser("census")
    census.add_argument("year", type=int)
    census.add_argument("dataset")
    census.add_argument("--get", dest="variables", required=True)
    census.add_argument("--for", dest="geography", required=True)

    args = parser.parse_args()
    try:
        if args.source == "datagov":
            records = datagov_search(
                args.query,
                required_env("DATAGOV_API_KEY"),
                args.per_page,
                args.org_slug,
            )
        elif args.source == "loc":
            records = loc_search(args.query, args.rows)
        elif args.source == "nara":
            result = nara_live_search(args.query, required_env("NARA_API_KEY"), args.rows)
            print(json.dumps({"mode": "live_query_only", "persisted": False, "response": result}, indent=2))
            return
        elif args.source == "smithsonian":
            records = smithsonian_search(
                args.query,
                required_env("SMITHSONIAN_API_KEY"),
                args.rows,
            )
        elif args.source == "bls":
            records = bls_series(
                args.series,
                args.start_year,
                args.end_year,
                os.getenv("BLS_REGISTRATION_KEY", "").strip(),
            )
        elif args.source == "census":
            records = census_query(
                args.year,
                args.dataset,
                args.variables,
                args.geography,
                required_env("CENSUS_API_KEY"),
            )
        else:
            raise AssertionError("unhandled source")

        if args.no_ingest:
            print(
                json.dumps(
                    [
                        {
                            **record.__dict__,
                            "payload": record.payload,
                        }
                        for record in records
                    ],
                    indent=2,
                    ensure_ascii=False,
                )
            )
        else:
            print(json.dumps(ingest(args.db, records), indent=2))
    except (RuntimeError, ValueError, PermissionError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()

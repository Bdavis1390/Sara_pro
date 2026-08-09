#!/usr/bin/env python3
"""Local provenance-aware research database for Worldshepherd intelligence sources.

This module intentionally lives outside the verified SARA deployment artifact. It
uses only Python's standard library and stores no API keys. The database is an
index/evidence cache, not a claim-validation oracle: source tier, validation
labels, rights information, query provenance, and hashes are retained with each
record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / "data" / "worldshepherd_research.sqlite3"
DEFAULT_REGISTRY = ROOT / "research_source_registry_v1.json"
SCHEMA_VERSION = 1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _secure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass


def _secure_file(path: Path) -> None:
    if path.exists():
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


@dataclass(frozen=True)
class ResearchRecord:
    source_id: str
    upstream_id: str
    title: str
    canonical_url: str
    query_text: str
    observed_at: str
    payload: Any
    validation_label: str
    rights_label: str = ""
    ttl_days: int | None = None
    collector_version: str = "worldshepherd-research-pipeline/1.0"


class ResearchDB:
    def __init__(self, path: str | Path = DEFAULT_DB) -> None:
        self.path = Path(path).expanduser().resolve()
        _secure_parent(self.path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute("PRAGMA synchronous = FULL")
        self._initialize()
        _secure_file(self.path)

    def close(self) -> None:
        self.connection.close()
        _secure_file(self.path)

    def __enter__(self) -> "ResearchDB":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sources (
                source_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                trust_tier TEXT NOT NULL,
                status TEXT NOT NULL,
                collector_allowed INTEGER NOT NULL,
                persistence_allowed INTEGER NOT NULL,
                ttl_days INTEGER,
                default_validation_label TEXT NOT NULL,
                registry_json TEXT NOT NULL,
                registry_sha256 TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL REFERENCES sources(source_id),
                upstream_id TEXT NOT NULL,
                title TEXT NOT NULL,
                canonical_url TEXT NOT NULL,
                query_text TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                ingested_at TEXT NOT NULL,
                expires_at TEXT,
                payload_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                validation_label TEXT NOT NULL,
                rights_label TEXT NOT NULL,
                collector_version TEXT NOT NULL,
                UNIQUE(source_id, payload_sha256)
            );

            CREATE INDEX IF NOT EXISTS idx_records_source_id
                ON records(source_id);
            CREATE INDEX IF NOT EXISTS idx_records_upstream_id
                ON records(source_id, upstream_id);
            CREATE INDEX IF NOT EXISTS idx_records_ingested_at
                ON records(ingested_at);
            """
        )
        self.connection.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        self.connection.commit()

    def load_registry(self, registry_path: str | Path = DEFAULT_REGISTRY) -> int:
        path = Path(registry_path)
        registry = json.loads(path.read_text(encoding="utf-8"))
        sources = registry.get("sources")
        if not isinstance(sources, list) or not sources:
            raise ValueError("source registry contains no sources")

        seen: set[str] = set()
        now = utc_now()
        with self.connection:
            for source in sources:
                if not isinstance(source, dict):
                    raise ValueError("every source registry entry must be an object")
                source_id = str(source.get("source_id", "")).strip()
                if not source_id:
                    raise ValueError("source_id is required")
                if source_id in seen:
                    raise ValueError(f"duplicate source_id: {source_id}")
                seen.add(source_id)
                blob = canonical_json(source)
                self.connection.execute(
                    """
                    INSERT INTO sources(
                        source_id, name, trust_tier, status,
                        collector_allowed, persistence_allowed, ttl_days,
                        default_validation_label, registry_json,
                        registry_sha256, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_id) DO UPDATE SET
                        name=excluded.name,
                        trust_tier=excluded.trust_tier,
                        status=excluded.status,
                        collector_allowed=excluded.collector_allowed,
                        persistence_allowed=excluded.persistence_allowed,
                        ttl_days=excluded.ttl_days,
                        default_validation_label=excluded.default_validation_label,
                        registry_json=excluded.registry_json,
                        registry_sha256=excluded.registry_sha256,
                        updated_at=excluded.updated_at
                    """,
                    (
                        source_id,
                        str(source.get("name", "")),
                        str(source.get("trust_tier", "")),
                        str(source.get("status", "")),
                        1 if source.get("collector_allowed", False) else 0,
                        1
                        if source.get(
                            "persistence_allowed",
                            source.get("collector_allowed", False),
                        )
                        else 0,
                        source.get("ttl_days"),
                        str(source.get("default_validation_label", "")),
                        blob,
                        hashlib.sha256(blob.encode("utf-8")).hexdigest(),
                        now,
                    ),
                )
        return len(seen)

    def source(self, source_id: str) -> sqlite3.Row:
        row = self.connection.execute(
            "SELECT * FROM sources WHERE source_id = ?", (source_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown source_id: {source_id}")
        return row

    def ingest(self, record: ResearchRecord) -> tuple[int, bool]:
        source = self.source(record.source_id)
        if not source["collector_allowed"]:
            raise PermissionError(
                f"collector disabled for source {record.source_id}; use authorized/manual review"
            )
        if not source["persistence_allowed"]:
            raise PermissionError(
                f"persistent storage prohibited for source {record.source_id}; live query only"
            )

        payload_json = canonical_json(record.payload)
        payload_sha256 = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        ttl_days = record.ttl_days
        if ttl_days is None:
            ttl_days = source["ttl_days"]
        expires_at = None
        if ttl_days is not None:
            expires_at = (
                datetime.now(timezone.utc) + timedelta(days=int(ttl_days))
            ).isoformat()

        before = self.connection.total_changes
        with self.connection:
            self.connection.execute(
                """
                INSERT OR IGNORE INTO records(
                    source_id, upstream_id, title, canonical_url, query_text,
                    observed_at, ingested_at, expires_at, payload_sha256,
                    payload_json, validation_label, rights_label,
                    collector_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.source_id,
                    record.upstream_id,
                    record.title,
                    record.canonical_url,
                    record.query_text,
                    record.observed_at,
                    utc_now(),
                    expires_at,
                    payload_sha256,
                    payload_json,
                    record.validation_label or source["default_validation_label"],
                    record.rights_label,
                    record.collector_version,
                ),
            )
        inserted = self.connection.total_changes > before
        row = self.connection.execute(
            "SELECT id FROM records WHERE source_id = ? AND payload_sha256 = ?",
            (record.source_id, payload_sha256),
        ).fetchone()
        assert row is not None
        return int(row["id"]), inserted

    def ingest_many(self, records: Iterable[ResearchRecord]) -> tuple[int, int]:
        inserted = 0
        duplicates = 0
        for record in records:
            _, was_inserted = self.ingest(record)
            if was_inserted:
                inserted += 1
            else:
                duplicates += 1
        return inserted, duplicates

    def stats(self) -> dict[str, Any]:
        source_count = self.connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        record_count = self.connection.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        by_source = [
            dict(row)
            for row in self.connection.execute(
                """
                SELECT s.source_id, s.name, COUNT(r.id) AS records
                FROM sources s
                LEFT JOIN records r ON r.source_id = s.source_id
                GROUP BY s.source_id, s.name
                ORDER BY records DESC, s.source_id ASC
                """
            )
        ]
        return {
            "schema_version": SCHEMA_VERSION,
            "database": str(self.path),
            "sources": source_count,
            "records": record_count,
            "by_source": by_source,
        }

    def search(self, text: str, limit: int = 50) -> list[dict[str, Any]]:
        needle = f"%{text}%"
        rows = self.connection.execute(
            """
            SELECT id, source_id, upstream_id, title, canonical_url, query_text,
                   observed_at, ingested_at, expires_at, payload_sha256,
                   validation_label, rights_label, collector_version
            FROM records
            WHERE title LIKE ? OR query_text LIKE ? OR upstream_id LIKE ?
            ORDER BY ingested_at DESC
            LIMIT ?
            """,
            (needle, needle, needle, max(1, min(int(limit), 500))),
        ).fetchall()
        return [dict(row) for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description="Worldshepherd research database")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init")
    init.add_argument("--registry", default=str(DEFAULT_REGISTRY))

    sub.add_parser("stats")

    search = sub.add_parser("search")
    search.add_argument("text")
    search.add_argument("--limit", type=int, default=50)

    args = parser.parse_args()
    with ResearchDB(args.db) as db:
        if args.command == "init":
            count = db.load_registry(args.registry)
            print(json.dumps({"ok": True, "sources_loaded": count, **db.stats()}, indent=2))
        elif args.command == "stats":
            print(json.dumps(db.stats(), indent=2))
        elif args.command == "search":
            print(json.dumps(db.search(args.text, args.limit), indent=2))


if __name__ == "__main__":
    main()

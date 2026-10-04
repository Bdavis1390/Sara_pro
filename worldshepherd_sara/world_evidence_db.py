"""WORLD CONTROLLER persistent evidence database + source-attributed dossier engine.

Local-first, SQLite-backed, FTS5-enabled when available. No network access.
"""
from __future__ import annotations

import hashlib
import html
import json
import mimetypes
import os
import re
import shutil
import sqlite3
import subprocess
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/world/memory", tags=["WORLD CONTROLLER MEMORY DB"])

TEXT_EXTS = {
    ".txt", ".md", ".markdown", ".json", ".jsonl", ".yaml", ".yml", ".py", ".sh", ".html", ".htm",
    ".css", ".js", ".ts", ".tsx", ".csv", ".log", ".ini", ".toml", ".cfg", ".conf", ".rst", ".rtf",
    ".sql", ".xml", ".svg"
}
DOC_EXTS = TEXT_EXTS | {".pdf", ".docx", ".odt"}
EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "env", "__pycache__", "node_modules", ".cache", ".mypy_cache",
    ".pytest_cache", "dist", "build", "site-packages", ".idea", ".vscode", "target"
}
DEFAULT_PROJECTS = [
    ("sara-sspadawanzz-admin", "SARA / SSPADAWANZZ Admin Stack", ["sara", "sspadawanzz", "fastapi", "uvicorn", "registry", "relay", "audit", "world controller", "admin token"]),
    ("worldshepherd-governance", "Worldshepherd Governance", ["worldshepherd", "governance", "prime sentinel", "guardian", "oracle", "ark", "watcher", "simulate-first"]),
    ("al-ti-meta-alloy", "Al-Ti Programmable Meta-Alloy", ["al-ti", "alti", "meta-alloy", "ded", "directed energy", "titanium", "scandium", "zirconium", "al-mg-sc-zr", "coupon validation"]),
    ("adaptive-metasurface-em-boundary", "Adaptive Metasurface / EM Boundary", ["metasurface", "rf", "phase shifter", "permittivity", "conductivity", "em tile", "beamforming", "null steering", "maxwell"]),
    ("gpt-session-archive", "GPT Session / Account Archive", ["chatgpt", "gpt", "conversation", "export", "session", "prompt", "assistant", "user"]),
    ("patent-counsel-outreach", "Patent / Counsel / Outreach Packets", ["patent", "counsel", "provisional", "claim", "attorney", "outreach", "valuation", "licensing"]),
    ("baros-medical-optimization", "BAROS Medical Optimization", ["baros", "radiotherapy", "dose", "gamma", "treatment planning", "monte carlo", "eclipse", "monaco"]),
    ("containerized-lab-admin", "Containerized Lab / Admin Infrastructure", ["docker", "compose", "containerized", "vault", "keycloak", "prometheus", "grafana"]),
    ("steganalysis-padawan-lab", "Steganography / Padawan Lab", ["steg", "stegriage", "icc", "exif", "png", "bmp", "svg", "payload", "color channel"]),
]
RISK_FLAGS = {
    "Requires legal review": ["legal review", "counsel", "patent", "provisional", "claim", "valuation", "licensing", "settlement"],
    "Requires lab validation": ["lab validation", "coupon", "fatigue", "xrd", "ebsd", "sem", "validated", "simulation only", "hypothesis"],
    "Hardware safety boundary": ["rf", "laser", "voltage", "actuator", "thermal", "metasurface", "power supply", "material state", "ded", "wire feed"],
    "Operational security boundary": ["token", "admin", "audit", "registry", "relay", "secret", "credential", "api key"],
}

class IngestRequest(BaseModel):
    roots: Optional[List[str]] = None
    force: bool = False
    limit: Optional[int] = None


def _now() -> float:
    return time.time()


def _human_ts(ts: Optional[float] = None) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(ts or _now()))


def _repo_root() -> Path:
    return Path(os.getenv("WORLD_REPO_DIR", os.getcwd())).expanduser().resolve()


def _data_dir() -> Path:
    d = Path(os.getenv("WORLD_DATA_DIR", str(_repo_root() / "data"))).expanduser()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _db_path() -> Path:
    return Path(os.getenv("WORLD_EVIDENCE_DB", str(_data_dir() / "world_evidence.db"))).expanduser()


def _audit_path() -> Path:
    return _data_dir() / "world_controller_audit.jsonl"


def _ark_dir() -> Path:
    d = _data_dir() / "world_controller_ark"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _require_admin(authorization: Optional[str], x_sara_admin_token: Optional[str]) -> str:
    expected = os.getenv("SARA_ADMIN_TOKEN", "")
    supplied = x_sara_admin_token or ""
    if authorization and authorization.lower().startswith("bearer "):
        supplied = authorization.split(" ", 1)[1].strip()
    if not expected:
        raise HTTPException(status_code=500, detail="SARA_ADMIN_TOKEN is not set")
    if supplied.strip() != expected:
        raise HTTPException(status_code=403, detail="WORLD CONTROLLER admin token required")
    return "SSPADAWANZZ_ADMIN"


def _append_audit(actor: str, event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    rec = {
        "ts": _now(),
        "human_time": _human_ts(),
        "audit_id": "WC-MEM-" + hashlib.sha1(f"{event}:{_now()}".encode()).hexdigest()[:14],
        "actor": actor,
        "event": event,
        "payload": payload,
    }
    try:
        with _audit_path().open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
    except Exception:
        pass
    return rec


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(_db_path())
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def _fts_available(con: sqlite3.Connection) -> bool:
    try:
        con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS __fts_probe USING fts5(x)")
        con.execute("DROP TABLE IF EXISTS __fts_probe")
        return True
    except sqlite3.OperationalError:
        return False


def _json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def _load_json(text: Optional[str], fallback: Any = None) -> Any:
    if not text:
        return fallback
    try:
        return json.loads(text)
    except Exception:
        return fallback


def init_db() -> Dict[str, Any]:
    _data_dir().mkdir(parents=True, exist_ok=True)
    with _conn() as con:
        fts = _fts_available(con)
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY,
                uri TEXT UNIQUE NOT NULL,
                source_type TEXT NOT NULL,
                title TEXT,
                path TEXT,
                hash TEXT NOT NULL,
                size_bytes INTEGER,
                modified_at REAL,
                imported_at REAL NOT NULL,
                metadata TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_sources_hash ON sources(hash);
            CREATE INDEX IF NOT EXISTS idx_sources_type ON sources(source_type);

            CREATE TABLE IF NOT EXISTS evidence (
                id INTEGER PRIMARY KEY,
                source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
                content TEXT,
                mime_type TEXT,
                dossier_category TEXT,
                project_slug TEXT,
                risk_flags TEXT,
                summary TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_evidence_source_id ON evidence(source_id);
            CREATE INDEX IF NOT EXISTS idx_evidence_project_slug ON evidence(project_slug);
            CREATE INDEX IF NOT EXISTS idx_evidence_category ON evidence(dossier_category);

            CREATE TABLE IF NOT EXISTS projects (
                slug TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                domain_tags TEXT,
                status TEXT DEFAULT 'indexed',
                guardian_classification TEXT DEFAULT 'GREEN',
                last_indexed_at REAL,
                metadata TEXT
            );

            CREATE TABLE IF NOT EXISTS evidence_links (
                id INTEGER PRIMARY KEY,
                evidence_id INTEGER NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
                link_type TEXT NOT NULL,
                target_uri TEXT NOT NULL,
                label TEXT,
                metadata TEXT
            );

            CREATE TABLE IF NOT EXISTS ark_snapshots (
                id INTEGER PRIMARY KEY,
                snapshot_id TEXT UNIQUE NOT NULL,
                created_at REAL NOT NULL,
                actor TEXT,
                registry_hash TEXT,
                db_hash TEXT,
                snapshot_path TEXT,
                metadata TEXT
            );

            CREATE TABLE IF NOT EXISTS ingest_runs (
                id INTEGER PRIMARY KEY,
                run_id TEXT UNIQUE NOT NULL,
                started_at REAL NOT NULL,
                finished_at REAL,
                actor TEXT,
                roots TEXT,
                files_seen INTEGER DEFAULT 0,
                files_ingested INTEGER DEFAULT 0,
                files_skipped INTEGER DEFAULT 0,
                metadata TEXT
            );
            """
        )
        if fts:
            con.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS evidence_fts USING fts5(content, title, project_slug, dossier_category, summary, content='')"
            )
        for slug, title, tags in DEFAULT_PROJECTS:
            con.execute(
                "INSERT OR IGNORE INTO projects(slug,title,domain_tags,last_indexed_at,metadata) VALUES(?,?,?,?,?)",
                (slug, title, _json(tags), _now(), _json({"seed": True})),
            )
        con.commit()
        return {"ok": True, "db_path": str(_db_path()), "fts5": fts, "projects_seeded": len(DEFAULT_PROJECTS)}


def _strip_xml(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()


def _extract_zip_xml(path: Path, candidates: Iterable[str]) -> str:
    try:
        with zipfile.ZipFile(path) as z:
            parts = []
            for name in candidates:
                if name in z.namelist():
                    parts.append(_strip_xml(z.read(name).decode("utf-8", "ignore")))
            return "\n".join(parts).strip()
    except Exception:
        return ""


def _extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    try:
        if ext in TEXT_EXTS:
            limit = int(os.getenv("WORLD_MEMORY_MAX_TEXT_BYTES", "5000000"))
            return path.read_text(encoding="utf-8", errors="ignore")[:limit]
        if ext == ".pdf":
            if shutil.which("pdftotext"):
                try:
                    r = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, timeout=30)
                    if r.stdout.strip():
                        return r.stdout[: int(os.getenv("WORLD_MEMORY_MAX_TEXT_BYTES", "5000000"))]
                except Exception:
                    pass
            return f"[PDF metadata only: {path.name}; install poppler-utils for text extraction]"
        if ext == ".docx":
            return _extract_zip_xml(path, ["word/document.xml"])
        if ext == ".odt":
            return _extract_zip_xml(path, ["content.xml"])
    except Exception as e:
        return f"[extraction error: {type(e).__name__}: {e}]"
    return ""


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _content_hash(text: str, meta: Dict[str, Any]) -> str:
    h = hashlib.sha256()
    h.update(text.encode("utf-8", "ignore"))
    h.update(_json(meta).encode("utf-8", "ignore"))
    return h.hexdigest()


def _roots(extra: Optional[List[str]] = None) -> List[Path]:
    home = Path.home()
    roots = [
        _repo_root(),
        _repo_root() / "docs",
        _repo_root() / "payloads",
        _repo_root() / "world_documents",
        _repo_root() / "data",
        home / "Downloads",
        home / "Documents",
        home / "ChatGPT_Exports",
        home / "GPT_Exports",
        home / "Worldshepherd",
        home / "worldshepherd",
    ]
    for item in re.split(r"[:,]", os.getenv("WORLD_PROJECT_ROOTS", "")):
        if item.strip():
            roots.append(Path(item.strip()).expanduser())
    if extra:
        roots += [Path(x).expanduser() for x in extra if x]
    seen, out = set(), []
    for r in roots:
        try:
            rr = r.resolve()
        except Exception:
            continue
        if rr.exists() and rr not in seen:
            seen.add(rr)
            out.append(rr)
    return out


def _iter_files(roots: List[Path], limit: Optional[int]) -> Iterable[Path]:
    max_files = limit or int(os.getenv("WORLD_MEMORY_SCAN_MAX_FILES", "10000"))
    count = 0
    for root in roots:
        if count >= max_files:
            return
        if root.is_file() and root.suffix.lower() in DOC_EXTS:
            count += 1
            yield root
            continue
        if not root.exists() or not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith(".")]
            for name in filenames:
                if count >= max_files:
                    return
                p = Path(dirpath) / name
                if p.suffix.lower() in DOC_EXTS:
                    count += 1
                    yield p


def _project_for_text(text: str, path: Path) -> Tuple[str, str, List[str]]:
    hay = f"{path.name}\n{path}\n{text[:15000]}".lower()
    best = ("uncategorized-evidence", "Uncategorized Evidence", [], 0)
    for slug, title, terms in DEFAULT_PROJECTS:
        score = sum(1 for t in terms if t.lower() in hay)
        if score > best[3]:
            best = (slug, title, terms, score)
    return best[0], best[1], best[2]


def _risk_flags(text: str, path: Path) -> Dict[str, List[str]]:
    hay = f"{path.name}\n{path}\n{text[:30000]}".lower()
    flags: Dict[str, List[str]] = {}
    for label, terms in RISK_FLAGS.items():
        hits = [t for t in terms if t in hay]
        if hits:
            flags[label] = hits[:12]
    return flags


def _summary(text: str, path: Path, max_items: int = 6) -> List[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return [f"No extractable text was found for {path.name}."]
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    out = []
    for s in sentences:
        s = s.strip()
        if 80 <= len(s) <= 420:
            out.append(s)
        if len(out) >= max_items:
            break
    if not out:
        out = [cleaned[:420]]
    return out


def _source_type(path: Path) -> str:
    p = str(path).lower()
    if "chatgpt" in p or "gpt_export" in p or "conversations.json" in p:
        return "gpt_export_or_session"
    if "world_documents" in p:
        return "world_document"
    if "/downloads" in p:
        return "download"
    if "/documents" in p:
        return "document_folder"
    return "local_file"


def _rebuild_fts(con: sqlite3.Connection) -> None:
    """Rebuild the contentless FTS index from authoritative evidence rows."""
    try:
        con.execute("INSERT INTO evidence_fts(evidence_fts) VALUES('delete-all')")
        con.execute(
            """INSERT INTO evidence_fts(rowid,content,title,project_slug,dossier_category,summary)
               SELECT e.id,e.content,s.title,e.project_slug,e.dossier_category,
                      COALESCE(e.summary,'')
               FROM evidence e JOIN sources s ON s.id=e.source_id"""
        )
    except sqlite3.OperationalError as exc:
        # FTS5 is optional, but a present/broken FTS table must never fail silently.
        if "no such table" not in str(exc).lower():
            raise


def _upsert_doc(con: sqlite3.Connection, path: Path, force: bool = False) -> Tuple[bool, Optional[int]]:
    stat = path.stat()
    file_hash = _hash_file(path)
    uri = "file://" + str(path.resolve())
    existing = con.execute("SELECT s.id, e.id AS evidence_id, s.hash FROM sources s LEFT JOIN evidence e ON e.source_id=s.id WHERE s.uri=?", (uri,)).fetchone()
    if existing and existing["hash"] == file_hash and not force:
        return False, existing["evidence_id"]
    text = _extract_text(path)
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    slug, project_title, _terms = _project_for_text(text, path)
    risks = _risk_flags(text, path)
    summ = _summary(text, path)
    meta = {
        "name": path.name,
        "relative_path": str(path),
        "modified_human": _human_ts(stat.st_mtime),
        "project_title": project_title,
        "extract_length": len(text),
    }
    source_hash = _content_hash(text, {"file_hash": file_hash, "uri": uri})
    con.execute(
        """INSERT INTO sources(uri,source_type,title,path,hash,size_bytes,modified_at,imported_at,metadata)
           VALUES(?,?,?,?,?,?,?,?,?)
           ON CONFLICT(uri) DO UPDATE SET source_type=excluded.source_type,title=excluded.title,path=excluded.path,hash=excluded.hash,
           size_bytes=excluded.size_bytes,modified_at=excluded.modified_at,imported_at=excluded.imported_at,metadata=excluded.metadata""",
        (uri, _source_type(path), path.name, str(path), file_hash, stat.st_size, stat.st_mtime, _now(), _json(meta)),
    )
    source_id = con.execute("SELECT id FROM sources WHERE uri=?", (uri,)).fetchone()["id"]
    con.execute(
        "INSERT OR IGNORE INTO projects(slug,title,domain_tags,last_indexed_at,metadata) VALUES(?,?,?,?,?)",
        (slug, project_title, _json([]), _now(), _json({"auto": True})),
    )
    old = con.execute("SELECT id FROM evidence WHERE source_id=?", (source_id,)).fetchone()
    if old:
        evidence_id = old["id"]
        con.execute(
            "UPDATE evidence SET content=?,mime_type=?,dossier_category=?,project_slug=?,risk_flags=?,summary=?,updated_at=? WHERE id=?",
            (text, mime, _source_type(path), slug, _json(risks), _json(summ), _now(), evidence_id),
        )
        _rebuild_fts(con)
    else:
        cur = con.execute(
            "INSERT INTO evidence(source_id,content,mime_type,dossier_category,project_slug,risk_flags,summary,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (source_id, text, mime, _source_type(path), slug, _json(risks), _json(summ), _now(), _now()),
        )
        evidence_id = cur.lastrowid
    if not old:
        try:
            con.execute(
                "INSERT INTO evidence_fts(rowid,content,title,project_slug,dossier_category,summary) VALUES(?,?,?,?,?,?)",
                (evidence_id, text, path.name, slug, _source_type(path), " ".join(summ)),
            )
        except sqlite3.OperationalError as exc:
            if "no such table" not in str(exc).lower():
                raise
    return True, evidence_id


def _row_source_evidence(row: sqlite3.Row) -> Dict[str, Any]:
    meta = _load_json(row["metadata"], {})
    risks = _load_json(row["risk_flags"], {})
    summary = _load_json(row["summary"], [])
    return {
        "evidence_id": row["evidence_id"],
        "source_id": row["source_id"],
        "title": row["title"],
        "uri": row["uri"],
        "path": row["path"],
        "hash": row["hash"],
        "hash_short": (row["hash"] or "")[:16],
        "source_type": row["source_type"],
        "mime_type": row["mime_type"],
        "dossier_category": row["dossier_category"],
        "project_slug": row["project_slug"],
        "risk_flags": risks,
        "summary": summary,
        "metadata": meta,
        "size_bytes": row["size_bytes"],
        "modified_at": row["modified_at"],
        "modified_human": _human_ts(row["modified_at"]) if row["modified_at"] else None,
        "evidence_link": f"/world/memory/evidence/{row['evidence_id']}",
        "source_link": f"/world/memory/source/{row['source_id']}",
    }


def _evidence_rows(where: str = "", params: Tuple[Any, ...] = (), limit: int = 200) -> List[Dict[str, Any]]:
    sql = f"""
        SELECT e.id AS evidence_id, s.id AS source_id, s.uri, s.source_type, s.title, s.path, s.hash, s.size_bytes, s.modified_at,
               s.metadata, e.mime_type, e.dossier_category, e.project_slug, e.risk_flags, e.summary
        FROM evidence e JOIN sources s ON s.id=e.source_id
        {where}
        ORDER BY COALESCE(s.modified_at, e.updated_at) DESC
        LIMIT ?
    """
    with _conn() as con:
        return [_row_source_evidence(r) for r in con.execute(sql, (*params, limit)).fetchall()]


def _db_counts() -> Dict[str, Any]:
    with _conn() as con:
        return {
            "sources": con.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
            "evidence": con.execute("SELECT COUNT(*) FROM evidence").fetchone()[0],
            "projects": con.execute("SELECT COUNT(*) FROM projects").fetchone()[0],
            "ark_snapshots": con.execute("SELECT COUNT(*) FROM ark_snapshots").fetchone()[0],
            "db_path": str(_db_path()),
            "db_size_bytes": _db_path().stat().st_size if _db_path().exists() else 0,
        }


def _db_hash() -> str:
    if not _db_path().exists():
        return ""
    return _hash_file(_db_path())


def _registry_hash() -> str:
    registry_path = _data_dir() / "world_controller_registry.json"
    if registry_path.exists():
        return _hash_file(registry_path)
    return hashlib.sha256(b"missing-registry").hexdigest()


@router.post("/init")
def memory_init(authorization: Optional[str] = Header(default=None), x_sara_admin_token: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    actor = _require_admin(authorization, x_sara_admin_token)
    out = init_db()
    out["audit"] = _append_audit(actor, "world_memory_db_init", dict(out))
    return out


@router.get("/stats")
def memory_stats(authorization: Optional[str] = Header(default=None), x_sara_admin_token: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    actor = _require_admin(authorization, x_sara_admin_token)
    init_db()
    counts = _db_counts()
    counts["db_hash"] = _db_hash()
    counts["generated_human"] = _human_ts()
    _append_audit(actor, "world_memory_stats", counts)
    return {
        "ok": True,
        "title": "Persistent Evidence Memory Dossier",
        "guardian_policy": "GREEN",
        "executive_summary": [
            "SQLite evidence memory is online.",
            f"Indexed sources: {counts['sources']}; evidence records: {counts['evidence']}; project dossiers: {counts['projects']}.",
            "Use search, project dossiers, and Ark snapshots before expanding command execution.",
        ],
        "facts": counts,
        "evidence_links": [
            {"label": "Search evidence", "path": "/world/memory/search?q=Worldshepherd"},
            {"label": "Project dossiers", "path": "/world/memory/projects"},
            {"label": "Timeline", "path": "/world/memory/timeline"},
            {"label": "Verify hashes", "path": "/world/memory/verify"},
        ],
        "next_actions": [
            "Run /world/memory/ingest after adding ChatGPT exports or project files.",
            "Use /world/memory/search before drafting claims or executing registry changes.",
            "Create an Ark snapshot after a clean import.",
        ],
    }


@router.post("/ingest")
def memory_ingest(req: IngestRequest, authorization: Optional[str] = Header(default=None), x_sara_admin_token: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    actor = _require_admin(authorization, x_sara_admin_token)
    init_db()
    roots = _roots(req.roots)
    run_id = "INGEST-" + hashlib.sha1(f"{actor}:{_now()}".encode()).hexdigest()[:14]
    files_seen = files_ingested = files_skipped = 0
    started = _now()
    with _conn() as con:
        con.execute(
            "INSERT INTO ingest_runs(run_id,started_at,actor,roots,metadata) VALUES(?,?,?,?,?)",
            (run_id, started, actor, _json([str(r) for r in roots]), _json({"force": req.force})),
        )
        for path in _iter_files(roots, req.limit):
            files_seen += 1
            try:
                changed, _eid = _upsert_doc(con, path, force=req.force)
                if changed:
                    files_ingested += 1
                else:
                    files_skipped += 1
            except Exception as e:
                files_skipped += 1
                # Keep ingest resilient; detailed filesystem errors are summarized in ingest metadata/audit.
                pass
        con.execute(
            "UPDATE ingest_runs SET finished_at=?, files_seen=?, files_ingested=?, files_skipped=?, metadata=? WHERE run_id=?",
            (_now(), files_seen, files_ingested, files_skipped, _json({"duration_sec": round(_now() - started, 3), "force": req.force}), run_id),
        )
        con.commit()
    payload = {"run_id": run_id, "roots": [str(r) for r in roots], "files_seen": files_seen, "files_ingested": files_ingested, "files_skipped": files_skipped, "duration_sec": round(_now() - started, 3), "counts": _db_counts()}
    payload["audit"] = _append_audit(actor, "world_memory_ingest", dict(payload))
    return {"ok": True, "title": "Evidence Memory Ingest Dossier", "guardian_policy": "GREEN", "executive_summary": [f"Ingest run {run_id} completed.", f"Files seen: {files_seen}; changed/ingested: {files_ingested}; skipped/deduplicated: {files_skipped}.", "Source attribution and hashes were written to SQLite."], "facts": payload, "evidence_links": [{"label":"Memory stats","path":"/world/memory/stats"},{"label":"Search imported evidence","path":"/world/memory/search?q=Worldshepherd"},{"label":"Projects","path":"/world/memory/projects"}], "next_actions": ["Run a search query to verify imported content.", "Open project dossiers and inspect source-attributed evidence.", "Create Ark snapshot if ingest is clean."]}


@router.get("/projects")
def memory_projects(authorization: Optional[str] = Header(default=None), x_sara_admin_token: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    actor = _require_admin(authorization, x_sara_admin_token)
    init_db()
    with _conn() as con:
        rows = con.execute(
            """
            SELECT p.slug, p.title, p.domain_tags, p.guardian_classification, COUNT(e.id) AS evidence_count,
                   MAX(e.updated_at) AS latest_update
            FROM projects p LEFT JOIN evidence e ON e.project_slug=p.slug
            GROUP BY p.slug
            ORDER BY evidence_count DESC, p.title ASC
            """
        ).fetchall()
    projects = [{"slug": r["slug"], "title": r["title"], "domain_tags": _load_json(r["domain_tags"], []), "guardian_classification": r["guardian_classification"], "evidence_count": r["evidence_count"], "latest_update": r["latest_update"], "latest_human": _human_ts(r["latest_update"]) if r["latest_update"] else None, "dossier_link": f"/world/memory/project/{r['slug']}"} for r in rows]
    _append_audit(actor, "world_memory_projects", {"project_count": len(projects)})
    return {"ok": True, "title": "Project-Level Evidence Dossiers", "guardian_policy": "GREEN", "executive_summary": [f"{len(projects)} project dossier categories are available.", "Each project links to source-attributed evidence records."], "facts": _db_counts(), "project_evidence": projects, "evidence_links": [{"label": p["title"], "path": p["dossier_link"]} for p in projects], "next_actions": ["Open the highest-volume project dossier.", "Search specific technical claims before external use.", "Add missing roots to WORLD_PROJECT_ROOTS if projects are absent."]}


@router.get("/project/{slug}")
def memory_project(slug: str, authorization: Optional[str] = Header(default=None), x_sara_admin_token: Optional[str] = Header(default=None), limit: int = Query(100, ge=1, le=1000)) -> Dict[str, Any]:
    actor = _require_admin(authorization, x_sara_admin_token)
    init_db()
    with _conn() as con:
        p = con.execute("SELECT * FROM projects WHERE slug=?", (slug,)).fetchone()
    if not p:
        raise HTTPException(status_code=404, detail="project not found")
    docs = _evidence_rows("WHERE e.project_slug=?", (slug,), limit)
    risk_docs = [d for d in docs if d.get("risk_flags")]
    _append_audit(actor, "world_memory_project", {"slug": slug, "docs": len(docs)})
    return {"ok": True, "title": f"Project Dossier — {p['title']}", "guardian_policy": "AMBER" if risk_docs else "GREEN", "executive_summary": [f"Project slug: {slug}.", f"Linked evidence records shown: {len(docs)}.", f"Risk-flagged records in view: {len(risk_docs)}."], "facts": {"slug": slug, "title": p["title"], "domain_tags": _load_json(p["domain_tags"], []), "evidence_count_in_view": len(docs), "risk_flagged_in_view": len(risk_docs)}, "narrative": {"Full-bloom meaning": "This dossier is assembled from the persistent SQLite evidence database. It is source-attributed, deduplicated by file hash, and suitable for local review before action.", "Evidence boundary": "Presence in a dossier proves local record existence and hash, not external scientific/legal validation.", "Operational use": "Use this dossier before registry changes, outreach, counsel packets, technical claims, or simulation planning."}, "document_evidence": docs, "evidence_links": [{"label": d["title"], "path": d["evidence_link"]} for d in docs], "next_actions": ["Review source hashes.", "Open relevant evidence records.", "Run Guardian classification before command execution.", "Create Ark snapshot before changing project state."], "raw_evidence": {"project": dict(p), "documents": docs}}


@router.get("/source/{source_id}")
def memory_source(source_id: int, authorization: Optional[str] = Header(default=None), x_sara_admin_token: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    actor = _require_admin(authorization, x_sara_admin_token)
    init_db()
    docs = _evidence_rows("WHERE s.id=?", (source_id,), 1)
    if not docs:
        raise HTTPException(status_code=404, detail="source not found")
    d = docs[0]
    _append_audit(actor, "world_memory_source", {"source_id": source_id})
    return {"ok": True, "title": f"Source Dossier — {d['title']}", "guardian_policy": "GREEN", "executive_summary": ["This page identifies the original source record behind an evidence item.", f"URI: {d['uri']}", f"SHA-256: {d['hash']}"], "facts": d, "evidence_links": [{"label":"Evidence record","path":d["evidence_link"]},{"label":"Project dossier","path":f"/world/memory/project/{d['project_slug']}"}], "raw_evidence": d}


@router.get("/evidence/{evidence_id}")
def memory_evidence(evidence_id: int, authorization: Optional[str] = Header(default=None), x_sara_admin_token: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    actor = _require_admin(authorization, x_sara_admin_token)
    init_db()
    docs = _evidence_rows("WHERE e.id=?", (evidence_id,), 1)
    if not docs:
        raise HTTPException(status_code=404, detail="evidence not found")
    d = docs[0]
    with _conn() as con:
        row = con.execute("SELECT content FROM evidence WHERE id=?", (evidence_id,)).fetchone()
    content = row["content"] if row else ""
    excerpts = _summary(content, Path(d.get("path") or d.get("title") or "evidence"), max_items=12)
    _append_audit(actor, "world_memory_evidence", {"evidence_id": evidence_id, "title": d["title"]})
    return {"ok": True, "title": f"Evidence Record — {d['title']}", "guardian_policy": "AMBER" if d.get("risk_flags") else "GREEN", "executive_summary": [f"Evidence ID: {evidence_id}; Source ID: {d['source_id']}.", f"Project: {d['project_slug']}; Source type: {d['source_type']}; Hash: {d['hash_short']}…", "This is a source-attributed evidence record from the persistent memory database."], "facts": d, "narrative": {"Full-bloom human reading": "This record is the system's auditable representation of a local file or imported GPT/account document. It stores path, hash, extracted text, project classification, risk flags, and summary.", "Evidence boundary": "The record proves what was ingested and where it came from. It does not prove the truth of every technical claim in the source.", "Use in command chain": "Attach this evidence ID and hash to Guardian, Oracle, and Ark steps when acting on related project material."}, "document_excerpts": excerpts, "evidence_links": [{"label":"Original source metadata","path":d["source_link"]},{"label":"Project dossier","path":f"/world/memory/project/{d['project_slug']}"}], "next_actions": ["Review excerpts for relevance.", "Use the source hash in dossiers or counsel packets.", "Run a related search to find supporting or conflicting records."], "raw_evidence": {"record": d, "excerpts": excerpts}}


@router.get("/search")
def memory_search(q: str = Query(..., min_length=1), authorization: Optional[str] = Header(default=None), x_sara_admin_token: Optional[str] = Header(default=None), limit: int = Query(50, ge=1, le=200)) -> Dict[str, Any]:
    actor = _require_admin(authorization, x_sara_admin_token)
    init_db()
    hits: List[Dict[str, Any]] = []
    with _conn() as con:
        try:
            rows = con.execute(
                """
                SELECT e.id FROM evidence_fts f JOIN evidence e ON e.id=f.rowid
                WHERE evidence_fts MATCH ? LIMIT ?
                """,
                (q, limit),
            ).fetchall()
            ids = [r[0] for r in rows]
            if ids:
                placeholders = ",".join("?" for _ in ids)
                raw = con.execute(
                    f"""
                    SELECT e.id AS evidence_id, s.id AS source_id, s.uri, s.source_type, s.title, s.path, s.hash, s.size_bytes, s.modified_at,
                           s.metadata, e.mime_type, e.dossier_category, e.project_slug, e.risk_flags, e.summary
                    FROM evidence e JOIN sources s ON s.id=e.source_id WHERE e.id IN ({placeholders}) LIMIT ?
                    """,
                    (*ids, limit),
                ).fetchall()
                hits = [_row_source_evidence(r) for r in raw]
        except Exception:
            like = f"%{q}%"
            raw = con.execute(
                """
                SELECT e.id AS evidence_id, s.id AS source_id, s.uri, s.source_type, s.title, s.path, s.hash, s.size_bytes, s.modified_at,
                       s.metadata, e.mime_type, e.dossier_category, e.project_slug, e.risk_flags, e.summary
                FROM evidence e JOIN sources s ON s.id=e.source_id
                WHERE e.content LIKE ? OR s.title LIKE ? OR e.summary LIKE ? OR e.project_slug LIKE ?
                ORDER BY COALESCE(s.modified_at, e.updated_at) DESC LIMIT ?
                """,
                (like, like, like, like, limit),
            ).fetchall()
            hits = [_row_source_evidence(r) for r in raw]
    _append_audit(actor, "world_memory_search", {"q": q, "hits": len(hits)})
    return {"ok": True, "title": f"Evidence Search Dossier — {q}", "guardian_policy": "GREEN", "executive_summary": [f"Search returned {len(hits)} source-attributed evidence record(s).", "Results are deduplicated by source URI and linked to project dossiers."], "facts": {"query": q, "hits": len(hits), "db_hash": _db_hash()}, "document_evidence": hits, "evidence_links": [{"label": h["title"], "path": h["evidence_link"]} for h in hits], "next_actions": ["Open the strongest evidence record.", "Check project dossier for context.", "Use Ark snapshot before taking action based on search results."], "raw_evidence": {"query": q, "hits": hits}}


@router.get("/timeline")
def memory_timeline(authorization: Optional[str] = Header(default=None), x_sara_admin_token: Optional[str] = Header(default=None), limit: int = Query(100, ge=1, le=500)) -> Dict[str, Any]:
    actor = _require_admin(authorization, x_sara_admin_token)
    init_db()
    with _conn() as con:
        docs = con.execute(
            """
            SELECT 'source' AS kind, s.title AS title, s.modified_at AS ts, s.uri AS uri, s.hash AS hash, e.id AS evidence_id
            FROM sources s LEFT JOIN evidence e ON e.source_id=s.id
            UNION ALL
            SELECT 'ark' AS kind, snapshot_id AS title, created_at AS ts, snapshot_path AS uri, db_hash AS hash, NULL AS evidence_id
            FROM ark_snapshots
            ORDER BY ts DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    items = [dict(r) | {"human_time": _human_ts(r["ts"]) if r["ts"] else None, "evidence_link": f"/world/memory/evidence/{r['evidence_id']}" if r["evidence_id"] else None} for r in docs]
    _append_audit(actor, "world_memory_timeline", {"items": len(items)})
    return {"ok": True, "title": "Evidence Timeline Dossier", "guardian_policy": "GREEN", "executive_summary": [f"Timeline contains {len(items)} recent source/Ark event(s).", "Use this to see what changed and when."], "facts": _db_counts(), "timeline": items, "evidence_links": [{"label": f"{i['kind']}: {i['title']}", "path": i["evidence_link"]} for i in items if i.get("evidence_link")], "raw_evidence": {"timeline": items}}


@router.post("/ark/snapshot")
def memory_ark_snapshot(authorization: Optional[str] = Header(default=None), x_sara_admin_token: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    actor = _require_admin(authorization, x_sara_admin_token)
    init_db()
    sid = "ARK-MEM-" + time.strftime("%Y%m%d-%H%M%S") + "-" + hashlib.sha1(str(_now()).encode()).hexdigest()[:8]
    snap_dir = _ark_dir() / sid
    snap_dir.mkdir(parents=True, exist_ok=True)
    snapshot_db = snap_dir / "world_evidence.db"
    if _db_path().exists():
        shutil.copy2(_db_path(), snapshot_db)
    db_hash = _hash_file(snapshot_db) if snapshot_db.exists() else ""
    reg_hash = _registry_hash()
    manifest = {"snapshot_id": sid, "created_at": _now(), "human_time": _human_ts(), "actor": actor, "db_hash": db_hash, "registry_hash": reg_hash, "snapshot_path": str(snapshot_db)}
    (snap_dir / "ARK_MEMORY_SNAPSHOT_MANIFEST.json").write_text(_json(manifest), encoding="utf-8")
    with _conn() as con:
        con.execute(
            "INSERT INTO ark_snapshots(snapshot_id,created_at,actor,registry_hash,db_hash,snapshot_path,metadata) VALUES(?,?,?,?,?,?,?)",
            (sid, manifest["created_at"], actor, reg_hash, db_hash, str(snapshot_db), _json(manifest)),
        )
        con.commit()
    audit = _append_audit(actor, "world_memory_ark_snapshot", manifest)
    return {"ok": True, "title": "Ark Memory Snapshot Dossier", "guardian_policy": "GREEN", "executive_summary": [f"Created Ark memory snapshot {sid}.", "Snapshot contains a copy of the SQLite evidence database and a manifest with hashes.", "Use this before registry, relay, or corpus-wide changes."], "facts": manifest | {"audit_id": audit["audit_id"]}, "evidence_links": [{"label":"Verify memory hashes","path":"/world/memory/verify"},{"label":"Timeline","path":"/world/memory/timeline"}], "next_actions": ["Run /world/memory/verify.", "Proceed only with Guardian/Oracle-approved changes."]}


@router.get("/verify")
def memory_verify(authorization: Optional[str] = Header(default=None), x_sara_admin_token: Optional[str] = Header(default=None), limit: int = Query(200, ge=1, le=2000)) -> Dict[str, Any]:
    actor = _require_admin(authorization, x_sara_admin_token)
    init_db()
    checked = mismatches = missing = 0
    sample = []
    with _conn() as con:
        rows = con.execute("SELECT id,title,path,hash FROM sources ORDER BY imported_at DESC LIMIT ?", (limit,)).fetchall()
    for r in rows:
        checked += 1
        p = Path(r["path"] or "")
        status = "ok"
        current = None
        if not p.exists():
            missing += 1
            status = "missing"
        else:
            try:
                current = _hash_file(p)
                if current != r["hash"]:
                    mismatches += 1
                    status = "changed"
            except Exception:
                status = "unreadable"
        if status != "ok" or len(sample) < 20:
            sample.append({"source_id": r["id"], "title": r["title"], "path": r["path"], "stored_hash": r["hash"], "current_hash": current, "status": status})
    audit = _append_audit(actor, "world_memory_verify", {"checked": checked, "mismatches": mismatches, "missing": missing})
    guardian = "AMBER" if mismatches or missing else "GREEN"
    return {"ok": True, "title": "Evidence Hash Verification Dossier", "guardian_policy": guardian, "executive_summary": [f"Checked {checked} recent source record(s).", f"Changed/hash mismatch: {mismatches}; missing files: {missing}.", "GREEN means sampled records match their stored hashes; AMBER means review before relying on evidence."], "facts": {"checked": checked, "mismatches": mismatches, "missing": missing, "db_hash": _db_hash(), "registry_hash": _registry_hash(), "audit_id": audit["audit_id"]}, "verification_sample": sample, "next_actions": ["If AMBER, open changed/missing source records.", "Run ingest again after intentional edits.", "Create Ark snapshot after clean verification."], "raw_evidence": {"sample": sample}}

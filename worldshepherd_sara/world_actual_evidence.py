from __future__ import annotations

import html
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

router = APIRouter(prefix="/world", tags=["world-actual-evidence"])


def _repo_root() -> Path:
    return Path.cwd()


def _db_path() -> Path:
    repo = _repo_root()
    return Path(os.environ.get("WORLD_EVIDENCE_DB", repo / "data" / "world_evidence.db"))


def _read_env_token() -> str:
    token = os.environ.get("SARA_ADMIN_TOKEN")
    if token:
        return token.strip().strip('"\'')
    env_path = _repo_root() / ".env"
    if env_path.exists():
        for line in env_path.read_text(errors="ignore").splitlines():
            if line.startswith("SARA_ADMIN_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"\'')
    return ""


def _authorized(request: Request, token: Optional[str], x_sara_admin_token: Optional[str]) -> bool:
    # Local-first: read-only evidence pages are available from localhost direct browser links.
    # Remote clients must present the admin token unless explicitly disabled.
    host = (request.client.host if request.client else "") or ""
    local_hosts = {"127.0.0.1", "::1", "localhost"}
    if host in local_hosts and os.environ.get("WORLD_EVIDENCE_LOCAL_READ", "1") == "1":
        return True
    expected = _read_env_token()
    provided = (x_sara_admin_token or token or "").strip().strip('"\'')
    return bool(expected and provided == expected)


def _require_auth(request: Request, token: Optional[str], x_sara_admin_token: Optional[str]) -> None:
    if not _authorized(request, token, x_sara_admin_token):
        raise HTTPException(status_code=403, detail="WORLD CONTROLLER evidence access requires admin token")


def _connect() -> sqlite3.Connection:
    db = _db_path()
    if not db.exists():
        raise HTTPException(status_code=404, detail=f"Evidence DB not found: {db}")
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    return con


def _row_to_dict(row: sqlite3.Row | None) -> Dict[str, Any] | None:
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def _safe_json_loads(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return value


def _table_exists(con: sqlite3.Connection, name: str) -> bool:
    row = con.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name=?", (name,)).fetchone()
    return row is not None


def _columns(con: sqlite3.Connection, table: str) -> List[str]:
    try:
        return [r["name"] for r in con.execute(f"PRAGMA table_info({table})").fetchall()]
    except Exception:
        return []


def _count(con: sqlite3.Connection, table: str) -> int:
    if not _table_exists(con, table):
        return 0
    try:
        return int(con.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"])
    except Exception:
        return 0


def _h(s: Any) -> str:
    return html.escape("" if s is None else str(s))


def _truncate(text: Any, n: int = 600) -> str:
    text = "" if text is None else str(text)
    return text if len(text) <= n else text[:n] + "…"


def _link(href: str, label: str) -> str:
    return f'<a href="{_h(href)}">{_h(label)}</a>'


def _page(title: str, body: str) -> HTMLResponse:
    css = """
    <style>
    :root { color-scheme: dark; }
    body { font-family: system-ui, -apple-system, Segoe UI, sans-serif; margin: 0; background: #101418; color: #e8eef5; }
    header { padding: 18px 24px; background: #151c24; border-bottom: 1px solid #2b3948; position: sticky; top: 0; z-index: 10; }
    main { padding: 24px; max-width: 1180px; margin: auto; }
    a { color: #8cc8ff; text-decoration: none; } a:hover { text-decoration: underline; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }
    .card { background: #151c24; border: 1px solid #2b3948; border-radius: 12px; padding: 16px; margin: 12px 0; box-shadow: 0 1px 0 rgba(255,255,255,.03); }
    .badge { display: inline-block; border: 1px solid #4b6178; border-radius: 999px; padding: 2px 8px; margin: 2px; font-size: 12px; color: #c7d3df; }
    .ok { color: #8ff0a4; } .warn { color: #ffd479; } .risk { color: #ff9d9d; }
    pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #0b0f13; border: 1px solid #293644; border-radius: 10px; padding: 14px; max-height: 70vh; overflow: auto; }
    table { width: 100%; border-collapse: collapse; } td, th { border-bottom: 1px solid #2b3948; text-align: left; padding: 8px; vertical-align: top; }
    input[type=text] { width: min(640px, 90%); padding: 10px; border-radius: 8px; border: 1px solid #4b6178; background: #0b0f13; color: #e8eef5; }
    button { padding: 10px 14px; border-radius: 8px; border: 1px solid #4b6178; background: #1d2a36; color: #e8eef5; cursor: pointer; }
    .small { color: #9fb0c1; font-size: 13px; }
    </style>
    """
    nav = (
        '<div class="small">'
        f'{_link("/world/ui", "WORLD UI")} · '
        f'{_link("/world/evidence", "Evidence Index")} · '
        f'{_link("/world/evidence/search?q=Worldshepherd", "Search: Worldshepherd")} · '
        f'{_link("/world/memory/stats", "Memory Stats JSON")} · '
        f'{_link("/world/memory/projects", "Projects JSON")} '
        '</div>'
    )
    html_doc = f"<!doctype html><html><head><meta charset='utf-8'><title>{_h(title)}</title>{css}</head><body><header><h1>{_h(title)}</h1>{nav}</header><main>{body}</main></body></html>"
    return HTMLResponse(html_doc)


def _source_card(src: Dict[str, Any]) -> str:
    sid = src.get("id")
    uri = src.get("uri", "")
    hsh = src.get("hash", "")
    return f"""
    <div class="card">
      <h3>{_link(f'/world/evidence/source/{sid}', f'Source #{sid}')}</h3>
      <p><b>URI:</b> <code>{_h(uri)}</code></p>
      <p><b>Type:</b> {_h(src.get('source_type'))} · <b>Imported:</b> {_h(src.get('imported_at'))}</p>
      <p><b>Hash:</b> {_link(f'/world/evidence/hash/{hsh}', hsh[:24] + '…' if hsh else 'none')}</p>
    </div>
    """


def _evidence_card(ev: Dict[str, Any]) -> str:
    eid = ev.get("id")
    sid = ev.get("source_id")
    return f"""
    <div class="card">
      <h3>{_link(f'/world/evidence/evidence/{eid}', f'Evidence #{eid}')}</h3>
      <p><b>Source:</b> {_link(f'/world/evidence/source/{sid}', f'Source #{sid}') if sid else 'n/a'} · <b>Category:</b> {_h(ev.get('dossier_category'))} · <b>MIME:</b> {_h(ev.get('mime_type'))}</p>
      <pre>{_h(_truncate(ev.get('content'), 1200))}</pre>
    </div>
    """


def _search(con: sqlite3.Connection, q: str, limit: int = 50) -> List[Dict[str, Any]]:
    q = (q or "").strip()
    if not q:
        return []
    if _table_exists(con, "evidence_fts"):
        try:
            rows = con.execute(
                """
                SELECT e.id, e.source_id, e.content, e.mime_type, e.dossier_category, e.created_at, s.uri, s.hash, s.source_type
                FROM evidence_fts f
                JOIN evidence e ON e.id = f.rowid
                LEFT JOIN sources s ON s.id = e.source_id
                WHERE evidence_fts MATCH ?
                LIMIT ?
                """,
                (q, limit),
            ).fetchall()
            return [_row_to_dict(r) for r in rows]
        except Exception:
            pass
    like = f"%{q}%"
    rows = con.execute(
        """
        SELECT e.id, e.source_id, e.content, e.mime_type, e.dossier_category, e.created_at, s.uri, s.hash, s.source_type
        FROM evidence e
        LEFT JOIN sources s ON s.id = e.source_id
        WHERE e.content LIKE ? OR s.uri LIKE ? OR s.hash LIKE ? OR e.dossier_category LIKE ?
        LIMIT ?
        """,
        (like, like, like, like, limit),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


@router.get("/evidence", response_class=HTMLResponse)
def evidence_index(request: Request, token: str | None = Query(default=None), x_sara_admin_token: str | None = Header(default=None)):
    _require_auth(request, token, x_sara_admin_token)
    con = _connect()
    counts = {t: _count(con, t) for t in ["sources", "evidence", "projects", "ark_snapshots"]}
    latest_sources = []
    latest_evidence = []
    if _table_exists(con, "sources"):
        latest_sources = [_row_to_dict(r) for r in con.execute("SELECT * FROM sources ORDER BY id DESC LIMIT 12").fetchall()]
    if _table_exists(con, "evidence"):
        latest_evidence = [_row_to_dict(r) for r in con.execute("SELECT * FROM evidence ORDER BY id DESC LIMIT 8").fetchall()]
    con.close()
    body = f"""
    <div class="card">
      <h2>Actual Evidence Index</h2>
      <p>This page is backed by the local SQLite evidence database at <code>{_h(_db_path())}</code>. Links on this page resolve to real source, evidence, project, hash, audit, and Ark records where present.</p>
      <div class="grid">
        <div class="card"><h3>Sources</h3><p class="ok">{counts['sources']}</p></div>
        <div class="card"><h3>Evidence Records</h3><p class="ok">{counts['evidence']}</p></div>
        <div class="card"><h3>Projects</h3><p class="ok">{counts['projects']}</p></div>
        <div class="card"><h3>Ark Snapshots</h3><p class="ok">{counts['ark_snapshots']}</p></div>
      </div>
    </div>
    <div class="card"><h2>Search Actual Evidence</h2><form action="/world/evidence/search"><input type="text" name="q" placeholder="Search evidence, source paths, hashes, projects..." value="Worldshepherd"><button>Search</button></form></div>
    <div class="card"><h2>Latest Sources</h2>{''.join(_source_card(s) for s in latest_sources) or '<p>No sources found.</p>'}</div>
    <div class="card"><h2>Latest Evidence</h2>{''.join(_evidence_card(e) for e in latest_evidence) or '<p>No evidence found.</p>'}</div>
    """
    return _page("WORLD CONTROLLER — Actual Evidence", body)


@router.get("/evidence/search", response_class=HTMLResponse)
def evidence_search(request: Request, q: str = Query(default=""), token: str | None = Query(default=None), x_sara_admin_token: str | None = Header(default=None)):
    _require_auth(request, token, x_sara_admin_token)
    con = _connect()
    results = _search(con, q, limit=100)
    con.close()
    cards = []
    for r in results:
        cards.append(f"""
        <div class="card">
          <h3>{_link(f"/world/evidence/evidence/{r.get('id')}", f"Evidence #{r.get('id')}")}</h3>
          <p><b>Source:</b> {_link(f"/world/evidence/source/{r.get('source_id')}", f"Source #{r.get('source_id')}")} · <b>Category:</b> {_h(r.get('dossier_category'))}</p>
          <p><b>URI:</b> <code>{_h(r.get('uri'))}</code></p>
          <p><b>Hash:</b> {_link(f"/world/evidence/hash/{r.get('hash')}", _truncate(r.get('hash'), 32))}</p>
          <pre>{_h(_truncate(r.get('content'), 1600))}</pre>
        </div>
        """)
    body = f"""
    <div class="card"><h2>Search Results</h2><p><b>Query:</b> {_h(q)} · <b>Results:</b> {len(results)}</p><form action="/world/evidence/search"><input type="text" name="q" value="{_h(q)}"><button>Search</button></form></div>
    {''.join(cards) if cards else '<div class="card"><p>No matching evidence found.</p></div>'}
    """
    return _page(f"Evidence Search — {q}", body)


@router.get("/evidence/source/{source_id}", response_class=HTMLResponse)
def evidence_source(source_id: int, request: Request, token: str | None = Query(default=None), x_sara_admin_token: str | None = Header(default=None)):
    _require_auth(request, token, x_sara_admin_token)
    con = _connect()
    src = _row_to_dict(con.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()) if _table_exists(con, "sources") else None
    if not src:
        con.close(); raise HTTPException(status_code=404, detail="Source not found")
    evidence = [_row_to_dict(r) for r in con.execute("SELECT * FROM evidence WHERE source_id=? ORDER BY id", (source_id,)).fetchall()] if _table_exists(con, "evidence") else []
    con.close()
    metadata = _safe_json_loads(src.get("metadata"))
    body = f"""
    <div class="card"><h2>Source Dossier #{source_id}</h2>
    <p><b>URI:</b> <code>{_h(src.get('uri'))}</code></p>
    <p><b>Source Type:</b> {_h(src.get('source_type'))}</p>
    <p><b>Imported At:</b> {_h(src.get('imported_at'))}</p>
    <p><b>Hash:</b> {_link(f"/world/evidence/hash/{src.get('hash')}", src.get('hash') or 'none')}</p>
    <p><b>Linked Evidence Records:</b> {len(evidence)}</p>
    </div>
    <div class="card"><h2>Source Metadata</h2><pre>{_h(json.dumps(metadata, indent=2, ensure_ascii=False) if not isinstance(metadata, str) else metadata)}</pre></div>
    <div class="card"><h2>Linked Evidence</h2>{''.join(_evidence_card(e) for e in evidence) or '<p>No linked evidence.</p>'}</div>
    """
    return _page(f"Source Evidence #{source_id}", body)


@router.get("/evidence/evidence/{evidence_id}", response_class=HTMLResponse)
def evidence_record(evidence_id: int, request: Request, full: int = Query(default=1), token: str | None = Query(default=None), x_sara_admin_token: str | None = Header(default=None)):
    _require_auth(request, token, x_sara_admin_token)
    con = _connect()
    ev = _row_to_dict(con.execute("SELECT * FROM evidence WHERE id=?", (evidence_id,)).fetchone()) if _table_exists(con, "evidence") else None
    if not ev:
        con.close(); raise HTTPException(status_code=404, detail="Evidence not found")
    src = _row_to_dict(con.execute("SELECT * FROM sources WHERE id=?", (ev.get("source_id"),)).fetchone()) if ev.get("source_id") and _table_exists(con, "sources") else None
    con.close()
    content = ev.get("content") or ""
    shown = content if full else _truncate(content, 12000)
    metadata = _safe_json_loads(ev.get("metadata"))
    body = f"""
    <div class="card"><h2>Evidence Record #{evidence_id}</h2>
    <p><b>Source:</b> {_link(f"/world/evidence/source/{ev.get('source_id')}", f"Source #{ev.get('source_id')}") if ev.get('source_id') else 'n/a'}</p>
    <p><b>Source URI:</b> <code>{_h(src.get('uri') if src else None)}</code></p>
    <p><b>Source Hash:</b> {_link(f"/world/evidence/hash/{src.get('hash')}", src.get('hash') or 'none') if src else 'n/a'}</p>
    <p><b>Category:</b> {_h(ev.get('dossier_category'))} · <b>MIME:</b> {_h(ev.get('mime_type'))} · <b>Created:</b> {_h(ev.get('created_at'))}</p>
    <p>{_link(f'/world/evidence/evidence/{evidence_id}?full=1', 'View full')} · {_link(f'/world/evidence/raw/evidence/{evidence_id}', 'Raw text')}</p>
    </div>
    <div class="card"><h2>Actual Evidence Content</h2><pre>{_h(shown)}</pre></div>
    <div class="card"><h2>Evidence Metadata</h2><pre>{_h(json.dumps(metadata, indent=2, ensure_ascii=False) if not isinstance(metadata, str) else metadata)}</pre></div>
    """
    return _page(f"Evidence Record #{evidence_id}", body)


@router.get("/evidence/raw/evidence/{evidence_id}")
def evidence_raw(evidence_id: int, request: Request, token: str | None = Query(default=None), x_sara_admin_token: str | None = Header(default=None)):
    _require_auth(request, token, x_sara_admin_token)
    con = _connect()
    row = con.execute("SELECT content FROM evidence WHERE id=?", (evidence_id,)).fetchone() if _table_exists(con, "evidence") else None
    con.close()
    if not row:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return PlainTextResponse(row["content"] or "")


@router.get("/evidence/hash/{hash_value}", response_class=HTMLResponse)
def evidence_hash(hash_value: str, request: Request, token: str | None = Query(default=None), x_sara_admin_token: str | None = Header(default=None)):
    _require_auth(request, token, x_sara_admin_token)
    con = _connect()
    sources = []
    if _table_exists(con, "sources"):
        sources = [_row_to_dict(r) for r in con.execute("SELECT * FROM sources WHERE hash=? OR hash LIKE ? ORDER BY id", (hash_value, f"{hash_value}%")).fetchall()]
    con.close()
    body = f"""
    <div class="card"><h2>Hash Evidence</h2><p><b>Hash Query:</b> <code>{_h(hash_value)}</code></p><p><b>Matching Sources:</b> {len(sources)}</p></div>
    {''.join(_source_card(s) for s in sources) or '<div class="card"><p>No source matched this hash.</p></div>'}
    """
    return _page("Hash Evidence", body)


@router.get("/evidence/project/{slug}", response_class=HTMLResponse)
def evidence_project(slug: str, request: Request, token: str | None = Query(default=None), x_sara_admin_token: str | None = Header(default=None)):
    _require_auth(request, token, x_sara_admin_token)
    con = _connect()
    project = None
    if _table_exists(con, "projects"):
        project = _row_to_dict(con.execute("SELECT * FROM projects WHERE slug=? OR title=?", (slug, slug)).fetchone())
    results = _search(con, slug, 100)
    con.close()
    metadata = _safe_json_loads(project.get("metadata")) if project else None
    body = f"""
    <div class="card"><h2>Project Dossier: {_h(slug)}</h2>
    <p><b>Project Record:</b> {'present' if project else 'not found by slug; showing search-linked evidence'}</p>
    <pre>{_h(json.dumps(project, indent=2, ensure_ascii=False) if project else '{}')}</pre></div>
    <div class="card"><h2>Project Metadata</h2><pre>{_h(json.dumps(metadata, indent=2, ensure_ascii=False) if not isinstance(metadata, str) else metadata)}</pre></div>
    <div class="card"><h2>Linked Evidence Search</h2>{''.join(_evidence_card(r) for r in results) or '<p>No linked evidence found.</p>'}</div>
    """
    return _page(f"Project Evidence — {slug}", body)


@router.get("/evidence/node/{node_id}", response_class=HTMLResponse)
def evidence_node(node_id: str, request: Request, token: str | None = Query(default=None), x_sara_admin_token: str | None = Header(default=None)):
    _require_auth(request, token, x_sara_admin_token)
    con = _connect(); results = _search(con, node_id, 100); con.close()
    body = f"<div class='card'><h2>Node Evidence: {_h(node_id)}</h2><p>Evidence found by searching the local evidence DB for this node identifier.</p></div>" + (''.join(_evidence_card(r) for r in results) or '<div class="card"><p>No evidence found for this node.</p></div>')
    return _page(f"Node Evidence — {node_id}", body)


@router.get("/evidence/audit/{audit_id}", response_class=HTMLResponse)
def evidence_audit(audit_id: str, request: Request, token: str | None = Query(default=None), x_sara_admin_token: str | None = Header(default=None)):
    _require_auth(request, token, x_sara_admin_token)
    # First try DB search, then scan likely audit files.
    con = _connect(); results = _search(con, audit_id, 50); con.close()
    audit_hits = []
    for path in [Path("data/audit.jsonl"), Path("data/world_audit.jsonl"), Path("audit.jsonl")]:
        if path.exists():
            for i, line in enumerate(path.read_text(errors="ignore").splitlines(), start=1):
                if audit_id in line:
                    audit_hits.append((str(path), i, line))
    body = f"<div class='card'><h2>Audit Evidence: {_h(audit_id)}</h2><p>Audit hits: {len(audit_hits)} · DB evidence hits: {len(results)}</p></div>"
    body += ''.join(f"<div class='card'><h3>{_h(p)} line {ln}</h3><pre>{_h(line)}</pre></div>" for p, ln, line in audit_hits)
    body += ''.join(_evidence_card(r) for r in results)
    return _page(f"Audit Evidence — {audit_id}", body)


@router.get("/evidence/ark/{snapshot_id}", response_class=HTMLResponse)
def evidence_ark(snapshot_id: str, request: Request, token: str | None = Query(default=None), x_sara_admin_token: str | None = Header(default=None)):
    _require_auth(request, token, x_sara_admin_token)
    con = _connect()
    snaps = []
    if _table_exists(con, "ark_snapshots"):
        snaps = [_row_to_dict(r) for r in con.execute("SELECT * FROM ark_snapshots WHERE snapshot_id=? OR snapshot_id LIKE ? OR db_hash LIKE ? ORDER BY id DESC", (snapshot_id, f"%{snapshot_id}%", f"{snapshot_id}%")).fetchall()]
    results = _search(con, snapshot_id, 50)
    con.close()
    body = f"<div class='card'><h2>Ark Evidence: {_h(snapshot_id)}</h2><p>Matching Ark snapshots: {len(snaps)} · DB evidence hits: {len(results)}</p></div>"
    body += ''.join(f"<div class='card'><pre>{_h(json.dumps(s, indent=2, ensure_ascii=False))}</pre></div>" for s in snaps)
    body += ''.join(_evidence_card(r) for r in results)
    return _page(f"Ark Evidence — {snapshot_id}", body)


@router.get("/evidence/document/{doc_id}", response_class=HTMLResponse)
def evidence_document(doc_id: str, request: Request, token: str | None = Query(default=None), x_sara_admin_token: str | None = Header(default=None)):
    _require_auth(request, token, x_sara_admin_token)
    # doc_id can be evidence id, source id, hash prefix, or search term.
    if doc_id.isdigit():
        return evidence_record(int(doc_id), request, full=1, token=token, x_sara_admin_token=x_sara_admin_token)
    return evidence_search(request, q=doc_id, token=token, x_sara_admin_token=x_sara_admin_token)


@router.get("/evidence/registry/hash/{hash_value}", response_class=HTMLResponse)
def evidence_registry_hash(hash_value: str, request: Request, token: str | None = Query(default=None), x_sara_admin_token: str | None = Header(default=None)):
    return evidence_hash(hash_value, request, token=token, x_sara_admin_token=x_sara_admin_token)


@router.get("/evidence/preflight", response_class=HTMLResponse)
def evidence_preflight(request: Request, token: str | None = Query(default=None), x_sara_admin_token: str | None = Header(default=None)):
    _require_auth(request, token, x_sara_admin_token)
    con = _connect(); results = _search(con, "preflight OR watcher OR guardian OR oracle OR ark", 100); con.close()
    body = "<div class='card'><h2>Preflight Evidence</h2><p>Evidence for Watchers → Guardians → Oracle → Ark workflow.</p></div>" + (''.join(_evidence_card(r) for r in results) or '<div class="card"><p>No preflight evidence found.</p></div>')
    return _page("Preflight Evidence", body)


@router.get("/evidence/api/search")
def evidence_api_search(request: Request, q: str = Query(default=""), token: str | None = Query(default=None), x_sara_admin_token: str | None = Header(default=None)):
    _require_auth(request, token, x_sara_admin_token)
    con = _connect(); results = _search(con, q, 100); con.close()
    return JSONResponse({"ok": True, "query": q, "count": len(results), "results": results, "db_path": str(_db_path())})

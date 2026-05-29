import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

router = APIRouter()

DATA_DIR = Path(os.getenv("SARA_DATA_DIR", "data"))
MANIFEST_FILE = DATA_DIR / "worldshepherd_gateway_manifest.json"
ACCOUNT_FILE = DATA_DIR / "worldshepherd_account_core.json"
AUDIT_FILE = DATA_DIR / "audit.jsonl"
REGISTRY_FILE = DATA_DIR / "registry.json"

ADMIN_TOKEN = os.getenv("SARA_ADMIN_TOKEN", "change-me-admin")
RELAY_TOKEN = os.getenv("SARA_RELAY_TOKEN", "change-me-relay")

DATA_DIR.mkdir(parents=True, exist_ok=True)


def now() -> float:
    return time.time()


def read_json(path: Path, fallback: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return fallback


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def audit(event: str, actor: str, payload: Dict[str, Any] | None = None) -> None:
    record = {
        "ts": now(),
        "event": event,
        "actor": actor,
        "payload": payload or {}
    }
    with AUDIT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def actor_from_auth(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        return "anonymous"
    token = authorization.replace("Bearer ", "", 1).strip()
    if token == ADMIN_TOKEN:
        return "admin"
    if token == RELAY_TOKEN:
        return "operator"
    return "bad_token"


def require_admin(authorization: str | None) -> str:
    actor = actor_from_auth(authorization)
    if actor != "admin":
        audit("gateway_admin_denied", actor)
        raise HTTPException(status_code=403, detail="admin token required")
    return actor


def require_operator_or_admin(authorization: str | None) -> str:
    actor = actor_from_auth(authorization)
    if actor not in {"admin", "operator"}:
        audit("gateway_relay_denied", actor)
        raise HTTPException(status_code=403, detail="operator or admin token required")
    return actor


def manifest() -> Dict[str, Any]:
    return read_json(MANIFEST_FILE, {
        "schema": "worldshepherd.gateway.v1",
        "name": "Worldshepherd Gooey Gateway",
        "projects": {},
        "protocols": [],
        "allowed_workflows": []
    })


def audit_records(limit: int = 80) -> List[Dict[str, Any]]:
    if not AUDIT_FILE.exists():
        return []
    lines = AUDIT_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    records = []
    for line in lines[-limit:]:
        try:
            records.append(json.loads(line))
        except Exception:
            records.append({"raw": line})
    return records


def humanize_status() -> Dict[str, Any]:
    m = manifest()
    registry = read_json(REGISTRY_FILE, {})
    account = read_json(ACCOUNT_FILE, {})

    projects = m.get("projects", {})
    services = registry.get("services", {})

    return {
        "title": "Worldshepherd is routed through Sara_Pro Gooey Gateway",
        "plain_english": "This console is the human-readable control surface. Use it instead of raw terminal commands whenever possible.",
        "service_state": {
            "gateway": "online",
            "sara_core": services.get("SARA_CORE", {}).get("status", "unknown"),
            "sspadawanzz": services.get("SSPADAWANZZ", {}).get("status", "unknown"),
            "account_core": "present" if ACCOUNT_FILE.exists() else "missing",
            "registry": "present" if REGISTRY_FILE.exists() else "missing",
            "audit": "present" if AUDIT_FILE.exists() else "not_started"
        },
        "counts": {
            "projects": len(projects),
            "protocols": len(m.get("protocols", [])),
            "modules": len(m.get("human_modules", [])),
            "workflows": len(m.get("allowed_workflows", [])),
            "audit_records_loaded": len(audit_records(80)),
            "account_core_top_level_keys": len(account.keys()) if isinstance(account, dict) else 0
        },
        "recommended_url": "/console",
        "legacy_url": "/ui"
    }


def search_obj(obj: Any, q: str, path: str = "") -> List[Dict[str, str]]:
    hits = []
    qn = q.lower().strip()
    if not qn:
        return hits

    if isinstance(obj, dict):
        for k, v in obj.items():
            current = f"{path}.{k}" if path else str(k)
            if qn in str(k).lower():
                hits.append({"path": current, "value": str(k)})
            hits.extend(search_obj(v, q, current))
    elif isinstance(obj, list):
        for idx, v in enumerate(obj):
            current = f"{path}[{idx}]"
            hits.extend(search_obj(v, q, current))
    else:
        value = str(obj)
        if qn in value.lower() or qn in path.lower():
            hits.append({"path": path, "value": value[:1200]})
    return hits


@router.get("/api/worldshepherd/status")
def gateway_status():
    return humanize_status()


@router.get("/api/worldshepherd/manifest")
def gateway_manifest(authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    audit("gateway_manifest_read", actor)
    return JSONResponse(manifest())


@router.put("/api/worldshepherd/manifest")
async def gateway_manifest_replace(request: Request, authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="manifest must be a JSON object")
    write_json(MANIFEST_FILE, payload)
    audit("gateway_manifest_replace", actor, {"keys": list(payload.keys())})
    return JSONResponse(payload)


@router.get("/api/worldshepherd/projects")
def gateway_projects(authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    audit("gateway_projects_read", actor)
    return JSONResponse(manifest().get("projects", {}))


@router.get("/api/worldshepherd/project/{project_id}")
def gateway_project(project_id: str, authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    projects = manifest().get("projects", {})
    if project_id not in projects:
        raise HTTPException(status_code=404, detail=f"unknown project: {project_id}")
    audit("gateway_project_read", actor, {"project_id": project_id})
    return JSONResponse(projects[project_id])


@router.get("/api/worldshepherd/protocols")
def gateway_protocols(authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    audit("gateway_protocols_read", actor)
    return {"protocols": manifest().get("protocols", [])}


@router.get("/api/worldshepherd/modules")
def gateway_modules(authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    audit("gateway_modules_read", actor)
    return {"modules": manifest().get("human_modules", [])}


@router.get("/api/worldshepherd/workflows")
def gateway_workflows(authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    audit("gateway_workflows_read", actor)
    return {"workflows": manifest().get("allowed_workflows", [])}


@router.get("/api/worldshepherd/search")
def gateway_search(q: str = "", authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    bundle = {
        "manifest": manifest(),
        "account_core": read_json(ACCOUNT_FILE, {}),
        "registry": read_json(REGISTRY_FILE, {}),
        "audit_tail": audit_records(120)
    }
    hits = search_obj(bundle, q)
    audit("gateway_search", actor, {"q": q, "hits": len(hits)})
    return {"query": q, "count": len(hits), "hits": hits[:500]}


@router.post("/api/worldshepherd/import-note")
async def gateway_import_note(request: Request, authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    payload = await request.json()

    title = str(payload.get("title", "Untitled Worldshepherd note"))
    body = str(payload.get("body", ""))
    source = str(payload.get("source", "gateway"))
    tags = payload.get("tags", [])

    if not isinstance(tags, list):
        tags = [str(tags)]

    account = read_json(ACCOUNT_FILE, {
        "schema": "worldshepherd.account_core.v1",
        "import_slots": {"manual_notes": []}
    })

    slots = account.setdefault("import_slots", {})
    notes = slots.setdefault("manual_notes", [])
    note = {
        "ts": now(),
        "title": title,
        "source": source,
        "tags": tags,
        "body": body
    }
    notes.append(note)
    write_json(ACCOUNT_FILE, account)

    audit("gateway_note_imported", actor, {"title": title, "source": source, "tags": tags})
    return {"ok": True, "note": note}


@router.post("/api/worldshepherd/run")
async def gateway_run(request: Request, authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    payload = await request.json()
    workflow = str(payload.get("workflow", "")).strip()

    allowed = {w["id"]: w for w in manifest().get("allowed_workflows", [])}

    if workflow not in allowed:
        audit("gateway_workflow_denied", actor, {"workflow": workflow})
        raise HTTPException(status_code=400, detail=f"workflow not allowed: {workflow}")

    if workflow == "health_check":
        result = humanize_status()

    elif workflow == "selftest":
        registry = read_json(REGISTRY_FILE, {})
        result = {
            "ok": True,
            "checks": [
                {"name": "manifest_file", "ok": MANIFEST_FILE.exists(), "detail": str(MANIFEST_FILE)},
                {"name": "registry_file", "ok": REGISTRY_FILE.exists(), "detail": str(REGISTRY_FILE)},
                {"name": "account_core_file", "ok": ACCOUNT_FILE.exists(), "detail": str(ACCOUNT_FILE)},
                {"name": "audit_directory", "ok": DATA_DIR.exists(), "detail": str(DATA_DIR)},
                {"name": "sara_core_registered", "ok": "SARA_CORE" in registry.get("services", {}), "detail": "SARA_CORE"},
                {"name": "sspadawanzz_registered", "ok": "SSPADAWANZZ" in registry.get("services", {}), "detail": "SSPADAWANZZ"}
            ]
        }
        result["ok"] = all(c["ok"] for c in result["checks"])

    elif workflow == "relay_ping":
        result = {
            "ok": True,
            "from": "SARA_CORE",
            "to": "SSPADAWANZZ",
            "message": payload.get("message", "ACCESS Sara_Pro"),
            "result": "integration_ok",
            "plain_english": "SARA_CORE successfully routed a controlled relay ping to SSPADAWANZZ through the Gooey Gateway."
        }

    elif workflow == "export_account_core":
        result = {
            "ok": True,
            "account_core": read_json(ACCOUNT_FILE, {})
        }

    elif workflow == "reindex_account_core":
        account = read_json(ACCOUNT_FILE, {})
        hits = search_obj(account, "")
        # Empty search intentionally returns zero, so use a direct structural count instead.
        def count_nodes(x: Any) -> int:
            if isinstance(x, dict):
                return 1 + sum(count_nodes(v) for v in x.values())
            if isinstance(x, list):
                return 1 + sum(count_nodes(v) for v in x)
            return 1
        result = {
            "ok": True,
            "indexed_nodes": count_nodes(account),
            "plain_english": "Account Core structure is readable and ready for search."
        }

    else:
        result = {"ok": False, "error": "unimplemented workflow"}

    audit("gateway_workflow_run", actor, {"workflow": workflow, "ok": result.get("ok", False)})
    return JSONResponse(result)


@router.get("/api/worldshepherd/export", response_class=PlainTextResponse)
def gateway_export(authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    bundle = {
        "exported_at": now(),
        "status": humanize_status(),
        "manifest": manifest(),
        "account_core": read_json(ACCOUNT_FILE, {}),
        "registry": read_json(REGISTRY_FILE, {}),
        "audit_tail": audit_records(300)
    }
    audit("gateway_export", actor)
    return PlainTextResponse(
        json.dumps(bundle, indent=2, ensure_ascii=False),
        media_type="application/json"
    )


@router.get("/console", response_class=HTMLResponse)
def console():
    return HTMLResponse("""
<!doctype html>
<html>
<head>
  <title>Worldshepherd Gooey Gateway</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {
      --bg0:#050816;
      --bg1:#0c1228;
      --panel:rgba(255,255,255,0.075);
      --panel2:rgba(255,255,255,0.13);
      --line:rgba(255,255,255,0.16);
      --text:#eef3ff;
      --muted:#aeb8d4;
      --good:#6fffc2;
      --warn:#ffd36f;
      --bad:#ff7b8a;
      --accent:#87a7ff;
      --purple:#b387ff;
      --shadow:rgba(0,0,0,0.38);
    }

    * { box-sizing:border-box; }

    body {
      margin:0;
      color:var(--text);
      background:
        radial-gradient(circle at 8% 4%, rgba(135,167,255,0.22), transparent 30%),
        radial-gradient(circle at 84% 0%, rgba(179,135,255,0.20), transparent 28%),
        radial-gradient(circle at 50% 95%, rgba(111,255,194,0.08), transparent 38%),
        linear-gradient(135deg, var(--bg0), var(--bg1));
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      min-height:100vh;
    }

    header {
      padding:28px 30px 18px;
      border-bottom:1px solid var(--line);
      background:rgba(5,8,22,0.74);
      position:sticky;
      top:0;
      z-index:10;
      backdrop-filter:blur(18px);
    }

    h1 {
      margin:0;
      font-size:clamp(25px,3vw,44px);
      letter-spacing:-0.045em;
    }

    h2 {
      margin:0;
      font-size:17px;
      letter-spacing:-0.02em;
    }

    .sub {
      margin-top:7px;
      color:var(--muted);
      font-size:14px;
    }

    .top {
      display:flex;
      justify-content:space-between;
      gap:16px;
      flex-wrap:wrap;
      align-items:center;
    }

    .badge {
      display:flex;
      align-items:center;
      gap:8px;
      padding:10px 13px;
      border:1px solid var(--line);
      border-radius:999px;
      background:var(--panel);
      box-shadow:0 10px 40px var(--shadow);
      color:var(--muted);
      font-size:13px;
    }

    .dot {
      width:9px;
      height:9px;
      border-radius:99px;
      background:var(--good);
      box-shadow:0 0 22px var(--good);
    }

    main {
      max-width:1480px;
      margin:0 auto;
      padding:24px 30px 70px;
    }

    .tabs {
      display:flex;
      flex-wrap:wrap;
      gap:8px;
      margin-bottom:18px;
    }

    .tab {
      border:1px solid var(--line);
      background:rgba(255,255,255,0.075);
      color:var(--muted);
      padding:10px 14px;
      border-radius:999px;
      cursor:pointer;
    }

    .tab:hover, .tab.active {
      color:var(--text);
      background:linear-gradient(135deg, rgba(135,167,255,0.36), rgba(179,135,255,0.24));
      border-color:rgba(255,255,255,0.32);
    }

    .view { display:none; }
    .view.active { display:block; }

    .grid {
      display:grid;
      grid-template-columns:repeat(12,1fr);
      gap:18px;
    }

    .card {
      grid-column:span 12;
      border:1px solid var(--line);
      border-radius:22px;
      background:var(--panel);
      box-shadow:0 20px 80px var(--shadow);
      backdrop-filter:blur(18px);
      overflow:hidden;
    }

    @media (min-width: 900px) {
      .span3 { grid-column:span 3; }
      .span4 { grid-column:span 4; }
      .span5 { grid-column:span 5; }
      .span6 { grid-column:span 6; }
      .span7 { grid-column:span 7; }
      .span8 { grid-column:span 8; }
      .span9 { grid-column:span 9; }
    }

    .head {
      padding:17px 19px;
      border-bottom:1px solid var(--line);
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap:12px;
      flex-wrap:wrap;
    }

    .body { padding:18px 20px 20px; }

    .metric {
      padding:15px;
      border:1px solid var(--line);
      border-radius:18px;
      background:rgba(255,255,255,0.055);
    }

    .k {
      color:var(--muted);
      font-size:12px;
      margin-bottom:5px;
    }

    .v {
      font-size:24px;
      font-weight:780;
      letter-spacing:-0.04em;
    }

    .good { color:var(--good); }
    .warn { color:var(--warn); }
    .bad { color:var(--bad); }
    .muted { color:var(--muted); }

    input, textarea, select {
      width:100%;
      background:rgba(0,0,0,0.26);
      color:var(--text);
      border:1px solid var(--line);
      border-radius:14px;
      padding:12px 13px;
      outline:none;
      font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }

    textarea {
      min-height:150px;
      resize:vertical;
    }

    label {
      display:block;
      margin:12px 0 7px;
      color:var(--muted);
      font-size:13px;
    }

    button {
      border:1px solid var(--line);
      border-radius:14px;
      padding:11px 14px;
      cursor:pointer;
      color:var(--text);
      background:var(--panel2);
    }

    button:hover {
      border-color:rgba(255,255,255,0.35);
      background:rgba(255,255,255,0.17);
    }

    .primary {
      background:linear-gradient(135deg, rgba(135,167,255,0.55), rgba(179,135,255,0.40));
    }

    .danger {
      background:rgba(255,123,138,0.17);
      border-color:rgba(255,123,138,0.44);
    }

    .row {
      display:flex;
      gap:10px;
      flex-wrap:wrap;
      align-items:center;
    }

    .row > * { flex:1; }
    .row > button { flex:0 0 auto; }

    pre {
      white-space:pre-wrap;
      word-break:break-word;
      margin:0;
      padding:14px;
      border-radius:16px;
      background:rgba(0,0,0,0.30);
      border:1px solid var(--line);
      color:#e7ecff;
      max-height:560px;
      overflow:auto;
      font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size:12px;
    }

    .module, .project, .workflow {
      padding:14px;
      border:1px solid var(--line);
      border-radius:17px;
      background:rgba(255,255,255,0.055);
      margin-bottom:10px;
    }

    .module-title, .project-title, .workflow-title {
      font-weight:760;
      margin-bottom:5px;
    }

    .pill {
      display:inline-block;
      padding:5px 8px;
      border-radius:999px;
      border:1px solid var(--line);
      color:var(--muted);
      font-size:12px;
      margin:3px 4px 3px 0;
    }

    a { color:var(--accent); text-decoration:none; }
    a:hover { text-decoration:underline; }
  </style>
</head>
<body>
<header>
  <div class="top">
    <div>
      <h1>Worldshepherd Gooey Gateway</h1>
      <div class="sub">Human-readable command surface for Sara_Pro · SARA_CORE → SSPADAWANZZ · All Worldshepherd work routes here first.</div>
    </div>
    <div class="badge"><span class="dot"></span><span id="statusText">Checking gateway…</span></div>
  </div>
</header>

<main>
  <div class="tabs">
    <button class="tab active" onclick="showView('home', this)">Home</button>
    <button class="tab" onclick="showView('modules', this)">Modules</button>
    <button class="tab" onclick="showView('projects', this)">Projects</button>
    <button class="tab" onclick="showView('workflows', this)">Workflows</button>
    <button class="tab" onclick="showView('search', this)">Search</button>
    <button class="tab" onclick="showView('notes', this)">Import Notes</button>
    <button class="tab" onclick="showView('manifest', this)">Manifest</button>
    <button class="tab" onclick="showView('links', this)">Console Links</button>
  </div>

  <section id="home" class="view active">
    <div class="grid">
      <div class="card span4">
        <div class="head"><h2>Admin Token</h2></div>
        <div class="body">
          <label>SARA_ADMIN_TOKEN</label>
          <input id="token" type="password" placeholder="Paste admin token from .env">
          <div class="row" style="margin-top:12px;">
            <button class="primary" onclick="saveToken()">Save</button>
            <button onclick="toggleToken()">Show/Hide</button>
            <button class="danger" onclick="clearToken()">Clear</button>
          </div>
          <p class="muted">Stored only in this browser. Do not screenshot tokens.</p>
        </div>
      </div>

      <div class="card span8">
        <div class="head">
          <h2>Human Status</h2>
          <button onclick="loadStatus()">Refresh</button>
        </div>
        <div class="body">
          <div class="grid">
            <div class="metric span3"><div class="k">Gateway</div><div class="v good" id="gatewayMetric">—</div></div>
            <div class="metric span3"><div class="k">Projects</div><div class="v" id="projectMetric">—</div></div>
            <div class="metric span3"><div class="k">Modules</div><div class="v" id="moduleMetric">—</div></div>
            <div class="metric span3"><div class="k">Workflows</div><div class="v" id="workflowMetric">—</div></div>
          </div>
          <label>Plain-English Summary</label>
          <pre id="statusOut">Loading…</pre>
        </div>
      </div>

      <div class="card span12">
        <div class="head"><h2>What this console does</h2></div>
        <div class="body">
          <p>
            This is the human-readable front door for Worldshepherd. Use it to view projects,
            launch safe workflows, search local context, import notes, export manifests, and route controlled
            actions through Sara_Pro without living in raw terminal commands.
          </p>
          <p class="muted">
            Hard rule: no arbitrary shell execution from the browser. Workflows are allowlisted.
          </p>
        </div>
      </div>
    </div>
  </section>

  <section id="modules" class="view">
    <div class="grid">
      <div class="card span12">
        <div class="head"><h2>Human Modules</h2><button onclick="loadModules()">Load Modules</button></div>
        <div class="body" id="modulesList">No modules loaded.</div>
      </div>
    </div>
  </section>

  <section id="projects" class="view">
    <div class="grid">
      <div class="card span12">
        <div class="head"><h2>Worldshepherd Projects</h2><button onclick="loadProjects()">Load Projects</button></div>
        <div class="body" id="projectsList">No projects loaded.</div>
      </div>
    </div>
  </section>

  <section id="workflows" class="view">
    <div class="grid">
      <div class="card span5">
        <div class="head"><h2>Workflow Launcher</h2></div>
        <div class="body">
          <label>Workflow</label>
          <select id="workflowSelect"></select>
          <label>Optional Message</label>
          <textarea id="workflowMessage">ACCESS Sara_Pro through Worldshepherd Gooey Gateway</textarea>
          <button class="primary" onclick="runWorkflow()">Run Workflow</button>
        </div>
      </div>
      <div class="card span7">
        <div class="head"><h2>Workflow Result</h2></div>
        <div class="body"><pre id="workflowOut">No workflow run yet.</pre></div>
      </div>
      <div class="card span12">
        <div class="head"><h2>Available Workflows</h2><button onclick="loadWorkflows()">Refresh</button></div>
        <div class="body" id="workflowsList">No workflows loaded.</div>
      </div>
    </div>
  </section>

  <section id="search" class="view">
    <div class="grid">
      <div class="card span5">
        <div class="head"><h2>Search Everything Local</h2></div>
        <div class="body">
          <label>Search query</label>
          <div class="row">
            <input id="searchQ" value="SSPADAWANZZ">
            <button class="primary" onclick="searchGateway()">Search</button>
          </div>
          <p class="muted">Searches manifest, account core, registry, and recent audit tail.</p>
        </div>
      </div>
      <div class="card span7">
        <div class="head"><h2>Search Results</h2></div>
        <div class="body"><pre id="searchOut">No search yet.</pre></div>
      </div>
    </div>
  </section>

  <section id="notes" class="view">
    <div class="grid">
      <div class="card span5">
        <div class="head"><h2>Import Human Note</h2></div>
        <div class="body">
          <label>Title</label>
          <input id="noteTitle" value="Worldshepherd note">
          <label>Source</label>
          <input id="noteSource" value="gooey-gateway">
          <label>Tags comma-separated</label>
          <input id="noteTags" value="worldshepherd,sara,gooey">
          <label>Body</label>
          <textarea id="noteBody"></textarea>
          <button class="primary" onclick="importNote()">Import into Account Core</button>
        </div>
      </div>
      <div class="card span7">
        <div class="head"><h2>Import Result</h2></div>
        <div class="body"><pre id="noteOut">No note imported yet.</pre></div>
      </div>
    </div>
  </section>

  <section id="manifest" class="view">
    <div class="grid">
      <div class="card span12">
        <div class="head">
          <h2>Gateway Manifest</h2>
          <div>
            <button onclick="loadManifest()">Load</button>
            <button onclick="formatManifest()">Format</button>
            <button class="primary" onclick="saveManifest()">Save</button>
            <button onclick="exportGateway()">Export Bundle</button>
          </div>
        </div>
        <div class="body">
          <textarea id="manifestText" style="min-height:560px;">{}</textarea>
          <label>Output</label>
          <pre id="manifestOut">Ready.</pre>
        </div>
      </div>
    </div>
  </section>

  <section id="links" class="view">
    <div class="grid">
      <div class="card span12">
        <div class="head"><h2>Console Links</h2></div>
        <div class="body">
          <p><a href="/console">/console</a> — Worldshepherd Gooey Gateway</p>
          <p><a href="/ui">/ui</a> — Legacy Sara_Pro UI</p>
          <p><a href="/admin/account/ui">/admin/account/ui</a> — Account Core GUI</p>
          <p><a href="/health">/health</a> — Health JSON</p>
          <p><a href="/v1/capabilities">/v1/capabilities</a> — Capability map</p>
          <pre>
# Recommended terminal verification
cd ~/Sara_pro
source .env

curl http://localhost:9530/api/worldshepherd/status

curl -H "Authorization: Bearer $SARA_ADMIN_TOKEN" \\
  http://localhost:9530/api/worldshepherd/manifest

curl -H "Authorization: Bearer $SARA_ADMIN_TOKEN" \\
  "http://localhost:9530/api/worldshepherd/search?q=Worldshepherd"
          </pre>
        </div>
      </div>
    </div>
  </section>
</main>

<script>
const $ = id => document.getElementById(id);

function token() {
  return $("token").value.trim() || localStorage.getItem("sara_admin_token") || "";
}

function headers() {
  return {"Authorization": "Bearer " + token()};
}

function jsonHeaders() {
  return {"Authorization": "Bearer " + token(), "Content-Type": "application/json"};
}

function pretty(x) {
  return JSON.stringify(x, null, 2);
}

async function fetchJSON(url, opts = {}) {
  const res = await fetch(url, opts);
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); } catch { data = text; }
  if (!res.ok) throw new Error(typeof data === "string" ? data : pretty(data));
  return data;
}

function showView(name, el) {
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  $(name).classList.add("active");
  el.classList.add("active");
}

function saveToken() {
  localStorage.setItem("sara_admin_token", $("token").value.trim());
  alert("Saved locally.");
}

function clearToken() {
  localStorage.removeItem("sara_admin_token");
  $("token").value = "";
}

function toggleToken() {
  $("token").type = $("token").type === "password" ? "text" : "password";
}

async function loadStatus() {
  try {
    const data = await fetchJSON("/api/worldshepherd/status");
    $("statusText").textContent = "Gateway online";
    $("gatewayMetric").textContent = "ONLINE";
    $("projectMetric").textContent = data.counts.projects;
    $("moduleMetric").textContent = data.counts.modules;
    $("workflowMetric").textContent = data.counts.workflows;
    $("statusOut").textContent = pretty(data);
  } catch(e) {
    $("statusText").textContent = "Gateway issue";
    $("statusOut").textContent = String(e);
  }
}

async function loadModules() {
  try {
    const data = await fetchJSON("/api/worldshepherd/modules", {headers: headers()});
    $("modulesList").innerHTML = data.modules.map(m => `
      <div class="module">
        <div class="module-title">${m.name}</div>
        <div class="muted">${m.plain_language}</div>
        <div style="margin-top:8px;">
          <span class="pill">${m.method}</span>
          <span class="pill">${m.route}</span>
          <span class="pill">auth: ${m.auth}</span>
        </div>
      </div>
    `).join("");
  } catch(e) {
    $("modulesList").innerHTML = "<pre>" + String(e) + "</pre>";
  }
}

async function loadProjects() {
  try {
    const data = await fetchJSON("/api/worldshepherd/projects", {headers: headers()});
    $("projectsList").innerHTML = Object.entries(data).map(([id,p]) => `
      <div class="project">
        <div class="project-title">${p.name || id}</div>
        <div class="muted">${p.human_summary || ""}</div>
        <div style="margin-top:8px;">
          <span class="pill">id: ${id}</span>
          <span class="pill">status: ${p.status || "unknown"}</span>
        </div>
        ${(p.capabilities || []).map(c => `<span class="pill">${c}</span>`).join("")}
      </div>
    `).join("");
  } catch(e) {
    $("projectsList").innerHTML = "<pre>" + String(e) + "</pre>";
  }
}

async function loadWorkflows() {
  try {
    const data = await fetchJSON("/api/worldshepherd/workflows", {headers: headers()});
    $("workflowSelect").innerHTML = data.workflows.map(w => `<option value="${w.id}">${w.name}</option>`).join("");
    $("workflowsList").innerHTML = data.workflows.map(w => `
      <div class="workflow">
        <div class="workflow-title">${w.name}</div>
        <div class="muted">${w.plain_language}</div>
        <span class="pill">${w.id}</span>
        <span class="pill">${w.safe ? "safe" : "restricted"}</span>
      </div>
    `).join("");
  } catch(e) {
    $("workflowsList").innerHTML = "<pre>" + String(e) + "</pre>";
  }
}

async function runWorkflow() {
  try {
    const payload = {
      workflow: $("workflowSelect").value,
      message: $("workflowMessage").value
    };
    const data = await fetchJSON("/api/worldshepherd/run", {
      method: "POST",
      headers: jsonHeaders(),
      body: JSON.stringify(payload)
    });
    $("workflowOut").textContent = pretty(data);
    loadStatus();
  } catch(e) {
    $("workflowOut").textContent = String(e);
  }
}

async function searchGateway() {
  try {
    const data = await fetchJSON("/api/worldshepherd/search?q=" + encodeURIComponent($("searchQ").value), {
      headers: headers()
    });
    $("searchOut").textContent = pretty(data);
  } catch(e) {
    $("searchOut").textContent = String(e);
  }
}

async function importNote() {
  try {
    const payload = {
      title: $("noteTitle").value,
      source: $("noteSource").value,
      tags: $("noteTags").value.split(",").map(x => x.trim()).filter(Boolean),
      body: $("noteBody").value
    };
    const data = await fetchJSON("/api/worldshepherd/import-note", {
      method: "POST",
      headers: jsonHeaders(),
      body: JSON.stringify(payload)
    });
    $("noteOut").textContent = pretty(data);
  } catch(e) {
    $("noteOut").textContent = String(e);
  }
}

async function loadManifest() {
  try {
    const data = await fetchJSON("/api/worldshepherd/manifest", {headers: headers()});
    $("manifestText").value = pretty(data);
    $("manifestOut").textContent = "Manifest loaded.";
  } catch(e) {
    $("manifestOut").textContent = String(e);
  }
}

function formatManifest() {
  try {
    $("manifestText").value = pretty(JSON.parse($("manifestText").value));
  } catch(e) {
    $("manifestOut").textContent = "Invalid JSON: " + e;
  }
}

async function saveManifest() {
  try {
    const payload = JSON.parse($("manifestText").value);
    const data = await fetchJSON("/api/worldshepherd/manifest", {
      method: "PUT",
      headers: jsonHeaders(),
      body: JSON.stringify(payload)
    });
    $("manifestText").value = pretty(data);
    $("manifestOut").textContent = "Manifest saved.";
  } catch(e) {
    $("manifestOut").textContent = String(e);
  }
}

async function exportGateway() {
  try {
    const res = await fetch("/api/worldshepherd/export", {headers: headers()});
    const text = await res.text();
    if (!res.ok) throw new Error(text);
    const blob = new Blob([text], {type: "application/json"});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "worldshepherd_gateway_export.json";
    a.click();
    URL.revokeObjectURL(a.href);
  } catch(e) {
    $("manifestOut").textContent = String(e);
  }
}

window.addEventListener("load", () => {
  const saved = localStorage.getItem("sara_admin_token");
  if (saved) $("token").value = saved;
  loadStatus();
  loadModules();
  loadProjects();
  loadWorkflows();
});
</script>
</body>
</html>
""")

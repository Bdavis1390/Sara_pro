import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Header, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

router = APIRouter()

DATA_DIR = Path(os.getenv("SARA_DATA_DIR", "data"))
ACCOUNT_FILE = DATA_DIR / "worldshepherd_account_core.json"
AUDIT_FILE = DATA_DIR / "audit.jsonl"

ADMIN_TOKEN = os.getenv("SARA_ADMIN_TOKEN", "change-me-admin")

DATA_DIR.mkdir(parents=True, exist_ok=True)


def now() -> float:
    return time.time()


def audit(event: str, actor: str, payload: Dict[str, Any] | None = None) -> None:
    record = {
        "ts": now(),
        "event": event,
        "actor": actor,
        "payload": payload or {}
    }
    with AUDIT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def require_admin(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        audit("account_admin_denied", "anonymous")
        raise HTTPException(status_code=403, detail="admin token required")

    token = authorization.replace("Bearer ", "", 1).strip()
    if token != ADMIN_TOKEN:
        audit("account_admin_denied", "bad_token")
        raise HTTPException(status_code=403, detail="admin token required")

    return "admin"


def default_account_core() -> Dict[str, Any]:
    return {
        "schema": "worldshepherd.account_core.v1",
        "root_context": {},
        "identity_and_roles": {},
        "canonical_projects": {},
        "protocols": {},
        "agents_and_modules": {},
        "local_gui_capabilities": {},
        "known_endpoints": {},
        "operational_notes": [],
        "import_slots": {
            "chat_exports": [],
            "uploaded_files": [],
            "gmail_project_notes": [],
            "repo_notes": [],
            "manual_notes": []
        }
    }


def load_core() -> Dict[str, Any]:
    if not ACCOUNT_FILE.exists():
        core = default_account_core()
        save_core(core)
        return core

    try:
        return json.loads(ACCOUNT_FILE.read_text(encoding="utf-8"))
    except Exception:
        return default_account_core()


def save_core(core: Dict[str, Any]) -> None:
    ACCOUNT_FILE.write_text(json.dumps(core, indent=2, ensure_ascii=False), encoding="utf-8")


def walk(obj: Any, path: str = "") -> List[Dict[str, Any]]:
    results = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            current = f"{path}.{key}" if path else str(key)
            results.append({"path": current, "value": key})
            results.extend(walk(value, current))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            current = f"{path}[{idx}]"
            results.extend(walk(value, current))
    else:
        results.append({"path": path, "value": str(obj)})

    return results


@router.get("/admin/account")
def get_account_core(authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    audit("account_core_read", actor)
    return JSONResponse(load_core())


@router.patch("/admin/account")
async def patch_account_core(request: Request, authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    patch = await request.json()

    if not isinstance(patch, dict):
        raise HTTPException(status_code=400, detail="patch must be a JSON object")

    core = load_core()
    core.update(patch)
    save_core(core)

    audit("account_core_patch", actor, {"keys": list(patch.keys())})
    return JSONResponse(core)


@router.put("/admin/account")
async def replace_account_core(request: Request, authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    payload = await request.json()

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="account core must be a JSON object")

    save_core(payload)
    audit("account_core_replace", actor, {"keys": list(payload.keys())})
    return JSONResponse(payload)


@router.post("/admin/account/import-note")
async def import_note(request: Request, authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    payload = await request.json()

    title = str(payload.get("title", "Untitled note"))
    body = str(payload.get("body", ""))
    source = str(payload.get("source", "manual"))
    tags = payload.get("tags", [])

    if not isinstance(tags, list):
        tags = [str(tags)]

    core = load_core()
    slots = core.setdefault("import_slots", {})
    manual_notes = slots.setdefault("manual_notes", [])

    note = {
        "ts": now(),
        "title": title,
        "source": source,
        "tags": tags,
        "body": body
    }

    manual_notes.append(note)
    save_core(core)

    audit("account_note_imported", actor, {"title": title, "source": source, "tags": tags})
    return {"ok": True, "note": note}


@router.get("/admin/account/search")
def search_account_core(
    q: str = Query(default=""),
    authorization: str | None = Header(default=None)
):
    actor = require_admin(authorization)
    core = load_core()
    q_norm = q.lower().strip()

    hits = []
    if q_norm:
        for item in walk(core):
            value = str(item["value"])
            if q_norm in value.lower() or q_norm in item["path"].lower():
                hits.append(item)

    audit("account_core_search", actor, {"q": q, "hits": len(hits)})
    return {"query": q, "hits": hits[:500], "count": len(hits)}


@router.get("/admin/account/export", response_class=PlainTextResponse)
def export_account_core(authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    audit("account_core_export", actor)
    return PlainTextResponse(
        json.dumps(load_core(), indent=2, ensure_ascii=False),
        media_type="application/json"
    )


@router.post("/admin/account/reindex")
def reindex_account_core(authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    core = load_core()
    index = walk(core)
    audit("account_core_reindex", actor, {"items": len(index)})
    return {
        "ok": True,
        "indexed_items": len(index),
        "file": str(ACCOUNT_FILE)
    }


@router.get("/admin/account/ui", response_class=HTMLResponse)
def account_ui():
    return HTMLResponse("""
<!doctype html>
<html>
<head>
  <title>Worldshepherd Account Core</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {
      --bg: #050816;
      --panel: rgba(255,255,255,0.08);
      --panel2: rgba(255,255,255,0.13);
      --line: rgba(255,255,255,0.17);
      --text: #eef3ff;
      --muted: #aeb8d4;
      --good: #6fffc2;
      --warn: #ffd36f;
      --bad: #ff7b8a;
      --accent: #87a7ff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 26px;
      background:
        radial-gradient(circle at 10% 0%, rgba(135,167,255,0.18), transparent 35%),
        linear-gradient(135deg, #050816, #111a33);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    h1 { margin: 0 0 6px; letter-spacing: -0.04em; }
    .sub { color: var(--muted); margin-bottom: 18px; }
    .grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 16px; }
    .card {
      grid-column: span 12;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      overflow: hidden;
      box-shadow: 0 20px 80px rgba(0,0,0,0.35);
    }
    @media (min-width: 900px) {
      .span4 { grid-column: span 4; }
      .span5 { grid-column: span 5; }
      .span6 { grid-column: span 6; }
      .span7 { grid-column: span 7; }
      .span8 { grid-column: span 8; }
    }
    .head {
      padding: 15px 17px;
      border-bottom: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }
    .body { padding: 17px; }
    button {
      color: var(--text);
      background: var(--panel2);
      border: 1px solid var(--line);
      padding: 10px 13px;
      border-radius: 13px;
      cursor: pointer;
    }
    button:hover { border-color: rgba(255,255,255,0.38); }
    .primary { background: linear-gradient(135deg, rgba(135,167,255,0.55), rgba(179,135,255,0.42)); }
    .danger { background: rgba(255,123,138,0.18); border-color: rgba(255,123,138,0.42); }
    input, textarea {
      width: 100%;
      background: rgba(0,0,0,0.25);
      color: var(--text);
      border: 1px solid var(--line);
      border-radius: 13px;
      padding: 11px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
    textarea { min-height: 180px; resize: vertical; }
    label { display: block; margin: 10px 0 6px; color: var(--muted); font-size: 13px; }
    pre {
      white-space: pre-wrap;
      word-break: break-word;
      margin: 0;
      max-height: 560px;
      overflow: auto;
      background: rgba(0,0,0,0.28);
      border: 1px solid var(--line);
      border-radius: 15px;
      padding: 13px;
      color: #e8edff;
      font-size: 12px;
    }
    .row { display: flex; gap: 10px; flex-wrap: wrap; }
    .row > * { flex: 1; }
    .row > button { flex: 0 0 auto; }
    .pill {
      display: inline-block;
      padding: 6px 9px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--muted);
      margin: 3px;
      font-size: 12px;
    }
    .metric {
      background: rgba(255,255,255,0.06);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 13px;
    }
    .k { color: var(--muted); font-size: 12px; }
    .v { font-size: 22px; font-weight: 750; }
  </style>
</head>
<body>
  <h1>Worldshepherd Account Core</h1>
  <div class="sub">Local manifest for Sara_Pro, CRE1AWS, SSPADAWANZZ, SARA, protocols, agents, notes, imports, and exports.</div>

  <div class="grid">
    <div class="card span4">
      <div class="head"><strong>Admin Token</strong></div>
      <div class="body">
        <label>SARA_ADMIN_TOKEN</label>
        <input id="token" type="password" placeholder="Paste admin token">
        <div class="row" style="margin-top:10px;">
          <button class="primary" onclick="saveToken()">Save</button>
          <button onclick="toggleToken()">Show</button>
          <button class="danger" onclick="clearToken()">Clear</button>
        </div>
      </div>
    </div>

    <div class="card span8">
      <div class="head">
        <strong>Account Core Status</strong>
        <div>
          <button onclick="loadCore()">Load</button>
          <button onclick="reindex()">Reindex</button>
          <button onclick="exportCore()">Export</button>
        </div>
      </div>
      <div class="body">
        <div class="grid">
          <div class="metric span4"><div class="k">Schema</div><div class="v" id="schemaMetric">—</div></div>
          <div class="metric span4"><div class="k">Projects</div><div class="v" id="projectMetric">—</div></div>
          <div class="metric span4"><div class="k">Agents</div><div class="v" id="agentMetric">—</div></div>
        </div>
      </div>
    </div>

    <div class="card span6">
      <div class="head"><strong>Search Account Core</strong></div>
      <div class="body">
        <label>Query</label>
        <div class="row">
          <input id="q" value="Sara">
          <button class="primary" onclick="searchCore()">Search</button>
        </div>
        <label>Results</label>
        <pre id="searchOut">No search yet.</pre>
      </div>
    </div>

    <div class="card span6">
      <div class="head"><strong>Import Manual Note</strong></div>
      <div class="body">
        <label>Title</label>
        <input id="noteTitle" value="Worldshepherd account note">
        <label>Source</label>
        <input id="noteSource" value="manual">
        <label>Tags comma-separated</label>
        <input id="noteTags" value="worldshepherd,sara,account">
        <label>Body</label>
        <textarea id="noteBody"></textarea>
        <button class="primary" onclick="importNote()">Import Note</button>
      </div>
    </div>

    <div class="card span12">
      <div class="head">
        <strong>Manifest Editor</strong>
        <div>
          <button onclick="formatCore()">Format</button>
          <button class="primary" onclick="replaceCore()">Save Full Manifest</button>
        </div>
      </div>
      <div class="body">
        <textarea id="coreText" style="min-height:520px;">{}</textarea>
      </div>
    </div>

    <div class="card span12">
      <div class="head"><strong>Output</strong></div>
      <div class="body"><pre id="out">Ready.</pre></div>
    </div>
  </div>

<script>
const $ = (id) => document.getElementById(id);

function token() {
  return $("token").value.trim() || localStorage.getItem("sara_admin_token") || "";
}

function headers() {
  return { "Authorization": "Bearer " + token() };
}

function jsonHeaders() {
  return { "Authorization": "Bearer " + token(), "Content-Type": "application/json" };
}

function pretty(x) { return JSON.stringify(x, null, 2); }

async function fetchJSON(url, opts = {}) {
  const res = await fetch(url, opts);
  const txt = await res.text();
  let data;
  try { data = JSON.parse(txt); } catch { data = txt; }
  if (!res.ok) throw new Error(typeof data === "string" ? data : pretty(data));
  return data;
}

function saveToken() {
  localStorage.setItem("sara_admin_token", $("token").value.trim());
  $("out").textContent = "Token saved locally.";
}

function clearToken() {
  localStorage.removeItem("sara_admin_token");
  $("token").value = "";
}

function toggleToken() {
  $("token").type = $("token").type === "password" ? "text" : "password";
}

async function loadCore() {
  try {
    const data = await fetchJSON("/admin/account", { headers: headers() });
    $("coreText").value = pretty(data);
    $("schemaMetric").textContent = data.schema || "—";
    $("projectMetric").textContent = Object.keys(data.canonical_projects || {}).length;
    $("agentMetric").textContent = Object.keys(data.agents_and_modules || {}).length;
    $("out").textContent = "Account core loaded.";
  } catch (e) {
    $("out").textContent = String(e);
  }
}

async function searchCore() {
  try {
    const data = await fetchJSON("/admin/account/search?q=" + encodeURIComponent($("q").value), {
      headers: headers()
    });
    $("searchOut").textContent = pretty(data);
  } catch (e) {
    $("searchOut").textContent = String(e);
  }
}

function formatCore() {
  try {
    $("coreText").value = pretty(JSON.parse($("coreText").value));
  } catch(e) {
    $("out").textContent = "Invalid JSON: " + e;
  }
}

async function replaceCore() {
  try {
    const payload = JSON.parse($("coreText").value);
    const data = await fetchJSON("/admin/account", {
      method: "PUT",
      headers: jsonHeaders(),
      body: JSON.stringify(payload)
    });
    $("coreText").value = pretty(data);
    $("out").textContent = "Account core saved.";
  } catch(e) {
    $("out").textContent = String(e);
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
    const data = await fetchJSON("/admin/account/import-note", {
      method: "POST",
      headers: jsonHeaders(),
      body: JSON.stringify(payload)
    });
    $("out").textContent = pretty(data);
    await loadCore();
  } catch(e) {
    $("out").textContent = String(e);
  }
}

async function reindex() {
  try {
    const data = await fetchJSON("/admin/account/reindex", {
      method: "POST",
      headers: headers()
    });
    $("out").textContent = pretty(data);
  } catch(e) {
    $("out").textContent = String(e);
  }
}

async function exportCore() {
  try {
    const res = await fetch("/admin/account/export", { headers: headers() });
    const text = await res.text();
    if (!res.ok) throw new Error(text);
    const blob = new Blob([text], {type: "application/json"});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "worldshepherd_account_core.json";
    a.click();
    URL.revokeObjectURL(a.href);
  } catch(e) {
    $("out").textContent = String(e);
  }
}

window.addEventListener("load", () => {
  const saved = localStorage.getItem("sara_admin_token");
  if (saved) $("token").value = saved;
  loadCore();
});
</script>
</body>
</html>
""")

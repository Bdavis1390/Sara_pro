import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from worldshepherd_sara.worldshepherd_gateway import router as worldshepherd_gateway_router
from worldshepherd_sara.account_core import router as account_core_router

APP_NAME = "Worldshepherd SARA / SSPADAWANZZ Admin Interface"
DATA_DIR = Path(os.getenv("SARA_DATA_DIR", "data"))
AUDIT_FILE = DATA_DIR / "audit.jsonl"
REGISTRY_FILE = DATA_DIR / "registry.json"
LOG_FILE = Path("sara_interface.log")

ADMIN_TOKEN = os.getenv("SARA_ADMIN_TOKEN", "change-me-admin")
RELAY_TOKEN = os.getenv("SARA_RELAY_TOKEN", "change-me-relay")

DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_REGISTRY = {
    "services": {
        "SARA_CORE": {
            "role": "core",
            "status": "online",
            "description": "Primary local relay/control core"
        },
        "SSPADAWANZZ": {
            "role": "admin_operator",
            "status": "online",
            "description": "Admin-capable local operator interface"
        }
    },
    "protocol": "Worldshepherd-SARA-local",
    "port": 9530,
    "capabilities": [
        "health",
        "ui",
        "audit",
        "registry",
        "relay",
        "selftest",
        "logs"
    ]
}

if not REGISTRY_FILE.exists():
    REGISTRY_FILE.write_text(json.dumps(DEFAULT_REGISTRY, indent=2), encoding="utf-8")

app = FastAPI(title=APP_NAME)
app.include_router(worldshepherd_gateway_router)
app.include_router(account_core_router)


def now() -> float:
    return time.time()


def read_json(path: Path, fallback: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def audit(event: str, actor: str, payload: Dict[str, Any] | None = None) -> None:
    record = {
        "ts": now(),
        "event": event,
        "actor": actor,
        "payload": payload or {}
    }
    with AUDIT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def resolve_actor(authorization: str | None) -> str:
    if not authorization:
        return "anonymous"

    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return "anonymous"

    token = authorization[len(prefix):].strip()

    if token == ADMIN_TOKEN:
        return "admin"
    if token == RELAY_TOKEN:
        return "operator"

    return "anonymous"


def require_admin(authorization: str | None) -> str:
    actor = resolve_actor(authorization)
    if actor != "admin":
        audit("admin_denied", actor)
        raise HTTPException(status_code=403, detail="admin token required")
    return actor


def require_operator_or_admin(authorization: str | None) -> str:
    actor = resolve_actor(authorization)
    if actor not in {"admin", "operator"}:
        audit("relay_denied", actor)
        raise HTTPException(status_code=403, detail="operator or admin token required")
    return actor


def read_audit_records(limit: int = 100) -> List[Dict[str, Any]]:
    if not AUDIT_FILE.exists():
        return []

    lines = AUDIT_FILE.read_text(encoding="utf-8").splitlines()
    records = []
    for line in lines[-limit:]:
        if line.strip():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                records.append({"raw": line})
    return records


@app.get("/", response_class=HTMLResponse)
def root():
    return HTMLResponse('<meta http-equiv="refresh" content="0; url=/console">')


@app.get("/health")
def health():
    registry = read_json(REGISTRY_FILE, DEFAULT_REGISTRY)
    return {
        "ok": True,
        "service": APP_NAME,
        "ui": "/ui",
        "audit": "/v1/audit?limit=50",
        "registry": "/admin/registry",
        "relay": "/v1/relay",
        "selftest": "/admin/selftest",
        "services": registry.get("services", {}),
        "time": now()
    }


@app.get("/v1/capabilities")
def capabilities():
    return {
        "service": APP_NAME,
        "capabilities": {
            "ui": {
                "path": "/ui",
                "method": "GET",
                "auth": "none"
            },
            "health": {
                "path": "/health",
                "method": "GET",
                "auth": "none"
            },
            "audit_read": {
                "path": "/v1/audit?limit=50",
                "method": "GET",
                "auth": "admin"
            },
            "audit_clear": {
                "path": "/v1/audit",
                "method": "DELETE",
                "auth": "admin"
            },
            "audit_export": {
                "path": "/v1/audit/export",
                "method": "GET",
                "auth": "admin"
            },
            "registry_read": {
                "path": "/admin/registry",
                "method": "GET",
                "auth": "admin"
            },
            "registry_patch": {
                "path": "/admin/registry",
                "method": "PATCH",
                "auth": "admin"
            },
            "relay": {
                "path": "/v1/relay",
                "method": "POST",
                "auth": "operator_or_admin"
            },
            "selftest": {
                "path": "/admin/selftest",
                "method": "POST",
                "auth": "admin"
            },
            "logs": {
                "path": "/admin/logs?lines=120",
                "method": "GET",
                "auth": "admin"
            }
        }
    }


@app.get("/ui", response_class=HTMLResponse)
def ui():
    return HTMLResponse("""
<!doctype html>
<html>
<head>
  <title>Worldshepherd SARA Console</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {
      --bg0: #050816;
      --bg1: #0d1327;
      --panel: rgba(255,255,255,0.075);
      --panel2: rgba(255,255,255,0.115);
      --text: #eef3ff;
      --muted: #aeb8d4;
      --line: rgba(255,255,255,0.16);
      --good: #6fffc2;
      --warn: #ffd36f;
      --bad: #ff7b8a;
      --accent: #87a7ff;
      --accent2: #b387ff;
      --shadow: rgba(0,0,0,0.35);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at 15% 10%, rgba(135,167,255,0.22), transparent 28%),
        radial-gradient(circle at 80% 0%, rgba(179,135,255,0.20), transparent 30%),
        radial-gradient(circle at 50% 90%, rgba(111,255,194,0.08), transparent 35%),
        linear-gradient(135deg, var(--bg0), var(--bg1));
      min-height: 100vh;
    }

    header {
      padding: 28px 30px 18px;
      border-bottom: 1px solid var(--line);
      backdrop-filter: blur(18px);
      position: sticky;
      top: 0;
      z-index: 10;
      background: rgba(5,8,22,0.72);
    }

    .titlebar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }

    h1 {
      margin: 0;
      font-size: clamp(24px, 3vw, 40px);
      letter-spacing: -0.04em;
    }

    .subtitle {
      margin-top: 6px;
      color: var(--muted);
      font-size: 14px;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 9px 12px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--panel);
      box-shadow: 0 8px 30px var(--shadow);
      color: var(--muted);
      font-size: 13px;
    }

    .dot {
      width: 9px;
      height: 9px;
      border-radius: 999px;
      background: var(--good);
      box-shadow: 0 0 20px var(--good);
    }

    main {
      padding: 24px 30px 60px;
      max-width: 1400px;
      margin: 0 auto;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 18px;
    }

    .card {
      grid-column: span 12;
      border: 1px solid var(--line);
      border-radius: 22px;
      background: var(--panel);
      box-shadow: 0 20px 80px var(--shadow);
      backdrop-filter: blur(20px);
      overflow: hidden;
    }

    @media (min-width: 900px) {
      .span4 { grid-column: span 4; }
      .span5 { grid-column: span 5; }
      .span6 { grid-column: span 6; }
      .span7 { grid-column: span 7; }
      .span8 { grid-column: span 8; }
    }

    .card h2 {
      margin: 0;
      font-size: 17px;
      letter-spacing: -0.02em;
    }

    .card-head {
      padding: 18px 20px;
      border-bottom: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }

    .card-body {
      padding: 18px 20px 20px;
    }

    .tabs {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 18px;
    }

    .tab {
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.07);
      color: var(--muted);
      padding: 10px 13px;
      border-radius: 999px;
      cursor: pointer;
      transition: all 140ms ease;
    }

    .tab.active,
    .tab:hover {
      background: linear-gradient(135deg, rgba(135,167,255,0.35), rgba(179,135,255,0.25));
      color: var(--text);
      border-color: rgba(255,255,255,0.30);
    }

    .view { display: none; }
    .view.active { display: block; }

    input, textarea, select {
      width: 100%;
      background: rgba(0,0,0,0.24);
      color: var(--text);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px 13px;
      outline: none;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }

    textarea {
      min-height: 140px;
      resize: vertical;
    }

    label {
      display: block;
      margin: 12px 0 7px;
      color: var(--muted);
      font-size: 13px;
    }

    button {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 11px 14px;
      cursor: pointer;
      color: var(--text);
      background: var(--panel2);
      transition: transform 120ms ease, border-color 120ms ease, background 120ms ease;
    }

    button:hover {
      transform: translateY(-1px);
      border-color: rgba(255,255,255,0.35);
      background: rgba(255,255,255,0.16);
    }

    .primary {
      background: linear-gradient(135deg, rgba(135,167,255,0.55), rgba(179,135,255,0.42));
    }

    .danger {
      background: rgba(255,123,138,0.18);
      border-color: rgba(255,123,138,0.45);
    }

    .row {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
    }

    .row > * { flex: 1; }
    .row > button { flex: 0 0 auto; }

    pre {
      white-space: pre-wrap;
      word-break: break-word;
      margin: 0;
      padding: 14px;
      border-radius: 16px;
      background: rgba(0,0,0,0.28);
      border: 1px solid var(--line);
      color: #dfe7ff;
      max-height: 520px;
      overflow: auto;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
    }

    .metric {
      padding: 15px;
      border-radius: 18px;
      background: rgba(255,255,255,0.06);
      border: 1px solid var(--line);
    }

    .metric .k {
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 6px;
    }

    .metric .v {
      font-size: 22px;
      font-weight: 750;
      letter-spacing: -0.04em;
    }

    .service-list {
      display: grid;
      gap: 10px;
    }

    .service {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 15px;
      background: rgba(255,255,255,0.055);
    }

    .muted { color: var(--muted); }
    .good { color: var(--good); }
    .warn { color: var(--warn); }
    .bad { color: var(--bad); }

    .small {
      font-size: 12px;
      color: var(--muted);
    }

    a { color: var(--accent); }
  </style>
</head>
<body>
<header>
  <div class="titlebar">
    <div>
      <h1>Worldshepherd SARA Console</h1>
      <div class="subtitle">SARA_CORE → SSPADAWANZZ · Local admin control surface · Port 9530</div>
    </div>
    <div class="badge"><span class="dot"></span><span id="topStatus">Checking status…</span></div>
  </div>
</header>

<main>
  <div class="tabs">
    <button class="tab active" onclick="showView('dashboard', this)">Dashboard</button>
    <button class="tab" onclick="showView('relay', this)">Relay</button>
    <button class="tab" onclick="showView('audit', this)">Audit</button>
    <button class="tab" onclick="showView('registry', this)">Registry</button>
    <button class="tab" onclick="showView('selftest', this)">Self-Test</button>
    <button class="tab" onclick="showView('logs', this)">Logs</button>
    <button class="tab" onclick="showView('endpoints', this)">Endpoints</button>
    <button class="tab" onclick="showView('accountcore', this)">Account Core</button>
  </div>

  <section id="dashboard" class="view active">
    <div class="grid">
      <div class="card span4">
        <div class="card-head"><h2>Admin Token</h2></div>
        <div class="card-body">
          <label>SARA_ADMIN_TOKEN</label>
          <input id="adminToken" type="password" placeholder="Paste admin token from .env">
          <div class="row" style="margin-top:12px;">
            <button class="primary" onclick="saveToken()">Save locally</button>
            <button onclick="toggleToken()">Show/Hide</button>
            <button class="danger" onclick="clearToken()">Clear</button>
          </div>
          <p class="small">Stored only in this browser via localStorage. Do not paste this token into screenshots or PDFs.</p>
        </div>
      </div>

      <div class="card span8">
        <div class="card-head">
          <h2>System Status</h2>
          <button onclick="loadHealth()">Refresh</button>
        </div>
        <div class="card-body">
          <div class="grid">
            <div class="metric span4">
              <div class="k">Health</div>
              <div class="v" id="healthMetric">—</div>
            </div>
            <div class="metric span4">
              <div class="k">UI</div>
              <div class="v">/ui</div>
            </div>
            <div class="metric span4">
              <div class="k">Port</div>
              <div class="v">9530</div>
            </div>
          </div>
          <label>Health Payload</label>
          <pre id="healthOut">No data loaded.</pre>
        </div>
      </div>

      <div class="card span6">
        <div class="card-head"><h2>Registered Services</h2></div>
        <div class="card-body">
          <div id="services" class="service-list">No services loaded.</div>
        </div>
      </div>

      <div class="card span6">
        <div class="card-head"><h2>Capabilities</h2><button onclick="loadCapabilities()">Load</button></div>
        <div class="card-body">
          <pre id="capOut">Click Load.</pre>
        </div>
      </div>
    </div>
  </section>

  <section id="relay" class="view">
    <div class="grid">
      <div class="card span5">
        <div class="card-head"><h2>Relay Command</h2></div>
        <div class="card-body">
          <label>Token Type</label>
          <select id="relayTokenType">
            <option value="admin">Use admin token</option>
            <option value="manual">Manual bearer token</option>
          </select>
          <label>Manual Token</label>
          <input id="manualRelayToken" type="password" placeholder="Optional SARA_RELAY_TOKEN">
          <label>Target</label>
          <input id="relayTarget" value="SSPADAWANZZ">
          <label>Message</label>
          <textarea id="relayMessage">ACCESS Sara_Pro</textarea>
          <button class="primary" onclick="sendRelay()">Send Relay</button>
        </div>
      </div>
      <div class="card span7">
        <div class="card-head"><h2>Relay Response</h2></div>
        <div class="card-body">
          <pre id="relayOut">No relay sent.</pre>
        </div>
      </div>
    </div>
  </section>

  <section id="audit" class="view">
    <div class="grid">
      <div class="card span12">
        <div class="card-head">
          <h2>Audit Viewer</h2>
          <div class="row" style="flex:0 0 auto;">
            <button onclick="loadAudit()">Load</button>
            <button onclick="exportAudit()">Export</button>
            <button class="danger" onclick="clearAudit()">Clear</button>
          </div>
        </div>
        <div class="card-body">
          <label>Limit</label>
          <input id="auditLimit" type="number" value="100" min="1" max="10000">
          <label>Audit Records</label>
          <pre id="auditOut">No audit loaded.</pre>
        </div>
      </div>
    </div>
  </section>

  <section id="registry" class="view">
    <div class="grid">
      <div class="card span6">
        <div class="card-head"><h2>Registry Editor</h2><button onclick="loadRegistry()">Load Registry</button></div>
        <div class="card-body">
          <label>Registry JSON</label>
          <textarea id="registryText" style="min-height:460px;">{}</textarea>
          <div class="row" style="margin-top:12px;">
            <button class="primary" onclick="patchRegistry()">Patch Registry</button>
            <button onclick="formatRegistry()">Format JSON</button>
          </div>
        </div>
      </div>
      <div class="card span6">
        <div class="card-head"><h2>Registry Response</h2></div>
        <div class="card-body">
          <pre id="registryOut">No registry action yet.</pre>
        </div>
      </div>
    </div>
  </section>

  <section id="selftest" class="view">
    <div class="grid">
      <div class="card span12">
        <div class="card-head">
          <h2>Admin Self-Test</h2>
          <button class="primary" onclick="runSelftest()">Run Self-Test</button>
        </div>
        <div class="card-body">
          <pre id="selftestOut">Ready.</pre>
        </div>
      </div>
    </div>
  </section>

  <section id="logs" class="view">
    <div class="grid">
      <div class="card span12">
        <div class="card-head">
          <h2>Server Logs</h2>
          <button onclick="loadLogs()">Refresh Logs</button>
        </div>
        <div class="card-body">
          <label>Lines</label>
          <input id="logLines" type="number" value="120" min="10" max="5000">
          <label>Log Tail</label>
          <pre id="logsOut">No logs loaded.</pre>
        </div>
      </div>
    </div>
  </section>

  
  <section id="accountcore" class="view">
    <div class="grid">
      <div class="card span12">
        <div class="card-head">
          <h2>Worldshepherd Account Core</h2>
          <button onclick="window.open('/admin/account/ui','_blank')">Open Full Account Core</button>
        </div>
        <div class="card-body">
          <p class="muted">
            Integrated local manifest for Worldshepherd, Sara_Pro, CRE1AWS, SSPADAWANZZ, SARA, protocols, agents, project notes, imports, search, and export.
          </p>
          <iframe
            src="/admin/account/ui"
            style="width:100%; height:820px; border:1px solid rgba(255,255,255,0.16); border-radius:18px; background:#050816;">
          </iframe>
        </div>
      </div>
    </div>
  </section>

<section id="endpoints" class="view">
    <div class="grid">
      <div class="card span12">
        <div class="card-head"><h2>Endpoint Reference</h2></div>
        <div class="card-body">
<pre>
# Health
curl http://localhost:9530/health

# Capabilities
curl http://localhost:9530/v1/capabilities

# Admin audit
curl -H "Authorization: Bearer $SARA_ADMIN_TOKEN" \
  http://localhost:9530/v1/audit?limit=50

# Export audit
curl -H "Authorization: Bearer $SARA_ADMIN_TOKEN" \
  http://localhost:9530/v1/audit/export

# Clear audit
curl -X DELETE -H "Authorization: Bearer $SARA_ADMIN_TOKEN" \
  http://localhost:9530/v1/audit

# Registry
curl -H "Authorization: Bearer $SARA_ADMIN_TOKEN" \
  http://localhost:9530/admin/registry

# Relay
curl -X POST http://localhost:9530/v1/relay \
  -H "Authorization: Bearer $SARA_RELAY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"target":"SSPADAWANZZ","message":"ACCESS Sara_Pro"}'

# Logs
curl -H "Authorization: Bearer $SARA_ADMIN_TOKEN" \
  http://localhost:9530/admin/logs?lines=120
</pre>
        </div>
      </div>
    </div>
  </section>
</main>

<script>
const $ = (id) => document.getElementById(id);

function token() {
  return $("adminToken").value.trim() || localStorage.getItem("sara_admin_token") || "";
}

function authHeaders() {
  return { "Authorization": "Bearer " + token() };
}

function jsonHeaders() {
  return {
    "Authorization": "Bearer " + token(),
    "Content-Type": "application/json"
  };
}

function pretty(obj) {
  return JSON.stringify(obj, null, 2);
}

async function fetchJSON(url, options = {}) {
  const res = await fetch(url, options);
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); }
  catch { data = text; }

  if (!res.ok) {
    throw new Error(typeof data === "string" ? data : pretty(data));
  }
  return data;
}

function showView(name, el) {
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  $(name).classList.add("active");
  el.classList.add("active");
}

function saveToken() {
  localStorage.setItem("sara_admin_token", $("adminToken").value.trim());
  alert("Admin token saved locally in this browser.");
}

function clearToken() {
  localStorage.removeItem("sara_admin_token");
  $("adminToken").value = "";
}

function toggleToken() {
  $("adminToken").type = $("adminToken").type === "password" ? "text" : "password";
  $("manualRelayToken").type = $("manualRelayToken").type === "password" ? "text" : "password";
}

async function loadHealth() {
  try {
    const data = await fetchJSON("/health");
    $("healthOut").textContent = pretty(data);
    $("healthMetric").textContent = data.ok ? "OK" : "FAIL";
    $("healthMetric").className = data.ok ? "v good" : "v bad";
    $("topStatus").textContent = data.ok ? "Online" : "Degraded";

    const services = data.services || {};
    const html = Object.entries(services).map(([name, svc]) => `
      <div class="service">
        <div>
          <strong>${name}</strong>
          <div class="small">${svc.description || svc.role || ""}</div>
        </div>
        <div class="${svc.status === "online" ? "good" : "warn"}">${svc.status || "unknown"}</div>
      </div>
    `).join("");
    $("services").innerHTML = html || "No services found.";
  } catch (err) {
    $("healthOut").textContent = String(err);
    $("healthMetric").textContent = "FAIL";
    $("healthMetric").className = "v bad";
    $("topStatus").textContent = "Offline";
  }
}

async function loadCapabilities() {
  try {
    const data = await fetchJSON("/v1/capabilities");
    $("capOut").textContent = pretty(data);
  } catch (err) {
    $("capOut").textContent = String(err);
  }
}

async function sendRelay() {
  try {
    let bearer = token();
    if ($("relayTokenType").value === "manual") {
      bearer = $("manualRelayToken").value.trim();
    }

    const payload = {
      target: $("relayTarget").value.trim(),
      message: $("relayMessage").value
    };

    const data = await fetchJSON("/v1/relay", {
      method: "POST",
      headers: {
        "Authorization": "Bearer " + bearer,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });
    $("relayOut").textContent = pretty(data);
  } catch (err) {
    $("relayOut").textContent = String(err);
  }
}

async function loadAudit() {
  try {
    const limit = $("auditLimit").value || 100;
    const data = await fetchJSON("/v1/audit?limit=" + encodeURIComponent(limit), {
      headers: authHeaders()
    });
    $("auditOut").textContent = pretty(data);
  } catch (err) {
    $("auditOut").textContent = String(err);
  }
}

async function exportAudit() {
  try {
    const res = await fetch("/v1/audit/export", { headers: authHeaders() });
    const text = await res.text();
    if (!res.ok) throw new Error(text);

    const blob = new Blob([text], {type: "application/jsonl"});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "sara_audit_export.jsonl";
    a.click();
    URL.revokeObjectURL(a.href);
  } catch (err) {
    $("auditOut").textContent = String(err);
  }
}

async function clearAudit() {
  if (!confirm("Clear local audit log? This cannot be undone.")) return;
  try {
    const data = await fetchJSON("/v1/audit", {
      method: "DELETE",
      headers: authHeaders()
    });
    $("auditOut").textContent = pretty(data);
  } catch (err) {
    $("auditOut").textContent = String(err);
  }
}

async function loadRegistry() {
  try {
    const data = await fetchJSON("/admin/registry", { headers: authHeaders() });
    $("registryText").value = pretty(data);
    $("registryOut").textContent = pretty(data);
  } catch (err) {
    $("registryOut").textContent = String(err);
  }
}

function formatRegistry() {
  try {
    $("registryText").value = pretty(JSON.parse($("registryText").value));
  } catch (err) {
    alert("Invalid JSON: " + err);
  }
}

async function patchRegistry() {
  try {
    const payload = JSON.parse($("registryText").value);
    const data = await fetchJSON("/admin/registry", {
      method: "PATCH",
      headers: jsonHeaders(),
      body: JSON.stringify(payload)
    });
    $("registryOut").textContent = pretty(data);
  } catch (err) {
    $("registryOut").textContent = String(err);
  }
}

async function runSelftest() {
  try {
    const data = await fetchJSON("/admin/selftest", {
      method: "POST",
      headers: authHeaders()
    });
    $("selftestOut").textContent = pretty(data);
  } catch (err) {
    $("selftestOut").textContent = String(err);
  }
}

async function loadLogs() {
  try {
    const lines = $("logLines").value || 120;
    const res = await fetch("/admin/logs?lines=" + encodeURIComponent(lines), {
      headers: authHeaders()
    });
    const text = await res.text();
    if (!res.ok) throw new Error(text);
    $("logsOut").textContent = text;
  } catch (err) {
    $("logsOut").textContent = String(err);
  }
}

window.addEventListener("load", () => {
  const saved = localStorage.getItem("sara_admin_token");
  if (saved) $("adminToken").value = saved;
  loadHealth();
  loadCapabilities();
});
</script>
</body>
</html>
""")


@app.get("/v1/audit")
def read_audit(limit: int = 50, authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    audit("audit_read", actor, {"limit": limit})
    return {"records": read_audit_records(limit)}


@app.get("/v1/audit/export", response_class=PlainTextResponse)
def export_audit(authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    audit("audit_export", actor)

    if not AUDIT_FILE.exists():
        return ""

    return PlainTextResponse(
        AUDIT_FILE.read_text(encoding="utf-8"),
        media_type="application/jsonl"
    )


@app.delete("/v1/audit")
def clear_audit(authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    if AUDIT_FILE.exists():
        AUDIT_FILE.unlink()
    audit("audit_cleared", actor)
    return {"ok": True, "cleared": True}


@app.get("/admin/registry")
def get_registry(authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    audit("registry_read", actor)
    return JSONResponse(read_json(REGISTRY_FILE, DEFAULT_REGISTRY))


@app.patch("/admin/registry")
async def patch_registry(request: Request, authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    patch = await request.json()

    if not isinstance(patch, dict):
        raise HTTPException(status_code=400, detail="registry patch must be a JSON object")

    current = read_json(REGISTRY_FILE, DEFAULT_REGISTRY)
    current.update(patch)

    write_json(REGISTRY_FILE, current)
    audit("registry_patch", actor, patch)
    return current


@app.post("/v1/relay")
async def relay(request: Request, authorization: str | None = Header(default=None)):
    actor = require_operator_or_admin(authorization)
    payload = await request.json()

    target = payload.get("target", "SSPADAWANZZ")
    message = payload.get("message", "ping")

    result = {
        "ok": True,
        "from": "SARA_CORE",
        "to": target,
        "message": message,
        "result": "integration_ok",
        "actor": actor,
        "time": now()
    }

    audit("relay", actor, result)
    return result


@app.post("/admin/selftest")
def selftest(authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)

    registry = read_json(REGISTRY_FILE, DEFAULT_REGISTRY)
    checks = [
        {
            "name": "health",
            "ok": True,
            "detail": "FastAPI process is responding"
        },
        {
            "name": "registry_file",
            "ok": REGISTRY_FILE.exists(),
            "detail": str(REGISTRY_FILE)
        },
        {
            "name": "audit_file_or_directory",
            "ok": DATA_DIR.exists(),
            "detail": str(DATA_DIR)
        },
        {
            "name": "admin_token_loaded",
            "ok": ADMIN_TOKEN != "change-me-admin",
            "detail": "admin token present"
        },
        {
            "name": "relay_token_loaded",
            "ok": RELAY_TOKEN != "change-me-relay",
            "detail": "relay token present"
        },
        {
            "name": "sara_core_registered",
            "ok": "SARA_CORE" in registry.get("services", {}),
            "detail": "SARA_CORE registry check"
        },
        {
            "name": "sspadawanzz_registered",
            "ok": "SSPADAWANZZ" in registry.get("services", {}),
            "detail": "SSPADAWANZZ registry check"
        }
    ]

    ok = all(c["ok"] for c in checks)

    result = {
        "ok": ok,
        "checks": checks,
        "platform": {
            "python": sys.version,
            "system": platform.platform(),
            "cwd": str(Path.cwd())
        }
    }

    audit("selftest", actor, {"ok": ok})
    return result


@app.get("/admin/logs", response_class=PlainTextResponse)
def logs(lines: int = 120, authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    audit("logs_read", actor, {"lines": lines})

    if not LOG_FILE.exists():
        return PlainTextResponse("No sara_interface.log file found.", media_type="text/plain")

    raw = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    return PlainTextResponse("\n".join(raw[-lines:]), media_type="text/plain")


@app.get("/{full_path:path}", response_class=HTMLResponse)
def catch_all(full_path: str):
    return HTMLResponse(f"""
<!doctype html>
<html>
<head>
  <meta http-equiv="refresh" content="2; url=/ui">
  <title>SARA Route Redirect</title>
</head>
<body style="font-family: system-ui; padding: 40px;">
  <h1>Route not found</h1>
  <p>The requested path <code>/{full_path}</code> is not a registered SARA endpoint.</p>
  <p>Redirecting to <a href="/ui">/ui</a>.</p>
</body>
</html>
""", status_code=404)

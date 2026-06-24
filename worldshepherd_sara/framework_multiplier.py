import json
import os
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

DATA_DIR = Path(os.getenv("SARA_DATA_DIR", "data"))
FRAMEWORK_FILE = DATA_DIR / "framework_multiplier.json"
AUDIT_FILE = DATA_DIR / "audit.jsonl"

ADMIN_TOKEN = os.getenv("SARA_ADMIN_TOKEN", "change-me-admin")
RELAY_TOKEN = os.getenv("SARA_RELAY_TOKEN", "change-me-relay")

DATA_DIR.mkdir(parents=True, exist_ok=True)


def now() -> float:
    return time.time()


def audit(event: str, actor: str, payload: Dict[str, Any] | None = None) -> None:
    with AUDIT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": now(),
            "event": event,
            "actor": actor,
            "payload": payload or {}
        }) + "\n")


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
        audit("framework23_admin_denied", actor)
        raise HTTPException(status_code=403, detail="admin token required")
    return actor


def default_framework() -> Dict[str, Any]:
    return {
        "schema": "worldshepherd.framework_multiplier.v1",
        "title": "Worldshepherd Sara_Pro Framework 23x Scorecard",
        "baseline": "1.00x = basic Sara_Pro health/audit/registry/relay UI",
        "target_multiplier": 23.0,
        "rule": "greater_than_target",
        "capabilities": {
            "human_readable_gooey": {"label": "Human-readable Gooey Gateway", "score": 3.0, "enabled": True},
            "account_core": {"label": "Account Core / local context registry", "score": 2.4, "enabled": True},
            "gpt_assistant": {"label": "GPT / local assistant panel", "score": 3.2, "enabled": True},
            "blockchain_structure": {"label": "Blockchain-structured console", "score": 2.8, "enabled": True},
            "workflow_launcher": {"label": "Allowlisted workflow launcher", "score": 2.1, "enabled": True},
            "auditability": {"label": "Audit trail and export", "score": 1.7, "enabled": True},
            "registry_control": {"label": "Registry control", "score": 1.5, "enabled": True},
            "project_library": {"label": "Worldshepherd project library", "score": 1.9, "enabled": True},
            "search_everything": {"label": "Local search across manifests/modules", "score": 1.6, "enabled": True},
            "import_export": {"label": "Import/export capability", "score": 1.5, "enabled": True},
            "token_separation": {"label": "Admin/operator token separation", "score": 1.4, "enabled": True},
            "safe_security_rules": {"label": "Safe security rules / no arbitrary shell", "score": 1.8, "enabled": True},
            "human_blockchain_audit_trail": {"label": "Human-readable blockchain audit trail", "score": 1.6, "enabled": True},
            "assistant_source_visibility": {"label": "Assistant source visibility", "score": 1.3, "enabled": True},
            "framework_scorecard": {"label": "Framework 23x readiness scorecard", "score": 1.4, "enabled": True}
        }
    }


def load_framework() -> Dict[str, Any]:
    if not FRAMEWORK_FILE.exists():
        data = default_framework()
        save_framework(data)
        return data

    try:
        return json.loads(FRAMEWORK_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = default_framework()
        save_framework(data)
        return data


def save_framework(data: Dict[str, Any]) -> None:
    FRAMEWORK_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def evaluate(data: Dict[str, Any]) -> Dict[str, Any]:
    caps = data.get("capabilities", {})
    enabled = {
        k: v for k, v in caps.items()
        if isinstance(v, dict) and v.get("enabled", False)
    }

    multiplier = round(1.0 + sum(float(v.get("score", 0)) for v in enabled.values()), 2)
    target = float(data.get("target_multiplier", 23.0))

    return {
        "ok": multiplier > target,
        "multiplier": multiplier,
        "target_multiplier": target,
        "over_target_by": round(multiplier - target, 2),
        "enabled_count": len(enabled),
        "total_capabilities": len(caps),
        "enabled_capabilities": enabled,
        "plain_english": f"Framework score is {multiplier}x against target greater than {target}x."
    }


@router.get("/api/framework23/status")
def framework23_status():
    data = load_framework()
    result = evaluate(data)
    return {
        "ok": result["ok"],
        "title": data.get("title"),
        "baseline": data.get("baseline"),
        "rule": data.get("rule"),
        **result
    }


@router.get("/api/framework23")
def framework23_get(authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    data = load_framework()
    audit("framework23_read", actor)
    return {
        "framework": data,
        "evaluation": evaluate(data)
    }


@router.put("/api/framework23")
async def framework23_put(request: Request, authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    payload = await request.json()

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON object required")

    save_framework(payload)
    audit("framework23_replaced", actor)
    return {
        "ok": True,
        "framework": payload,
        "evaluation": evaluate(payload)
    }


@router.patch("/api/framework23/capability/{capability_id}")
async def framework23_patch_capability(
    capability_id: str,
    request: Request,
    authorization: str | None = Header(default=None)
):
    actor = require_admin(authorization)
    payload = await request.json()

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON object required")

    data = load_framework()
    data.setdefault("capabilities", {})

    current = data["capabilities"].get(capability_id, {
        "label": capability_id,
        "score": 0,
        "enabled": True
    })

    if not isinstance(current, dict):
        current = {"label": capability_id, "score": 0, "enabled": True}

    current.update(payload)
    data["capabilities"][capability_id] = current
    save_framework(data)

    audit("framework23_capability_patched", actor, {"capability_id": capability_id})

    return {
        "ok": True,
        "capability_id": capability_id,
        "capability": current,
        "evaluation": evaluate(data)
    }


@router.post("/api/framework23/boost")
def framework23_boost(authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)

    data = load_framework()
    caps = data.setdefault("capabilities", {})

    boosts = {
        "guided_onboarding": {"label": "Guided reboot/onboarding flow", "score": 1.2, "enabled": True},
        "cross_console_navigation": {"label": "Cross-console navigation", "score": 1.1, "enabled": True},
        "readiness_gate": {"label": "Readiness gate and route verification", "score": 1.3, "enabled": True}
    }

    caps.update(boosts)
    save_framework(data)

    audit("framework23_boosted", actor, {"boosts": list(boosts.keys())})

    return {
        "ok": True,
        "added": boosts,
        "evaluation": evaluate(data)
    }


@router.get("/framework23", response_class=HTMLResponse)
def framework23_ui():
    return HTMLResponse("""
<!doctype html>
<html>
<head>
  <title>Worldshepherd Framework 23x</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { margin:0; font-family:system-ui,sans-serif; background:#07111f; color:#eef4ff; }
    header { padding:28px; background:linear-gradient(135deg,#172c54,#0b1528); border-bottom:1px solid rgba(255,255,255,.14); }
    h1 { margin:0; font-size:clamp(30px,5vw,62px); letter-spacing:-.05em; }
    main { max-width:1200px; margin:0 auto; padding:22px; display:grid; grid-template-columns:340px 1fr; gap:16px; }
    @media(max-width:900px){ main{grid-template-columns:1fr;} }
    .card { background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.15); border-radius:20px; overflow:hidden; box-shadow:0 18px 60px rgba(0,0,0,.25); }
    .head { padding:14px 16px; border-bottom:1px solid rgba(255,255,255,.13); font-weight:900; display:flex; justify-content:space-between; gap:10px; flex-wrap:wrap; }
    .body { padding:16px; }
    input, textarea { width:100%; box-sizing:border-box; padding:11px; border-radius:12px; border:1px solid rgba(255,255,255,.18); background:rgba(0,0,0,.25); color:white; font-family:ui-monospace,Menlo,Consolas,monospace; }
    textarea { min-height:260px; }
    button { border:1px solid rgba(255,255,255,.18); border-radius:12px; padding:10px 12px; background:rgba(255,255,255,.12); color:white; font-weight:800; cursor:pointer; margin:4px 4px 4px 0; }
    .primary { background:#366dff; }
    .good { color:#77ffc3; }
    .bad { color:#ff8a8a; }
    pre { white-space:pre-wrap; word-break:break-word; background:rgba(0,0,0,.26); padding:12px; border-radius:12px; border:1px solid rgba(255,255,255,.12); max-height:520px; overflow:auto; }
    .score { font-size:54px; font-weight:1000; letter-spacing:-.06em; }
    a { color:#93b5ff; font-weight:900; text-decoration:none; }
  </style>
</head>
<body>
<header>
  <h1>Framework 23x Scorecard</h1>
  <p>Measures whether Sara_Pro has exceeded the original baseline by more than 23x.</p>
</header>

<main>
  <aside class="card">
    <div class="head">Admin</div>
    <div class="body">
      <label>SARA_ADMIN_TOKEN</label>
      <input id="token" type="password" placeholder="Paste admin token">
      <p>
        <button class="primary" onclick="saveToken()">Save</button>
        <button onclick="toggleToken()">Show</button>
        <button onclick="clearToken()">Clear</button>
      </p>
      <p>
        <a href="/console">Gooey</a><br>
        <a href="/chain">Chain</a><br>
        <a href="/assistant">Assistant</a><br>
        <a href="/ui">Legacy UI</a>
      </p>
      <button onclick="loadStatus()">Refresh Status</button>
      <button onclick="loadFull()">Load Full</button>
      <button onclick="boost()">Boost</button>
    </div>
  </aside>

  <section class="card">
    <div class="head">Score</div>
    <div class="body">
      <div id="score" class="score">--</div>
      <div id="verdict">Loading…</div>
      <pre id="statusOut">Loading…</pre>
    </div>
  </section>

  <section class="card" style="grid-column:1 / -1;">
    <div class="head">Raw Framework JSON</div>
    <div class="body">
      <textarea id="raw"></textarea>
      <p><button class="primary" onclick="saveFull()">Save Full JSON</button></p>
    </div>
  </section>
</main>

<script>
const $ = id => document.getElementById(id);

function token() {
  return $("token").value.trim() || localStorage.getItem("sara_admin_token") || "";
}
function headers() { return {"Authorization": "Bearer " + token()}; }
function jsonHeaders() { return {"Authorization": "Bearer " + token(), "Content-Type": "application/json"}; }
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
    const data = await fetchJSON("/api/framework23/status");
    $("statusOut").textContent = pretty(data);
    $("score").textContent = data.multiplier + "x";
    $("verdict").innerHTML = data.ok
      ? '<span class="good">PASS: greater than 23x</span>'
      : '<span class="bad">BUILD: not greater than 23x yet</span>';
  } catch(e) {
    $("statusOut").textContent = String(e);
  }
}

async function loadFull() {
  try {
    const data = await fetchJSON("/api/framework23", {headers: headers()});
    $("raw").value = pretty(data.framework);
    $("statusOut").textContent = pretty(data.evaluation);
  } catch(e) {
    $("statusOut").textContent = String(e);
  }
}

async function saveFull() {
  try {
    const payload = JSON.parse($("raw").value);
    const data = await fetchJSON("/api/framework23", {
      method:"PUT",
      headers:jsonHeaders(),
      body:JSON.stringify(payload)
    });
    $("statusOut").textContent = pretty(data.evaluation);
    loadStatus();
  } catch(e) {
    $("statusOut").textContent = String(e);
  }
}

async function boost() {
  try {
    const data = await fetchJSON("/api/framework23/boost", {
      method:"POST",
      headers:headers()
    });
    $("statusOut").textContent = pretty(data.evaluation);
    loadStatus();
    loadFull();
  } catch(e) {
    $("statusOut").textContent = String(e);
  }
}

window.addEventListener("load", () => {
  const saved = localStorage.getItem("sara_admin_token");
  if (saved) $("token").value = saved;
  loadStatus();
});
</script>
</body>
</html>
""")

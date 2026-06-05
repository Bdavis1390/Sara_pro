import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter()

DATA_DIR = Path(os.getenv("SARA_DATA_DIR", "data"))
CHAIN_FILE = DATA_DIR / "worldshepherd_chain.json"
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
        audit("chain_admin_denied", actor)
        raise HTTPException(status_code=403, detail="admin token required")
    return actor


def canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def block_hash(block: Dict[str, Any]) -> str:
    clean = dict(block)
    clean.pop("hash", None)
    return hashlib.sha256(canonical(clean).encode("utf-8")).hexdigest()


def default_chain() -> Dict[str, Any]:
    genesis = {
        "index": 0,
        "timestamp": now(),
        "type": "GENESIS",
        "actor": "SARA_CORE",
        "summary": "Worldshepherd Sara_Pro genesis block",
        "payload": {
            "network": "Worldshepherd",
            "core": "SARA_CORE",
            "operator": "SSPADAWANZZ",
            "console": "/chain"
        },
        "previous_hash": "0" * 64,
        "nonce": 0
    }
    genesis["hash"] = block_hash(genesis)

    return {
        "schema": "worldshepherd.local_chain.v1",
        "network": "Worldshepherd Sara_Pro Local Chain",
        "consensus": "local-admin-append-only",
        "validators": [
            {"id": "SARA_CORE", "role": "genesis/core relay", "status": "online"},
            {"id": "SSPADAWANZZ", "role": "local operator validator", "status": "online"},
            {"id": "ACCOUNT_CORE", "role": "context validator", "status": "online"},
            {"id": "GOOEY_GATEWAY", "role": "human interface validator", "status": "online"}
        ],
        "mempool": [],
        "blocks": [genesis]
    }


def load_chain() -> Dict[str, Any]:
    if not CHAIN_FILE.exists():
        chain = default_chain()
        save_chain(chain)
        return chain

    try:
        return json.loads(CHAIN_FILE.read_text(encoding="utf-8"))
    except Exception:
        chain = default_chain()
        save_chain(chain)
        return chain


def save_chain(chain: Dict[str, Any]) -> None:
    CHAIN_FILE.write_text(json.dumps(chain, indent=2, ensure_ascii=False), encoding="utf-8")


def validate_chain(chain: Dict[str, Any]) -> Dict[str, Any]:
    blocks = chain.get("blocks", [])
    issues = []

    if not blocks:
        return {"ok": False, "issues": ["chain has no blocks"], "height": -1}

    for i, block in enumerate(blocks):
        if block.get("hash") != block_hash(block):
            issues.append(f"block {i} hash mismatch")

        if i == 0:
            if block.get("previous_hash") != "0" * 64:
                issues.append("genesis previous_hash invalid")
        else:
            if block.get("previous_hash") != blocks[i - 1].get("hash"):
                issues.append(f"block {i} previous_hash mismatch")

    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "height": len(blocks) - 1,
        "blocks": len(blocks)
    }


@router.get("/api/chain/status")
def chain_status():
    chain = load_chain()
    validation = validate_chain(chain)
    latest = chain.get("blocks", [{}])[-1]

    return {
        "ok": validation["ok"],
        "network": chain.get("network"),
        "consensus": chain.get("consensus"),
        "height": validation["height"],
        "blocks": len(chain.get("blocks", [])),
        "mempool": len(chain.get("mempool", [])),
        "validators": chain.get("validators", []),
        "latest_hash": latest.get("hash"),
        "validation": validation
    }


@router.get("/api/chain")
def get_chain(authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    chain = load_chain()
    audit("chain_read", actor, {"blocks": len(chain.get("blocks", []))})
    return JSONResponse(chain)


@router.post("/api/chain/tx")
async def add_tx(request: Request, authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    payload = await request.json()

    tx = {
        "id": hashlib.sha256(f"{now()}:{canonical(payload)}".encode("utf-8")).hexdigest()[:16],
        "timestamp": now(),
        "actor": actor,
        "type": payload.get("type", "WORLD_SHEPHERD_EVENT"),
        "summary": payload.get("summary", "Worldshepherd event"),
        "payload": payload.get("payload", {})
    }

    chain = load_chain()
    chain.setdefault("mempool", []).append(tx)
    save_chain(chain)

    audit("chain_tx_added", actor, {"tx": tx["id"]})
    return {"ok": True, "tx": tx, "mempool": len(chain["mempool"])}


@router.post("/api/chain/seed-demo")
def seed_demo(authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    chain = load_chain()

    demos = [
        {
            "id": hashlib.sha256(f"{now()}:route".encode()).hexdigest()[:16],
            "timestamp": now(),
            "actor": actor,
            "type": "ROUTE",
            "summary": "Route Worldshepherd through Sara_Pro",
            "payload": {"from": "Worldshepherd", "to": "Sara_Pro", "route": "/console"}
        },
        {
            "id": hashlib.sha256(f"{now()}:assistant".encode()).hexdigest()[:16],
            "timestamp": now(),
            "actor": actor,
            "type": "ASSISTANT",
            "summary": "Attach GPT assistant to Gooey",
            "payload": {"route": "/assistant"}
        },
        {
            "id": hashlib.sha256(f"{now()}:chain".encode()).hexdigest()[:16],
            "timestamp": now(),
            "actor": actor,
            "type": "CHAIN",
            "summary": "Activate blockchain-structured console",
            "payload": {"route": "/chain"}
        }
    ]

    chain.setdefault("mempool", []).extend(demos)
    save_chain(chain)

    audit("chain_demo_seeded", actor, {"count": len(demos)})
    return {"ok": True, "added": len(demos), "mempool": len(chain["mempool"])}


@router.post("/api/chain/mine")
async def mine(request: Request, authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    payload = await request.json()

    chain = load_chain()
    mempool = chain.setdefault("mempool", [])
    blocks = chain.setdefault("blocks", [])

    if not mempool:
        raise HTTPException(status_code=400, detail="mempool is empty")

    previous = blocks[-1]

    block = {
        "index": len(blocks),
        "timestamp": now(),
        "type": payload.get("type", "WORLD_SHEPHERD_BLOCK"),
        "actor": actor,
        "summary": payload.get("summary", "Mined Worldshepherd block"),
        "payload": {
            "transactions": mempool,
            "transaction_count": len(mempool)
        },
        "previous_hash": previous.get("hash"),
        "nonce": 0
    }

    block["hash"] = block_hash(block)

    blocks.append(block)
    chain["mempool"] = []
    save_chain(chain)

    audit("chain_block_mined", actor, {"index": block["index"], "hash": block["hash"]})
    return {"ok": True, "block": block, "validation": validate_chain(chain)}


@router.delete("/api/chain/reset")
def reset_chain(authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    chain = default_chain()
    save_chain(chain)
    audit("chain_reset", actor)
    return {"ok": True, "validation": validate_chain(chain)}


@router.get("/chain", response_class=HTMLResponse)
def chain_ui():
    return HTMLResponse("""
<!doctype html>
<html>
<head>
  <title>Worldshepherd Chain Console</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {
      margin: 0;
      font-family: system-ui, sans-serif;
      background: linear-gradient(180deg, #d9ebe8 0%, #d9ebe8 55%, #7daf58 55%, #6fa34a 100%);
      color: #152036;
    }
    header {
      text-align: center;
      padding: 30px 20px 10px;
    }
    h1 {
      margin: 0;
      font-size: clamp(34px, 6vw, 72px);
      letter-spacing: -0.06em;
      font-weight: 1000;
      color: #4cc9e8;
      text-shadow: 3px 3px 0 white, -3px 3px 0 white, 3px -3px 0 white, -3px -3px 0 white;
    }
    h2 {
      margin: 0;
      font-size: clamp(30px, 5vw, 58px);
      letter-spacing: -0.05em;
      font-weight: 1000;
      color: #f14d3b;
      text-shadow: 3px 3px 0 white, -3px 3px 0 white, 3px -3px 0 white, -3px -3px 0 white;
    }
    main {
      max-width: 1280px;
      margin: 0 auto;
      padding: 20px;
    }
    .grid {
      display: grid;
      grid-template-columns: 340px 1fr;
      gap: 16px;
    }
    @media (max-width: 900px) {
      .grid { grid-template-columns: 1fr; }
    }
    .card {
      background: rgba(255,255,255,0.82);
      border: 1px solid rgba(0,0,0,0.15);
      border-radius: 22px;
      box-shadow: 0 14px 40px rgba(0,0,0,0.18);
      overflow: hidden;
    }
    .head {
      padding: 14px 16px;
      border-bottom: 1px solid rgba(0,0,0,0.13);
      font-weight: 900;
      display: flex;
      justify-content: space-between;
      gap: 10px;
      flex-wrap: wrap;
    }
    .body { padding: 16px; }
    label {
      display: block;
      margin: 10px 0 6px;
      color: #607086;
      font-weight: 700;
      font-size: 13px;
    }
    input, textarea {
      width: 100%;
      box-sizing: border-box;
      border: 1px solid rgba(0,0,0,0.18);
      border-radius: 13px;
      padding: 11px;
      font-family: ui-monospace, Menlo, Consolas, monospace;
    }
    textarea { min-height: 90px; }
    button {
      border: 1px solid rgba(0,0,0,0.14);
      border-radius: 13px;
      padding: 10px 13px;
      font-weight: 900;
      cursor: pointer;
      background: white;
    }
    .primary { background: #4cc9e8; color: white; }
    .gold { background: #f4c64e; }
    .danger { background: #f14d3b; color: white; }
    .row {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 10px;
    }
    .nodes {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
      margin: 18px 0;
    }
    @media (max-width: 900px) {
      .nodes { grid-template-columns: 1fr 1fr; }
    }
    .node {
      text-align: center;
      background: rgba(255,255,255,0.78);
      border: 1px solid rgba(0,0,0,0.13);
      border-radius: 22px;
      padding: 16px;
      box-shadow: 0 12px 28px rgba(0,0,0,0.14);
    }
    .face {
      width: 100px;
      height: 100px;
      border-radius: 38%;
      background: white;
      margin: 0 auto 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 32px;
      box-shadow: 0 10px 22px rgba(0,0,0,0.16);
    }
    .rail {
      background: #f4c64e;
      border-radius: 22px;
      padding: 16px;
      margin: 16px 0;
      display: flex;
      gap: 10px;
      overflow-x: auto;
      box-shadow: 0 12px 32px rgba(0,0,0,0.18);
    }
    .block {
      min-width: 150px;
      background: white;
      border-radius: 16px;
      padding: 12px;
      border-top: 7px solid #4cc9e8;
      box-shadow: 0 8px 20px rgba(0,0,0,0.12);
    }
    .block:nth-child(even) { border-top-color: #f14d3b; }
    .small {
      color: #607086;
      font-size: 12px;
      word-break: break-all;
    }
    .mempool {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
    @media (max-width: 900px) {
      .mempool { grid-template-columns: 1fr; }
    }
    .tx {
      background: rgba(76,201,232,0.14);
      border: 1px solid rgba(76,201,232,0.35);
      border-radius: 13px;
      padding: 10px;
      margin: 7px 0;
    }
    pre {
      white-space: pre-wrap;
      word-break: break-word;
      max-height: 380px;
      overflow: auto;
      background: white;
      border-radius: 14px;
      padding: 12px;
      border: 1px solid rgba(0,0,0,0.12);
    }
    a { color: #173557; font-weight: 900; }
  </style>
</head>
<body>
<header>
  <h2>WORLDSHEPHERD</h2>
  <h1>CHAIN CONSOLE</h1>
  <p>SARA_CORE → SSPADAWANZZ · validators · mempool · genesis · linked blocks</p>
</header>

<main>
  <div class="grid">
    <div class="card">
      <div class="head">Admin Token</div>
      <div class="body">
        <label>SARA_ADMIN_TOKEN</label>
        <input id="token" type="password" placeholder="Paste admin token">
        <div class="row">
          <button class="primary" onclick="saveToken()">Save</button>
          <button onclick="toggleToken()">Show</button>
          <button class="danger" onclick="clearToken()">Clear</button>
        </div>
        <p><a href="/console">Gooey</a> · <a href="/assistant">Assistant</a> · <a href="/ui">Legacy UI</a></p>
      </div>
    </div>

    <div class="card">
      <div class="head">
        <span>Network Status</span>
        <span>
          <button onclick="loadChain()">Refresh</button>
          <button class="gold" onclick="seedDemo()">Seed TXs</button>
          <button class="primary" onclick="mineBlock()">Mine</button>
          <button class="danger" onclick="resetChain()">Reset</button>
        </span>
      </div>
      <div class="body">
        <pre id="statusOut">Loading…</pre>
      </div>
    </div>
  </div>

  <div class="nodes" id="nodes"></div>

  <div class="rail" id="blocks"></div>

  <div class="mempool">
    <div class="card">
      <div class="head">Pending Transactions / Mempool</div>
      <div class="body" id="mempool">No pending transactions.</div>
    </div>

    <div class="card">
      <div class="head">Add Transaction</div>
      <div class="body">
        <label>Summary</label>
        <input id="txSummary" value="Route Worldshepherd event through Sara_Pro">
        <label>Type</label>
        <input id="txType" value="WORLD_SHEPHERD_EVENT">
        <label>Payload JSON</label>
        <textarea id="txPayload">{"route":"/chain","operator":"SSPADAWANZZ"}</textarea>
        <button class="primary" onclick="submitTx()">Add Transaction</button>
      </div>
    </div>
  </div>

  <div class="card" style="margin-top:16px;">
    <div class="head">Raw Chain</div>
    <div class="body"><pre id="chainOut">No chain loaded.</pre></div>
  </div>
</main>

<script>
const $ = id => document.getElementById(id);

function token() {
  return $("token").value.trim() || localStorage.getItem("sara_admin_token") || "";
}
function headers() { return {"Authorization": "Bearer " + token()}; }
function jsonHeaders() { return {"Authorization": "Bearer " + token(), "Content-Type": "application/json"}; }
function pretty(x) { return JSON.stringify(x, null, 2); }
function shortHash(h) { return h ? h.slice(0, 10) + "…" + h.slice(-8) : "—"; }

async function fetchJSON(url, opts = {}) {
  const res = await fetch(url, opts);
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); } catch { data = text; }
  if (!res.ok) throw new Error(typeof data === "string" ? data : pretty(data));
  return data;
}

function saveToken() {
  localStorage.setItem("sara_admin_token", $("token").value.trim());
  alert("Token saved locally.");
}
function clearToken() {
  localStorage.removeItem("sara_admin_token");
  $("token").value = "";
}
function toggleToken() {
  $("token").type = $("token").type === "password" ? "text" : "password";
}

async function loadChain() {
  try {
    const status = await fetchJSON("/api/chain/status");
    $("statusOut").textContent = pretty(status);

    const chain = await fetchJSON("/api/chain", {headers: headers()});
    $("chainOut").textContent = pretty(chain);

    $("nodes").innerHTML = (chain.validators || []).map(v => `
      <div class="node">
        <div class="face">• •</div>
        <strong>${v.id}</strong>
        <div class="small">${v.role}</div>
        <div class="small">${v.status}</div>
      </div>
    `).join("");

    $("blocks").innerHTML = (chain.blocks || []).map(b => `
      <div class="block">
        <strong>Block #${b.index}</strong>
        <div>${b.summary}</div>
        <div class="small">${shortHash(b.hash)}</div>
        <div class="small">${b.type}</div>
      </div>
    `).join("");

    const txs = chain.mempool || [];
    $("mempool").innerHTML = txs.length ? txs.map(tx => `
      <div class="tx">
        <strong>${tx.summary}</strong>
        <div class="small">${tx.id} · ${tx.type}</div>
      </div>
    `).join("") : "No pending transactions.";
  } catch(e) {
    $("statusOut").textContent = String(e);
  }
}

async function submitTx() {
  try {
    const payload = JSON.parse($("txPayload").value);
    const data = await fetchJSON("/api/chain/tx", {
      method: "POST",
      headers: jsonHeaders(),
      body: JSON.stringify({
        type: $("txType").value,
        summary: $("txSummary").value,
        payload
      })
    });
    $("chainOut").textContent = pretty(data);
    loadChain();
  } catch(e) {
    $("chainOut").textContent = String(e);
  }
}

async function seedDemo() {
  try {
    const data = await fetchJSON("/api/chain/seed-demo", {
      method: "POST",
      headers: headers()
    });
    $("chainOut").textContent = pretty(data);
    loadChain();
  } catch(e) {
    $("chainOut").textContent = String(e);
  }
}

async function mineBlock() {
  try {
    const data = await fetchJSON("/api/chain/mine", {
      method: "POST",
      headers: jsonHeaders(),
      body: JSON.stringify({summary: "Mined from Chain Console"})
    });
    $("chainOut").textContent = pretty(data);
    loadChain();
  } catch(e) {
    $("chainOut").textContent = String(e);
  }
}

async function resetChain() {
  if (!confirm("Reset chain to genesis?")) return;
  try {
    const data = await fetchJSON("/api/chain/reset", {
      method: "DELETE",
      headers: headers()
    });
    $("chainOut").textContent = pretty(data);
    loadChain();
  } catch(e) {
    $("chainOut").textContent = String(e);
  }
}

window.addEventListener("load", () => {
  const saved = localStorage.getItem("sara_admin_token");
  if (saved) $("token").value = saved;
  loadChain();
});
</script>
</body>
</html>
""")

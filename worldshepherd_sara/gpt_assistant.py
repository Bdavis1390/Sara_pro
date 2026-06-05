import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

router = APIRouter()

DATA_DIR = Path(os.getenv("SARA_DATA_DIR", "data"))
AUDIT_FILE = DATA_DIR / "audit.jsonl"

ADMIN_TOKEN = os.getenv("SARA_ADMIN_TOKEN", "change-me-admin")
RELAY_TOKEN = os.getenv("SARA_RELAY_TOKEN", "change-me-relay")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")
MAX_CONTEXT_CHARS = int(os.getenv("SARA_ASSISTANT_MAX_CONTEXT_CHARS", "60000"))

KNOWLEDGE_PATHS = [
    Path("data"),
    Path("docs"),
    Path("worldshepherd_sara"),
]

SAFE_EXTENSIONS = {
    ".json", ".jsonl", ".txt", ".md", ".py", ".yaml", ".yml", ".toml"
}

EXCLUDED_NAMES = {
    ".env",
    "sara_interface.log",
    "sara_diag.txt",
}

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
        audit("assistant_admin_denied", actor)
        raise HTTPException(status_code=403, detail="admin token required")
    return actor


def safe_read(path: Path, max_chars: int = 12000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except Exception as exc:
        return f"[unreadable: {exc}]"


def iter_knowledge_files() -> List[Path]:
    files: List[Path] = []

    for base in KNOWLEDGE_PATHS:
        if not base.exists():
            continue

        candidates = [base] if base.is_file() else [p for p in base.rglob("*") if p.is_file()]

        for p in candidates:
            if p.name in EXCLUDED_NAMES:
                continue
            if p.suffix.lower() not in SAFE_EXTENSIONS:
                continue
            if ".git" in p.parts or ".venv" in p.parts or "__pycache__" in p.parts:
                continue
            files.append(p)

    return sorted(set(files))


def collect_context(query: str = "") -> Dict[str, Any]:
    q = query.lower().strip()
    scored = []

    for p in iter_knowledge_files():
        name = str(p).lower()
        score = 0

        if q and q in name:
            score += 12

        for key in [
            "worldshepherd",
            "gateway",
            "account",
            "chain",
            "framework",
            "registry",
            "server",
            "assistant",
            "sara",
            "sspadawanzz"
        ]:
            if key in name:
                score += 3

        scored.append((score, p))

    scored.sort(key=lambda x: (-x[0], str(x[1])))

    selected = []
    total = 0

    for score, p in scored:
        if total >= MAX_CONTEXT_CHARS:
            break

        text = safe_read(p)
        block = f"\n\n--- FILE: {p} ---\n{text}\n"

        if total + len(block) > MAX_CONTEXT_CHARS:
            block = block[:MAX_CONTEXT_CHARS - total]

        selected.append({
            "path": str(p),
            "score": score,
            "chars": len(block),
            "content": block
        })

        total += len(block)

    return {
        "chars": total,
        "files": [
            {
                "path": x["path"],
                "score": x["score"],
                "chars": x["chars"]
            }
            for x in selected
        ],
        "context_text": "".join(x["content"] for x in selected)
    }


def local_fallback_answer(message: str, ctx: Dict[str, Any]) -> str:
    q = message.lower()

    lines = [
        "Local Worldshepherd Assistant is active.",
        "",
        "OpenAI API mode is not active yet, so I am answering from local context only.",
        "",
        f"Loaded {ctx['chars']} characters from {len(ctx['files'])} local files.",
        ""
    ]

    if "route" in q or "chain" in q:
        lines += [
            "Blockchain routes currently expected:",
            "- /chain — blockchain-structured console",
            "- /api/chain/status — public chain health/status",
            "- /api/chain — admin chain JSON",
            "- /api/chain/tx — add transaction",
            "- /api/chain/seed-demo — seed demo transactions",
            "- /api/chain/mine — mine pending transactions",
            ""
        ]

    if "assistant" in q or "gpt" in q:
        lines += [
            "Assistant routes now expected:",
            "- /assistant — human chat UI",
            "- /api/assistant/status — assistant status",
            "- /api/assistant/sources — local source list",
            "- /api/assistant/chat — chat endpoint",
            ""
        ]

    if "commit" in q or "git" in q:
        lines += [
            "Safe commit rule:",
            "- commit code and manifests",
            "- never commit .env",
            "- ignore sara_interface.log",
            "- inspect git status before committing",
            ""
        ]

    lines += [
        "Most relevant local source files loaded:",
        *[f"- {f['path']}" for f in ctx["files"][:12]],
        "",
        "To enable full GPT mode, add OPENAI_API_KEY to .env and install the openai package."
    ]

    return "\n".join(lines)


def extract_output_text(response: Any) -> str:
    if hasattr(response, "output_text") and response.output_text:
        return response.output_text

    try:
        chunks = []
        for item in response.output:
            if getattr(item, "type", None) == "message":
                for content in item.content:
                    if hasattr(content, "text"):
                        chunks.append(content.text)
        if chunks:
            return "\n".join(chunks)
    except Exception:
        pass

    return str(response)


SYSTEM_PROMPT = """
You are the embedded Worldshepherd Sara_Pro assistant.

Rules:
- Be clear, direct, and human-readable.
- Use the local Worldshepherd context supplied in the prompt.
- Preserve separation between CRE1AWS and SSPADAWANZZ.
- Treat Sara_Pro as the local GUI/API control surface.
- Do not claim access to hidden ChatGPT memory, private account systems, Gmail, calendar, internet, or tools unless the local app explicitly provides that data.
- Never reveal tokens, .env values, API keys, or bearer secrets.
- Prefer safe GUI workflows over arbitrary shell execution.
"""


@router.get("/api/assistant/status")
def assistant_status(authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    ctx = collect_context("")
    audit("assistant_status", actor, {"files": len(ctx["files"]), "chars": ctx["chars"]})

    return {
        "ok": True,
        "route": "/assistant",
        "model": OPENAI_MODEL,
        "openai_sdk_available": OpenAI is not None,
        "api_key_configured": bool(OPENAI_API_KEY and OPENAI_API_KEY != "PASTE_YOUR_OPENAI_API_KEY_HERE"),
        "context_files": ctx["files"],
        "context_chars": ctx["chars"],
        "plain_english": "Assistant route is mounted. It can use local context now and OpenAI API when configured."
    }


@router.get("/api/assistant/sources")
def assistant_sources(authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    ctx = collect_context("")
    audit("assistant_sources", actor, {"files": len(ctx["files"])})

    return {
        "knowledge_paths": [str(p) for p in KNOWLEDGE_PATHS],
        "safe_extensions": sorted(SAFE_EXTENSIONS),
        "files": ctx["files"]
    }


@router.post("/api/assistant/chat")
async def assistant_chat(request: Request, authorization: str | None = Header(default=None)):
    actor = require_admin(authorization)
    payload = await request.json()

    message = str(payload.get("message", "")).strip()
    history = payload.get("history", [])

    if not message:
        raise HTTPException(status_code=400, detail="message required")

    ctx = collect_context(message)

    audit("assistant_chat", actor, {
        "message_chars": len(message),
        "context_chars": ctx["chars"],
        "files": len(ctx["files"])
    })

    if OpenAI is None or not OPENAI_API_KEY or OPENAI_API_KEY == "PASTE_YOUR_OPENAI_API_KEY_HERE":
        return {
            "ok": True,
            "mode": "local_fallback",
            "model": "local-context",
            "answer": local_fallback_answer(message, ctx),
            "sources": ctx["files"]
        }

    client = OpenAI(api_key=OPENAI_API_KEY)

    compact_history = []
    if isinstance(history, list):
        for item in history[-8:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role", "user")
            content = str(item.get("content", ""))[:4000]
            if role in {"user", "assistant"} and content:
                compact_history.append({"role": role, "content": content})

    user_payload = f"""
LOCAL WORLDSHEPHERD CONTEXT:
{ctx["context_text"]}

USER MESSAGE:
{message}
"""

    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            instructions=SYSTEM_PROMPT,
            input=[
                *compact_history,
                {
                    "role": "user",
                    "content": user_payload
                }
            ]
        )
        answer = extract_output_text(response)
        return {
            "ok": True,
            "mode": "openai",
            "model": OPENAI_MODEL,
            "answer": answer,
            "sources": ctx["files"]
        }
    except Exception as exc:
        return {
            "ok": False,
            "mode": "openai_error",
            "model": OPENAI_MODEL,
            "answer": (
                "OpenAI API call failed, but the local assistant route is working.\n\n"
                f"Error: {exc}\n\n"
                + local_fallback_answer(message, ctx)
            ),
            "sources": ctx["files"]
        }


@router.get("/assistant", response_class=HTMLResponse)
def assistant_ui():
    return HTMLResponse("""
<!doctype html>
<html>
<head>
  <title>Worldshepherd GPT Assistant</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {
      --bg0:#050816;
      --bg1:#0e1730;
      --panel:rgba(255,255,255,0.08);
      --panel2:rgba(255,255,255,0.14);
      --line:rgba(255,255,255,0.16);
      --text:#eef3ff;
      --muted:#aeb8d4;
      --good:#6fffc2;
      --bad:#ff7b8a;
      --accent:#87a7ff;
      --shadow:rgba(0,0,0,0.38);
    }
    * { box-sizing:border-box; }
    body {
      margin:0;
      color:var(--text);
      background:
        radial-gradient(circle at 12% 4%, rgba(135,167,255,0.22), transparent 30%),
        radial-gradient(circle at 84% 0%, rgba(179,135,255,0.18), transparent 28%),
        linear-gradient(135deg, var(--bg0), var(--bg1));
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      min-height:100vh;
    }
    header {
      padding:24px 28px 16px;
      border-bottom:1px solid var(--line);
      background:rgba(5,8,22,0.75);
      backdrop-filter:blur(18px);
    }
    h1 {
      margin:0;
      font-size:clamp(24px,3vw,42px);
      letter-spacing:-0.045em;
    }
    .sub { margin-top:7px; color:var(--muted); font-size:14px; }
    main {
      max-width:1450px;
      margin:0 auto;
      padding:22px 28px 70px;
      display:grid;
      grid-template-columns:360px 1fr;
      gap:18px;
    }
    @media (max-width:950px) { main { grid-template-columns:1fr; } }
    .card {
      border:1px solid var(--line);
      border-radius:22px;
      background:var(--panel);
      box-shadow:0 20px 80px var(--shadow);
      backdrop-filter:blur(18px);
      overflow:hidden;
    }
    .head {
      padding:16px 18px;
      border-bottom:1px solid var(--line);
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap:10px;
      font-weight:900;
    }
    .body { padding:17px 18px 20px; }
    label {
      display:block;
      margin:12px 0 7px;
      color:var(--muted);
      font-size:13px;
    }
    input, textarea {
      width:100%;
      background:rgba(0,0,0,0.28);
      color:var(--text);
      border:1px solid var(--line);
      border-radius:14px;
      padding:12px 13px;
      outline:none;
      font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
    textarea { min-height:115px; resize:vertical; }
    button {
      border:1px solid var(--line);
      border-radius:14px;
      padding:11px 14px;
      cursor:pointer;
      color:var(--text);
      background:var(--panel2);
      font-weight:800;
    }
    .primary { background:linear-gradient(135deg, rgba(135,167,255,0.55), rgba(179,135,255,0.40)); }
    .danger { background:rgba(255,123,138,0.17); border-color:rgba(255,123,138,0.44); }
    .row { display:flex; gap:10px; flex-wrap:wrap; align-items:center; }
    .row > * { flex:1; }
    .row > button { flex:0 0 auto; }
    #chat {
      height:calc(100vh - 260px);
      min-height:560px;
      overflow:auto;
      padding:18px;
      display:flex;
      flex-direction:column;
      gap:14px;
    }
    .msg {
      max-width:86%;
      padding:14px 15px;
      border-radius:18px;
      border:1px solid var(--line);
      white-space:pre-wrap;
      line-height:1.45;
    }
    .user { align-self:flex-end; background:rgba(135,167,255,0.18); }
    .assistant { align-self:flex-start; background:rgba(255,255,255,0.075); }
    .meta { color:var(--muted); font-size:12px; margin-bottom:6px; }
    pre {
      white-space:pre-wrap;
      word-break:break-word;
      margin:0;
      padding:12px;
      border-radius:14px;
      background:rgba(0,0,0,0.30);
      border:1px solid var(--line);
      color:#e7ecff;
      max-height:360px;
      overflow:auto;
      font-size:12px;
    }
    .muted { color:var(--muted); }
    a { color:var(--accent); text-decoration:none; font-weight:900; }
  </style>
</head>
<body>
<header>
  <h1>Worldshepherd GPT Assistant</h1>
  <div class="sub">Local assistant for Sara_Pro, Gooey Gateway, Chain Console, Account Core, registry, docs, and workflows.</div>
</header>

<main>
  <aside class="card">
    <div class="head">Control Panel</div>
    <div class="body">
      <label>SARA_ADMIN_TOKEN</label>
      <input id="token" type="password" placeholder="Paste admin token">
      <div class="row" style="margin-top:10px;">
        <button class="primary" onclick="saveToken()">Save</button>
        <button onclick="toggleToken()">Show</button>
        <button class="danger" onclick="clearToken()">Clear</button>
      </div>

      <label>Status</label>
      <pre id="statusOut">Not loaded.</pre>

      <div class="row" style="margin-top:12px;">
        <button onclick="loadStatus()">Status</button>
        <button onclick="loadSources()">Sources</button>
      </div>

      <label>Sources</label>
      <pre id="sourcesOut">Click Sources.</pre>

      <p>
        <a href="/console">Gooey</a><br>
        <a href="/chain">Chain Console</a><br>
        <a href="/ui">Legacy UI</a>
      </p>
    </div>
  </aside>

  <section class="card">
    <div class="head">
      <span>Assistant Chat</span>
      <button onclick="clearChat()">Clear</button>
    </div>

    <div id="chat"></div>

    <div class="body" style="border-top:1px solid var(--line);">
      <label>Message</label>
      <textarea id="message" placeholder="Ask about Sara_Pro, Worldshepherd, routes, chain, commits, assistant, account core..."></textarea>
      <div class="row" style="margin-top:12px;">
        <button class="primary" onclick="sendMessage()">Send</button>
        <button onclick="quick('Summarize current Sara_Pro architecture.')">Summarize</button>
        <button onclick="quick('What should I test next?')">Next Test</button>
      </div>
    </div>
  </section>
</main>

<script>
const $ = id => document.getElementById(id);
let history = [];

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

function escapeHtml(s) {
  return String(s).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");
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

function addMsg(role, text) {
  const div = document.createElement("div");
  div.className = "msg " + role;
  div.innerHTML = `<div class="meta">${role}</div>${escapeHtml(text)}`;
  $("chat").appendChild(div);
  $("chat").scrollTop = $("chat").scrollHeight;
}

async function loadStatus() {
  try {
    const data = await fetchJSON("/api/assistant/status", {headers: headers()});
    $("statusOut").textContent = pretty(data);
  } catch(e) {
    $("statusOut").textContent = String(e);
  }
}

async function loadSources() {
  try {
    const data = await fetchJSON("/api/assistant/sources", {headers: headers()});
    $("sourcesOut").textContent = pretty(data);
  } catch(e) {
    $("sourcesOut").textContent = String(e);
  }
}

async function sendMessage() {
  const msg = $("message").value.trim();
  if (!msg) return;

  $("message").value = "";
  addMsg("user", msg);
  history.push({role: "user", content: msg});
  addMsg("assistant", "Thinking through local Worldshepherd context…");

  try {
    const data = await fetchJSON("/api/assistant/chat", {
      method: "POST",
      headers: jsonHeaders(),
      body: JSON.stringify({message: msg, history})
    });

    $("chat").lastChild.remove();
    const answer = data.answer || "(no answer)";
    addMsg("assistant", answer);
    history.push({role: "assistant", content: answer});
  } catch(e) {
    $("chat").lastChild.remove();
    addMsg("assistant", "Error: " + String(e));
  }
}

function quick(text) {
  $("message").value = text;
  sendMessage();
}

function clearChat() {
  history = [];
  $("chat").innerHTML = "";
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

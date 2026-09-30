import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const PARENT_V34 = "806db617532dc8840dca3f39504efa4cd78f5b4312005d730e5a73e4b54fffd8";
const CONTROL_CORE = "4b4e1c85b80b8ad5b9326cbacec0a8754dcc80ec98cf2b2e7bc917cd921d8341";
const REGISTRY: Record<string, Set<string>> = {
  SIP: new Set(["sim-sip"]),
  PRIMARY_LISTING_EXCHANGE: new Set(["sim-primary"]),
  LULD_PLAN: new Set(["sim-luld"]),
};
const HEX64 = /^[0-9a-f]{64}$/;

function canon(v: unknown): string {
  if (v === null || typeof v !== "object") return JSON.stringify(v);
  if (Array.isArray(v)) return "[" + v.map(canon).join(",") + "]";
  const o = v as Record<string, unknown>;
  return "{" + Object.keys(o).sort().map(k => JSON.stringify(k) + ":" + canon(o[k])).join(",") + "}";
}
async function sha(text: string): Promise<string> {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(d)).map(x => x.toString(16).padStart(2,"0")).join("");
}
function dt(v: unknown): Date | null {
  if (typeof v !== "string") return null;
  const d = new Date(v);
  return Number.isFinite(d.getTime()) ? d : null;
}
function fail(checks: any[], id: string, detail: string) { checks.push({id,status:"FAIL",detail}); }
function pass(checks: any[], id: string, detail: string) { checks.push({id,status:"PASS",detail}); }

function validateStream(p: any, checks: any[]) {
  const now = dt(p.now);
  const rows = Array.isArray(p.market_messages) ? p.market_messages : [];
  if (!now || rows.length === 0) { fail(checks,"MARKET_STREAM_PRESENT","missing now or market messages"); return; }
  pass(checks,"MARKET_STREAM_PRESENT",`messages=${rows.length}`);
  const cursor = new Map<string,{seq:number,payload:string,effective:number}>();
  const latest = new Map<string,any>();
  let streamOk = true;
  for (let i=0;i<rows.length;i++) {
    const m=rows[i] ?? {};
    const key=`${m.source_kind}|${m.source_id}|${String(m.symbol||"").toUpperCase()}|${m.session_id}`;
    const registered = REGISTRY[m.source_kind]?.has(m.source_id) === true;
    if (!registered) { fail(checks,"MARKET_SOURCE_IDENTITY",`index=${i}`); streamOk=false; }
    if (String(m.symbol||"").toUpperCase() !== "ABC") { fail(checks,"MARKET_SYMBOL_BINDING",`index=${i}`); streamOk=false; }
    if (!Number.isInteger(m.sequence) || m.sequence < 1) { fail(checks,"MARKET_SEQUENCE_VALID",`index=${i}`); streamOk=false; }
    if (!HEX64.test(String(m.payload_sha256||""))) { fail(checks,"MARKET_PAYLOAD_HASH",`index=${i}`); streamOk=false; }
    if (m.verified !== true) { fail(checks,"MARKET_VERIFIED_FLAG",`index=${i}`); streamOk=false; }
    const eff=dt(m.effective_at), obs=dt(m.observed_at);
    if (!eff || !obs) { fail(checks,"MARKET_TIMESTAMP_PARSE",`index=${i}`); streamOk=false; continue; }
    const future=Math.max(eff.getTime()-now.getTime(),obs.getTime()-now.getTime());
    const age=now.getTime()-obs.getTime();
    const delay=obs.getTime()-eff.getTime();
    if (future>2000 || age>30000 || delay< -2000 || delay>10000) { fail(checks,"MARKET_FRESHNESS_CLOCK",`index=${i};age_ms=${age};delay_ms=${delay};future_ms=${future}`); streamOk=false; }
    const c=cursor.get(key);
    if (c) {
      if (m.sequence < c.seq) { fail(checks,"MARKET_SEQUENCE_REPLAY_OR_REORDER",`index=${i}`); streamOk=false; }
      else if (m.sequence === c.seq && m.payload_sha256 !== c.payload) { fail(checks,"MARKET_SEQUENCE_EQUIVOCATION",`index=${i}`); streamOk=false; }
      else if (m.sequence > c.seq + 1) { fail(checks,"MARKET_SEQUENCE_GAP",`index=${i}`); streamOk=false; }
      if (eff.getTime() < c.effective) { fail(checks,"MARKET_EFFECTIVE_TIME_REORDER",`index=${i}`); streamOk=false; }
      if (m.sequence === c.seq && m.payload_sha256 === c.payload) continue;
    }
    cursor.set(key,{seq:m.sequence,payload:m.payload_sha256,effective:eff.getTime()});
    latest.set(`${m.source_kind}|${m.source_id}`,m);
  }
  if (streamOk) pass(checks,"MARKET_STREAM_SEQUENCE_AND_FRESHNESS","registered/fresh/ordered");

  const primary=[...latest.values()].filter((m:any)=>m.source_kind==="PRIMARY_LISTING_EXCHANGE");
  const sip=[...latest.values()].filter((m:any)=>m.source_kind==="SIP");
  if (primary.length===0) { fail(checks,"PRIMARY_EXCHANGE_STATUS_REQUIRED","no primary source"); return; }
  const pset=new Set(primary.map((m:any)=>m.status));
  if (pset.size!==1) { fail(checks,"MARKET_STATUS_CONFLICT","primary sources disagree"); return; }
  const pstatus=[...pset][0];
  if (pstatus === "HALTED") { fail(checks,"MARKET_STATUS_CLEAR","primary halt active"); return; }
  const all=[...latest.values()].map((m:any)=>m.status);
  if (all.some((x:any)=>x==="HALTED"||x==="PAUSED") && all.some((x:any)=>x==="TRADING"||x==="RESUME_ELIGIBLE")) {
    fail(checks,"MARKET_STATUS_CONFLICT","stopping and permissive statuses conflict"); return;
  }
  if (pstatus === "RESUME_ELIGIBLE") {
    const sipOk=sip.length>0 && sip.every((m:any)=>m.status==="RESUME_ELIGIBLE");
    if (!sipOk) { fail(checks,"RESUME_QUORUM","primary resume lacks SIP agreement"); return; }
  }
  if (all.includes("PAUSED")) { fail(checks,"LULD_SUPPLEMENTAL_PAUSE","supplemental pause active"); return; }
  pass(checks,"MARKET_STATUS_CLEAR",`primary=${pstatus}`);
}

function validateIssuer(p:any, checks:any[]) {
  const r=p.issuer_receipt ?? {};
  const now=dt(p.now), trading=dt(p.trading_start_at), delivered=dt(r.delivered_at), recorded=dt(r.provider_recorded_at);
  let ok=true;
  if (r.symbol !== "ABC" || !String(r.issuer_id||"").trim()) { fail(checks,"ISSUER_IDENTITY","symbol/issuer mismatch"); ok=false; }
  if (r.notice_sha256 !== p.expected_notice_sha256 || !HEX64.test(String(r.notice_sha256||""))) { fail(checks,"ISSUER_NOTICE_DIGEST","notice digest mismatch"); ok=false; }
  if (!["REGISTERED_EMAIL","COURIER","ISSUER_PORTAL"].includes(r.delivery_channel)) { fail(checks,"ISSUER_DELIVERY_CHANNEL","unapproved channel"); ok=false; }
  if (!String(r.delivery_provider_id||"").trim() || !String(r.provider_receipt_id||"").trim() || !HEX64.test(String(r.provider_payload_sha256||"")) || r.verified!==true) { fail(checks,"ISSUER_RECEIPT_PROVENANCE","provider evidence incomplete"); ok=false; }
  if (!now || !trading || !delivered || !recorded) { fail(checks,"ISSUER_TIMESTAMP_PARSE","timestamp missing/invalid"); ok=false; }
  else {
    if (delivered>now || recorded>now || recorded<delivered || recorded.getTime()-delivered.getTime()>3600000) { fail(checks,"ISSUER_DELIVERY_TIMING","provider timing invalid"); ok=false; }
    if (trading.getTime()-delivered.getTime()<30*86400000) { fail(checks,"ISSUER_30_DAY_WAIT","less than 30 calendar days"); ok=false; }
  }
  if (r.objection_received_at != null) { fail(checks,"ISSUER_OBJECTION_HOLD","objection requires hold"); ok=false; }
  if (ok) pass(checks,"ISSUER_DELIVERY_AND_WAIT","hash-bound synthetic receipt passes modeled gate");
}

Deno.serve(async (req:Request)=>{
  if (req.method!=="POST") return new Response(JSON.stringify({error:"POST_REQUIRED"}),{status:405,headers:{"content-type":"application/json"}});
  let p:any; try { p=await req.json(); } catch { return new Response(JSON.stringify({error:"INVALID_JSON"}),{status:400,headers:{"content-type":"application/json"}}); }
  const checks:any[]=[];
  p.parent_v3_4_release_sha256===PARENT_V34 ? pass(checks,"PARENT_V34_BINDING","exact parent release") : fail(checks,"PARENT_V34_BINDING","parent release mismatch");
  p.v3_5_control_core_sha256===CONTROL_CORE ? pass(checks,"CONTROL_CORE_BINDING","exact control-core digest") : fail(checks,"CONTROL_CORE_BINDING","control-core mismatch");
  validateStream(p,checks);
  validateIssuer(p,checks);
  const decision=checks.some(c=>c.status==="FAIL")?"DENY":"ALLOW";
  const material={schema:"WS-QCRYPTO-TSV-V3_5-EXTERNAL-ADVERSARIAL-V1",execution_target:"Supabase Edge Function",project_ref:"aspmlcdjnbcujsxdhwri",decision,checks,claims_label:"EXTERNAL_SYNTHETIC_ADVERSARIAL_SOFTWARE_EVIDENCE_ONLY_NOT_LIVE_MARKET_DATA_OR_LEGAL_COMPLIANCE"};
  const receipt_sha256=await sha("WS-QCRYPTO-TSV-V3_5-EXTERNAL-ADVERSARIAL-V1\0"+canon(material));
  return new Response(JSON.stringify({...material,receipt_sha256}),{headers:{"content-type":"application/json","cache-control":"no-store"}});
});

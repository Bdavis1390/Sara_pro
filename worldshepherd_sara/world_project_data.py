
"""WORLD CONTROLLER real-time local project/document data hub."""
from __future__ import annotations
import hashlib, html, json, os, re, subprocess, time, zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from fastapi import APIRouter, Header, HTTPException, Query
router = APIRouter(prefix="/world", tags=["WORLD CONTROLLER REALTIME DATA"])
TEXT_EXTS={".txt",".md",".markdown",".json",".jsonl",".yaml",".yml",".py",".sh",".html",".htm",".css",".js",".ts",".tsx",".csv",".log",".ini",".toml",".cfg",".conf",".rst",".rtf"}; DOC_EXTS=TEXT_EXTS|{".pdf",".docx",".odt"}
EXCLUDE_DIRS={".git",".venv","venv","env","__pycache__","node_modules",".cache",".mypy_cache",".pytest_cache","dist","build","site-packages",".idea",".vscode","target"}
MAX_TEXT_BYTES=int(os.getenv("WORLD_DOC_MAX_TEXT_BYTES",str(2_500_000))); MAX_FILES=int(os.getenv("WORLD_SCAN_MAX_FILES","4000"))
KEYWORDS=[("WORLD CONTROLLER / SARA / SSPADAWANZZ",["world controller","sara","sspadawanzz","prime sentinel","ark","guardian","oracle","watcher","audit"]),("WS-AlTi Meta-Alloy / Additive Manufacturing",["al-ti","alti","meta-alloy","ded","directed energy","titanium","scandium","zirconium","al-mg-sc-zr","coupon validation"]),("Adaptive Metasurface / RF Control",["metasurface","rf","phase shifter","permittivity","conductivity","em tile","beamforming","null steering","maxwell"]),("BAROS / Medical Optimization",["baros","radiotherapy","dose","gamma","treatment planning","monte carlo","eclipse","monaco"]),("DIAS-C / IP Attribution / Counsel",["dias-c","superuser","compensation","counsel","evidentiary","pro bono","reparations","token"]),("Steganography / Padawan Lab",["steg","stegriage","icc","exif","png","bmp","svg","color channel","payload"]),("Containerized Lab / Admin Infrastructure",["docker","compose","containerized lab","path 2","vault","keycloak","prometheus","grafana","uvicorn","fastapi"])]
RISK_TERMS={"Requires legal review":["legal review","counsel","patent","provisional","claim","valuation","licensing"],"Requires lab validation":["lab validation","coupon","fatigue","xrd","ebsd","sem","validated","simulation only","hypothesis"],"Hardware safety boundary":["rf","laser","voltage","actuator","thermal","metasurface","power supply","material state"],"Operational security boundary":["token","admin","audit","registry","relay","secret","credential"]}
def _now(): return time.time()
def _repo_root(): return Path(os.getenv("WORLD_REPO_DIR",os.getcwd())).expanduser().resolve()
def _data_dir():
    r=Path(os.getenv("WORLD_DATA_DIR",str(_repo_root()/"data"))).expanduser(); r.mkdir(parents=True,exist_ok=True); return r
def _registry_path(): return _data_dir()/"world_controller_registry.json"
def _audit_path(): return _data_dir()/"world_controller_audit.jsonl"
def _ark_dir():
    r=_data_dir()/"world_controller_ark"; r.mkdir(parents=True,exist_ok=True); return r
def _index_path(): return _data_dir()/"world_realtime_document_index.json"
def _sha1_key(s): return hashlib.sha1(str(s).encode("utf-8","ignore")).hexdigest()[:12]
def _sha256_obj(obj): return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode("utf-8","ignore")).hexdigest()
def _doc_id(path): return hashlib.sha256(str(path.resolve()).encode("utf-8","ignore")).hexdigest()[:18]
def _default_roots():
    home=Path.home(); roots=[_repo_root(),_repo_root()/"docs",_repo_root()/"world_documents",_repo_root()/"payloads",_repo_root()/"data",home/"Worldshepherd",home/"worldshepherd",home/"Documents"/"Worldshepherd",home/"Documents",home/"Downloads"]
    for item in re.split(r"[:,]",os.getenv("WORLD_PROJECT_ROOTS","")):
        if item.strip(): roots.append(Path(item.strip()).expanduser())
    seen=set(); out=[]
    for r in roots:
        try: rr=r.resolve()
        except Exception: continue
        if rr.exists() and rr not in seen: seen.add(rr); out.append(rr)
    return out
def _require_admin(authorization:Optional[str], x_sara_admin_token:Optional[str]):
    expected=os.getenv("SARA_ADMIN_TOKEN",""); supplied=x_sara_admin_token or ""
    if authorization and authorization.lower().startswith("bearer "): supplied=authorization.split(" ",1)[1].strip()
    if not expected: raise HTTPException(status_code=500,detail="SARA_ADMIN_TOKEN is not set")
    if supplied.strip()!=expected: raise HTTPException(status_code=403,detail="WORLD CONTROLLER admin token required")
    return "SSPADAWANZZ_ADMIN"
def _append_audit(actor,event,payload):
    rec={"ts":_now(),"audit_id":f"WC-RT-{hashlib.sha1((event+str(_now())).encode()).hexdigest()[:12]}","actor":actor,"event":event,"payload":payload}
    with _audit_path().open("a",encoding="utf-8") as f: f.write(json.dumps(rec,sort_keys=True)+"\n")
    return rec
def _read_json(path,fallback):
    try: return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback
    except Exception: return fallback
def _read_audit(limit=50):
    if not _audit_path().exists(): return []
    rows=[]
    for line in _audit_path().read_text(encoding="utf-8",errors="ignore").splitlines()[-limit:]:
        try: rows.append(json.loads(line))
        except Exception: pass
    return list(reversed(rows))
def _iter_files():
    count=0
    for root in _default_roots():
        if root.is_file(): yield root; continue
        if not root.exists(): continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:]=[d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith(".")]
            for name in filenames:
                if count>=MAX_FILES: return
                p=Path(dirpath)/name
                if p.suffix.lower() in DOC_EXTS: count+=1; yield p
def _strip_xml(raw): return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",raw))).strip()
def _extract_zip_xml(path,candidates):
    try:
        with zipfile.ZipFile(path) as zf: return "\n".join(_strip_xml(zf.read(n).decode("utf-8","ignore")) for n in candidates if n in zf.namelist())
    except Exception: return ""
def _extract_pdf(path):
    try:
        proc=subprocess.run(["pdftotext","-layout",str(path),"-"],text=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=8)
        if proc.returncode==0 and proc.stdout.strip(): return proc.stdout
    except Exception: pass
    try:
        text=path.read_bytes()[:MAX_TEXT_BYTES].decode("latin-1","ignore"); return re.sub(r"\s+"," ",re.sub(r"[^\x09\x0A\x0D\x20-\x7E]+"," ",text))
    except Exception: return ""
def _extract_text(path):
    ext=path.suffix.lower()
    try:
        if ext in TEXT_EXTS: return path.read_text(encoding="utf-8",errors="ignore")[:MAX_TEXT_BYTES]
        if ext==".docx": return _extract_zip_xml(path,["word/document.xml"])
        if ext==".odt": return _extract_zip_xml(path,["content.xml"])
        if ext==".pdf": return _extract_pdf(path)[:MAX_TEXT_BYTES]
    except Exception: return ""
    return ""
def _classify(text,path):
    hay=f"{path.name}\n{text[:20000]}".lower(); scores=[]; hits=[]
    for label,keys in KEYWORDS:
        matched=[k for k in keys if k in hay]
        if matched: scores.append((len(matched),label)); hits.extend(matched[:8])
    project=sorted(scores,reverse=True)[0][1] if scores else "General / Unclassified Technical Corpus"
    risk=[label for label,terms in RISK_TERMS.items() if any(t in hay for t in terms)]
    return project,sorted(set(hits))[:20],risk
def _summarize_text(text,max_sentences=5):
    clean=re.sub(r"\s+"," ",text).strip()
    if not clean: return ["No extractable text was available; dossier is based on file metadata only."]
    preferred=["world","sara","metasurface","alloy","audit","registry","validation","control","dossier","ip","ded","thermal","risk","oracle","ark","guardian"]; useful=[]
    for s in re.split(r"(?<=[.!?])\s+",clean):
        s=s.strip()
        if len(s)>=30 and any(k in s.lower() for k in preferred): useful.append(s[:420])
        if len(useful)>=max_sentences: break
    return (useful or [clean[:420]])[:max_sentences]
def _scan_documents():
    docs=[]; projects={}; roots=[str(r) for r in _default_roots()]
    for path in _iter_files():
        try: st=path.stat()
        except Exception: continue
        text=_extract_text(path); project,keywords,risk=_classify(text,path)
        try: rel=str(path.relative_to(_repo_root()))
        except Exception: rel=str(path)
        try: digest=hashlib.sha256(path.read_bytes()[:5_000_000]).hexdigest()
        except Exception: digest=_sha256_obj({"path":str(path),"mtime":st.st_mtime,"size":st.st_size})
        doc={"doc_id":_doc_id(path),"title":path.name,"path":str(path),"relative_path":rel,"extension":path.suffix.lower(),"size_bytes":st.st_size,"modified_ts":st.st_mtime,"modified_human":time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(st.st_mtime)),"project":project,"project_key":_sha1_key(project),"keywords":keywords,"risk_flags":risk,"text_available":bool(text.strip()),"summary":_summarize_text(text),"sha256":digest}
        docs.append(doc); p=projects.setdefault(project,{"project":project,"project_key":_sha1_key(project),"documents":0,"bytes":0,"risk_flags":{},"latest_modified_ts":0,"top_documents":[]})
        p["documents"]+=1; p["bytes"]+=st.st_size; p["latest_modified_ts"]=max(p["latest_modified_ts"],st.st_mtime)
        for flag in risk: p["risk_flags"][flag]=p["risk_flags"].get(flag,0)+1
    docs.sort(key=lambda d:d["modified_ts"],reverse=True)
    for p in projects.values():
        p["latest_modified_human"]=time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(p["latest_modified_ts"])) if p["latest_modified_ts"] else "n/a"; p["top_documents"]=[d for d in docs if d["project"]==p["project"]][:10]
    result={"ok":True,"generated_ts":_now(),"generated_human":time.strftime("%Y-%m-%d %H:%M:%S",time.localtime()),"roots":roots,"document_count":len(docs),"project_count":len(projects),"projects":sorted(projects.values(),key=lambda x:(x["documents"],x["bytes"]),reverse=True),"documents":docs}
    result["index_hash"]=_sha256_obj({"docs":[{"id":d["doc_id"],"sha256":d["sha256"],"mtime":d["modified_ts"]} for d in docs]}); _index_path().write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8"); return result
def _load_or_scan(): return _scan_documents()
def _find_doc(doc_id):
    for d in _load_or_scan().get("documents",[]):
        if d.get("doc_id")==doc_id or d.get("sha256","").startswith(doc_id): return d
    raise HTTPException(status_code=404,detail=f"Document evidence not found: {doc_id}")
def _project_by_key(key):
    for p in _load_or_scan().get("projects",[]):
        if p.get("project_key")==key or p.get("project","").lower()==key.lower(): return p
    raise HTTPException(status_code=404,detail=f"Project evidence not found: {key}")
def _ark_tail():
    out=[]
    for p in sorted(_ark_dir().glob("ARK-RP-*.json"),key=lambda x:x.stat().st_mtime if x.exists() else 0,reverse=True)[:25]: out.append({"snapshot_id":p.stem,"file":str(p),"modified_human":time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(p.stat().st_mtime)),"size_bytes":p.stat().st_size})
    return out
def _panel_dossier(panel,actor):
    idx=_load_or_scan(); registry=_read_json(_registry_path(),{}); audit=_read_audit(25); ark=_ark_tail(); docs=idx.get("documents",[]); projects=idx.get("projects",[]); recent=docs[:12]; risk_doc_count=sum(1 for d in docs if d.get("risk_flags")); panel=panel.lower().strip(); guardian="AMBER" if panel in {"guardians","registry","ark","admin","preflight"} or (panel=="guardians" and risk_doc_count) else "GREEN"
    narrative={"Operational meaning":"This readout is populated from local repo files, scanned project roots, technical documents, registry, audit log, and Ark restore-point store at request time.","Evidence boundary":"The dossier proves what is currently readable on this machine. It cannot include documents that have not been downloaded, copied into the project, or placed under a scanned folder.","Completion result":"Panel evidence is linked to project and document dossiers so the UI can move from summary to source-level evidence."}
    if panel=="watchers": components={"registry_nodes":registry,"recent_file_heartbeats":recent,"heartbeat_rule":"File modified times and registry last_seen values are used as local heartbeat evidence until external telemetry adapters are added."}; summary=[f"Watcher readout scanned {idx['document_count']} document/project files across {len(idx['roots'])} root(s).",f"{len(registry) if isinstance(registry,dict) else 0} registry node(s) are visible in local state.","Recent document modifications are treated as project heartbeat evidence."]
    elif panel=="guardians": components={"risk_flagged_documents":[d for d in docs if d.get("risk_flags")][:30],"risk_terms":RISK_TERMS}; summary=[f"Guardian readout found {risk_doc_count} document(s) with legal, lab-validation, hardware-safety, or operational-security boundary terms.","These flags identify records needing classification before execution or external sharing.","RED/BLACK command boundaries remain enforced by the command gate; project documents only inform the dossier."]
    elif panel=="oracle": components={"project_forecast_inputs":projects,"recent_documents":recent}; summary=["Oracle readout uses the live corpus as dry-run context for decisions.",f"{idx['project_count']} project cluster(s) and {idx['document_count']} document(s) are available as forecast context.","High-friction actions should cite relevant document/project evidence before execution."]
    elif panel=="ark": components={"ark_snapshots":ark,"document_index_hash":idx.get("index_hash"),"index_path":str(_index_path())}; summary=[f"Ark readout found {len(ark)} local restore-point file(s).","The real-time document index is hashable and stored as local continuity evidence.","Before registry or relay changes, create an Ark snapshot and link it to the project/document evidence used."]
    elif panel=="registry": components={"registry":registry,"project_registry_overlay":projects}; summary=[f"Registry readout combines {len(registry) if isinstance(registry,dict) else 0} local node record(s) with {idx['project_count']} project corpus cluster(s).","Project clusters are evidence domains, not executable nodes by themselves.","Use registry patches only after Watchers, Guardians, Oracle, and Ark preflight are complete."]
    elif panel=="audit": components={"recent_audit_records":audit,"recent_document_changes":recent}; summary=[f"Audit readout shows {len(audit)} recent WORLD/SARA audit record(s) and latest project-file changes.","Audit records are local JSONL evidence; document changes are filesystem evidence.","Together they form the local operational timeline."]
    elif panel=="admin": components={"scan_roots":idx.get("roots"),"env":{"WORLD_PROJECT_ROOTS":os.getenv("WORLD_PROJECT_ROOTS",""),"WORLD_DATA_DIR":str(_data_dir()),"WORLD_SCAN_MAX_FILES":MAX_FILES,"WORLD_DOC_MAX_TEXT_BYTES":MAX_TEXT_BYTES}}; summary=["Admin readout shows scanned roots and corpus bounds.","Add folders to WORLD_PROJECT_ROOTS to pull in more projects.","Keep secrets out of scanned documents before broad sharing."]
    elif panel=="preflight": components={"recommended_chain":["Watchers heartbeat","Guardian classification","Oracle dry-run","Ark snapshot"],"project_context":projects[:12],"evidence_rule":"Use project/document links as supporting context for each preflight step."}; summary=["Preflight now has real-time project/document context attached.","The four next actions remain required before registry or relay changes.","Project evidence supports decisions; it does not replace Guardian policy."]
    else: components={"projects":projects,"recent_documents":recent,"registry":registry,"audit_tail":audit[:10],"ark_tail":ark[:10]}; summary=[f"Dashboard scanned {idx['document_count']} technical/project document(s) across {len(idx['roots'])} root(s).",f"Detected {idx['project_count']} project/evidence cluster(s).","This panel is now populated from live local data, not fixed placeholder text."]
    links=[{"label":"Real-Time Evidence Index","path":"/world/realtime/evidence"},{"label":"All Projects","path":"/world/realtime/projects"},{"label":"All Documents","path":"/world/realtime/documents"}]+[{"label":f"Project Evidence — {p['project']}","path":f"/world/realtime/project/{p['project_key']}"} for p in projects[:8]]+[{"label":f"Document Evidence — {d['title']}","path":f"/world/realtime/document/{d['doc_id']}"} for d in recent[:8]]
    audit_rec=_append_audit(actor,"world_realtime_panel_read",{"panel":panel,"document_count":idx.get("document_count"),"project_count":idx.get("project_count")})
    return {"ok":True,"panel":panel,"title":f"{panel.title()} Real-Time Project Dossier","guardian_policy":guardian,"generated_human":idx.get("generated_human"),"executive_summary":summary,"facts":{"documents_scanned":idx.get("document_count"),"projects_detected":idx.get("project_count"),"scan_roots":len(idx.get("roots",[])),"index_hash":idx.get("index_hash"),"audit_id":audit_rec.get("audit_id"),"risk_flagged_documents":risk_doc_count},"narrative":narrative,"components":components,"project_evidence":projects[:20],"document_evidence":recent,"evidence_links":links,"next_actions":["Use Watchers to inspect live registry and document heartbeat state.","Use Guardians to classify commands using relevant project/document evidence.","Use Oracle to dry-run high-friction actions with the scanned corpus as context.","Use Ark before registry or relay changes; link restore points to evidence."],"raw_evidence":{"index":{k:v for k,v in idx.items() if k!="documents"},"sample_documents":recent}}
@router.get("/realtime/scan")
def realtime_scan(authorization:Optional[str]=Header(default=None),x_sara_admin_token:Optional[str]=Header(default=None))->Dict[str,Any]:
    actor=_require_admin(authorization,x_sara_admin_token); idx=_load_or_scan(); _append_audit(actor,"world_realtime_scan",{"documents":idx.get("document_count"),"projects":idx.get("project_count")}); return idx
@router.get("/realtime/panel/{panel}")
def realtime_panel(panel:str,authorization:Optional[str]=Header(default=None),x_sara_admin_token:Optional[str]=Header(default=None))->Dict[str,Any]: return _panel_dossier(panel,_require_admin(authorization,x_sara_admin_token))
@router.get("/realtime/projects")
def realtime_projects(authorization:Optional[str]=Header(default=None),x_sara_admin_token:Optional[str]=Header(default=None))->Dict[str,Any]:
    actor=_require_admin(authorization,x_sara_admin_token); idx=_load_or_scan(); _append_audit(actor,"world_realtime_projects_read",{"projects":idx.get("project_count")}); return {"ok":True,"title":"All Project Evidence Dossier","guardian_policy":"GREEN","executive_summary":[f"{idx['project_count']} project/evidence cluster(s) detected from {idx['document_count']} document(s).","Each project links to source document evidence."],"facts":{"projects_detected":idx["project_count"],"documents_scanned":idx["document_count"],"index_hash":idx["index_hash"]},"projects":idx.get("projects",[]),"project_evidence":idx.get("projects",[]),"evidence_links":[{"label":p["project"],"path":f"/world/realtime/project/{p['project_key']}"} for p in idx.get("projects",[])],"raw_evidence":idx}
@router.get("/realtime/project/{project_key}")
def realtime_project(project_key:str,authorization:Optional[str]=Header(default=None),x_sara_admin_token:Optional[str]=Header(default=None))->Dict[str,Any]:
    actor=_require_admin(authorization,x_sara_admin_token); idx=_load_or_scan(); project=_project_by_key(project_key); docs=[d for d in idx.get("documents",[]) if d.get("project")==project.get("project")]; _append_audit(actor,"world_realtime_project_read",{"project":project.get("project"),"documents":len(docs)}); return {"ok":True,"title":f"Project Evidence Dossier — {project['project']}","guardian_policy":"AMBER" if project.get("risk_flags") else "GREEN","executive_summary":[f"Project cluster contains {len(docs)} document(s).",f"Latest modification: {project.get('latest_modified_human')}.","Use linked document evidence before making claims, outreach, registry, or relay changes."],"facts":project,"narrative":{"Full-bloom project meaning":"This cluster is built from keyword classification across local technical records. It is an operational evidence domain, not an automatic truth claim.","Evidence boundary":"The dossier is only as complete as scanned local folders. Add missing repositories/docs to WORLD_PROJECT_ROOTS or world_documents/inbox.","Next use":"Open document dossiers, cite hashes, and attach Ark restore points before external action."},"document_evidence":docs[:100],"evidence_links":[{"label":d["title"],"path":f"/world/realtime/document/{d['doc_id']}"} for d in docs[:100]],"next_actions":["Open top documents.","Check risk flags.","Create Ark snapshot before changes.","Use Guardian classification before execution or outreach."],"raw_evidence":{"project":project,"documents":docs}}
@router.get("/realtime/documents")
def realtime_documents(authorization:Optional[str]=Header(default=None),x_sara_admin_token:Optional[str]=Header(default=None),limit:int=Query(200,ge=1,le=1000))->Dict[str,Any]:
    actor=_require_admin(authorization,x_sara_admin_token); idx=_load_or_scan(); docs=idx.get("documents",[])[:limit]; _append_audit(actor,"world_realtime_documents_read",{"returned":len(docs)}); return {"ok":True,"title":"All Technical Documents Dossier","guardian_policy":"GREEN","executive_summary":[f"Showing {len(docs)} of {idx['document_count']} scanned technical/project document(s).","Each document has local evidence ID, hash, modified time, project cluster, and summary."],"facts":{"returned":len(docs),"total":idx["document_count"],"index_hash":idx["index_hash"]},"document_evidence":docs,"evidence_links":[{"label":d["title"],"path":f"/world/realtime/document/{d['doc_id']}"} for d in docs[:200]],"raw_evidence":{"documents":docs}}
@router.get("/realtime/document/{doc_id}")
def realtime_document(doc_id:str,authorization:Optional[str]=Header(default=None),x_sara_admin_token:Optional[str]=Header(default=None))->Dict[str,Any]:
    actor=_require_admin(authorization,x_sara_admin_token); doc=_find_doc(doc_id); text=_extract_text(Path(doc["path"])); excerpts=_summarize_text(text,12); _append_audit(actor,"world_realtime_document_read",{"doc_id":doc_id,"title":doc.get("title")}); return {"ok":True,"title":f"Document Evidence Dossier — {doc['title']}","guardian_policy":"AMBER" if doc.get("risk_flags") else "GREEN","executive_summary":[f"Document belongs to project cluster: {doc.get('project')}.",f"Local evidence ID: {doc.get('doc_id')}; SHA-256: {doc.get('sha256')[:24]}…","Use this dossier as source-level evidence for UI readouts, preflight decisions, and Ark-linked changes."],"facts":doc,"narrative":{"Full-bloom document meaning":"This is a local source record. The UI uses metadata, hash, extracted text, and classification keywords to populate project dossiers.","Evidence boundary":"Text extraction is best-effort. For PDFs without pdftotext, the dossier may rely on metadata and printable fragments.","Operational use":"Before citing claims from this file, review the excerpt and open the original document when needed."},"document_excerpts":excerpts,"document_evidence":[doc],"evidence_links":[{"label":"All Documents","path":"/world/realtime/documents"},{"label":f"Project — {doc.get('project')}","path":f"/world/realtime/project/{doc.get('project_key')}"}],"next_actions":["Review excerpts.","Check risk flags.","Attach this doc ID/hash to relevant Ark snapshots.","Refresh dashboard after editing source docs."],"raw_evidence":{"document":doc,"excerpts":excerpts}}
@router.get("/realtime/search")
def realtime_search(q:str=Query(...,min_length=1),authorization:Optional[str]=Header(default=None),x_sara_admin_token:Optional[str]=Header(default=None))->Dict[str,Any]:
    actor=_require_admin(authorization,x_sara_admin_token); idx=_load_or_scan(); query=q.lower(); hits=[]
    for d in idx.get("documents",[]):
        hay=json.dumps({"title":d.get("title"),"project":d.get("project"),"keywords":d.get("keywords"),"summary":d.get("summary"),"path":d.get("path")}).lower()
        if query in hay: hits.append(d)
    _append_audit(actor,"world_realtime_search",{"q":q,"hits":len(hits)}); return {"ok":True,"title":f"Search Evidence Dossier — {q}","guardian_policy":"GREEN","executive_summary":[f"Search returned {len(hits)} document(s) for query: {q}.","Results are drawn from the live local project/document corpus."],"facts":{"query":q,"hits":len(hits),"index_hash":idx.get("index_hash")},"document_evidence":hits[:200],"evidence_links":[{"label":d["title"],"path":f"/world/realtime/document/{d['doc_id']}"} for d in hits[:200]],"raw_evidence":{"query":q,"hits":hits[:200]}}
@router.get("/realtime/evidence")
def realtime_evidence(authorization:Optional[str]=Header(default=None),x_sara_admin_token:Optional[str]=Header(default=None))->Dict[str,Any]: return _panel_dossier("dashboard",_require_admin(authorization,x_sara_admin_token))

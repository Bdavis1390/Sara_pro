#!/usr/bin/env python3
"""Fetch exact published STAR baryon-transport derived HEPData tables (CC0).
No detector raw data, no untrusted scripts executed, no deserialization via pickle.
"""
import argparse, datetime, hashlib, json, pathlib, subprocess, urllib.parse
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--record-metadata",required=True)
 ap.add_argument("--out",required=True)
 ap.add_argument("--max-bytes",type=int,default=2000000)
 a=ap.parse_args()
 m=json.loads(pathlib.Path(a.record_metadata).read_text())
 assert m.get("recid")==154708,"Unexpected HEPData record"
 root=pathlib.Path(a.out).resolve();root.mkdir(parents=True,exist_ok=True)
 collected=[];fail=[]
 for i,t in enumerate(m["data_tables"],1):
  url=t["data"]["json"].replace(" ","%20")
  parsed=urllib.parse.urlparse(url)
  if parsed.scheme!="https" or parsed.hostname!="www.hepdata.net" or not parsed.path.startswith("/download/table/ins2822399/"):
   raise RuntimeError("Source URL not allowlisted: "+url)
  f=root/("table_%02d.json"%i)
  if f.exists():
   raw=f.read_bytes()
  else:
   p=subprocess.run(["curl","-fLsS","--max-time","25","--max-filesize",str(a.max_bytes),url],capture_output=True,timeout=30)
   if p.returncode:
    fail.append({"table":i,"error":p.stderr.decode(errors="replace")[:200]});print("ERROR",i,fail[-1]["error"],flush=True);continue
   raw=p.stdout
   if len(raw)>a.max_bytes:raise RuntimeError("Max single-table byte limit")
  tab=json.loads(raw)
  if tab.get("table_license",{}).get("name")!="CC0":
   raise RuntimeError("Unverified reuse license for table "+str(i))
  f.write_bytes(raw)
  row={"id":i,"name":t.get("name"),"description":t.get("description"),"source_url":url,
       "bytes":len(raw),"sha256":sha(raw),"values":len(tab.get("values",[])),
       "license":"CC0","source_record":"https://www.hepdata.net/record/154708"}
  collected.append(row);print("VERIFIED",i,row["name"],row["values"],"rows",flush=True)
 manifest={"retrieved_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "source_doi":"10.17182/hepdata.154708","source_paper":"10.1126/science.ads5962",
           "record_id":154708,"license":"CC0","table_count":len(collected),
           "total_bytes":sum(x["bytes"] for x in collected),"tables":collected,
           "errors":fail,"data_role":"Published derived numerical observables, not raw detector data"}
 (root/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
 print("SUMMARY",json.dumps({"tables":len(collected),"errors":len(fail),"bytes":manifest["total_bytes"]}))
 if fail or len(collected)!=26:raise SystemExit(2)
if __name__=="__main__":main()

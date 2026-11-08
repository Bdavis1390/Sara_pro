#!/usr/bin/env python3
"""Exports external QGP source metadata as SARA/WS-PHYS.1.0 review-staging records.
This DOES NOT write to the SARA runtime or approve scientific claims.
"""
import argparse, hashlib, json, pathlib, sqlite3, datetime
def sha(b): return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--database",required=True)
 p.add_argument("--output",required=True)
 p.add_argument("--hepdata-manifest",default="")
 a=p.parse_args()
 db=sqlite3.connect("file:"+str(pathlib.Path(a.database).resolve())+"?mode=ro",uri=True)
 out=pathlib.Path(a.output);out.mkdir(parents=True,exist_ok=True)
 totals={}
 file=out/"ws_physics_external_sources.jsonl"
 with file.open("w",encoding="utf-8") as f:
  q="""SELECT w.id,w.title,w.year,w.doi,
        group_concat(DISTINCT o.provider),group_concat(DISTINCT o.url),
        count(DISTINCT o.provider||':'||o.provider_id)
        FROM works w LEFT JOIN observations o ON o.work_id=w.id
        GROUP BY w.id ORDER BY w.year,w.id"""
  for work_id,title,year,doi,providers,urls,n in db.execute(q):
   record={
    "record_id":"WS-QGP-SRC-"+sha(work_id.encode())[:16],
    "physics_domain":"QCD / heavy-ion physics",
    "model_scope":"EXTERNAL bibliographic record; unreviewed scientific content",
    "study_year":year,"study_title":title,"external_source_id":work_id,
    "doi":doi or None,"source_providers":(providers or "").split(","),
    "source_urls":(urls or "").split(","),
    "source_observations":n,
    "governing_equations":[],"conservation_constraints":[],
    "assumptions":["Bibliographic metadata is not a physical observation"],
    "boundary_conditions":[],"parameter_sources":(urls or "").split(","),
    "unit_system":"not applicable to bibliographic record",
    "uncertainty_method":"requires paper-specific review",
    "sensitivity_method":"not evaluated",
    "calibration_record_id":None,
    "raw_data_digest":None,
    "validation_state":"SOURCE_INDEXED_UNREVIEWED",
    "independent_review_state":"NOT_REVIEWED",
    "external_safe_statement":"External paper indexed. No independent WorldShepherd physical validation is claimed.",
    "cre1aws_approval_state":"PENDING",
    "scientific_claim_maturity":"LITERATURE_METADATA_ONLY"
   }
   f.write(json.dumps(record,ensure_ascii=False,sort_keys=True)+"\n")
   totals[str(year or "unknown")]=totals.get(str(year or "unknown"),0)+1
 counts={"total_records":sum(totals.values()),"by_year":totals}
 if a.hepdata_manifest:
  meta=json.loads(pathlib.Path(a.hepdata_manifest).read_text())
  count=sum(1 for t in meta.get("tables",[]) if "sha256" in t)
  counts["hepdata_tables_observed"]=count
  ds={"record_id":"WS-QGP-HEPDATA-147195",
      "physics_domain":"QCD/thermal dielectron spectroscopy",
      "model_scope":"External STAR published derived numerical tables",
      "validation_state":"PUBLISHED_TABLE_DOWNLOADED_CHECKSUMMED",
      "independent_review_state":"NOT_REPRODUCED_BY_WORLDSHEPHERD",
      "raw_detector_data_available":False,
      "derived_dataset_source":"https://hepdata.net/record/147195?format=json",
      "table_manifest":meta.get("tables",[]),
      "external_safe_statement":"STAR HEPData tables archived for analysis; not independent reconstruction.",
      "cre1aws_approval_state":"PENDING"}
  (out/"hepdata_review_record.json").write_text(json.dumps(ds,indent=2,sort_keys=True))
 raw=file.read_bytes()
 counts["jsonl_sha256"]=sha(raw)
 counts["jsonl_bytes"]=len(raw)
 counts["generated_utc"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
 counts["stage_only"]=True
 (out/"export_manifest.json").write_text(json.dumps(counts,indent=2,sort_keys=True)+"\n")
 print(json.dumps(counts))
 db.close()
if __name__=="__main__": main()

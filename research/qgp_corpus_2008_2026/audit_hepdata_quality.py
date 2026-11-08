#!/usr/bin/env python3
"""HEPData numerical-table quality audit. Flags, never silently discards, records.
Archived source hashes certify exact copy NOT scientific meaning of every cell.
"""
import argparse,collections,datetime,hashlib,json,pathlib,re,statistics

def audit(obj):
  rows=obj.get("values",[])
  n=len(rows)
  groups=collections.defaultdict(list)
  hidden=0;zero_uncertainty=0;missing=0;non_numeric=0
  for row in rows:
    for dep in row.get("y",[]):
      g=int(dep.get("group",0))
      try:
        v=float(dep["value"])
        groups[g].append(v)
      except (ValueError,TypeError,KeyError):
        missing+=1
        continue
      errs=dep.get("errors",[])
      if not errs:missing+=1
      if errs and all(float(e.get("symerror",0))==0 for e in errs if "symerror" in e) and all("symerror" in e for e in errs):
        zero_uncertainty+=1
      if any(e.get("hide",False) for e in errs):hidden+=1
  groupstats={}
  for g,v in groups.items():
    constant=(len(v)>=2 and len(set(v))==1)
    zero=all(x==0 for x in v)
    groupstats[str(g)]={"points":len(v),"all_values_identical":constant,
      "all_zero":zero,"common_value":v[0] if constant else None}
  suspects=[g for g,st in groupstats.items() if st["all_values_identical"]]
  flags=[]
  if suspects:flags.append("CONSTANT_Y_GROUPS_"+",".join(suspects))
  if hidden:flags.append("HIDDEN_ERRORS_PRESENT")
  if zero_uncertainty:flags.append("ZERO_UNCERTAINTIES_PRESENT")
  if missing:flags.append("MISSING_OR_NONNUMERIC_VALUES")
  headers=str(obj.get("headers",""))
  if "[GeV/c]" in headers and ("Delta Q" in headers or "\\\\Delta Q" in headers or "langle B" in headers or "\\\\langle B" in headers):
    flags.append("POTENTIAL_DIMENSIONLESS_OBSERVABLE_WITH_MOMENTUM_UNIT")
  quarantine=bool(suspects) and (bool(hidden) or zero_uncertainty>=n)
  return {"rows":n,"dependent_groups":groupstats,"hidden_error_cells":hidden,
    "zero_uncertainty_cells":zero_uncertainty,"missing_values_or_errors":missing,
    "flags":flags,"automated_status":"QUARANTINE_FOR_MANUAL_VERIFICATION" if quarantine else
      ("REQUIRES_METADATA_REVIEW" if flags else "STRUCTURALLY_PLAUSIBLE_UNVALIDATED"),
    "caveat":"A flagged constant may be intentional; compare against paper figures and original HEPData submission before assigning fault."}

def main():
  p=argparse.ArgumentParser()
  p.add_argument("--hepdata-dir",required=True);p.add_argument("--out",required=True)
  a=p.parse_args()
  root=pathlib.Path(a.hepdata_dir)
  m=json.loads((root/"manifest.json").read_text())
  statuses=collections.Counter();entries=[]
  for meta in m["tables"]:
    file=root/("table_%02d.json"%meta["id"])
    raw=file.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=meta["sha256"]:raise RuntimeError("Source hash mismatch")
    data=json.loads(raw);result=audit(data)
    entry={"id":meta["id"],"name":meta["name"],"source_sha256":meta["sha256"],
           "source_url":meta["source_url"],**result}
    entries.append(entry);statuses[result["automated_status"]]+=1
  output={"created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source":"https://www.hepdata.net/record/154708",
    "hashes_verified":len(entries),"tables":entries,"status_counts":dict(statuses),
    "independent_raw_detector_validation":False,
    "scientific_readiness":"FLAGS_MUST_BE_REVIEWED_BEFORE_FIT_OR_CLAIM",
    "no_new_physics_claim":True}
  out=pathlib.Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
  out.write_text(json.dumps(output,indent=2)+"\n")
  print(json.dumps({"table_count":len(entries),"statuses":dict(statuses),
    "quarantine":[{"table":e["id"],"name":e["name"],"flags":e["flags"]} for e in entries if e["automated_status"]=="QUARANTINE_FOR_MANUAL_VERIFICATION"],
    "metadata_review":[e["id"] for e in entries if e["automated_status"]=="REQUIRES_METADATA_REVIEW"]},sort_keys=True))
if __name__=="__main__":main()

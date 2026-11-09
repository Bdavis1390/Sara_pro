#!/usr/bin/env python3
"""Power-balance review of passive, shielded RF coupon experiments.
Conservation closure alone cannot establish new physics. This is a data
validator and NOT a certified calorimeter, instrument driver or safety system.
"""
import argparse, collections, csv, datetime, hashlib, json, math, pathlib

CHANNELS=("input","reflected","transmitted","radiated","heat","stored","other")
OUT=("reflected","transmitted","radiated","heat","stored","other")
BASE={"experiment_id","replicate_id","pair_id","sample_type","condition",
      "instrument_id","calibration_id","timestamp_utc","data_origin",
      "device_class","coverage_status"}
REQUIRED=BASE|{f"p_{c}_w" for c in CHANNELS}|{f"u_{c}_w" for c in CHANNELS}
SAMPLES={"CANDIDATE","BLANK"}
CONDITIONS={"OFF","A","B","AB"}
ORIGINS={"SYNTHETIC_TEST","MEASURED_UNVERIFIED"}
def load(path):
 raw=path.read_bytes()
 if len(raw)>2_000_000:raise ValueError("Maximum CSV size 2MB")
 reader=csv.DictReader(raw.decode("utf-8-sig").splitlines())
 if not REQUIRED.issubset(set(reader.fieldnames or [])):
  raise ValueError("Missing CSV fields: "+str(sorted(REQUIRED-set(reader.fieldnames or []))))
 rows=list(reader)
 if not rows:raise ValueError("Empty CSV")
 origin={r["data_origin"] for r in rows}
 if len(origin)!=1 or not origin.issubset(ORIGINS):raise ValueError("Mixed or invalid data_origin")
 grouped=collections.defaultdict(dict)
 for row in rows:
  if any(not str(row.get(k,"")).strip() for k in REQUIRED):raise ValueError("Missing required field value")
  if row["device_class"]!="PASSIVE":
   raise ValueError("Active/pumped devices require a different complete external power budget")
  if row["coverage_status"]!="ALL_PORTS_ACCOUNTED_MEASURED_OR_BOUNDED":
   raise ValueError("Unmeasured radiation, storage and heat must not be silently treated as zero")
  if row["sample_type"] not in SAMPLES or row["condition"] not in CONDITIONS:
   raise ValueError("Unexpected condition or sample type")
  if not row["calibration_id"].startswith("CAL-"):
   raise ValueError("Calibration reference ID missing")
  if row["data_origin"]=="MEASURED_UNVERIFIED" and "SYNTH" in row["calibration_id"]:
   raise ValueError("Synthetic calibration must not be represented as measured evidence")
  k=(row["pair_id"],row["replicate_id"],row["sample_type"])
  cond=row["condition"]
  if cond in grouped[k]:raise ValueError("Duplicate condition")
  vals={}
  for c in CHANNELS:
   v=float(row[f"p_{c}_w"]);u=float(row[f"u_{c}_w"])
   if not(math.isfinite(v) and math.isfinite(u)):raise ValueError("NaN/Inf measurement")
   if v<0 or u<=0:raise ValueError("Negative power or nonpositive standard uncertainty")
   if v>1e3 or u>1e3:raise ValueError("Unexpected unit scale / instrument limit")
   vals[c]=(v,u)
  if cond=="OFF" and vals["input"][0] > 5*vals["input"][1]:
   raise ValueError("OFF condition requires input power compatible with zero")
  grouped[k][cond]={"channels":vals,"instrument":row["instrument_id"],"cal":row["calibration_id"]}
 pairs=collections.defaultdict(set)
 for (pair,rep,sample),records in grouped.items():
  if set(records)!=CONDITIONS:raise ValueError("Missing OFF/A/B/AB condition for "+str((pair,rep,sample)))
  identities={(r["instrument"],r["cal"]) for r in records.values()}
  if len(identities)!=1:raise ValueError("Instrument/calibration changed mid-run")
  pairs[(pair,rep)].add(sample)
 if any(s!=SAMPLES for s in pairs.values()):raise ValueError("Candidate and blank must both be present")
 nrep=collections.Counter(pair for pair,rep in pairs)
 if any(n<3 for n in nrep.values()):raise ValueError("At least 3 independent replicate IDs required")
 return grouped,hashlib.sha256(raw).hexdigest(),next(iter(origin)),len(rows)

def analyze(path):
 grouped,digest,origin,nrows=load(path)
 result=[];nonclosure=0
 for (pair,rep,sample),conditions in sorted(grouped.items()):
  for condition,data in sorted(conditions.items()):
   vals=data["channels"]
   power_in=vals["input"][0]
   power_out=sum(vals[ch][0] for ch in OUT)
   resid=power_in-power_out
   # DIAGONAL preliminary bound; common-mode error and correlated calibration
   # remain unknown until measured covariance supplied.
   sigma=math.sqrt(sum(u*u for _,u in vals.values()))
   z=resid/sigma
   fraction=resid/power_in if power_in>0 else None
   status="PRELIMINARY_DIAGONAL_CLOSURE" if abs(z)<=3 else "NONCLOSURE_REVIEW_REQUIRED"
   if status!="PRELIMINARY_DIAGONAL_CLOSURE":nonclosure+=1
   result.append({"pair_id":pair,"replicate_id":rep,"sample_type":sample,
      "condition":condition,"measured_input_w":power_in,"sum_assigned_outputs_w":power_out,
      "closure_residual_w":resid,"fraction_of_input_unaccounted":fraction,
      "diagonal_uncertainty_w":sigma,"diagnostic_z_diagonal_only":z,"status":status})
 return {"created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "raw_csv_sha256":digest,"data_origin":origin,"number_of_rows":nrows,
  "device_class":"PASSIVE_DECLARED_NOT_CERTIFIED","conditions":result,
  "nonclosure_count":nonclosure,
  "qualifications":[
   "All power channels must be physically exclusive and include measured or defensibly bounded radiation, thermal, storage and other losses",
   "Pump/active devices, transient electrical storage and unaccounted coupling make this simplified passive budget inapplicable",
   "Instrument IDs and calibration certificates are only self-declared; no hardware authenticity verified",
   "Results assume independent channel standard errors; physical calibration covariance can increase or decrease residual uncertainty",
   "A nonclosure may reflect unmeasured channels, wrong reference planes, receiver/sensor nonlinearity or incorrect uncertainty—not creation or violation of energy",
   "A closure check alone is not a test of novel material coupling and cannot rule out normal frequency mixing",
   "No independent lab replication, no source trace hashes, no complete complex S-parameter provenance"
  ],
  "novel_physics_demonstrated":False,
  "discovery_gate":"BLOCKED"}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--csv",required=True);p.add_argument("--out",required=True)
 a=p.parse_args()
 x=analyze(pathlib.Path(a.csv))
 out=pathlib.Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(x,indent=2)+"\n")
 print(json.dumps({"rows":x["number_of_rows"],"nonclosure_review":x["nonclosure_count"],
       "origin":x["data_origin"],"new_physics":False}))
if __name__=="__main__":main()

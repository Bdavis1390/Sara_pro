#!/usr/bin/env python3
"""RF attenuation-after-DUT artifact discriminator, data-only.
Raw receiver signals. An attenuated true pre-receiver spur should scale ~-1
dB spur per 1dB added pad; cubic RECEIVER-generated IM3 ~-3dB/dB
when both input tones suffer the same attenuation in perturbative regime.
This is provisional and neither slope can prove new fundamental physics.
"""
import argparse,collections,csv,datetime,hashlib,json,math,pathlib,statistics
import numpy as np
NEEDED={"experiment_id","pair_id","sample_type","replicate_id","pad_loss_db",
        "tone_low_rx_dbm","tone_high_rx_dbm","spur_raw_rx_dbm",
        "spur_uncertainty_db","spur_above_noise_margin_db",
        "pad_calibration_id","receiver_calibration_id","source_setting_id",
        "timestamp_utc","data_origin"}
ALLOWED={"SYNTHETIC_TEST","MEASURED_UNVERIFIED"}
def slope(x,y,u):
 X=np.column_stack([np.ones(len(x)),x])
 W=1/np.maximum(u,1e-12)**2
 A=X*np.sqrt(W[:,None])
 beta=np.linalg.lstsq(A,y*np.sqrt(W),rcond=None)[0]
 pred=X@beta
 chi=float(np.sum(((y-pred)*np.sqrt(W))**2))
 return {"intercept_dbm":float(beta[0]),"slope_db_per_db":float(beta[1]),
         "residual_chi2_diagonal":chi,
         "max_abs_residual_db":float(np.max(np.abs(y-pred)))}
def parse(path):
 raw=path.read_bytes()
 if len(raw)>2_000_000:raise ValueError("Input >2 MB")
 rdr=csv.DictReader(raw.decode("utf-8-sig").splitlines())
 if not NEEDED.issubset(set(rdr.fieldnames or [])):raise ValueError("Input fields absent")
 rs=list(rdr)
 if not rs:raise ValueError("Empty data")
 origin={r["data_origin"] for r in rs}
 if len(origin)!=1 or not origin.issubset(ALLOWED):raise ValueError("Mixed data origins")
 by=collections.defaultdict(list)
 for row in rs:
  if any(not str(row[c]).strip() for c in NEEDED):raise ValueError("Blank field")
  if row["sample_type"] not in ("CANDIDATE","BLANK"):raise ValueError("No sample identity")
  if not row["pad_calibration_id"].startswith("CAL-") or not row["receiver_calibration_id"].startswith("CAL-"):
   raise ValueError("Missing calibration reference")
  if row["data_origin"]=="MEASURED_UNVERIFIED" and ("SYNTH" in row["pad_calibration_id"] or "SYNTH" in row["receiver_calibration_id"]):
   raise ValueError("Synthetic calibration cannot prove measurement authenticity")
  for key in ("pad_loss_db","tone_low_rx_dbm","tone_high_rx_dbm","spur_raw_rx_dbm","spur_uncertainty_db","spur_above_noise_margin_db"):
   row[key]=float(row[key])
   if not math.isfinite(row[key]):raise ValueError("Nonfinite data")
  if not (0<=row["pad_loss_db"]<=35 and .01<=row["spur_uncertainty_db"]<=3):
   raise ValueError("Pad/uncertainty outside supported range")
  if row["spur_above_noise_margin_db"]<6:raise ValueError("Censored/low-SNR spur must not be treated as reliable detection")
  by[(row["pair_id"],row["replicate_id"],row["sample_type"])].append(row)
 reps=collections.defaultdict(set)
 for (pair,rep,sample),values in by.items():
  levels=[r["pad_loss_db"] for r in values]
  if len(levels)<3 or len(set(levels))!=len(levels) or max(levels)-min(levels)<8:
   raise ValueError("Need 3+ nonduplicate pads over >=8 dB")
  if len({r["source_setting_id"] for r in values})!=1:
   raise ValueError("Source power settings changed with attenuation")
  for key in ("tone_low_rx_dbm","tone_high_rx_dbm"):
   low=next(v[key] for v in values if v["pad_loss_db"]==min(levels))
   a0=min(levels)
   if any(abs((v[key]-low)+(v["pad_loss_db"]-a0))>1.5 for v in values):
    raise ValueError("Incident tone-power check inconsistent with downstream pad location")
  reps[(pair,rep)].add(sample)
  for v in values:
   if any(str(v["pad_calibration_id"])!=str(values[0]["pad_calibration_id"]) for v in values):
    raise ValueError("Pad calibration inconsistent")
 if any(v!={"CANDIDATE","BLANK"} for v in reps.values()):raise ValueError("Both sample and blank must be measured")
 if any(sum(k[0]==pair for k in reps)<3 for pair,rep in reps):raise ValueError("3+ independent sessions required")
 for pair,rep in reps:
  a={v["pad_loss_db"] for v in by[(pair,rep,"CANDIDATE")]}
  b={v["pad_loss_db"] for v in by[(pair,rep,"BLANK")]}
  if a!=b:raise ValueError("Candidate and blank pad schedules differ")
 return by,hashlib.sha256(raw).hexdigest(),next(iter(origin)),len(rs)
def analyze(path):
 by,digest,origin,nrows=parse(path)
 entries=[]
 for (pair,rep,sample),values in sorted(by.items()):
  order=sorted(values,key=lambda r:r["pad_loss_db"])
  x=np.array([r["pad_loss_db"] for r in order])
  y=np.array([r["spur_raw_rx_dbm"] for r in order])
  u=np.array([r["spur_uncertainty_db"] for r in order])
  f=slope(x,y,u)
  s=f["slope_db_per_db"]
  if abs(s+1)<=.25:kind="PRE_RECEIVER_SPUR_SCALING_COMPATIBLE"
  elif abs(s+3)<=.45:kind="CUBIC_RECEIVER_IM3_SCALING_COMPATIBLE"
  else:kind="OTHER_OR_INTERFERING_BEHAVIOR_REVIEW_REQUIRED"
  entries.append({"pair":pair,"replicate":rep,"sample":sample,
                  "classification":kind,**f,
                  "receiver_im3_exclusion_proven":False})
 return {"created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
         "source_csv_sha256":digest,"source_origin":origin,"data_rows":nrows,
         "results":entries,"novel_physics_demonstrated":False,"discovery_gate":"BLOCKED",
         "limitations":[
          "Only within-campaign raw uncorrected receiver readings are valid; logarithmic display amplitude normalization can alter slopes",
          "A -1 dB/dB scaling is compatible with pre-receiver DUT spurs AND source/combiner spurs, not necessarily sample physics",
          "A -3 dB/dB scaling is compatible with cubic receiver IM3 only in weak, unsaturated matched-tone conditions",
          "Coherent sums of receiver and DUT spurs can interfere, yielding non-integer apparent slopes",
          "Source loading, match, effective attenuation, phase, temperature, noise floor and pad calibration must be independently checked",
          "At least three independent sample-vs-blank sessions are required; instrument IDs are not authenticated",
          "Anomalous slope and power nonclosure are investigation triggers, not evidence of a new force"
         ]}
def main():
 p=argparse.ArgumentParser();p.add_argument("--csv",required=True);p.add_argument("--out",required=True)
 a=p.parse_args();r=analyze(pathlib.Path(a.csv))
 out=pathlib.Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(r,indent=2)+"\n")
 print(json.dumps({"rows":r["data_rows"],"classes":collections.Counter(v["classification"] for v in r["results"]),"discovery":False}))
if __name__=="__main__":main()

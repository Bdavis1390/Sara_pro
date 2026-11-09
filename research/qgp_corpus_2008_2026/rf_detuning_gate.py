#!/usr/bin/env python3
"""Classify apparent RF spectral peaks by perturbative source-detuning signatures.
Data-only diagnostic. Does NOT certify an anomalous force or experimental authenticity.
"""
import argparse, collections, csv, datetime, hashlib, json, math, pathlib
import numpy as np
from rf_intermod_prior import PAIRS, products

COLUMNS={"pair_id","sample_type","detune_id","f_low_hz","f_high_hz",
         "observed_peak_hz","frequency_uncertainty_hz","instrument_id",
         "calibration_id","data_origin"}
SAMPLES={"CANDIDATE","BLANK"}
ORIGINS={"SYNTHETIC_TEST","MEASURED_UNVERIFIED"}
def validate_and_group(path):
 raw=path.read_bytes()
 if len(raw)>2_000_000:raise ValueError("Input CSV size exceeds 2 MB; split acquisition")
 reader=csv.DictReader(raw.decode("utf-8-sig").splitlines())
 if not COLUMNS.issubset(set(reader.fieldnames or [])):
  raise ValueError("Required CSV fields absent")
 rows=list(reader)
 if not rows:raise ValueError("Empty source")
 origin={r["data_origin"] for r in rows}
 if len(origin)!=1 or not origin.issubset(ORIGINS):
  raise ValueError("Explicit uniform data_origin required")
 group=collections.defaultdict(dict)
 for r in rows:
  pair=r["pair_id"]
  if pair not in PAIRS:raise ValueError("Unsupported pair")
  s=r["sample_type"]
  if s not in SAMPLES:raise ValueError("Unsupported sample label")
  if not all(r[c] for c in COLUMNS):raise ValueError("Missing source field")
  if not r["calibration_id"].startswith("CAL-"):raise ValueError("Calibration ID absent")
  for k in ("f_low_hz","f_high_hz","observed_peak_hz","frequency_uncertainty_hz"):
   r[k]=float(r[k])
   if not math.isfinite(r[k]):raise ValueError("Nonfinite measurement")
  if not (0<r["f_low_hz"]<r["f_high_hz"]<1e11):
   raise ValueError("Invalid source frequencies")
  peak,err=r["observed_peak_hz"],r["frequency_uncertainty_hz"]
  if not (0<peak<1e11 and 0<err<=1e7 and err/peak<.0005):
   raise ValueError("Invalid peak or precision")
  reflo,refhi=PAIRS[pair]
  if abs(r["f_low_hz"]-float(reflo)*1e9)>1.1e7 or abs(r["f_high_hz"]-float(refhi)*1e9)>1.1e7:
   raise ValueError("Detuning beyond ±11 MHz per source; separate calibration required")
  key=(pair,s,r["detune_id"])
  if key in group:raise ValueError("Duplicate detuning step: "+str(key))
  group[key]=r
 if len(group)!=len(rows):raise ValueError("Duplicate rows")
 bypair=collections.defaultdict(lambda:collections.defaultdict(list))
 for (pair,s,step),r in group.items():bypair[pair][s].append(r)
 for pair, samples in bypair.items():
  if set(samples)!=SAMPLES:raise ValueError("Candidate and blank both required")
  seq={}
  for sample, rs in samples.items():
   if len(rs)<6:raise ValueError("At least six two-dimensional detuning steps required")
   low=np.array([r["f_low_hz"] for r in rs])
   high=np.array([r["f_high_hz"] for r in rs])
   sigma=np.array([r["frequency_uncertainty_hz"] for r in rs])
   if len(set(low))<3 or len(set(high))<3:raise ValueError("Both inputs need 3+ distinct detunings")
   A=np.column_stack((low-np.mean(low),high-np.mean(high)))
   if np.linalg.matrix_rank(A,tol=1)>2 or np.linalg.matrix_rank(A,tol=1)<2:
    raise ValueError("Source changes are collinear; both tones must vary independently")
   if np.ptp(low)<4*max(sigma) or np.ptp(high)<4*max(sigma):
    raise ValueError("Frequency detuning smaller than instrument uncertainty")
   seq[sample]={r["detune_id"]:(r["f_low_hz"],r["f_high_hz"]) for r in rs}
  if seq["CANDIDATE"]!=seq["BLANK"]:
   raise ValueError("Candidate and blank need the same source-detuning schedule")
 return bypair,hashlib.sha256(raw).hexdigest(),next(iter(origin)),len(rows)

def goodness(observed,pred,sig,fit_parameters=0):
 z=(observed-pred)/sig
 return {"chi2":float(np.dot(z,z)),
         "reduced_chi2":float(np.dot(z,z)/max(1,len(z)-fit_parameters)),
         "maximum_standardized_residual":float(np.max(np.abs(z))),
         "rms_standardized_residual":float(np.sqrt(np.mean(z*z)))}

def classify(rs,pair):
 rs=sorted(rs,key=lambda x:x["detune_id"])
 lo=np.array([r["f_low_hz"] for r in rs]);hi=np.array([r["f_high_hz"] for r in rs])
 obs=np.array([r["observed_peak_hz"] for r in rs])
 sig=np.array([r["frequency_uncertainty_hz"] for r in rs])
 model=[]
 for prod in products(pair,3):
  m,n=prod["m_low"],prod["n_high"]
  predicted=np.abs(m*lo+n*hi)
  check=goodness(obs,predicted,sig)
  model.append({"m_low":m,"n_high":n,"order":prod["order"],
                "type":prod["type"],"expected_freq_GHz":prod["frequency_GHz"],
                **check})
 best=min(model,key=lambda x:x["chi2"])
 fixed=float(np.sum(obs/sig**2)/np.sum(1/sig**2))
 fixed_eval=goodness(obs,np.repeat(fixed,len(obs)),sig,1)
 standard_ok=(best["maximum_standardized_residual"]<4 and best["rms_standardized_residual"]<2.5)
 fixed_ok=(fixed_eval["maximum_standardized_residual"]<4 and fixed_eval["rms_standardized_residual"]<2.5)
 if standard_ok and fixed_ok:label="AMBIGUOUS_MIXING_OR_STATIC_LINE"
 elif standard_ok:label="CONSISTENT_WITH_STANDARD_FREQUENCY_MIXING"
 elif fixed_ok:label="CONSISTENT_WITH_FIXED_FREQUENCY_INTERFERENCE"
 else:label="UNMATCHED_LIMITED_CATALOG_REVIEW_REQUIRED"
 return {"measurements":len(rs),"classification":label,
         "best_standard_model":best,"best_fixed_frequency_hz":fixed,
         "fixed_frequency_diagnostic":fixed_eval,
         "diagnostic_threshold":"max |residual / supplied frequency sigma| <4 AND RMS <2.5",
         "frequency_only":True}

def analyze(path):
 groups,digest,origin,nrows=validate_and_group(path)
 out=[]
 for pair, samples in sorted(groups.items()):
  candidate=classify(samples["CANDIDATE"],pair)
  blank=classify(samples["BLANK"],pair)
  out.append({"pair_id":pair,"candidate":candidate,"blank":blank,
              "same_classification":candidate["classification"]==blank["classification"],
              "claim":"NO_PHYSICAL_DISCOVERY_INFERABLE_FROM_FREQUENCY_TRACKING_ALONE"})
 return {"created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
         "file_sha256":digest,"rows":nrows,"origin":origin,
         "synthetic":origin=="SYNTHETIC_TEST",
         "pairs":out,"discovery_gate":"BLOCKED",
         "limitations":[
          "Frequency-only data, not a calibrated power-and-phase transfer-function measurement",
          "The source powers and receiver frequency-spur baselines are not supplied",
          "Receiver-generated nonlinear mixing follows exactly the same input-detuning pattern as candidate-material mixing",
          "Only integer mixing terms of order <=3 are enumerated; higher harmonics and complex responses remain possible",
          "Other physical resonances or fixed external interference can exist; unmatched does not mean new physics",
          "Frequency uncertainty is user-declared, not authenticated against a calibration record",
          "No independent replication, blind controls or conservation-law closure"
         ]}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--csv",required=True)
 p.add_argument("--out",required=True)
 a=p.parse_args()
 v=analyze(pathlib.Path(a.csv))
 path=pathlib.Path(a.out);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(v,indent=2)+"\n")
 print(json.dumps({"file_sha256":v["file_sha256"],"pair_results":[{"pair":r["pair_id"],"candidate":r["candidate"]["classification"],"blank":r["blank"]["classification"]} for r in v["pairs"]],
                  "new_physics":False}))
if __name__=="__main__":main()

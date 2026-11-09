#!/usr/bin/env python3
"""Complex RF source-phase-cycle gate, data-only and NON-DISCOVERY.
Fits conventional source-locked m*phi_lo+n*phi_hi mixing and fixed receiver spur.
No underlying hardware data authenticity, no new material effect certified.
"""
import argparse,collections,csv,datetime,hashlib,json,math,pathlib
import numpy as np
SIGNS={"WS-RF-001":(-2,1),"WS-RF-002":(-1,2),"WS-RF-003":(-1,2)}
TYPES={"CANDIDATE","BLANK","KNOWN_NONLINEAR_REFERENCE"}
ORIGINS={"SYNTHETIC_TEST","MEASURED_UNVERIFIED"}
REQUIRED={"experiment_id","pair_id","replicate_id","sample_type",
"phase_low_rad","phase_high_rad","iq_real_v","iq_imag_v","iq_sigma_v",
"calibration_id","reference_plane_id","receiver_id","source_state_id",
"data_origin"}
def rows_by_group(path):
 raw=path.read_bytes()
 if len(raw)>2_000_000:raise ValueError("CSV >2 MB")
 rd=csv.DictReader(raw.decode("utf-8-sig").splitlines())
 if not REQUIRED.issubset(set(rd.fieldnames or [])):
  raise ValueError("Missing required complex-phase columns")
 rows=list(rd)
 if not rows:raise ValueError("Empty phase dataset")
 origin={r["data_origin"] for r in rows}
 if len(origin)!=1 or not origin.issubset(ORIGINS):
  raise ValueError("Mixed/unknown data origin")
 grouped=collections.defaultdict(list)
 for r in rows:
  if any(not str(r[k]).strip() for k in REQUIRED):
   raise ValueError("Missing required data field")
  if r["pair_id"] not in SIGNS or r["sample_type"] not in TYPES:
   raise ValueError("Unsupported pair or sample identity")
  if not r["calibration_id"].startswith("CAL-"):
   raise ValueError("Missing calibration reference")
  if r["data_origin"]=="MEASURED_UNVERIFIED" and "SYNTH" in r["calibration_id"]:
   raise ValueError("Synthetic certificate not acceptable for declared measurements")
  for k in ("phase_low_rad","phase_high_rad","iq_real_v","iq_imag_v","iq_sigma_v"):
   r[k]=float(r[k])
   if not math.isfinite(r[k]):raise ValueError("Nonfinite phase or IQ")
  if not (0<r["iq_sigma_v"]<=1 and
      -1e3<r["iq_real_v"]<1e3 and -1e3<r["iq_imag_v"]<1e3):
   raise ValueError("Unsupported IQ or uncertainty range")
  if not (0<=r["phase_low_rad"]<2*math.pi+1e-9 and 0<=r["phase_high_rad"]<2*math.pi+1e-9):
   raise ValueError("Phases must be on [0,2pi)")
  grouped[(r["pair_id"],r["replicate_id"],r["sample_type"])].append(r)
 for key,rows in grouped.items():
  if len(rows)<16:raise ValueError("Require complete 4x4 low/high phase cycle")
  combos={(round(r["phase_low_rad"],6),round(r["phase_high_rad"],6)) for r in rows}
  if len(combos)!=len(rows):raise ValueError("Duplicate phase cycle point")
  if len({p[0] for p in combos})<4 or len({p[1] for p in combos})<4:
   raise ValueError("At least four independent phase settings on each tone")
  if len(combos)!=(len({x[0] for x in combos})*len({x[1] for x in combos})):
   raise ValueError("Full two-tone factorial phase cycle required")
  if len({r["receiver_id"] for r in rows})!=1 or len({r["calibration_id"] for r in rows})!=1:
   raise ValueError("Receiver/calibration unstable within cycle")
 reps=collections.defaultdict(dict)
 for (pair,rep,typ),rows in grouped.items():reps[(pair,rep)][typ]=rows
 for key,types in reps.items():
  if set(types)!=TYPES:raise ValueError("Candidate, blank and known nonlinear reference all mandatory")
  schedules=[sorted((round(r["phase_low_rad"],6),round(r["phase_high_rad"],6)) for r in rs) for rs in types.values()]
  if not all(x==schedules[0] for x in schedules):raise ValueError("Matched phase schedules absent")
  for field in ("receiver_id","calibration_id","reference_plane_id","source_state_id"):
   vals={r[field] for rows in types.values() for r in rows}
   if len(vals)!=1:raise ValueError("Mismatched instrument/reference/source-state "+field)
 counts=collections.Counter(pair for pair,rep in reps)
 if any(v<3 for v in counts.values()):raise ValueError("3+ independent runs per pair required")
 return grouped,hashlib.sha256(raw).hexdigest(),next(iter(origin)),sum(len(v) for v in grouped.values()),len(reps)

def fit_phase(rs,coeff):
 lo=np.array([r["phase_low_rad"] for r in rs])
 hi=np.array([r["phase_high_rad"] for r in rs])
 z=np.array([complex(r["iq_real_v"],r["iq_imag_v"]) for r in rs])
 s=np.array([r["iq_sigma_v"] for r in rs])
 m,n=coeff
 X=np.column_stack([np.exp(1j*(m*lo+n*hi)),np.ones(len(z),complex)])
 weighted=X/s[:,None]
 amps=np.linalg.lstsq(weighted,z/s,rcond=None)[0]
 resid=z-X@amps
 chi=float(np.sum(abs(resid/s)**2))
 # Residual classification is descriptive only; real IQ calibration covariance omitted.
 amplitude,static=amps
 scatter=float(np.sqrt(np.mean(abs(resid)**2)))
 return {"source_locked_re_v":float(amplitude.real),
         "source_locked_im_v":float(amplitude.imag),
         "source_locked_abs_v":float(abs(amplitude)),
         "source_locked_arg_rad":float(np.angle(amplitude)),
         "static_spur_re_v":float(static.real),
         "static_spur_im_v":float(static.imag),
         "static_spur_abs_v":float(abs(static)),
         "noise_normalized_residual_rms":float(np.sqrt(np.mean(abs(resid/s)**2))),
         "iq_residual_rms_v":scatter,
         "fit_chi2_uncorrelated_IQ_units":chi,
         "model_kind":f"STANDARD_MIXING_PHASE_{m:+d}_{n:+d}_PLUS_STATIC"}
def analyze(path):
 groups,digest,origin,nrows,nreps=rows_by_group(path)
 data=collections.defaultdict(dict)
 for (pair,rep,typ),rows in sorted(groups.items()):
  data[(pair,rep)][typ]=fit_phase(rows,SIGNS[pair])
 results=[]
 for (pair,rep),types in sorted(data.items()):
  cand=complex(types["CANDIDATE"]["source_locked_re_v"],types["CANDIDATE"]["source_locked_im_v"])
  blank=complex(types["BLANK"]["source_locked_re_v"],types["BLANK"]["source_locked_im_v"])
  ref=complex(types["KNOWN_NONLINEAR_REFERENCE"]["source_locked_re_v"],types["KNOWN_NONLINEAR_REFERENCE"]["source_locked_im_v"])
  candidate_excess=cand-blank
  nuisance_ratio=abs(blank)/max(abs(cand),1e-30)
  if all(v["noise_normalized_residual_rms"]<4 for v in types.values()):
   label="CONVENTIONAL_PHASE_SIGNATURE_FIT_ACCEPTABLE"
  else:label="UNMODELED_PHASE_RESPONSE_REQUIRES_ARTIFACT_REVIEW"
  results.append({"pair_id":pair,"replicate_id":rep,
    "fit_type":label,"sample_source_locked_minus_blank_re_v":float(candidate_excess.real),
    "sample_source_locked_minus_blank_im_v":float(candidate_excess.imag),
    "sample_source_locked_minus_blank_abs_v":float(abs(candidate_excess)),
    "blank_source_locked_fraction_of_candidate":float(nuisance_ratio),
    "known_nonlinear_reference_detected":bool(abs(ref)>0),
    "sample_effect_may_be_standard_nonlinearity":True,
    "receiver_source_spur_remains_possible":True,
    "components":types})
 return {
   "created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
   "source_csv_sha256":digest,"rows":nrows,"matched_sessions":nreps,
   "data_origin":origin,"synthetic_test":origin=="SYNTHETIC_TEST",
   "source_phase_relation":"phi_spur = m*phi_low + n*phi_high + phi_sample_or_receiver",
   "results":results,"discovery_gate":"BLOCKED",
   "novel_physics_demonstrated":False,
   "limitations":[
    "Measured IQ and phase references, calibration IDs and phase source settings are self-reported, not authenticated",
    "Source/combiner/receiver nonlinearity can track precisely the same m,n phases as a real nonlinear sample",
    "A complex phase relation cannot localize the nonlinear element or establish microscopic material physics",
    "Global phase reference plane, IQ imbalance and source loading should be independently calibrated",
    "Unmodeled phase residuals can come from harmonics, drift, mixer compression, aliases or wrong uncertainties",
    "Quantitative uncertainty in complex sample-minus-blank susceptibility needs independent sessions and full covariance",
    "Only phase cycles collected on a qualified shielded bench, using blinded samples and full power accounting, can become physical evidence"
   ]}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--csv",required=True)
 p.add_argument("--out",required=True)
 a=p.parse_args()
 obj=analyze(pathlib.Path(a.csv))
 dest=pathlib.Path(a.out);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(obj,indent=2)+"\n")
 print(json.dumps({"origin":obj["data_origin"],"rows":obj["rows"],
   "sessions":obj["matched_sessions"],"fits":[{"pair":x["pair_id"],"rep":x["replicate_id"],
   "excess_V":x["sample_source_locked_minus_blank_abs_v"],"state":x["fit_type"]} for x in obj["results"][:4]],
   "new_physics":False}))
if __name__=="__main__":main()

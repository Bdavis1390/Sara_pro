#!/usr/bin/env python3
"""Falsifiable zero-fit ideal SERIES versus SHUNT two-port topology diagnostic.
Real data are EXTERNAL Zenodo 20186567, not our own measurements.
Reference-differenced residuals are NOT full fixture deembedding or significance.
"""
import argparse,datetime,hashlib,json,pathlib
import numpy as np
from analyze_terrameta_measured_rf import read_s2p,classify

BANDS=[(0.,10.),(10.,20.),(20.,40.),(40.,80.),(80.,120.),(120.,160.1)]
REFERENCE_NAMES=("02_THRU_1.S2P","02_THRU_2.S2P")
def compare(S,T,frequency_hz,bands=BANDS):
 if S.shape!=T.shape:raise ValueError("Different measured grids")
 a=S[:,0,0];b=S[:,1,0];ta=T[:,0,0];tb=T[:,1,0]
 # Lumped ideal series: S11+S21=1. Lumped ideal shunt: S21-S11=1.
 # Reference subtraction removes SOME shared fixture structure but
 # is not network-cascade deembedding of two physical half-fixtures.
 rs=np.abs((a+b)-(ta+tb))
 rh=np.abs((b-a)-(tb-ta))
 results=[]
 for lo,hi in bands:
  mask=(frequency_hz>=lo*1e9)&(frequency_hz<hi*1e9)
  if not mask.any():continue
  ser=float(np.median(rs[mask]));sh=float(np.median(rh[mask]))
  results.append({"band_GHz":[lo,hi],"points":int(np.sum(mask)),
    "median_series_identity_difference_from_thru":ser,
    "median_shunt_identity_difference_from_thru":sh,
    "shunt_to_series_median_ratio":float(sh/max(ser,1e-15)),
    "comparison":"REFERENCE_DIFFERENCED_ZERO_FIT_NOT_DEEMBEDDED"})
 return results
def analyze(root):
 root=pathlib.Path(root)
 manifest=json.loads((root.parent/"terrameta_local_manifest.json").read_text())
 source={r["filename"]:r for r in manifest["raw_s2p_files"]}
 raw={}
 for name,entry in source.items():
  p=root/name;b=p.read_bytes()
  if hashlib.sha256(b).hexdigest()!=entry["local_sha256"]:
   raise ValueError("Measured-source checksum mismatch: "+name)
  raw[name]=read_s2p(p)
 out=[]
 for name,(frequency,S) in sorted(raw.items()):
  identity=classify(name)
  if identity["type"]!="MEMRISTOR":continue
  refs=[]
  for ref in REFERENCE_NAMES:
   f,T=raw[ref]
   if not np.allclose(f,frequency,atol=1,rtol=0):
    raise RuntimeError("Nonaligned grids")
   bands=compare(S,T,frequency)
   refs.append({"thru_reference":ref,"by_frequency":bands})
  first_band=[r["by_frequency"][0] for r in refs]
  out.append({"device_file":name,**identity,
    "reference_comparisons":refs,
    "first_10_GHz_series_residual_median_over_refs":float(np.median([x["median_series_identity_difference_from_thru"] for x in first_band])),
    "first_10_GHz_shunt_residual_median_over_refs":float(np.median([x["median_shunt_identity_difference_from_thru"] for x in first_band])),
    "model_diagnostic":"SERIES_IDENTITY_CLOSER_THAN_SHUNT" if all(x["median_series_identity_difference_from_thru"] < x["median_shunt_identity_difference_from_thru"] for x in first_band) else "AMBIGUOUS_REVIEW"})
 return {"created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source_record":manifest["source_url"],"source_doi":manifest["source_doi"],
    "data_provenance":"EXTERNAL_LAB_MEASURED_RAW_CHECKSUMS_VERIFIED_LOCALLY",
    "reference_labs_claimed_calibration":"Publisher reports LRRM-calibrated VNA; independent uncertainty certificates not available",
    "topology_identities":{
      "series":"S11+S21=1 for ideal lumped series Z between matched ports",
      "shunt":"S21-S11=1 for ideal lumped shunt Y between matched ports"},
    "comparison_domain":"Complex S matrices, broadband direct source measurements, 2 on-substrate THRU references",
    "device_state_results":out,
    "all_measured_device_states_better_series_first_10GHz":bool(all(r["model_diagnostic"]=="SERIES_IDENTITY_CLOSER_THAN_SHUNT" for r in out)),
    "limitations":[
      "This is retrospective state-dependent linear two-port behavior, NOT a nonlinear mixing or new-physics measurement",
      "Ref subtracting algebraic identities does not replace physically correct multiport/electrical-delay deembedding",
      "Known series/shunt topologies are competing conventional descriptions, not competing theories of new interactions",
      "Device reference planes, parasitics, calibration covariance and contact geometry are not independently certified",
      "A smaller median complex residual is not a statistical significance or validated fitted resistance/capacitance",
      "The original measurements have ~200.25 MHz grid spacing; cannot resolve 2.56 MHz features",
      "Raw third-party files remain local because reuse license not independently confirmed"],
    "new_physics":False}
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--data-dir",required=True);ap.add_argument("--out",required=True)
 a=ap.parse_args()
 j=analyze(a.data_dir)
 o=pathlib.Path(a.out);o.parent.mkdir(parents=True,exist_ok=True)
 o.write_text(json.dumps(j,indent=2)+"\n");o.chmod(0o600)
 print(json.dumps({"states":len(j["device_state_results"]),
     "all_prefer_series_under_descriptive_metric":j["all_measured_device_states_better_series_first_10GHz"],
     "reference_sensitivity":[{"file":r["device_file"],"series_residual":round(r["first_10_GHz_series_residual_median_over_refs"],6),
       "shunt_residual":round(r["first_10_GHz_shunt_residual_median_over_refs"],6)}
       for r in j["device_state_results"]],"new_physics":False}))
if __name__=="__main__":main()

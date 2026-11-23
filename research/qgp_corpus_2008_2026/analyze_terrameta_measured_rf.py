#!/usr/bin/env python3
"""WorldShepherd analysis of third-party measured S2P from Zenodo 20186567.
Only passive linear two-port metrics; no claim of WorldShepherd laboratory work,
nonlinear mixing, source-pair coupling, or new physics. Raw inputs stay local.
"""
import argparse,datetime,hashlib,json,math,pathlib,re
import numpy as np

TARGETS_GHZ=(.242,.396,.953,.993,1.590,1.59256,3.96993,9.53242)
REFERENCE_FILES={"01_ISS_THRU.S2P","02_THRU_1.S2P","02_THRU_2.S2P"}
def read_s2p(path):
 raw=path.read_text(encoding="utf-8-sig")
 data=[];header=None
 for line in raw.splitlines():
  s=line.strip()
  if not s or s.startswith("!"):continue
  if s.startswith("#"):
   if header is not None:raise ValueError("More than one Touchstone header")
   header=[p.lower() for p in s.split()]
   continue
  parts=s.replace("D","E").replace("d","e").split()
  if len(parts)!=9:raise ValueError(f"Expected 9 RI columns in {path.name}: {len(parts)}")
  data.append([float(x) for x in parts])
 if header!=["#","hz","s","ri","r","50"]:
  raise ValueError(f"Unsupported Touchstone data format: {header}")
 z=np.asarray(data,float)
 if z.shape!=(800,9):raise ValueError("Unexpected raw measurement grid shape")
 f=z[:,0]
 if np.any(np.diff(f)<=0) or abs(f[0]-70_000)>1 or abs(f[-1]-160e9)>1:
  raise ValueError("Missing/unsorted frequency grid")
 if not np.allclose(np.diff(f),np.median(np.diff(f)),rtol=1e-7,atol=2):
  raise ValueError("Nonuniform frequency grid: separate interpolation treatment required")
 if np.any(~np.isfinite(z)):raise ValueError("NaN or Inf in raw measurements")
 # Touchstone convention: f, S11, S21, S12, S22 as RI pairs
 S=np.empty((800,2,2),dtype=complex)
 S[:,0,0]=z[:,1]+1j*z[:,2]
 S[:,1,0]=z[:,3]+1j*z[:,4]
 S[:,0,1]=z[:,5]+1j*z[:,6]
 S[:,1,1]=z[:,7]+1j*z[:,8]
 return f,S

def interp_complex(freq,S,point):
 if point<freq[0] or point>freq[-1]:raise ValueError("Target outside measured span")
 flat=S.reshape(len(freq),4)
 re=np.array([np.interp(point,freq,flat[:,i].real) for i in range(4)])
 im=np.array([np.interp(point,freq,flat[:,i].imag) for i in range(4)])
 k=int(np.clip(np.searchsorted(freq,point),1,len(freq)-1))
 return (re+1j*im).reshape((2,2)),(float(freq[k-1]),float(freq[k]))

def classify(name):
 if name in REFERENCE_FILES:return {"type":"THRU_REFERENCE","device_id":None,"state":None,"nominal_DC_Ohm":None}
 m=re.fullmatch(r"(03|04)[a-z]_MEMR_([12])_(HRS|LRS)_([0-9]+(?:p[0-9]+)?)(k?)Ohm\.S2P",name)
 if m is None:raise ValueError("Unrecognized device label: "+name)
 _,device,state,r,k=m.groups()
 resistance=float(r.replace("p","."))*(1000 if k else 1)
 return {"type":"MEMRISTOR","device_id":int(device),"state":state,"nominal_DC_Ohm":resistance}

def db(x):return 20*math.log10(max(float(abs(x)),1e-20))

def analyze(rawdir):
 root=pathlib.Path(rawdir)
 manifest=json.loads((root.parent/"terrameta_local_manifest.json").read_text())
 files=manifest["raw_s2p_files"]
 if len(files)!=12:raise RuntimeError("Expected all 12 publisher source files")
 output=[]
 frequency_grid=None
 for entry in files:
  p=root/entry["filename"]
  raw=p.read_bytes()
  if len(raw)!=entry["size"] or hashlib.sha256(raw).hexdigest()!=entry["local_sha256"]:
   raise ValueError("Local source file failed SHA-256 revalidation")
  freq,S=read_s2p(p)
  if frequency_grid is None:frequency_grid=freq
  if not np.allclose(freq,frequency_grid,rtol=0,atol=1.):raise ValueError("Different measurement frequency grids beyond 1 Hz textual rounding")
  singular=np.linalg.svd(S,compute_uv=False)[:,0]
  reciprocity=np.abs(S[:,1,0]-S[:,0,1])
  power_from_port1=abs(S[:,0,0])**2+abs(S[:,1,0])**2
  points=[]
  for f_GHz in TARGETS_GHZ:
   pred,bracket=interp_complex(freq,S,f_GHz*1e9)
   magn=abs(pred[1,0])
   points.append({"requested_frequency_GHz":f_GHz,
     "is_directly_measured_at_target":bool(np.any(np.isclose(freq,f_GHz*1e9,rtol=0,atol=1))),
     "interpolation_bracket_GHz":[x/1e9 for x in bracket],
     "bracket_width_MHz":(bracket[1]-bracket[0])/1e6,
     "S21_dB_complex_linear_interp":db(magn),
     "S11_dB_complex_linear_interp":db(pred[0,0]),
     "S21_phase_rad_complex_linear_interp":float(np.angle(pred[1,0])),
     "port1_reflected_plus_transmitted_normalized":float(abs(pred[0,0])**2+abs(pred[1,0])**2),
     "interpolation_uncertainty":"NOT_ESTABLISHED"})
  output.append({"file":p.name,**classify(p.name),
   "raw_sha256":entry["local_sha256"],"rows":len(freq),
   "largest_singular_value":float(np.max(singular)),
   "passivity_flag_gt_1p02_count":int(np.sum(singular>1.02)),
   "passivity_flag_gt_1p001_count":int(np.sum(singular>1.001)),
   "port1_apparent_power_gt_1p02_count":int(np.sum(power_from_port1>1.02)),
   "max_reciprocity_mismatch_abs":float(np.max(reciprocity)),
   "targets":points})
 device_comparisons=[]
 for device in (1,2):
  d=[r for r in output if r["device_id"]==device]
  highs=[r for r in d if r["state"]=="HRS"];lows=[r for r in d if r["state"]=="LRS"]
  if not highs or not lows:raise RuntimeError("No both-state contrasts")
  for index,fghz in enumerate(TARGETS_GHZ):
   h=[r["targets"][index]["S21_dB_complex_linear_interp"] for r in highs]
   l=[r["targets"][index]["S21_dB_complex_linear_interp"] for r in lows]
   device_comparisons.append({"device_id":device,"frequency_GHz":fghz,
    "HRS_state_count":len(h),"LRS_state_count":len(l),
    "median_HRS_S21_dB":float(np.median(h)),
    "median_LRS_S21_dB":float(np.median(l)),
    "LRS_minus_HRS_median_S21_dB":float(np.median(l)-np.median(h)),
    "HRS_range_dB":[min(h),max(h)],"LRS_range_dB":[min(l),max(l)],
    "critical_caveat":"Configuration snapshots and DC states are not independent lab replicate uncertainty distributions"})
 result={
   "created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
   "source_doi":manifest["source_doi"],"source_record":manifest["source_url"],
   "data_provenance":"EXTERNAL_MEASURED_BUT_SCIENTIFIC_REUSE_AND_CALIBRATION_METADATA_NEED_REVIEW",
   "actual_measurements_derived_from":12,
   "worldshepherd_original_measurements":0,
   "instrument":manifest["laboratory_reported_instrument"],
   "raw_license":"UNVERIFIED_NO_RAW_REDISTRIBUTION",
   "raw_sha256_reverified":True,
   "frequency_span_Hz":[float(frequency_grid[0]),float(frequency_grid[-1])],
   "freq_sample_count":len(frequency_grid),
   "frequency_spacing_MHz":float(np.median(np.diff(frequency_grid))/1e6),
   "historical_near_coincidence_separation_MHz":2.56,
   "grid_spacing_over_near_coincidence_separation":float(np.median(np.diff(frequency_grid))/2.56e6),
   "files":output,
   "device_state_comparisons":device_comparisons,
   "interpretation":[
    "These are genuine reported passive linear two-port VNA measurements of memristor states from another research group.",
    "HRS and LRS reflect state-dependent response within ordinary microwave circuit physics, not new physical interactions.",
    "Single-tone linear S-parameters cannot measure cubic two-tone intermodulation or cross-frequency energy exchange.",
    "Input frequencies are interpolated at ~200.25 MHz point spacing. No 2.56 MHz doublet could be resolved by this dataset.",
    "Simple interpolation of complex S does not provide measurement error bars; no independent calibration certificate or full covariance was supplied.",
    "A singular value >1 in measured S may reflect calibration/noise/fixture effects; it is not energy creation.",
    "Nonlinear device response and antenna characteristic modes need distinct independent measurements, not invented from two-port S.",
    "Broadband S21 differences may support device benchmark and conventional response modeling but not original physics claims."
   ],
   "original_novel_physics_demonstrated":False}
 return result

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--data-dir",required=True);ap.add_argument("--out",required=True)
 a=ap.parse_args()
 result=analyze(a.data_dir)
 path=pathlib.Path(a.out);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(result,indent=2)+"\n");path.chmod(0o600)
 print(json.dumps({
  "file_count":len(result["files"]),
  "measured_rows_per_file":result["freq_sample_count"],
  "max_freq_grid_spacing_MHz":round(result["frequency_spacing_MHz"],4),
  "states":[(r["device_id"],r["state"],r["nominal_DC_Ohm"]) for r in result["files"] if r["type"]=="MEMRISTOR"],
  "nonpassive_gt2pc":{r["file"]:r["passivity_flag_gt_1p02_count"] for r in result["files"]},
  "summary_contrasts":[{k:round(r[k],3) if isinstance(r[k],float) else r[k] for k in ("device_id","frequency_GHz","LRS_minus_HRS_median_S21_dB")} for r in result["device_state_comparisons"] if r["frequency_GHz"] in (3.96993,9.53242)],
  "new_physics":False},sort_keys=True))
if __name__=="__main__":main()

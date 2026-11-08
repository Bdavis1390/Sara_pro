#!/usr/bin/env python3
"""Independent numerical check of STAR 2026 published baryon-transport data.
This compares released model curves to released HEPData. It is NOT a new-physics discovery.
Requires numpy. No external code from the Zenodo archive is executed.
"""
import argparse,ast,csv,datetime,hashlib,io,json,math,pathlib,tarfile
import numpy as np

SOURCE_MD5="7cbf93f2e57a06bc0ed7e701d4977cb3"
def sha(b):return hashlib.sha256(b).hexdigest()
def compare(obs,model,errs,modelerrs,rho):
 stat,sys_a,sys_b=errs.T
 diag=stat**2+np.square(modelerrs)+(1-rho)*(sys_a**2+sys_b**2)
 cov=np.diag(diag)+rho*np.outer(sys_a,sys_a)+rho*np.outer(sys_b,sys_b)
 diff=obs-model
 return float(diff@np.linalg.solve(cov,diff))
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--source-dir",required=True)
 ap.add_argument("--output",required=True)
 a=ap.parse_args()
 root=pathlib.Path(a.source_dir)
 hep=root/"hepdata_154708"
 manifest=json.loads((hep/"manifest.json").read_text())
 if manifest["table_count"]!=26 or manifest["errors"]:raise RuntimeError("HEPData completeness failed")
 for entry in manifest["tables"]:
  f=hep/("table_%02d.json"%entry["id"])
  if sha(f.read_bytes())!=entry["sha256"]:raise RuntimeError("HEPData hash mismatch: "+str(f))
 dataset=json.loads((hep/"table_03.json").read_text())
 if dataset["name"]!="Figure 4":raise RuntimeError("Unexpected observable")
 rows=sorted(dataset["values"],key=lambda r:int(r["x"][0]["value"].split("-")[0]))
 x=np.array([0.5*sum(int(y.strip("%")) for y in r["x"][0]["value"].split("-")) for r in rows],float)
 obs=np.array([float(r["y"][0]["value"]) for r in rows])
 errs=np.array([[float(e["symerror"]) for e in r["y"][0]["errors"]] for r in rows])
 if x.tolist()!=[5.,15.,30.,50.,70.] or errs.shape!=(5,3):raise RuntimeError("HEPData schema unexpected")
 archive=root/"Baryon_Junction_Theoretical_curves.tar.gz"
 if hashlib.md5(archive.read_bytes()).hexdigest()!=SOURCE_MD5:raise RuntimeError("Zenodo model SHA/MD5 source mismatch")
 with tarfile.open(archive,"r:gz") as tar:
  rootp="Baryon_Junction_Theoretical_curves/BDeltaQ/"
  model_band={}
  for N in (20,47,70):
   raw=tar.extractfile(rootp+"Theory/Lc"+str(N)+".dat").read().decode()
   arr=np.array([[float(z) for z in line.split()] for line in raw.splitlines()[1:] if line.strip()])
   if arr.shape!=(9,9):raise RuntimeError("Model source shape failure")
   model_band["Trento_Lc"+str(N)]=np.interp(x,arr[:,0],arr[:,5]+arr[:,7])/np.interp(x,arr[:,0],arr[:,5]-arr[:,1])*(4/96)
  script=tar.extractfile(rootp+"PlotSysTrack.py").read().decode()
  funcs=[v for v in ast.parse(script).body if isinstance(v,ast.FunctionDef) and v.name=="GetUrQMD"]
  if len(funcs)!=1:raise RuntimeError("No single GetUrQMD source")
  dat={}
  for node in funcs[0].body:
   if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
    k=node.targets[0].id
    if k in ("x","y","yerr"):
     dat[k]=ast.literal_eval(node.value)
  if set(dat)!={"x","y","yerr"}:raise RuntimeError("Incomplete UrQMD source")
  model=np.interp(x,dat["x"],dat["y"])
  modelerr=np.interp(x,dat["x"],dat["yerr"])
 models={"Unit_ratio_reference":np.ones(len(x)), "UrQMD":model,**model_band}
 evaluations={}
 for name, values in models.items():
  me=modelerr if name=="UrQMD" else np.zeros(len(x))
  evaluations[name]={
   "predictions":np.round(values,6).tolist(),
   "diagnostic_chi2_by_correlated_sys_fraction":
    {str(rho):round(compare(obs,values,errs,me,rho),5) for rho in (0.,0.5,1.)},
   "mean_difference":float(np.mean(obs-values)),
   "model_uncertainty":"UrQMD plotting-statistical only; no full model systematic" if name=="UrQMD" else "not quantified in this check"
  }
 lo=np.minimum(models["Trento_Lc20"],models["Trento_Lc70"])
 hi=np.maximum(models["Trento_Lc20"],models["Trento_Lc70"])
 residual=np.maximum(0,np.maximum(lo-obs,obs-hi))
 evaluations["Trento_band_optimistic"]={
  "envelope_min":np.round(lo,6).tolist(),
  "envelope_max":np.round(hi,6).tolist(),
  "distance_outside_band":np.round(residual,6).tolist(),
  "caveat":"Bin-wise envelope projection is not one globally coherent physical parameter fit"
 }
 summary={"date_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "dataset":"https://www.hepdata.net/record/154708",
  "paper":"https://doi.org/10.1126/science.ads5962",
  "theory":"https://doi.org/10.5281/zenodo.19463261",
  "data_stage":"external_published_derived_not_raw",
  "measurement_type":"scaled B/DeltaQ times Delta Z/A in Ru+Ru and Zr+Zr",
  "centrality_centers_pct":x.tolist(),"measured_ratio":obs.tolist(),
  "errors_per_bin_stat_sys_nofeeddown_sys_feeddown":errs.tolist(),
  "comparison":evaluations,
  "assumptions":["No global STAR covariance matrix supplied in HEPData figure table",
    "Systematic components are modeled as either independent, 50% or fully coherent; actual correlations unknown",
    "Model curves do not span every plausible valence or junction explanation",
    "Chi-square is a descriptive diagnostic, not a new-physics discovery significance",
    "The data/model disagreement is already reported by STAR",
    "A novel mechanism requires prospectively withheld, independent test data"],
  "evidence_state":"PUBLISHED_MODEL_COMPARISON_REPRODUCED_NO_NEW_PHYSICS"
 }
 out=pathlib.Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(summary,indent=2)+"\n")
 print(json.dumps({"centrality":x.tolist(),"measured":obs.tolist(),
  "UrQMD":evaluations["UrQMD"]["predictions"],
  "chi2_diagnostics":{k:v["diagnostic_chi2_by_correlated_sys_fraction"] for k,v in evaluations.items() if "diagnostic_chi2_by_correlated_sys_fraction" in v},
  "trento_band_max":evaluations["Trento_band_optimistic"]["envelope_max"],
  "new_physics":False},sort_keys=True))
if __name__=="__main__":main()

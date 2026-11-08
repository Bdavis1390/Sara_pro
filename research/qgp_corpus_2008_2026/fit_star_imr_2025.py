#!/usr/bin/env python3
"""STAR 2025 IMR thermal-spectrum shape fit from public, derived HEPData.
Fits M^1.5 exp(-M/T) with center approximation and diagonal total errors.
Not the collaboration's bin-integrated, correlated detector-analysis fit.
"""
import argparse,datetime,hashlib,json,pathlib
import numpy as np
def sha(b):return hashlib.sha256(b).hexdigest()
def fit(M,y,sigma,tmin=.10,tmax=1.20,gridn=11001):
 T=np.linspace(tmin,tmax,gridn)
 F=np.power(M[None,:],1.5)*np.exp(-M[None,:]/T[:,None])
 W=np.square(1/sigma)
 A=np.sum(F*(y*W),axis=1)/np.sum(F**2*W,axis=1)
 chi=np.sum(np.square(y[None,:]-A[:,None]*F)*W,axis=1)
 i=int(np.argmin(chi));ok=np.flatnonzero(chi<=chi[i]+1.0)
 return {"T_MeV":round(float(T[i]*1000),3),
         "nominal_delta_chi2_1_interval_MeV":[round(float(T[ok[0]]*1000),3),round(float(T[ok[-1]]*1000),3)],
         "chi2":float(chi[i]),"dof":len(M)-2,
         "fitted_normalization":float(A[i]),"points":int(len(M))}
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--data-dir",required=True)
 ap.add_argument("--out",required=True)
 a=ap.parse_args()
 root=pathlib.Path(a.data_dir);results={}
 for table,beam in [(3,"27_GeV"),(4,"54.4_GeV")]:
  p=root/("table_%02d.json"%table)
  raw=p.read_bytes()
  obj=json.loads(raw)
  if obj.get("table_license",{}).get("name")!="CC0":raise RuntimeError("Expected CC0")
  M=[];y=[];s=[]
  for row in obj["values"]:
   mass=float(row["x"][0]["value"])
   if not 1.0<mass<2.9:continue
   dep=row["y"][0]; val=float(dep["value"])
   err=(sum(float(e["symerror"])**2 for e in dep["errors"]))**0.5
   if err<=0:raise RuntimeError("Non-positive error")
   M.append(mass);y.append(val);s.append(err)
  M=np.array(M);y=np.array(y);s=np.array(s)
  if len(M)<5:raise RuntimeError("Too few points for spectrum fit")
  primary=fit(M,y,s)
  leave_one_out={}
  for k in range(len(M)):
   mask=np.arange(len(M))!=k
   leave_one_out[str(float(M[k]))]=fit(M[mask],y[mask],s[mask])["T_MeV"]
  results[beam]={"primary":primary,"leave_one_mass_out_T_MeV":leave_one_out,
    "mass_bin_centers_GeV":M.tolist(),"data_sha256":sha(raw),
    "assumed_covariance":"diagonal of stat^2+syst^2","fit_range":"1.0<M<2.9 GeV"}
 output={"created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
         "source":"https://doi.org/10.17182/hepdata.147195",
         "paper":"https://doi.org/10.1038/s41467-025-63216-5",
         "result":results,
         "baseline_published_IMR_T_MeV":{"27_GeV":273.57,"54.4_GeV":287.3},
         "scope":"independent approximate shape fit of published derived spectra, not detector-pipeline reproduction",
         "limitations":["Bin centers rather than STAR bin-integrated theoretical template",
                        "Systematics combined diagonally, missing original covariance",
                        "No subtraction/refit of raw cocktail backgrounds",
                        "Delta-chi-square=1 intervals nominal under Gaussian assumptions",
                        "These QGP temperatures were already reported by STAR; no new physics"],
         "novel_physics":False}
 path=pathlib.Path(a.out);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(output,indent=2)+"\n")
 print(json.dumps({b:{"T":r["primary"]["T_MeV"],
                       "profile68":r["primary"]["nominal_delta_chi2_1_interval_MeV"],
                       "loo_range":(min(r["leave_one_mass_out_T_MeV"].values()),max(r["leave_one_mass_out_T_MeV"].values())),
                       "chi2":r["primary"]["chi2"],"dof":r["primary"]["dof"]}
                   for b,r in results.items()}))
 if not 180<=results["27_GeV"]["primary"]["T_MeV"]<=450:raise SystemExit(2)
 if not 180<=results["54.4_GeV"]["primary"]["T_MeV"]<=450:raise SystemExit(2)
if __name__=="__main__":main()

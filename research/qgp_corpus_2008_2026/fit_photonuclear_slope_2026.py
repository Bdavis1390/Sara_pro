#!/usr/bin/env python3
"""STAR 2026 gamma+Au rapidity slope consistency check (published-derived data).
GLS of log(net-proton yield) vs bin-centre rapidity. No original detector-data refit.
"""
import argparse,datetime,hashlib,json,pathlib
import numpy as np

def sha(raw):return hashlib.sha256(raw).hexdigest()
def fit(x,log_y,cov):
 xmat=np.column_stack([np.ones(len(x)),x])
 cix=np.linalg.solve(cov,xmat)
 bcov=np.linalg.inv(xmat.T@cix)
 beta=bcov @ xmat.T @ np.linalg.solve(cov,log_y)
 chi=float((log_y-xmat@beta) @ np.linalg.solve(cov,(log_y-xmat@beta)))
 return {"amplitude":float(np.exp(beta[0])),"slope":float(beta[1]),
         "slope_sigma_assumed":float(np.sqrt(bcov[1,1])),
         "chi2":chi,"dof":int(len(x)-2)}
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--source-dir",required=True)
 ap.add_argument("--output",required=True)
 a=ap.parse_args()
 p=pathlib.Path(a.source_dir);h=p/"hepdata_154708"
 m=json.loads((h/"manifest.json").read_text())
 for i in (1,2):
  t=next(x for x in m["tables"] if x["id"]==i)
  if sha((h/("table_%02d.json"%i)).read_bytes())!=t["sha256"]:raise RuntimeError("Checksum mismatch")
 fig2=json.loads((h/"table_01.json").read_text())
 xs=[];ys=[];stat=[];sys=[]
 for row in fig2["values"]:
  x=row["x"][0];xs.append((float(x["low"])+float(x["high"]))/2)
  yy=[y for y in row["y"] if y.get("group")==2]
  if len(yy)!=1:raise ValueError("Unexpected net-proton group")
  y=yy[0];v=float(y["value"]);d={e["label"]:float(e["symerror"]) for e in y["errors"]}
  ys.append(v);stat.append(d["Stat."]);sys.append(d["Sys."])
 xs=np.array(xs);ys=np.array(ys);stat=np.array(stat)/ys;sys=np.array(sys)/ys
 logy=np.log(ys);n=len(xs)
 estimates={}
 for rho in (0,0.5,1.0):
  cov=np.diag(stat**2+(1-rho)*sys**2)+rho*np.outer(sys,sys)+0.06**2*np.ones((n,n))
  estimates[str(rho)]=fit(xs,logy,cov)
 cov=np.diag(stat**2+sys**2)+0.06**2*np.ones((n,n))
 rng=np.random.default_rng(20261108)
 xmat=np.column_stack([np.ones(n),xs]);W=np.linalg.solve(cov,xmat)
 projector=np.linalg.inv(xmat.T@W) @ W.T
 draws=rng.multivariate_normal(logy,cov,size=3000)
 bootstrap_slopes=(projector@draws.T)[1]
 fig3=json.loads((h/"table_02.json").read_text())
 published=[]
 for row in fig3["values"]:
  lbl=row["x"][0].get("value","")
  if "Au Data Au+Au 54.4 GeV" in lbl:
   published.append({"label":lbl,"slope":float(row["y"][0]["value"]),
     "sigma":float(row["y"][0]["errors"][0]["symerror"])})
 if len(published)!=1:raise RuntimeError("Cannot locate comparator in STAR figure 3 table")
 measured=estimates["0"]
 state="COMPATIBLE_IN_APPROXIMATE_ANALYSIS" if abs(measured["slope"]-published[0]["slope"])<2*(measured["slope_sigma_assumed"]**2+published[0]["sigma"]**2)**0.5 else "REQUIRES_INVESTIGATION"
 result={"source":"https://hepdata.net/record/154708","date_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
   "slope_model":"log dN/dy = ln A + alpha * y_center",
   "published_comparator":published[0],
   "correlated_normalization_uncertainty_fraction":0.06,
   "systematic_cross_bin_correlation_scan":estimates,
   "bootstrap_rho0":{"seed":20261108,"replicates":3000,"sd":float(np.std(bootstrap_slopes,ddof=1)),
                      "range_2_5_to_97_5":np.quantile(bootstrap_slopes,[0.025,0.975]).tolist()},
   "qualifications":["Log-linear approximation; STAR fit may integrate bins and include other detector and fit details",
     "Covariance assumptions are scenarios, not measured STAR covariance",
     "No new physics claim; this checks published observations against a published model"],
   "evidence_state":state}
 path=pathlib.Path(a.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,indent=2)+"\n")
 print(json.dumps({"published":published[0],"rho0":measured,
                   "bootstrap_sigma":result["bootstrap_rho0"]["sd"],"rho0_5":estimates["0.5"],
                   "rho1_chi2_dof":estimates["1.0"]["chi2"]/estimates["1.0"]["dof"],
                   "state":state},sort_keys=True))
 if state!="COMPATIBLE_IN_APPROXIMATE_ANALYSIS":raise SystemExit(2)
if __name__=="__main__":main()

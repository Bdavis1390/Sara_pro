#!/usr/bin/env python3
"""Checks publicly released STAR HEPData tables. NOT a reproduction of STAR spectrum fits."""
import argparse, hashlib, json, math, pathlib, datetime
K_PER_MEV=11604518121.55
def sha(b): return hashlib.sha256(b).hexdigest()
def main():
 a=argparse.ArgumentParser()
 a.add_argument("--dir",required=True)
 a.add_argument("--out",required=True)
 p=a.parse_args()
 root=pathlib.Path(p.dir); manifest=json.loads((root/"manifest.json").read_text())
 counts=[]; mismatch=[]
 for t in manifest["tables"]:
  dest=root/("table_%02d.json"%t["table"])
  if not dest.exists(): mismatch.append(str(dest));continue
  raw=dest.read_bytes(); h=sha(raw)
  if h!=t.get("sha256"): mismatch.append(str(dest))
  dat=json.loads(raw)
  counts.append({"table":t["table"],"points":len(dat.get("values",[])),
                "bytes":len(raw),"license":dat.get("table_license",{}).get("name")})
 table=json.loads((root/"table_05.json").read_text())
 obs=[]
 for row in table["values"]:
  x=row["x"][0]
  mu=float(x.get("low",x.get("value")))
  for label, y in zip(("LMR","IMR"),row["y"]):
   e={v["label"]:float(v["symerror"]) for v in y["errors"]}
   v=float(y["value"])
   combined=math.hypot(e.get("stat",0),e.get("syst",0))
   obs.append({"muB_MeV":mu,"stage":label,"T_MeV":v,
               "stat_MeV":e.get("stat"),"syst_MeV":e.get("syst"),
               "quadrature_uncertainty_MeV":combined,
               "T_K":v*K_PER_MEV,"quadrature_uncertainty_K":combined*K_PER_MEV})
 groups={}
 for stage in ("LMR","IMR"):
  vals=[x for x in obs if x["stage"]==stage]
  weights=[1/x["quadrature_uncertainty_MeV"]**2 for x in vals]
  avg=sum(x["T_MeV"]*w for x,w in zip(vals,weights))/sum(weights)
  sig=math.sqrt(1/sum(weights))
  groups[stage]={"naive_inverse_variance_MeV":avg,"naive_unc_MeV":sig,
    "naive_inverse_variance_K":avg*K_PER_MEV,"warning":"Independence and correlation assumptions unverified; NOT STAR published fit or independently reproduced thermometry."}
 result={"source":"https://hepdata.net/record/147195?format=json",
         "source_paper":"https://doi.org/10.1038/s41467-025-63216-5",
         "file_sha256_mismatches":mismatch,"tables":counts,
         "individual_temperatures":obs,"naive_weighted_summary":groups,
         "state":"CHECKSUM_AND_UNIT_CONSISTENCY_ONLY",
         "not_a_full_temperature_fit":True,
         "generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
 out=pathlib.Path(p.out);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(result,indent=2)+"\n")
 print(json.dumps({"checksum_mismatches":len(mismatch),"tables":len(counts),"temperature_points":len(obs),"weighted_MeV":{k:round(v["naive_inverse_variance_MeV"],2) for k,v in groups.items()}}))
 if mismatch:raise SystemExit(2)
if __name__=="__main__":main()

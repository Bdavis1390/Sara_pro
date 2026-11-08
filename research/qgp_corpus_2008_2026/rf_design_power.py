#!/usr/bin/env python3
"""WorldShepherd RF measurement design simulation — synthetic only.
Calculates limits of exact paired sign-flip tests with multiple outputs.
Does NOT model hardware power, establish physics, or claim a measured effect.
"""
import argparse,datetime,json,math,pathlib
import numpy as np

def sign_matrix(n):
  if n<3 or n>14:raise ValueError("n must be 3..14")
  m=1<<n
  index=np.arange(m,dtype=np.uint32)[:,None]
  flips=((index>>np.arange(n,dtype=np.uint32)[None,:]) & 1).astype(np.float64)
  return flips*2-1

def exact_p_batch(Z,signs):
  # each column in Z is a synthetic independent-run vector
  obs=np.abs(Z.sum(axis=0))
  permutation_sums=np.abs(signs@Z)
  count=np.count_nonzero(permutation_sums>=obs[None,:]-1e-10,axis=0)
  return count/signs.shape[0]

def holm_adjusted(P):
  # columns are one synthetic experiment; rows are m output bands
  ordered=np.argsort(P,axis=0)
  sortedP=np.take_along_axis(P,ordered,axis=0)
  m=len(P)
  corrected=np.maximum.accumulate(sortedP*(m-np.arange(m))[:,None],axis=0)
  out=np.empty_like(P)
  np.put_along_axis(out,ordered,np.minimum(1,corrected),axis=0)
  return out

def estimate(n,d,nsim,rng,m=4):
  signs=sign_matrix(n)
  # 1 candidate output + (m-1) negative controls, including sham
  raw=np.empty((m,nsim),dtype=float)
  for j in range(m):
    v=rng.normal(loc=d if j==0 else 0.,scale=1.,size=(n,nsim))
    raw[j]=exact_p_batch(v,signs)
  adj=holm_adjusted(raw)
  return {
   "n_independent_replicates":n,
   "effect_size_mean_over_run_sd":d,
   "simulation_repetitions":nsim,
   "familywise_tested_outputs":m,
   "candidate_detection_rate":float(np.mean(adj[0]<.05)),
   "at_least_one_false_positive_rate":float(np.mean((adj[1:]<.05).any(axis=0))),
   "ideal_smallest_two_sided_raw_p":2/(2**n),
   "ideal_smallest_bonferroni_4_adjusted_p":min(1.,2*m/(2**n)),
   "a_detectable_standard_nonlinearity_is_not_new_physics":True
  }

def main():
  ap=argparse.ArgumentParser()
  ap.add_argument("--out",required=True)
  ap.add_argument("--replicates",type=int,default=400)
  ap.add_argument("--seed",type=int,default=20261108)
  a=ap.parse_args()
  if not 100<=a.replicates<=4000:ap.error("replicates must be 100..4000")
  rng=np.random.default_rng(a.seed)
  result=[]
  for n in (6,7,8,10,12):
    for effect in (0.,0.5,1.,1.5,2.):
      result.append(estimate(n,effect,a.replicates,rng,m=4))
  report={
    "date_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "state":"SIMULATED_DESIGN_SENSITIVITY_NOT_PHYSICAL_MEASUREMENT",
    "random_seed":a.seed,"simulations":result,
    "interpretation":"Four tested output regions including sham. One synthetically shifted channel, all other channels null; Holm familywise p<0.05. No instrument systematic error, correlations, drifts or power closure modeled.",
    "sample_size_note":"n=8 is mathematical minimum for ideal all-same-sign paired results with four-test Bonferroni threshold; it is not a recommended minimum for power.",
    "scientific_claim":"NONE","new_physics":False,
    "limitations":["Gaussian synthetic independent runs only","Independence and exchangeability unverified in hardware","Effect size is normalized to run-to-run standard deviation, not a physical unit","Sham rejection is a negative-control failure, not an interesting effect","No apparatus available on the tested Lenovo for actual calibrated GHz measurements"]
  }
  out=pathlib.Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
  out.write_text(json.dumps(report,indent=2)+"\n")
  print(json.dumps({"seed":a.seed,"replicates":a.replicates,
    "power_by_n":[{"n":n,"d1":round(next(x["candidate_detection_rate"] for x in result if x["n_independent_replicates"]==n and x["effect_size_mean_over_run_sd"]==1.),3),
                   "d2":round(next(x["candidate_detection_rate"] for x in result if x["n_independent_replicates"]==n and x["effect_size_mean_over_run_sd"]==2.),3)} for n in (6,7,8,10,12)],
    "discovery":False}))
if __name__=="__main__":main()

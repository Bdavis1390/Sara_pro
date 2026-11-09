#!/usr/bin/env python3
"""Exploratory post-selection calibration for 3 WorldShepherd RF frequency pairs.
Simulation is of ARBITRARY hypothetical input selection, NOT a valid physics
significance test or sample measurement. All runs deterministic, CPU bounded.
"""
import argparse, datetime, json, pathlib
import numpy as np

NOMINAL=np.array([[3.96993,9.53242],[.242,.953],[.396,.993]],dtype=float)
COEFF=np.array([[1,1],[1,-1],[2,1],[2,-1],[1,2],[1,-2]],dtype=float)

def simulate(nsamples,uniform_spread,seed,chunk=10000):
 rng=np.random.default_rng(seed)
 best=[]
 special=[]
 for start in range(0,nsamples,chunk):
  n=min(chunk,nsamples-start)
  factor=rng.uniform(1-uniform_spread,1+uniform_spread,size=(n,3,2))
  freqs=NOMINAL[None,:,:]*factor
  vals=np.abs(np.einsum("bij,kj->bik",freqs,COEFF))  # n, pair, 6 products
  minv=np.full(n,np.inf)
  for i,j in ((0,1),(0,2),(1,2)):
   v=np.min(np.abs(vals[:,i,:,None]-vals[:,j,None,:]),axis=(1,2))
   minv=np.minimum(minv,v)
  best.append(minv)
  # Signed pair1: | f_high - 2*f_low | ; signed pair3: |2*f_high - f_low|
  c1=np.abs(freqs[:,0,1]-2*freqs[:,0,0])
  c3=np.abs(2*freqs[:,2,1]-freqs[:,2,0])
  special.append(np.abs(c1-c3))
 return np.concatenate(best),np.concatenate(special)

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--out",required=True)
 p.add_argument("--samples",type=int,default=50000)
 a=p.parse_args()
 if not 1000<=a.samples<=150000:p.error("samples outside [1000,150000]")
 nominal=np.abs(np.einsum("ij,kj->ik",NOMINAL,COEFF))
 diffs=[]
 for i,j in ((0,1),(0,2),(1,2)):
  diffs.extend(np.abs(nominal[i,:,None]-nominal[j,None,:]).ravel().tolist())
 obs_min=min(diffs)
 selected=np.abs(np.abs(NOMINAL[0,1]-2*NOMINAL[0,0])-np.abs(2*NOMINAL[2,1]-NOMINAL[2,0]))
 scenarios=[]
 for i,spread in enumerate((.02,.10,.30)):
  m,sp=simulate(a.samples,spread,20261108+i)
  scenarios.append({"independent_frequency_variation_fraction":spread,
    "number_of_simulated_frequency_sets":a.samples,
    "any_pair_min_separation_MHz_quantiles":[float(v*1000) for v in np.quantile(m,[0.05,.25,.50,.75,.95])],
    "any_cross_pair_product_within_observed_2_56_MHz_fraction":float(np.mean(m<=obs_min+1e-12)),
    "preselected_specific_cross_pair_product_within_2_56_MHz_fraction":float(np.mean(sp<=selected+1e-12)),
    "any_cross_pair_product_within_10_MHz_fraction":float(np.mean(m<=.01)),
    "monte_carlo_fraction_standard_error_max":float((.25/a.samples)**.5)})
 report={
  "created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "source_input":"Operator-proposed WorldShepherd GHz pairs, not calibrated observations",
  "input_frequency_pairs_GHz":NOMINAL.tolist(),
  "products":"First through third order mixed products abs(m*low+n*high), abs(m)+abs(n)<=3, both m,n != 0",
  "observed_exploratory_closest_separation_MHz":float(obs_min*1000),
  "selected_pair_difference_MHz":float(selected*1000),
  "null_scenarios":scenarios,
  "scientific_validity":"EXPLORATORY_SENSITIVITY_TO_ARBITRARY_REFERENCE_GENERATORS",
  "critical_limitations":[
   "Historical frequencies were not sampled randomly, and were chosen before this analysis",
   "A simulation under arbitrary ±2, ±10 and ±30 percent independent variation is not a calibrated null distribution for real resonances",
   "Search space and 10 MHz window were chosen post hoc; numerical fractions are NOT confirmatory p-values",
   "No RF amplitude, phase, linewidth, uncertainty, material or power measurement was used",
   "Exact spectral coincidences may arise in conventional devices, unrelated signals, cable/electronic spurs or bookkeeping",
   "No independent held-out experimental validation and NO new physical interaction demonstrated"
  ],
  "new_physics":False
 }
 out=pathlib.Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(report,indent=2)+"\n")
 print(json.dumps({"observed_sep_mhz":report["observed_exploratory_closest_separation_MHz"],
   "scenarios":[{"spread":r["independent_frequency_variation_fraction"],
   "any_2_56MHz":round(r["any_cross_pair_product_within_observed_2_56_MHz_fraction"],4),
   "specific_2_56MHz":round(r["preselected_specific_cross_pair_product_within_2_56_MHz_fraction"],4),
   "any_10MHz":round(r["any_cross_pair_product_within_10_MHz_fraction"],4)} for r in scenarios],
   "physical_evidence":False}))
if __name__=="__main__":main()

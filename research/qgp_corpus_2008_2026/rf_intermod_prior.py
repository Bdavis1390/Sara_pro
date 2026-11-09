#!/usr/bin/env python3
"""WorldShepherd three-pair conventional intermodulation prior.
PRECOMPUTED predictions only. Does not retrieve/claim measured spectra.
All source pair frequencies are historical user-proposed unvalidated inputs.
"""
import argparse, datetime, json
from decimal import Decimal, getcontext
from itertools import combinations

getcontext().prec=28
D=Decimal
H_EV_S=D("4.135667696e-15")
QCD_SCALE_EV=D("150000000")
PAIRS = {
 "WS-RF-001":(D("3.96993"),D("9.53242")),
 "WS-RF-002":(D("0.242"),D("0.953")),
 "WS-RF-003":(D("0.396"),D("0.993")),
}
def products(pair, max_order=3):
 lo,hi=PAIRS[pair]
 outcomes={}
 for order in range(1,max_order+1):
  for cl in range(-order,order+1):
   for ch in range(-order,order+1):
    if abs(cl)+abs(ch)!=order:continue
    frequency=cl*lo+ch*hi
    if frequency==0:continue
    if frequency<0:
      cl,ch,frequency=-cl,-ch,-frequency
    # Dedupe sign-reversed conjugate oscillations.
    key=(cl,ch)
    if key in outcomes:continue
    outcomes[key]={
      "pair_id":pair,
      "order":order,
      "m_low":cl,"n_high":ch,
      "frequency_GHz":str(frequency),
      "frequency_MHz":str(frequency*D(1000)),
      "type":"fundamental_or_harmonic" if (cl==0 or ch==0) else "intermodulation",
      "weak_nonlinearity_prediction":{
         "input_power_exponent_low":abs(cl),
         "input_power_exponent_high":abs(ch),
         "phase_relation":"m_low*phi_low + n_high*phi_high for phase-coherent tones",
         "validity":"Perturbative unsaturated single-path mixing; not evidence of an anomalous physical interaction"
      }
    }
 return sorted(outcomes.values(),key=lambda p:(D(p["frequency_GHz"]),p["order"]))

def overlaps(threshold_MHz=D("10")):
 pool=[p for name in PAIRS for p in products(name,3) if p["type"]=="intermodulation"]
 matches=[]
 for a,b in combinations(pool,2):
  if a["pair_id"]==b["pair_id"]:continue
  delta=abs(D(a["frequency_MHz"])-D(b["frequency_MHz"]))
  if delta<=threshold_MHz:
   center=(D(a["frequency_MHz"])+D(b["frequency_MHz"]))/2
   matches.append({
    "source_A":a,"source_B":b,
    "separation_MHz":str(delta),
    "mid_frequency_GHz":str(center/D(1000)),
    "fractional_separation":str(delta/center),
    "linewidth_overlap_requirement":"Combined spectral width must be measured and comparable to separation; this is not observed resonance",
    "rough_Q_if_linewidth_equals_separation":float(center/delta) if delta else None,
    "status":"POST_HOC_FREQUENCY_ARITHMETIC_NOT_A_MEASUREMENT"
   })
 return sorted(matches,key=lambda x:D(x["separation_MHz"]))

def report(threshold_MHz=D("10")):
 catalog={name:{"input_low_GHz":str(pair[0]),"input_high_GHz":str(pair[1]),
                "products":products(name)} for name,pair in PAIRS.items()}
 max_f=max(f for v in PAIRS.values() for f in v)*D("1e9")
 energy=H_EV_S*max_f
 return {
    "as_of_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "input_provenance":"WorldShepherd operator's three historical GHz pairs, unvalidated",
    "scope":"Passive arithmetic anticipation of standard 1st-3rd order frequency mixing",
    "catalog":catalog,
    "max_interpair_separation_MHz":str(threshold_MHz),
    "close_cross_pair_products":overlaps(threshold_MHz),
    "largest_original_photon_energy_eV":str(energy),
    "qcd_thermal_scale_eV":str(QCD_SCALE_EV),
    "qcd_to_largest_photon_energy_ratio":str(QCD_SCALE_EV/energy),
    "interpretation":[
      "Products are calculated from elementary polynomial/nonlinear mixing; none demonstrate physical coupling between source sets.",
      "Mixing products can originate in signal generators, combiners, amplifiers, nonlinear sample material or the receiver.",
      "Third-order power-law exponents under unsaturated perturbative assumptions can also occur in electronics; not unique to a material or a novel force.",
      "Near-coincident frequency arithmetic was selected after historical frequencies were known and cannot support a confirmatory p-value.",
      "A shared spectral band is not evidence of inter-pair energy exchange; test sample-vs-blank using physical linewidth, phase, power closure, sham setpoints and calibrated instruments.",
      "The ~150 MeV QCD thermal crossover scale differs by >10^12 from the energy of an individual photon in these microwave pairs; naive microwave photon activation of QGP is unsupported."
    ],
    "claims":{"new_material_effect":False,"new_physics":False,"independent_experimental_data":False}
 }
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--out",required=True)
 p.add_argument("--threshold-mhz",type=Decimal,default=D("10"))
 a=p.parse_args()
 if not 0<=a.threshold_mhz<=D("500"):p.error("invalid threshold")
 j=report(a.threshold_mhz)
 with open(a.out,"w") as f:json.dump(j,f,indent=2);f.write("\n")
 print(json.dumps({
   "all_catalog_products":sum(len(v["products"]) for v in j["catalog"].values()),
   "close_cross_pair_matches":len(j["close_cross_pair_products"]),
   "matches":[{"A":m["source_A"]["pair_id"],"freqA":m["source_A"]["frequency_GHz"],
               "B":m["source_B"]["pair_id"],"freqB":m["source_B"]["frequency_GHz"],
               "separation_MHz":m["separation_MHz"]} for m in j["close_cross_pair_products"]],
   "qcd_to_rf_max_photon_energy_ratio":j["qcd_to_largest_photon_energy_ratio"],
   "new_physics":False
 }))
if __name__=="__main__":main()

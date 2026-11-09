#!/usr/bin/env python3
"""MOSAIC-RF 2021 published antenna benchmark: equivalent-state geometry gate.

This is an external-paper DATA + GEOMETRY check, not WorldShepherd RF measurements.
The 8 off-broadside azimuths are a direction SET. The paper's physical
mode-to-azimuth table requires figure/CAD confirmation; do not assume a mode mapping.
"""
import argparse
import datetime
import itertools
import json
import math
import pathlib
import statistics

DOI="10.3390/s21072557"
SOURCE_URL="https://www.mdpi.com/1424-8220/21/7/2557"
MODES=("M1","M2","M3","M4","M5","M6","M7","M8","M9")
S11_DB=(-11.95,-7.80,-16.81,-13.19,-12.18,-8.59,-11.95,-12.24,-11.67)
S21_DB=(-14.63,-19.49,-13.32,-10.41,-10.47,-19.39,-11.62,-10.73,-10.25)
S22_DB=(-11.30,-11.53,-13.32,-9.82,-10.24,-12.29,-9.95,-10.39,-11.37)
POWER_MARGIN_DB=(13.37,5.50,7.66,7.75,6.98,5.52,7.04,7.66,6.94)
# Directions from paper's explicit beam-direction set; indices here are arbitrary,
# not asserted to be physical switch configuration labels M2..M9.
DIRECTIONS=[{"id":"broadside","theta_deg":0.,"phi_deg":0.}]
DIRECTIONS += [{"id":f"offaxis_azimuth_{az}","theta_deg":40.,"phi_deg":float(az)}
               for az in range(0,360,45)]

def unit(theta_deg,phi_deg):
    t=math.radians(theta_deg)
    p=math.radians(phi_deg)
    return (math.sin(t)*math.cos(p), math.sin(t)*math.sin(p),math.cos(t))

def greatcircle(a,b):
    u=unit(a["theta_deg"],a["phi_deg"])
    v=unit(b["theta_deg"],b["phi_deg"])
    dot=sum(x*y for x,y in zip(u,v))
    return math.degrees(math.acos(max(-1.,min(1.,dot))))

def equivalence(tol_deg=10.):
    if not 0<tol_deg<=90: raise ValueError("Tolerance must be (0,90] degrees")
    pairs=[]
    for a,b in itertools.combinations(DIRECTIONS,2):
        distance=greatcircle(a,b)
        pairs.append({"direction_a":a["id"],"direction_b":b["id"],
                      "separation_deg":distance,
                      "equivalent_under_pointing_tolerance":distance<=tol_deg})
    return pairs

def build(tol_deg=10.):
    pairs=equivalence(tol_deg)
    matches=[p for p in pairs if p["equivalent_under_pointing_tolerance"]]
    closest=sorted(pairs,key=lambda p:p["separation_deg"])[:8]
    mean_margin=statistics.mean(POWER_MARGIN_DB)
    mean_linear_power_db=10*math.log10(statistics.mean(10**(v/10) for v in POWER_MARGIN_DB))
    return {
      "created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "provenance":{"doi":DOI,"url":SOURCE_URL,"paper_year":2021,
         "paper_title":"Design of Minimum Nonlinear Distortion Reconfigurable Antennas for Next-Generation Communication Systems",
         "numeric_status":"EXTERNAL_PUBLISHED_BENCHMARK_NOT_WORLDSHEPHERD_MEASUREMENT"},
      "benchmark":{"nominal_frequency_GHz":3.5,
         "source_switch_configurations_count":9,
         "direction_set":DIRECTIONS,
         "physical_mode_to_direction_map":"NOT_ASSERTED_FROM_DIRECTION_SET",
         "published_port_data_mode_labels":list(MODES),
         "S11_dB":list(S11_DB),"S21_dB":list(S21_DB),"S22_dB":list(S22_DB),
         "power_margin_dB":list(POWER_MARGIN_DB),
         "mean_power_margin_dB_arithmetic":mean_margin,
         "mean_power_margin_dB_linear_power_ratio":mean_linear_power_db,
         "mean_power_margin_convention":"10log10(mean(10^(dB/10))) reconciles published 8.34 dB; direct arithmetic mean of dB is 7.60 dB",
         "published_rounded_mean_margin_dB":8.34},
      "same_radiation_objective_test":{
         "pointing_tolerance_deg":tol_deg,
         "angle_metric":"3D angular distance between unit boresight directions, not difference of elevation angles",
         "number_of_distinct_direction_pairs":len(pairs),
         "number_of_equivalent_direction_pairs":len(matches),
         "minimum_3D_separation_deg":min(p["separation_deg"] for p in pairs),
         "closest_pairs":closest,
         "outcome":"NO_EQUIVALENT_BEAM_STATES_IN_PUBLISHED_NINE_DIRECTION_SET" if not matches
                  else "NEEDS_FURTHER_PATTERN_EQUIVALENCE_REVIEW"},
      "MOSAIC_R4_gate":{
         "supports_original_state_equivalence_H1":bool(matches),
         "requires_redundant_state_configurations_for_same_objective":not bool(matches),
         "requires_fullwave_model_and_convergence":True,
         "requires_device_nonlinearity_model":True,
         "requires_real_IM3_and_full_radiation_pattern_data":True,
         "requires_heldout_state_power_temperature_prediction":True,
         "source_paper_port_data_are_not_IM3_measurements":True,
         "novel_physics_demonstrated":False,
         "evidence_state":"BENCHMARK_GEOMETRY_AUDITED_NO_ORIGINAL_EXPERIMENT"},
      "limits":[
        "The published nine configurations point into nine geometrically different directions. They are not automatically equal beam objectives.",
        "True far-field objective equivalence also requires pattern shape, gain, polarization, side lobes, bandwidth and tolerance, not pointing alone.",
        "Published power margin is a derived external metric, NOT measured modal susceptibility or new response.",
        "Additional switch configurations on one common beam objective require source CAD/current models or new physical device and are not inferred here.",
        "No unpublished device geometry, local field or nonlinear characteristic current was fabricated or claimed.",
        "A novel efficient distortion-aware state controller may be valuable engineering while remaining within standard Maxwell electrodynamics."
      ]
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--pointing-tolerance-deg",type=float,default=10.)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    result=build(args.pointing_tolerance_deg)
    dest=pathlib.Path(args.out)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2)+"\n")
    geo=result["same_radiation_objective_test"]
    print(json.dumps({"modes":len(MODES),"beam_targets":len(DIRECTIONS),
        "direction_pairs":geo["number_of_distinct_direction_pairs"],
        "nearest_separation_deg":round(geo["minimum_3D_separation_deg"],6),
        "equivalent_pairs_at_tolerance":geo["number_of_equivalent_direction_pairs"],
        "mean_power_margin_dB_direct":round(statistics.mean(POWER_MARGIN_DB),4),
        "mean_power_margin_dB_power_domain":round(10*math.log10(statistics.mean(10**(v/10) for v in POWER_MARGIN_DB)),4),
        "MOSAIC_R4_closed":False,"novel_physics":False}))
if __name__=="__main__":main()

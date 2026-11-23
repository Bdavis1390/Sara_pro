#!/usr/bin/env python3
"""NIST measured IQ IM3: censor noise-selected spectral maxima before slope fitting.
RETROSPECTIVE QUALITY FILTER, NOT A PREREGISTERED DETECTION THRESHOLD.
This program processes compact derived results, not raw third-party IQ.
"""
import argparse,datetime,json,math,pathlib
import numpy as np

def summarize(path,added_null_margin_db=6.,peak_stability_hz=250):
 j=json.loads(pathlib.Path(path).read_text())
 if j["measurement_type"]!="THIRD_PARTY_NIST_MEASURED_IQ_RECEIVER_NONLINEARITY":
  raise ValueError("Measurement source misclassified")
 if not j["terminated_receiver_reference"]:raise ValueError("No actual terminated reference")
 baseline=j["terminated_receiver_reference"]
 null_snr=float(baseline["peak_SNR_dB_relative_to_median_single_bin_noise"])
 threshold=null_snr+added_null_margin_db
 rows=j["selected_samples"]
 selected0=[]
 for row in rows:
  m=row["measurement"]
  snr=float(m["peak_SNR_dB_relative_to_median_single_bin_noise"])
  selected0.append(snr>=threshold)
 if sum(selected0)<3:
  return {"source":str(path),"state":"INSUFFICIENT_RELIABLE_SIGNAL","threshold":threshold}
 anchor=float(np.median([float(x["measurement"]["peak_IF_hz"]) for x,keep in zip(rows,selected0) if keep]))
 qualified=[];detail=[]
 for r,snrkeep in zip(rows,selected0):
  m=r["measurement"];peak=float(m["peak_IF_hz"])
  stable=abs(peak-anchor)<=peak_stability_hz
  keep=snrkeep and stable
  detail.append({"source_index":r["index"],
    "input_per_tone_dBm":r["source_input_power_each_dBm"],
    "peak_IF_Hz":peak,
    "peak_amplitude_relative_ADC_dB":m["peak_amplitude_db_relative_to_unscaled_ADC"],
    "peak_SNR_dB":m["peak_SNR_dB_relative_to_median_single_bin_noise"],
    "exceeds_null_search_max_by_6dB":snrkeep,
    "stays_within_250Hz_of_posthoc_anchor":stable,
    "accepted_for_exploratory_slope":keep})
  if keep:qualified.append(r)
 if len(qualified)<3:raise ValueError("Less than 3 strong, frequency-consistent points")
 inputs=np.array([q["source_input_power_each_dBm"] for q in qualified],dtype=float)
 outputs=np.array([q["measurement"]["peak_amplitude_db_relative_to_unscaled_ADC"] for q in qualified],dtype=float)
 co=np.polyfit(inputs,outputs,1)
 pred=np.polyval(co,inputs)
 rmse=float(np.sqrt(np.mean((outputs-pred)**2)))
 pair_slopes=[]
 for i in range(len(qualified)):
  for k in range(i+1,len(qualified)):
   if inputs[i]!=inputs[k]:
    pair_slopes.append(float((outputs[k]-outputs[i])/(inputs[k]-inputs[i])))
 return {
  "analysis_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "source_report":str(path),
  "NIST_original_data":"https://doi.org/10.18434/mds2-2628",
  "experiment_platform":j["remote_archive"],
  "method":"RETROSPECTIVE_STRONG_SIGNAL_QUALITY_GATE_NOT_INDEPENDENTLY_BLINDED",
  "null_max_SNR_dB_in_preselected_30kHz_scan":null_snr,
  "discovery_style_margin_above_null_max_dB":added_null_margin_db,
  "qualified_SNR_min_dB":threshold,
  "posthoc_frequency_anchor_Hz":anchor,
  "frequency_anchor_tolerance_Hz":peak_stability_hz,
  "total_selected_captures":len(rows),
  "qualified_captures":len(qualified),
  "excluded_captures":len(rows)-len(qualified),
  "fit_linear_slope_dB_output_per_dB_input":float(co[0]),
  "fit_intercept_relative_ADC_units":float(co[1]),
  "fit_rms_residual_dB":rmse,
  "all_pairwise_power_slopes":pair_slopes,
  "source_power_interval_dBm":[float(min(inputs)),float(max(inputs))],
  "per_capture":detail,
  "interpretation":"Ordinary instrument/source IM3 is the relevant null. A near-cubic relative slope over a narrow range does not demonstrate a new response.",
  "limitations":[
    "Threshold and peak-frequency anchor chosen AFTER inspecting measured candidate captures and 50-ohm control; no confirmatory p-value",
    "Only 1 NIST terminated capture used for maximum-bin noise benchmark; no null distribution or multiple independent sessions",
    "No absolute receiver RF calibration of IQ ADC values, only relative output amplitude",
    "Two-tone source/receiver clocks can be offset and drift; peak frequency is selected by search not guaranteed tone tracking",
    "No independently verified instrument phase calibration and no original WorldShepherd material sample",
    "Tiny selected range does not establish a fundamental cubic law across all drive powers",
    "Frequency and gain transfer function/covariance not estimated; results cannot support discovery statistical significance"
  ],
  "new_physics_demonstrated":False}
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--inputs",nargs="+",required=True)
 ap.add_argument("--out",required=True)
 a=ap.parse_args()
 results=[summarize(path) for path in a.inputs]
 out=pathlib.Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps({"analysis":"POSTHOC_NIST_RECEIVER_IM3_QA",
   "sources":results,"new_physics":False},indent=2)+"\n")
 print(json.dumps({"scans":[{"source":v.get("experiment_platform"),
 "qualified":v.get("qualified_captures"),"slope":v.get("fit_linear_slope_dB_output_per_dB_input"),
 "excluded":v.get("excluded_captures"),"threshold_dB":v.get("qualified_SNR_min_dB")} for v in results],
 "new_physics":False}))
if __name__=="__main__":main()

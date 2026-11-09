#!/usr/bin/env python3
"""Ordinary coherent interference between two third-order RF mixing products.
SIMULATED / CALCULATED optical-style complex field superposition at baseband.
This is an algebraic counterexample to treating a 2.56MHz beat as energy exchange.
"""
import argparse,datetime,json,math,pathlib
import numpy as np

LOW_A=3.96993e9
HIGH_A=9.53242e9
LOW_C=.396e9
HIGH_C=.993e9
OUT_A=abs(HIGH_A-2*LOW_A)
OUT_C=abs(2*HIGH_C-LOW_C)
DELTA=abs(OUT_A-OUT_C)
PHI_A=lambda phi_low,phi_high:phi_high-2*phi_low
PHI_C=lambda phi_low,phi_high:2*phi_high-phi_low

def normalized_envelope(t_s,amp_a=1,amp_c=1,phase_a=0,phase_c=0):
 t=np.asarray(t_s,dtype=float)
 # Rotating baseband at OUT_C; two fixed independent nonlinear branches.
 complex_a=amp_a*np.exp(1j*(2*np.pi*(OUT_A-OUT_C)*t+phase_a))
 complex_c=amp_c*np.exp(1j*phase_c)*np.ones_like(t,dtype=complex)
 return abs(complex_a+complex_c)**2

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--out",required=True)
 p.add_argument("--points",type=int,default=16000)
 a=p.parse_args()
 if not 4000<=a.points<=100000:p.error("points 4000..100000")
 period=1/DELTA
 # 32 full beat cycles, exact endpoint excluded, discretized on baseband.
 times=np.arange(a.points)*32*period/a.points
 vals=normalized_envelope(times)
 phase_shifted=normalized_envelope(times,phase_a=math.pi/2)
 theoretical_average=2.
 result={
  "created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "source_provenance":"historical operator frequency pairs, unvalidated hardware hypotheses",
  "model":"Independent conventional cubic-mixing outputs that are linearly superposed at a receiver; no coupling term",
  "branch_A_frequency_hz":OUT_A,"branch_C_frequency_hz":OUT_C,
  "frequency_separation_hz":DELTA,
  "baseband_beat_period_s":period,
  "baseband_beat_period_ns":period*1e9,
  "nominal_normalized_amplitudes":[1,1],
  "relative_phase_formula":"(phi_high_A - 2 phi_low_A) - (2 phi_high_C - phi_low_C)",
  "intensity":"|A exp(i*(2pi*(fA-fC)*t +phiA))+C exp(i*phiC)|^2",
  "predicted_normalized_mean_power":theoretical_average,
  "numerical_time_mean_normalized_power":float(np.mean(vals)),
  "numerical_min_normalized_power":float(np.min(vals)),
  "numerical_max_normalized_power":float(np.max(vals)),
  "relative_phase_pi_over_2_at_t0_power":float(normalized_envelope([0],phase_a=math.pi/2)[0]),
  "sample_envelope": [{"relative_beat_cycles":round(float(x),4),
                       "normalized_intensity":round(float(normalized_envelope([x*period])[0]),7)}
                      for x in np.linspace(0,2,17)],
  "baseband_phase_shift_intensity_mean":float(np.mean(phase_shifted)),
  "scope":"CALCULATED_NORMALIZED_INTERFERENCE_NO_MEASUREMENTS",
  "new_physics":False,
  "warnings":[
    "Beat intensity occurs without physical energy transfer between the independent RF generation branches",
    "Actual interference requires phase coherence and coherent combining in the receiver observation path",
    "Spectral resolution and physical bandwidth/noise sensitivity must be measured to resolve the two nearby lines",
    "A second-harmonic or third-order intermodulation output can be created by source, combiner, sample or analyzer",
    "Envelope intensity is a normalized field-squared quantity, not certified output power in watts",
    "Real power conservation and an actual nonlinear material susceptibility need separately calibrated measurements"
  ]}
 o=pathlib.Path(a.out);o.parent.mkdir(parents=True,exist_ok=True)
 o.write_text(json.dumps(result,indent=2)+"\n")
 print(json.dumps({"A_GHz":OUT_A/1e9,"C_GHz":OUT_C/1e9,
    "delta_MHz":DELTA/1e6,"period_ns":period*1e9,
    "mean_normalized_intensity":result["numerical_time_mean_normalized_power"],
    "min":result["numerical_min_normalized_power"],
    "max":result["numerical_max_normalized_power"],
    "measured_data":False,"new_physics":False}))
if __name__=="__main__":main()

#!/usr/bin/env python3
"""Bounded NIST 2022 measured SDR IM3 spectral analysis via HTTP Range ZIP.
No full archive storage, no extraction. NIST Open Access measurement data.
Shows conventional receiver distortion; never WorldShepherd material physics.
"""
import argparse,datetime,hashlib,json,math,pathlib,zipfile
import numpy as np
from nist_range_zip_metadata import HTTPRange,BASE,FILES

def first_iq_and_crc(z,member,n=524288):
 info=z.getinfo(member)
 if info.file_size>45_000_000:raise ValueError("Member unexpectedly large")
 if info.file_size%8:raise ValueError("IQ not divisible by complex float32")
 h=hashlib.sha256(); prefix=bytearray();received=0
 with z.open(info) as f:
  while True:
   b=f.read(1048576)
   if not b:break
   received+=len(b);h.update(b)
   if len(prefix)<n*8:prefix.extend(b[:max(0,n*8-len(prefix))])
 if received!=info.file_size:raise RuntimeError("Incomplete member")
 if len(prefix)!=n*8:raise RuntimeError("Not enough IQ samples")
 iq=np.frombuffer(prefix,dtype="<c8").copy()
 if not np.all(np.isfinite(iq)):raise ValueError("Nonfinite IQ")
 return iq,{"uncompressed_bytes":received,"member_sha256":h.hexdigest(),
   "zip_member_crc32":f"{info.CRC:08x}","source":member}

def spectrum(iq,if_frequency,sample_rate=5e6):
 n=len(iq)
 window=np.hanning(n).astype(np.float32)
 Z=np.fft.fft(iq*window)
 freq=np.fft.fftfreq(n,d=1/sample_rate)
 mag=np.abs(Z)/np.sum(window)
 desired=abs(freq-if_frequency)
 select=desired<15000
 if not select.any():raise RuntimeError("No frequency bin near source-predicted IM3")
 peak_index=np.where(select)[0][np.argmax(mag[select])]
 noise_band=(desired>50000)&(desired<250000)
 if not noise_band.any():raise RuntimeError("Noise band absent")
 # Independent noise distribution from surrounding, non-coincident bins.
 baseline=float(np.median(mag[noise_band]))
 peak=float(mag[peak_index])
 phase=float(np.angle(Z[peak_index]))
 return {"target_IF_hz":float(if_frequency),
         "peak_IF_hz":float(freq[peak_index]),
         "peak_minus_target_hz":float(freq[peak_index]-if_frequency),
         "peak_amplitude_db_relative_to_unscaled_ADC":float(20*math.log10(max(peak,1e-25))),
         "median_neighbor_noise_amplitude_db":float(20*math.log10(max(baseline,1e-25))),
         "peak_SNR_dB_relative_to_median_single_bin_noise":float(20*math.log10(max(peak/baseline,1e-25))),
         "IQ_sample_count":n,"sample_rate_Hz":sample_rate,
         "window":"Hann","frequency_resolution_hz":sample_rate/n,
         "calibrated_output_power_dBm":False}

def analyze(index_path,zip_name,indexes,include_null):
 j=json.loads(pathlib.Path(index_path).read_text())
 which="sdr0" if "sdr0" in zip_name else "sdr1"
 if zip_name!=FILES[which]:raise ValueError("Archive mismatch")
 h=HTTPRange(BASE+zip_name)
 param=j["json_metadata"]["measurement_space_imd3_imd2.json"]["content"]["parameters"]
 mapped={int(x["index"]):x for x in param if float(x["nisg_0_freq"])<2e9}
 if len(mapped)<len(indexes):raise RuntimeError("Insufficient source conditions")
 baseline=j["json_metadata"][which+".json"]["content"]
 fs=float(baseline["sample_rate"][1])
 output=[]
 with zipfile.ZipFile(h) as z:
  for idx in indexes:
   row=mapped.get(idx)
   if not row:raise ValueError("Requested index outside expected 2f1-f2 sweep")
   member=f"2f1-f2/test_{idx}.bin"
   IQ,provenance=first_iq_and_crc(z,member)
   expected=2*float(row["nisg_0_freq"])-float(row["nisg_1_freq"])
   center=float(row[which+"_center_freq"])
   result=spectrum(IQ,expected-center,fs)
   output.append({"index":idx,"source_input_power_each_dBm":float(row["nisg_0_power"]),
     "source_input_power_other_dBm":float(row["nisg_1_power"]),
     "source_input_frequency_Hz":[float(row["nisg_0_freq"]),float(row["nisg_1_freq"])],
     "receiver_center_frequency_Hz":center,"expected_intermod_frequency_Hz":expected,
     "measurement":result,"integrity":provenance})
  if include_null:
   nullpath="50_omega_term/test_0.bin"
   IQ,provenance=first_iq_and_crc(z,nullpath)
   # Compare 50-ohm terminated receiver capture in identical IF channel.
   target=output[0]["measurement"]["target_IF_hz"]
   null=spectrum(IQ,target,fs)
  else:null=None
 p=np.array([v["source_input_power_each_dBm"] for v in output])
 amp=np.array([v["measurement"]["peak_amplitude_db_relative_to_unscaled_ADC"] for v in output])
 snr=np.array([v["measurement"]["peak_SNR_dB_relative_to_median_single_bin_noise"] for v in output])
 slope=float(np.polyfit(p,amp,1)[0]) if len(p)>=3 else None
 report={"created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
   "nist_data_reference":"https://doi.org/10.18434/mds2-2628",
   "publication":"McNulty et al. 2022 EuCAP DOI 10.23919/EuCAP53622.2022.9769373",
   "measurement_type":"THIRD_PARTY_NIST_MEASURED_IQ_RECEIVER_NONLINEARITY",
   "remote_archive":zip_name,"full_source_archive_downloaded":False,
   "zip_member_CRCs_verified_on_full_decompression":True,
   "independent_source_sha256_for_each_uncompressed_capture":True,
   "waveform_storage":"NONE: stream, analyze in RAM; no IQ files persisted",
   "selected_samples":output,"terminated_receiver_reference":null,
   "slope_of_relative_IM3_amplitude_dB_per_input_dBm":slope,
   "minimum_spur_SNR_dB":float(np.min(snr)),
   "input_power_levels_dBm":p.tolist(),
   "receiver_linearity_claims":"NO_CALIBRATED_ABSOLUTE_OUTPUT_POWER",
   "source_zip_sha256_verified":False,
   "bytes_transferred_over_HTTP_range":h.bytes_downloaded,
   "HTTP_range_requests":h.requests,
   "claims":{"receiver_distortion_possible":True,
     "proves_original_sample_interaction":False,
     "new_fundamental_physics":False},
   "critical_limitations":[
     "IQ ADC raw units not traceable dBm without independent receiver transfer calibration",
     "Spectral peak from short initial window can depend on drift, spurious tones, IQ balance, window leakage",
     "Zip member CRC-32 and local uncompressed SHA-256 verified; full ~773 MB archive SHA-256 NOT verified",
     "Two-tone source frequency read from NIST public JSON; phase-coherence and port calibration not newly measured",
     "Small selected input power range and no independent run-to-run uncertainty: slope is descriptive, not a statistical discovery result",
     "This is established receiver-generated nonlinear physics, not a new WorldShepherd sample effect"
   ]}
 return report

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--which",choices=["sdr0","sdr1"],default="sdr0")
 ap.add_argument("--index-file",required=True)
 ap.add_argument("--indexes",default="1,4,7,10,13")
 ap.add_argument("--include-null",action="store_true")
 ap.add_argument("--out",required=True)
 a=ap.parse_args()
 indices=[int(s) for s in a.indexes.split(",")]
 if len(indices)>8 or len(indices)<3 or len(set(indices))!=len(indices) or any(x<0 or x>14 for x in indices):
  ap.error("Specify 3..8 distinct indices in [0..14]")
 r=analyze(a.index_file,FILES[a.which],indices,a.include_null)
 out=pathlib.Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(r,indent=2)+"\n")
 print(json.dumps({"archive":r["remote_archive"],"captures":len(r["selected_samples"]),
  "powers_dBm":r["input_power_levels_dBm"],
  "detected_relative_IM3_dB":[round(x["measurement"]["peak_amplitude_db_relative_to_unscaled_ADC"],2) for x in r["selected_samples"]],
  "spur_SNR_dB":[round(x["measurement"]["peak_SNR_dB_relative_to_median_single_bin_noise"],2) for x in r["selected_samples"]],
  "slope":r["slope_of_relative_IM3_amplitude_dB_per_input_dBm"],
  "range_bytes":r["bytes_transferred_over_HTTP_range"],
  "null_SNR_dB":r["terminated_receiver_reference"]["peak_SNR_dB_relative_to_median_single_bin_noise"] if r["terminated_receiver_reference"] else None,
  "new_physics":False}))
if __name__=="__main__":main()

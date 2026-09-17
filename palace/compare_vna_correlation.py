#!/usr/bin/env python3
"""Fail-closed complex-S11 PALACE/VNA correlation comparator.

Inputs are canonical CSV files with columns frequency_ghz,real,imag plus a
measurement metadata JSON. No interpolation is performed. This tool does not
promote numerical evidence to partner/independent/qualified evidence.
"""
from __future__ import annotations

import argparse, csv, hashlib, json, math, tempfile
from pathlib import Path

REQ_COLS={"frequency_ghz","real","imag"}


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()


def load_csv(path: Path):
    out={}
    with path.open(newline="",encoding="utf-8") as f:
        r=csv.DictReader(f)
        if not REQ_COLS.issubset(r.fieldnames or []):
            raise ValueError(f"{path}: required columns {sorted(REQ_COLS)}")
        for row in r:
            freq=float(row["frequency_ghz"]); z=complex(float(row["real"]),float(row["imag"]))
            if not (math.isfinite(freq) and math.isfinite(z.real) and math.isfinite(z.imag)):
                raise ValueError(f"{path}: non-finite value")
            key=round(freq,12)
            if key in out: raise ValueError(f"{path}: duplicate frequency {freq}")
            out[key]=z
    if len(out)<2: raise ValueError(f"{path}: insufficient samples")
    return out


def wrap_deg(x):
    return (x+180.0)%360.0-180.0


def phase_deg(z):
    return math.degrees(math.atan2(z.imag,z.real))


def resonance(freqs, data):
    return min(freqs,key=lambda f:abs(data[f]))


def validate_meta(meta, protocol, measurement_csv):
    missing=[k for k in protocol["required_measurement_metadata"] if k not in meta or meta[k] in (None,"")]
    if missing: raise ValueError("measurement metadata missing: "+", ".join(missing))
    minr=protocol["minimum_requirements"]
    if int(meta["remove_replace_repeat_count"]) < int(minr["remove_replace_repeats"]):
        raise ValueError("insufficient remove/replace repeats")
    if str(meta["raw_data_sha256"]).lower()!=sha256(measurement_csv):
        raise ValueError("raw_data_sha256 does not match measurement CSV")


def compare(model_csv:Path, measurement_csv:Path, metadata_json:Path, protocol_json:Path):
    p=json.loads(protocol_json.read_text()); meta=json.loads(metadata_json.read_text())
    if p.get("schema")!="WS-PALACE-VNA-CORRELATION-PROTOCOL-V1": raise ValueError("wrong protocol schema")
    validate_meta(meta,p,measurement_csv)
    mod=load_csv(model_csv); meas=load_csv(measurement_csv)
    common=sorted(set(mod)&set(meas))
    required=int(p["minimum_requirements"]["common_frequency_points"])
    if len(common)<required: raise ValueError(f"only {len(common)} common points; need {required}")

    mag=[]; phase=[]; c2=[]; m2=[]
    eps=1e-15
    for f in common:
        a,b=mod[f],meas[f]
        mag.append((20*math.log10(max(abs(a),eps))-20*math.log10(max(abs(b),eps)))**2)
        phase.append(wrap_deg(phase_deg(a)-phase_deg(b))**2)
        c2.append(abs(a-b)**2); m2.append(abs(b)**2)
    magnitude_rmse_db=math.sqrt(sum(mag)/len(mag))
    phase_rmse_deg=math.sqrt(sum(phase)/len(phase))
    fr_model=resonance(common,mod); fr_meas=resonance(common,meas)
    resonance_shift_percent=abs(fr_model-fr_meas)/max(abs(fr_meas),eps)*100.0
    complex_normalized_rmse=math.sqrt(sum(c2)/len(c2))/max(math.sqrt(sum(m2)/len(m2)),eps)
    th=p["frozen_acceptance_thresholds"]
    checks={
      "magnitude_rmse_db": magnitude_rmse_db <= th["magnitude_rmse_db_max"],
      "phase_rmse_deg": phase_rmse_deg <= th["phase_rmse_deg_max"],
      "resonance_shift_percent": resonance_shift_percent <= th["resonance_shift_percent_max"],
      "complex_normalized_rmse": complex_normalized_rmse <= th["complex_normalized_rmse_max"]
    }
    return {
      "schema":"WS-PALACE-VNA-CORRELATION-REPORT-V1",
      "dataset_id":meta["dataset_id"],
      "common_frequency_points":len(common),
      "metrics":{
        "magnitude_rmse_db":magnitude_rmse_db,
        "phase_rmse_deg":phase_rmse_deg,
        "resonance_model_ghz":fr_model,
        "resonance_measurement_ghz":fr_meas,
        "resonance_shift_percent":resonance_shift_percent,
        "complex_normalized_rmse":complex_normalized_rmse
      },
      "threshold_checks":checks,
      "gate_pass":all(checks.values()),
      "digests":{"model_sha256":sha256(model_csv),"measurement_sha256":sha256(measurement_csv),"metadata_sha256":sha256(metadata_json),"protocol_sha256":sha256(protocol_json)},
      "evidence_class":"BOUNDED_MODEL_TO_MEASUREMENT_CORRELATION_ONLY",
      "external_gate_effect":"NONE_AUTOMATIC",
      "claims_boundary":"A pass demonstrates only the predeclared correlation metrics for this measured dataset. It is not partner acceptance, independent replication, qualification, certification, or marketplace-contact authority."
    }


def write_csv(path,scale=1.0,phase=0.0,n=121):
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["frequency_ghz","real","imag"]); w.writeheader()
        ph=math.radians(phase)
        rot=complex(math.cos(ph),math.sin(ph))
        for i in range(n):
            freq=8.0+4.0*i/(n-1)
            # smooth notch centered at 10 GHz
            amp=0.10+0.70*min(abs(freq-10.0)/2.0,1.0)
            z=scale*amp*rot
            w.writerow({"frequency_ghz":f"{freq:.12f}","real":z.real,"imag":z.imag})


def self_test():
    with tempfile.TemporaryDirectory() as td:
        d=Path(td); model=d/'model.csv'; meas=d/'meas.csv'; meta=d/'meta.json'; protocol=d/'protocol.json'
        write_csv(model); write_csv(meas,scale=1.01,phase=2.0)
        proto={
          "schema":"WS-PALACE-VNA-CORRELATION-PROTOCOL-V1",
          "required_measurement_metadata":["dataset_id","measurement_authority","instrument_make_model","instrument_serial_or_asset_id","calibration_method","calibration_date_utc","reference_plane","polarization","angle_deg","control_state","frequency_min_ghz","frequency_max_ghz","frequency_point_count","remove_replace_repeat_count","uncertainty_statement","raw_data_sha256"],
          "minimum_requirements":{"common_frequency_points":101,"remove_replace_repeats":3},
          "frozen_acceptance_thresholds":{"magnitude_rmse_db_max":1.5,"phase_rmse_deg_max":15.0,"resonance_shift_percent_max":1.0,"complex_normalized_rmse_max":0.2}
        }
        protocol.write_text(json.dumps(proto))
        m={"dataset_id":"T","measurement_authority":"TEST","instrument_make_model":"TEST","instrument_serial_or_asset_id":"T1","calibration_method":"TEST","calibration_date_utc":"2026-09-04T00:00:00Z","reference_plane":"PORT","polarization":"TE","angle_deg":0,"control_state":"LOW_C","frequency_min_ghz":8,"frequency_max_ghz":12,"frequency_point_count":121,"remove_replace_repeat_count":3,"uncertainty_statement":"synthetic self-test only","raw_data_sha256":sha256(meas)}
        meta.write_text(json.dumps(m))
        r=compare(model,meas,meta,protocol); assert r['gate_pass']
        m['remove_replace_repeat_count']=2; meta.write_text(json.dumps(m))
        try: compare(model,meas,meta,protocol)
        except ValueError: pass
        else: raise AssertionError('repeat-count fail-closed test failed')
    print('PALACE VNA comparator self-test: PASS')


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--model',type=Path); ap.add_argument('--measurement',type=Path); ap.add_argument('--metadata',type=Path); ap.add_argument('--protocol',type=Path,default=Path('palace/vna_correlation_protocol.v1.json')); ap.add_argument('--output',type=Path); ap.add_argument('--self-test',action='store_true'); a=ap.parse_args()
    if a.self_test: self_test(); return
    if not all((a.model,a.measurement,a.metadata,a.output)): ap.error('--model --measurement --metadata --output required')
    r=compare(a.model,a.measurement,a.metadata,a.protocol); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(r,indent=2)+'\n'); print(json.dumps({"gate_pass":r['gate_pass'],"metrics":r['metrics'],"external_gate_effect":r['external_gate_effect']},indent=2))

if __name__=='__main__': main()

"""Run the bounded WS-QPHONON v0.3 multimode/thermal/channel benchmark."""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import numpy as np
import scipy
from ws_qphonon_multimode.model import (
    Mode, MultiModeModel, bose_occupation, propagation_delay_s,
    propagation_phase_rad, best_phase_corrected_fidelity,
    paper_parameter_context,
)

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'results'


def h(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def scenario(q: float, temperature_k: float, distance_m: float,
             group_velocity_m_s: float) -> MultiModeModel:
    f0 = 25e9
    phases = [propagation_phase_rad(f0+d, distance_m, group_velocity_m_s)
              for d in (-4e6, 0, 6e6)]
    modes = (
        Mode(f0-4e6, -4e6, .30e6, .25e6, q, phases[0]),
        Mode(f0,      0.0,  1.00e6, 1.00e6, q, phases[1]),
        Mode(f0+6e6,  6e6, .25e6, .35e6, q, phases[2]),
    )
    return MultiModeModel(modes, temperature_k=temperature_k,
                          gamma_phi_a_s_inv=1/5e-6,
                          gamma_phi_b_s_inv=1/5e-6)


def main():
    OUT.mkdir(exist_ok=True)
    paper = paper_parameter_context()
    temperatures = [.01, .05, .1, .5, 1.0]
    freqs = [10e9, 25e9, 50e9]
    thermal = [
        {'temperature_k': T, 'frequency_ghz': f/1e9,
         'nbar': bose_occupation(f,T),
         'single_excitation_screen_pass': bose_occupation(f,T) <= .05}
        for T in temperatures for f in freqs
    ]

    distance_m = 100e-6
    velocity = 4000.0
    delays = {
        'distance_m': distance_m,
        'illustrative_group_velocity_m_s': velocity,
        'delay_s': propagation_delay_s(distance_m, velocity),
        'status': 'HEURISTIC BENCHMARK INPUT / NOT SOURCE-PAPER CALIBRATED',
    }

    rows=[]
    time_grid=np.linspace(0.10e-6, 0.80e-6, 29)
    for q in (1e4,1e5,1e6):
        model=scenario(q,.05,distance_m,velocity)
        best=None
        for t in time_grid:
            metric=best_phase_corrected_fidelity(model,float(t),phase_points=121)
            row={'q':q,'time_s':float(t),**metric}
            if best is None or row['phase_corrected_six_state_fidelity'] > best['phase_corrected_six_state_fidelity']:
                best=row
        rows.append(best)

    results={
      'experiment_id':'WS-QPHONON-MULTIMODE-003',
      'version':'0.3.0',
      'evidence_class':['IMPLEMENTED IN SOFTWARE','SIMULATED ONLY','SUPPORTED BY LITERATURE'],
      'paper_context':paper,
      'benchmark_assumptions':{
        'central_frequency_ghz':25.0,
        'central_coupling_mhz':1.0,
        'side_mode_detuning_mhz':[-4.0,6.0],
        'side_mode_couplings_mhz':'heuristic; see source',
        'temperature_k':.05,
        'T2_star_us_surrogate':5.0,
        **delays,
      },
      'thermal_occupation_screen':thermal,
      'q_sweep_best_over_disclosed_time_grid':rows,
      'time_grid_s':[float(x) for x in time_grid],
      'channel_metric':'six cardinal-state average fidelity; receiver-only Z phase correction disclosed and optimized on fixed grid',
      'limitations':[
        'single-excitation truncation; finite-temperature dynamics are only used when nbar <= 0.05',
        'discrete Markovian modes, not COMSOL or a measured waveguide spectral density',
        'group velocity, side-mode spacings/couplings and temperature are benchmark assumptions',
        'T2* mapped to phenomenological projector dephasing without claiming a device-specific convention',
        'phase-corrected fidelity permits a deterministic receiver Z calibration and is reported alongside raw fidelity',
        'no hardware, partner or source-paper figure reproduction claim',
      ],
    }
    out=OUT/'v03_results.json'
    out.write_text(json.dumps(results,indent=2,sort_keys=True,allow_nan=False)+'\n')
    files=[ROOT/'run_v03.py',*sorted((ROOT/'ws_qphonon_multimode').glob('*.py')),*sorted((ROOT/'tests').glob('*.py'))]
    hashes={p.relative_to(ROOT).as_posix():h(p) for p in files}
    manifest={
      'experiment_id':results['experiment_id'],
      'generated_at_utc':datetime.now(timezone.utc).isoformat(),
      'python':platform.python_version(),
      'numpy':np.__version__, 'scipy':scipy.__version__,
      'source_files_sha256':hashes,
      'source_manifest_sha256':sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest(),
      'results_sha256':h(out),
      'claims_boundary':'simulation/literature-context only; no physical validation',
    }
    (OUT/'v03_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True,allow_nan=False)+'\n')
    for r in rows:
        if r is not None:
            print(f"Q={r['q']:.0e}: t={r['time_s']*1e6:.3f} us, raw F6={r['raw_six_state_fidelity']:.6f}, corrected F6={r['phase_corrected_six_state_fidelity']:.6f}")
    print('THERMAL SCREEN PASS CELLS', sum(x['single_excitation_screen_pass'] for x in thermal), '/', len(thermal))
    print('V0.3 NUMERICAL RUN PASS')

if __name__ == '__main__':
    main()

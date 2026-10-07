"""WS-QPHONON-ZENO-TOY-002: autonomous, bounded, deterministic research run.

Four-state dimensionless model only, no hardware optimization claim.
Outputs JSON + plots + SHA-256 provenance. Fails if numerical health gates fail.
"""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import platform
import sys

import numpy as np
import scipy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ws_qphonon_zeno.model import ideal_swap_time
from ws_qphonon_zeno.coherent import Pulse, pulse_trajectory, constant_trajectory, site_monitoring_at

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'
PLOTS=ROOT/'plots'

def hashfile(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def gate_check(run):
    probabilities=[run['final'][name] for name in
                   ('qubit_a','phonon','qubit_b','environment_loss')]
    gated_values=[
        run['max_trace_error'],
        run['minimum_sampled_eigenvalue'],
        run['loss_integral_estimate'],
        run['final']['environment_loss'],
        *probabilities,
    ]
    if not all(np.isfinite(value) for value in gated_values):
        raise RuntimeError('QC non-finite metric gate failed')
    if run['max_trace_error'] > 1e-8:
        raise RuntimeError('QC trace gate failed')
    if run['minimum_sampled_eigenvalue'] < -1e-8:
        raise RuntimeError('QC positivity gate failed')
    if abs(run['loss_integral_estimate']-run['final']['environment_loss']) > 5e-4:
        raise RuntimeError('QC integrated-loss gate failed')
    if any(x < -1e-8 or x > 1+1e-8 for x in probabilities):
        raise RuntimeError('QC probability gate failed')
    if abs(sum(probabilities)-1)>1e-8:
        raise RuntimeError('QC probability sum failed')
    return True


def main():
    OUT.mkdir(exist_ok=True)
    PLOTS.mkdir(exist_ok=True)
    kap_values=[0, .2, .5, 1, 2]
    duration_values=[8, 12, 16, 24]
    kappa_rows=[]
    for kappa in kap_values:
        for duration in duration_values:
            pulse=Pulse(duration=duration)
            run=pulse_trajectory(pulse,kappa=kappa,steps=401)
            gate_check(run)
            static=constant_trajectory(duration,kappa=kappa,steps=401)
            kappa_rows.append({
                'kappa_over_g':kappa,'duration_times_g':duration,
                'pulse_final_b':run['final']['qubit_b'],
                'pulse_final_loss':run['final']['environment_loss'],
                'pulse_final_a':run['final']['qubit_a'],
                'pulse_max_phonon':run['max_phonon_population'],
                'pulse_integrated_phonon':run['integrated_phonon_population'],
                'static_final_b_at_equal_duration':static['final']['qubit_b'],
                'static_best_b_at_any_earlier_time':static['max_b_anytime'],
                'static_time_of_best_b':static['time_of_max_b'],
                'static_integrated_phonon_full_duration':static['integrated_phonon_population'],
                'qc_max_trace_error':run['max_trace_error'],
                'qc_min_eigenvalue':run['minimum_sampled_eigenvalue'],
                'qc_loss_integral_error':abs(run['loss_integral_estimate']-run['final']['environment_loss'])
            })
    gamma_values=[0,.1,1,5,20,100]
    monitor=[{'gamma_a_over_g':g,**site_monitoring_at(g,ideal_swap_time())} for g in gamma_values]
    loss=[{'kappa_over_g':k,**constant_trajectory(ideal_swap_time(),kappa=k,steps=41)['final']}
          for k in gamma_values]

    detuning_values=[-.6,-.3,-.1,0,.1,.3,.6,1,2]
    detuning=[]
    for delta in detuning_values:
        run=pulse_trajectory(Pulse(duration=24),kappa=.5,detuning_b=delta,steps=401)
        gate_check(run)
        detuning.append({'qubit_b_detuning_over_g':delta,
                         'pulse_final_b':run['final']['qubit_b'],
                         'pulse_final_loss':run['final']['environment_loss'],
                         'max_phonon_population':run['max_phonon_population']})

    results={
        'experiment_id':'WS-QPHONON-ZENO-TOY-002','version':'0.2.0',
        'evidence_class':['IMPLEMENTED IN SOFTWARE','SIMULATED ONLY'],
        'external_validation':False,'hardware_validation':False,
        'paper_figure_reproduced':False,
        'scope':'Phenomenological four-state single-excitation GKLS Lindblad model',
        'physical_units':'dimensionless with hbar=1 and nominal peak coupling g=1',
        'initial_state':'|A><A|', 'unconditional_loss_included':True,
        'pulse':{'early_receiver_center_fraction':.33,'late_sender_center_fraction':.67,
                 'gaussian_sigma_fraction':.17,'peak_g':1,'pulse_durations':duration_values},
        'comparison':'static g_a=g_b=1; matched maximum instantaneous amplitude, not matched total pulse energy; report best earlier static time separately',
        'modeling_limitations':['one phenomenological discrete phonon bus mode',
          'no continuum spectral density, propagation delay, calibrated length or frequency',
          'no Fock-space thermal occupancy, full logical qubit channel, two-qubit entanglement or error correction',
          'Markovian constant-rate dissipation only','no material, fabrication or lab measurement',
          'dephasing projector is nonselective monitoring; phonon damping is different'],
        'references':[{'doi':'10.1063/5.0332643','reproduction':False},
                      {'arxiv':'2512.14204','reproduction':False}],
        'pulse_sweep':kappa_rows,
        'sender_measurement_sweep':monitor,
        'phonon_damping_sweep':loss,
        'pulse_qubit_b_detuning_sweep':detuning,
        'health_gate':'trace<1e-8 eigen>-1e-8 integrated_loss_error<5e-4',
    }
    jsonpath=OUT/'protocol_results.json'
    jsonpath.write_text(json.dumps(results,indent=2,sort_keys=True,allow_nan=False)+'\n')

    fig,ax=plt.subplots(figsize=(8,4.5))
    for k in (.2,.5,1,2):
        vals=[r for r in kappa_rows if r['kappa_over_g']==k]
        ax.plot([v['duration_times_g'] for v in vals],
                [v['pulse_final_b'] for v in vals],marker='o',label=f'pulse κ/g={k}')
    for k in (.5,1):
        vals=[r for r in kappa_rows if r['kappa_over_g']==k]
        ax.plot([v['duration_times_g'] for v in vals],
                [v['static_best_b_at_any_earlier_time'] for v in vals],linestyle='--',
                label=f'best earlier static κ/g={k}')
    ax.set(xlabel='protocol duration × nominal coupling g',ylabel='Unconditional receiver population',
           title='Pulse sequencing vs best static-bus transfer (toy model)',ylim=(0,1.03))
    ax.grid(alpha=.25);ax.legend(fontsize=7,ncol=2);fig.tight_layout()
    fig.savefig(PLOTS/'pulse_vs_static.png',dpi=160);plt.close(fig)

    fig,ax=plt.subplots(figsize=(8,4.3))
    ax.semilogx([r['gamma_a_over_g'] for r in monitor if r['gamma_a_over_g']>0],
                [r['qubit_b'] for r in monitor if r['gamma_a_over_g']>0],marker='o',
                label='Sender-site monitoring, dephasing')
    ax.semilogx([r['kappa_over_g'] for r in loss if r['kappa_over_g']>0],
                [r['qubit_b'] for r in loss if r['kappa_over_g']>0],marker='x',
                label='Irreversible phonon loss')
    ax.set(xlabel='monitoring/decoherence rate divided by g',ylabel='Receiver population at ideal static swap time',
           title='Distinct mechanisms of transfer suppression',ylim=(0,1.03))
    ax.grid(alpha=.25);ax.legend();fig.tight_layout()
    fig.savefig(PLOTS/'monitoring_vs_damping.png',dpi=160);plt.close(fig)

    fig,ax=plt.subplots(figsize=(8,4.3))
    ax.plot([r['qubit_b_detuning_over_g'] for r in detuning],
            [r['pulse_final_b'] for r in detuning],marker='o')
    ax.set(xlabel='Relative receiver detuning ΔB/g',ylabel='Unconditional receiver population',
           title='Pulse sensitivity to receiver detuning (κ/g=0.5, gT=24)',ylim=(0,1.03))
    ax.grid(alpha=.25);fig.tight_layout()
    fig.savefig(PLOTS/'pulse_detuning_robustness.png',dpi=160);plt.close(fig)

    files={p.relative_to(ROOT).as_posix():hashfile(p) for sub in
           [ROOT/'ws_qphonon_zeno',ROOT/'tests'] for p in sorted(sub.glob('*.py'))}
    files['run_protocol.py']=hashfile(ROOT/'run_protocol.py')
    files['requirements.txt']=hashfile(ROOT/'requirements.txt')
    manifest={
      'experiment_id':results['experiment_id'],
      'generated_at_utc':datetime.now(timezone.utc).isoformat(),
      'platform_python':platform.python_version(),
      'numerical_packages':{'numpy':np.__version__,'scipy':scipy.__version__,
                            'matplotlib':matplotlib.__version__},
      'source_files_sha256':files,
      'source_manifest_sha256':sha256(json.dumps(files,sort_keys=True).encode()).hexdigest(),
      'results_sha256':hashfile(jsonpath),
      'plot_sha256':{p.relative_to(ROOT).as_posix():hashfile(p)
                     for p in sorted(PLOTS.glob('*.png'))},
      'numerical_health_gates_pass':True,
      'statement':'numerical validation only; not literature figure or laboratory reproduction'
    }
    (OUT/'provenance_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True,allow_nan=False)+'\n')
    for row in kappa_rows:
        if row['duration_times_g'] in (8,24) and row['kappa_over_g'] in (.5,1):
            print(f"κ/g={row['kappa_over_g']}, gT={row['duration_times_g']}: "
                  f"pulse B={row['pulse_final_b']:.6f}, "
                  f"static best earlier B={row['static_best_b_at_any_earlier_time']:.6f}, "
                  f"peak phonon={row['pulse_max_phonon']:.6f}")
    print('Final output:',jsonpath)
    print('source digest:',manifest['source_manifest_sha256'])
    print('NUMERICAL HEALTH GATES PASS')

if __name__=='__main__':
    main()

"""Run preregistered toy sweeps, output numerical evidence and provenance."""
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ws_qphonon_zeno.model import Model, attenuated_coupling, density_at, metrics, ideal_swap_time

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / 'results'
PLOTS = ROOT / 'plots'


def code_hash():
    paths = [ROOT / 'run_benchmark.py', *sorted((ROOT / 'ws_qphonon_zeno').glob('*.py')),
             *sorted((ROOT / 'tests').glob('*.py'))]
    values = [(str(p.relative_to(ROOT)), sha256(p.read_bytes()).hexdigest()) for p in paths]
    return sha256(json.dumps(values, sort_keys=True).encode()).hexdigest(), dict(values)


def simulate(m, t):
    return metrics(density_at(m, float(t)))


def main():
    RESULTS.mkdir(exist_ok=True); PLOTS.mkdir(exist_ok=True)
    t = ideal_swap_time()
    kappas = [0, .1, .5, 1, 2, 5, 20, 100]
    gammas = [0, .1, .5, 1, 2, 5, 20, 100]
    rows_k = [{'kappa_over_g': k, **simulate(Model(kappa=k), t)} for k in kappas]
    rows_g = [{'gamma_over_g': g, **simulate(Model(gamma_a=g, gamma_b=g, gamma_phonon=g), t)} for g in gammas]
    detunings = np.linspace(-10, 10, 81)
    rows_d = [{'delta_p_over_g': float(d), **simulate(Model(detuning_phonon=float(d), kappa=.2), t)} for d in detunings]
    d_over_att_len = [0, .25, .5, 1, 2, 4]
    rows_len = [{'distance_over_attenuation_length': d,
                 'g_b_over_g_a': attenuated_coupling(1, d),
                 **simulate(Model(g_b=attenuated_coupling(1, d), kappa=.2), t)} for d in d_over_att_len]
    sim_params = {'dimensionless_hbar': 1, 'g_a': 1, 'g_b_nominal': 1,
                  'nominal_evolution_time': t, 'model_basis': ['A', 'phonon', 'B', 'loss'],
                  'sweep_kappa': kappas, 'sweep_gamma': gammas,
                  'sweep_detuning_phonon': {'start': -10, 'stop': 10, 'points': 81, 'kappa': .2},
                  'sweep_distance_over_attenuation_length': d_over_att_len,
                  'distance_model': 'g_b = g_a * exp(-distance/(2 * attenuation_length))',
                  'distance_model_status': 'HEURISTIC_NOT_DEVICE_CALIBRATED',
                  'initial_state': '|A><A|', 'conditional_postselection': False}
    results = {
        'benchmark_id': 'WS-QPHONON-ZENO-TOY-001',
        'version': '0.1.0',
        'evidence_status': 'IMPLEMENTED IN SOFTWARE / SIMULATED ONLY',
        'hardware_validation': False,
        'published_paper_replication': False,
        'paper_context': [
            {'doi':'10.1063/5.0332643', 'role':'motivates phononic link study; NOT reproduced'},
            {'arxiv':'2512.14204', 'role':'motivates decoherence/Zeno comparison; cosmological model NOT reproduced'}
        ],
        'parameters': sim_params,
        'loss_sweep': rows_k,
        'dephasing_sweep': rows_g,
        'bus_detuning_sweep': rows_d,
        'heuristic_distance_sweep': rows_len,
        'caution': 'The finite 4-state Lindblad bus is not a Ge/Si COMSOL model, continuum waveguide, or inflationary scalar-field model.'
    }
    out = RESULTS / 'benchmark_results.json'
    out.write_text(json.dumps(results, indent=2, sort_keys=True) + '\n')

    fig, ax = plt.subplots(figsize=(7.6, 4.5))
    ax.semilogx([x['kappa_over_g'] for x in rows_k if x['kappa_over_g'] > 0],
                [x['qubit_b'] for x in rows_k if x['kappa_over_g'] > 0], 'o-', label='Transfer to B (phonon loss)')
    ax.semilogx([x['kappa_over_g'] for x in rows_k if x['kappa_over_g'] > 0],
                [x['qubit_a'] for x in rows_k if x['kappa_over_g'] > 0], 'o-', label='Retained at A (phonon loss)')
    ax.semilogx([x['gamma_over_g'] for x in rows_g if x['gamma_over_g'] > 0],
                [x['qubit_b'] for x in rows_g if x['gamma_over_g'] > 0], 'o--', label='Transfer to B (pure dephasing)')
    ax.set(xlabel='Rate / nominal coupling g (dimensionless)', ylabel='Unconditional population at ideal swap time',
           title='Four-state toy model: dissipation versus transfer', ylim=(0, 1.04))
    ax.legend(fontsize=8); ax.grid(True, alpha=.22); fig.tight_layout()
    fig.savefig(PLOTS / 'noise_sweep.png', dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.6, 4.1))
    ax.plot([x['delta_p_over_g'] for x in rows_d], [x['qubit_b'] for x in rows_d], label='Transfer to B')
    ax.plot([x['delta_p_over_g'] for x in rows_d], [x['environment_loss'] for x in rows_d], label='Environment loss')
    ax.set(xlabel='Phonon detuning / g', ylabel='Unconditional population at nominal swap time',
           title='Detuning sensitivity (κ/g = 0.2)', ylim=(0, 1.04))
    ax.grid(True, alpha=.22); ax.legend(); fig.tight_layout()
    fig.savefig(PLOTS / 'detuning_sweep.png', dpi=160); plt.close(fig)

    checksum, inputs = code_hash()
    manifest = {'benchmark_id': results['benchmark_id'], 'generated_at_utc': datetime.now(timezone.utc).isoformat(),
                'run_classification': results['evidence_status'],
                'code_digest_sha256': checksum, 'file_sha256': inputs,
                'parameters_sha256': sha256(json.dumps(sim_params, sort_keys=True).encode()).hexdigest(),
                'results_sha256': sha256(out.read_bytes()).hexdigest(),
                'artifacts': {p.relative_to(ROOT).as_posix(): sha256(p.read_bytes()).hexdigest()
                              for p in sorted(PLOTS.glob('*.png'))},
                'notes': 'No claims about physical hardware, material parameters, cosmology, or source-paper numerical reproduction.'}
    (RESULTS/'provenance_manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
    for row in rows_k:
        print(f"kappa={row['kappa_over_g']:>5}: B={row['qubit_b']:.6f}, A={row['qubit_a']:.6f}, loss={row['environment_loss']:.6f}")
    for row in rows_g:
        print(f"gamma={row['gamma_over_g']:>5}: B={row['qubit_b']:.6f}, A={row['qubit_a']:.6f}")
    print('benchmark:', out)
    print('code sha256:', checksum)


if __name__ == '__main__':
    main()

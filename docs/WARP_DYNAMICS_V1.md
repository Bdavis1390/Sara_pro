# Worldshepherd Warp Dynamics v1

## Purpose

This branch implements an adversarial reduced-model screening pipeline for warp/analogue dynamics. It does **not** claim a physical warp drive.

## Implemented

- Pressureless characteristic caustic benchmark.
- Passive wall-width bound.
- Global-damping operational rejection criterion.
- 1-D special-relativistic hydrodynamics (SRHD) with gamma-law EOS.
- HLL finite-volume fluxes.
- Explicit rejection of `gamma > 2` in the gamma-law model because the asymptotic sound-speed limit becomes acausal.
- Resolution-based shock-suspicion gate.
- Machine-readable promotion/claims states.

## Current result

The earlier nonrelativistic pressure proxy produced an apparent survivor around `gamma=3`, but this implementation rejects that EOS family as a general relativistic candidate.

In the causal SRHD search (`gamma=2`, compact candidate walls), pressure can trade compression against profile retention, but the steepening indicator grows materially with resolution. Therefore the current campaign does **not** promote a full reduced survivor.

This is a useful negative result: scalar pressure alone has not yet passed the combined density + operational-amplitude + causality + shock-convergence gates.

## Gate logic

A reduced candidate must simultaneously satisfy:

- `rho_max / rho0 <= 2`
- peak velocity retention `>= 0.90` through the five-baseline-caustic-time horizon
- `c_s < c`
- resolution gradient growth ratio `<= 1.50`

A passing reduced candidate still does **not** imply:

- Einstein constraint satisfaction;
- acceptable energy conditions;
- a physical source;
- measurable spacetime engineering;
- propulsion.

## Next promoted physics

1. Source-derived anisotropic stress rather than arbitrary scalar pressure.
2. Tilted relativistic flow models that are not equivalent to simple added swirl.
3. Einstein-constraint initial-data solve.
4. Full 3+1 evolution only after reduced-source gates pass.
5. Time-programmable bianisotropic optical analogue for controller validation.

## Run

```bash
python tools/warp_dynamics_reduced.py \
  --out warp_campaign.json \
  --csv warp_campaign.csv
```

Requires Python 3.10+ and NumPy.

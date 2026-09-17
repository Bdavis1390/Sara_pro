# Worldshepherd Constitutive Discovery v0.4

Status: `PROVEN INTERNALLY — SYNTHETIC ONLY`

Physical execution status: `PROPOSED_NOT_EXECUTED`

This research node is a bounded, synthetic-only working model for constitutive-law discovery. It tests whether a memoryless stress/strain model is inadequate, escalates to a controlled one-internal-state family, estimates the relaxation state equation, and compares model classes.

The node does **not** claim a new physical material law, does not identify a latent variable with a specific microstructural mechanism, and does not execute hardware.

## Run

```bash
python research/constitutive_discovery_v04/working_model.py
python -m pytest -q research/constitutive_discovery_v04/test_working_model.py
```

## Acceptance boundary

The synthetic benchmark hides a standard-linear-solid-like law:

`stress = E_inf*strain + E1*q`

`qdot = strain_rate - q/tau`

The discovery path compares a memoryless model against a controlled one-state family and requires a large held-out/training evidence margin before declaring that a latent state is required.

Any future physical adapter must preserve the repository doctrine: AI proposes, human approves, automation remains bounded, and actions/evidence are logged.
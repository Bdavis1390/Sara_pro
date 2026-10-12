# UC06-P1 Next-Generation R&D Objectives — 2026-09-30

Status: research planning only. No frozen scientific gate is changed.

## Evidence-derived architecture
Current D4 diagnostics support a functional split:
- TE: stable reference / angle-observable channel
- TM: state-programmable / sensitive discriminator channel
- TE/TM pair: self-referenced differential measurement primitive
- low-dimensional latent manifold: compact operational state representation

## Next-generation multi-objective cell target
Do not optimize only for phase range. Preserve TE reference behavior while increasing TM controllability.

Primary objectives:
1. maximize TE angular observability;
2. minimize TE state crosstalk;
3. increase TM state phase separation;
4. reduce TM numerical/model uncertainty;
5. preserve high reflection where required;
6. preserve polarization isolation;
7. maintain a SAFE_OPEN degraded state;
8. constrain geometry to realizable fabrication tolerances.

The present ~84 degree coarse TM phase span is treated as limited phase trimming/state modulation, not arbitrary beamforming. Future versioned studies may explore approximately 180 degree binary phase separation and eventually broader/full phase coverage. These are R&D targets, not UC06-P1 acceptance thresholds.

## Physical Jacobian campaign
For each selected physical parameter x, estimate both TE and TM derivatives:
- substrate permittivity and loss tangent
- substrate thickness
- bridge/gap/island dimensions
- installed component/package inductance
- conductor thickness/conductivity
- roughness/plating
- temperature
- finite coupon edges

Compute J_TE,x, J_TM,x and the differential J_delta,x = d(S_TM-S_TE)/dx.
Purpose: test whether the numerically observed TE/TM asymmetry becomes a physically useful self-referenced sensing architecture.

## Sparse-tone operational interrogator
D5 will determine whether a small deterministic tone set can preserve the geometry of the 161-point complex spectral manifold.
If supported, separate modes:
- audit/calibration mode: full 161-point sweep;
- operational mode: sparse 2-8 tone I/Q interrogation;
- ECHO mode: compact latent state vector plus provenance.

## Latent surrogate and inverse design
Use full-wave Palace results as authoritative forward evidence. A surrogate may propose candidate designs but never validate them.
Pipeline:
geometry/material/state -> latent coordinates -> reconstructed S11 spectrum -> Palace verification.

Candidate optimization objectives should include angle observability, polarization isolation, TM phase span, TE state invariance, refinement robustness and fabrication constraints.

## Finite-array progression
Only after unit-cell convergence and model-discrepancy work:
- finite aperture synthesis
- beam/focus/scattering patterns
- sidelobes and scan loss
- mutual coupling
- near-field behavior
- RCS where applicable

## Hardware progression
After numerical gates:
- coupon/VNA correlation
- uncertainty budget
- repeatability/reproducibility
- physical perturbation/Jacobian validation
- sparse-tone hardware feasibility
- self-sensing closed-loop prototype

## Frontier alignment
2026 literature increasingly frames dynamic/intelligent metasurfaces as programmable RF front ends supporting sensing, imaging, communications, wave-domain processing and autonomous/cognitive control. Worldshepherd should differentiate by maintaining governed autonomy: SARA proposes/optimizes, PRIME authorizes, ECHO preserves provenance, OVERWATCH displays evidence/confidence.

## Claims boundary
- no claim of full convergence
- no hardware validation claim
- no intrinsic-dimension claim beyond tested ensemble
- no arbitrary beam-steering claim
- no PUF claim
- no topological claim for current geometry
- no Shannon-information claim
- no H2 promotion
- no full-campaign authorization
- active A027-A054 recovery remains independent

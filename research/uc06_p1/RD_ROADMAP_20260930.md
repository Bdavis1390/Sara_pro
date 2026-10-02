# UC06-P1 Worldshepherd R&D Roadmap — 2026-09-30

Status: diagnostic R&D planning only. This document does not alter any frozen UC06-P1 convergence gate, does not promote H2, and does not authorize the full campaign.

## Current internal evidence basis

From D4:
- first 2 principal components explain 97.4061% of coarse-ensemble spectral variance
- first 3 principal components explain 99.4613%
- strongest validation-aware angle discriminator: LOW_C TE 0° vs 60°, Q = 230.2389
- strongest modeled median polarization isolation: 70.0178 dB
- largest coarse TM state phase span: 83.9532°
- LOW_C TM/TE coarse-to-medium RMS refinement sensitivity ratio reaches 45.5859 at 60°
- TE LOW_C vs HIGH_C state discrimination at 0° and 30° is negligible relative to the refinement-uncertainty proxy

Working architecture:
- TE: reference / angle-sensing channel
- TM: state-control / sensitive discriminator channel
- TE+TM: self-referenced differential instrument
- low-dimensional latent manifold: compact operational state representation

## Frontier-informed R&D work packages

### WP1 — Polarization-separated co-design
Goal: preserve TE state-invariance and angle observability while increasing useful TM state phase span.

Future-version design objectives, not current validation thresholds:
- preserve high TE angular discriminability
- minimize TE response change across control states
- increase TM state phase span beyond the current ~84°
- preserve high reflected magnitude
- reduce TM mesh/model sensitivity

External precedent:
- 2025 adaptively programmable metasurface: element-level sensing plus wave manipulation, full phase range, reflection magnitude >0.84
  https://www.nature.com/articles/s41467-025-61409-6
- physics-informed inverse design of programmable metasurfaces: ~300° phase tuning with >90% reflection demonstrated in a different THz platform
  https://doi.org/10.1002/advs.202406878

### WP2 — D5 interaction-channel discovery
Resolve PC1-PC3 into state, polarization, angle, and interaction terms.

Primary hypothesis classes:
- polarization × angle -> joint polarimetric orientation sensing
- polarization × state -> polarization-selective actuation
- state × angle -> incidence-conditioned control
- three-way interaction -> context-sensitive physical challenge-response

No causal claim from descriptive factorial decomposition.

### WP3 — Sparse-tone interrogator
Use D5 to determine whether a small deterministic set of frequencies preserves the geometry of the 161-point complex spectrum.

If supported, develop a versioned operational concept:
- full 161-point sweep remains calibration/audit standard
- sparse 2–8 tone set becomes low-power operational self-test

Potential benefits:
- lower latency
- lower RF frontend complexity
- lower energy use
- faster autonomous health checks
- reduced telemetry bandwidth
- better swarm/space integration

Same-data sparse-frequency selection is not held-out validation.

### WP4 — Differential electromagnetic metrology
Test whether the TE/TM asymmetry survives physical parameter perturbations.

One-factor-at-a-time candidates:
- substrate permittivity and loss tangent
- substrate thickness
- bridge width / gap / island geometry
- package inductance
- copper thickness / conductivity
- roughness / plating
- temperature
- finite-edge/coupon geometry

Compute for each physical variable x:
- dS_TE/dx
- dS_TM/dx
- differential sensitivity d(S_TM-S_TE)/dx

Purpose: determine whether TE can serve as a common-mode reference while TM provides high physical sensitivity.

External precedent: differential microwave sensing is used to suppress measurement/environmental errors in dielectric characterization.
- https://www.sciencedirect.com/science/article/pii/S092442472401121X
- https://www.sciencedirect.com/science/article/pii/S0924424725001876

### WP5 — Physics-informed inverse design / surrogate loop
Exploit the empirically low-dimensional spectral manifold rather than fitting a black-box model directly to all 322 real spectral features.

Proposed representation:
geometry/material/state -> latent z1,z2,z3 -> reconstructed complex S11

Then solve inverse problems:
- desired TE angle observability + low state crosstalk
- desired TM state phase span + high reflected magnitude
- robustness to tolerance perturbations
- reduced TM numerical sensitivity

Use Palace as the authoritative forward solver for training/verification; surrogate predictions never replace full-wave validation.

External precedent:
- physics-informed periodic-structure inverse design, IEEE T-MTT 2025
  https://doi.org/10.1109/TMTT.2024.3435970
- physics-informed programmable metasurface inverse design
  https://doi.org/10.1002/advs.202406878
- 2026 physics-informed reactively loaded metasurface design preprint
  https://arxiv.org/abs/2603.15430

### WP6 — Self-sensing closed-loop surface
Longer-term hardware architecture:

incident field -> TE reference/angle sensing -> SARA inference -> PRIME authorization -> TM/control state -> RF verification -> ECHO provenance -> OVERWATCH confidence

External experimental precedent:
- self-adaptive metasurface that senses direction of arrival and adjusts reflection using a phase comparator + lookup table; ±50° experimental sensing/control and reported 415 mW power in that prototype
  https://pmc.ncbi.nlm.nih.gov/articles/PMC12407367/
- adaptively programmable metasurface with integrated complex-field sensing and manipulation
  https://www.nature.com/articles/s41467-025-61409-6

### WP7 — ISAC / space-time extension
Do not alter current static UC06-P1 model. Create a separate future architecture if time modulation is pursued.

Potential capability:
- carrier/fundamental channel for communications/control
- generated harmonic channels for sensing or identification

External precedent:
- 2025 space-time-coding metasurface ISAC demonstration
  https://www.nature.com/articles/s41467-025-57137-6

Classification for current UC06-P1: SPECULATIVE EXTENSION.

### WP8 — Material and health sensing
If WP4 establishes physical differential sensitivity, evaluate:
- dielectric characterization
- moisture/contamination sensing
- coating/plating condition
- structural deformation
- thermal drift
- aging/corrosion
- manufacturing QA

External precedent includes reflective single-port complex-permittivity sensing and polarization-based microwave dielectric sensing, but those results do not validate UC06-P1 for those uses.

### WP9 — Manifold anomaly detector
After experimental repeatability is available, enroll the healthy latent manifold M_healthy.

Operational statistic:
- latent displacement along the manifold -> known state/environment variation
- reconstruction residual / off-manifold distance -> possible unknown fault, tamper, contamination, damage, or model discrepancy

Required before deployment:
- repeated measurements
- temperature/environment envelopes
- multiple units
- false-positive/false-negative analysis
- held-out fault conditions

### WP10 — Governed active-learning experiment selection
SARA selects the next simulation or lab measurement by expected uncertainty reduction per resource cost.

Candidate utility variables:
- numerical uncertainty reduction
- model-discrimination value
- compute-hours
- lab-hours
- energy
- calendar time

PRIME must authorize experiment classes; ECHO must preserve inputs, outputs, hashes, failures, and negative findings.

## Validation sequence

1. Finish A027-A054 recovery.
2. Execute D5 interaction + sparse-frequency diagnostics on the completed prefix as preregistered.
3. Adjudicate frozen medium-to-fine complex S11 and resonance gates when all required results exist.
4. Inspect energy-output schema before calculating frozen energy closure.
5. Only after numerical convergence: open versioned physical-parameter discriminator campaign.
6. Then design VNA/coupon validation with uncertainty and registration closed before correlation claims.

## Claims boundary

Current UC06-P1 supports simulation-derived evidence for angular observability, polarization isolation, TM state separability, limited TM phase programmability, low-dimensional spectral structure, and TE/TM differential numerical sensitivity.

It does not yet establish:
- experimental sensing accuracy
- material-property sensitivity
- hardware repeatability
- beam steering
- PUF behavior
- absorption
- nonreciprocity
- nonlinear/time-modulated functions
- space qualification
- medium-to-fine convergence

Overall convergence remains NOT ADJUDICATED.

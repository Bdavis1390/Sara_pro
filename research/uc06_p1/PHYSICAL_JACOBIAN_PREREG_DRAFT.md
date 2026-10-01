# UC06-P1 Physical Jacobian Campaign — Draft Preregistration

Status: DRAFT / NOT AUTHORIZED FOR EXECUTION

Purpose: determine whether the TE/TM asymmetry seen in UC06-P1 numerical refinement becomes a physically useful differential sensing/metrology property when actual material, geometry and environmental parameters are perturbed.

## Preconditions
Do not execute this campaign until:
1. A027-A054 recovery is complete and evidenced;
2. frozen medium-fine convergence is adjudicated;
3. energy closure is adjudicated;
4. the retained baseline model/version is explicitly identified;
5. no parameter is silently retuned to improve agreement.

## Baseline doctrine
- Palace/full-wave model is authoritative for simulation evidence.
- One physical discriminator is varied at a time for the primary Jacobian study.
- All perturbation values are selected before numerical outputs are inspected.
- TE and TM are both retained for every discriminator.
- 0, 30 and 60 degree incidence remain the initial angular set unless separately versioned.
- LOW_C, HIGH_C and SAFE_OPEN remain explicit states where the physical parameter permits them.
- Failed solves, solver warnings and boundary minima remain visible.
- The retained baseline is one shared 3-state x 2-polarization x 3-angle matrix (18 conditions), referenced by every perturbation. Repeating nominal baselines under different parameter labels does not create independent baseline evidence.

## Initial discriminator variables
A. substrate relative permittivity
B. substrate loss tangent
C. substrate thickness
D. bridge width / gap / island dimensions
E. installed component/package inductance
F. conductor thickness
G. conductor conductivity
H. roughness/plating model
I. temperature-dependent electrical properties
J. finite coupon-edge geometry

## Continuous derivatives versus model comparisons
A Jacobian is only claimed for an explicitly numeric, continuous parameter with units and a preregistered finite-difference scheme.

For continuous parameters, preregister before execution:
- parameter identifier and units;
- retained baseline value;
- FORWARD or CENTRAL difference scheme;
- all perturbation values.

For bridge geometry, width, gap, island width and island length are separate one-factor discriminators. They are not changed together in the primary Jacobian experiment.

Roughness/plating model choices are categorical model-discrepancy comparisons unless a separately defined continuous roughness or plating parameter is introduced and preregistered. A categorical model switch is not reported as dS/dx.

Finite coupon-edge geometry may be treated as a continuous parameter only when a numeric edge dimension is explicitly defined; otherwise it is a versioned model comparison.

No derivative scheme or perturbation amplitude is selected after response data are viewed.

## Primary outputs
For continuous parameter x and each retained frequency point:
- J_TE,x = dS_TE/dx
- J_TM,x = dS_TM/dx
- J_delta,x = d(S_TM-S_TE)/dx
- magnitude sensitivity
- wrapped phase sensitivity
- resonance movement where evaluable
- numerical-conditioning telemetry

For categorical model-discrepancy comparisons:
- complex spectral difference from the exact retained baseline;
- magnitude and wrapped-phase difference;
- resonance movement where evaluable;
- numerical-conditioning telemetry;
- explicit model/context identifiers.

Categorical comparisons are not labeled Jacobians.

## Differential-sensing question
Test whether there exist physical variables x for which:
1. |J_TM,x| is materially larger than |J_TE,x|;
2. the TE response remains sufficiently stable to serve as a reference channel;
3. the differential response survives mesh refinement and measurement uncertainty;
4. the relationship is reproducible in hardware.

No fixed sensitivity-ratio threshold is created in this draft. Thresholds, if needed, must be preregistered before results are viewed.

## Candidate applications if supported
- self-referenced dielectric metrology
- manufacturing QA
- coating/plating condition monitoring
- structural/deformation sensing
- contamination detection
- thermal/aging monitoring
- tamper detection
- model-discrepancy localization

## Explicit non-claims
This campaign does not assume that numerical mesh sensitivity equals physical sensitivity.
It does not assume TM will remain the more sensitive physical channel.
It does not establish a PUF, structural-health sensor, material sensor or hardware anomaly detector without physical validation.
It does not treat categorical model switches as physical derivatives.

## Hardware validation path
After converged simulations:
1. fabricate nominally identical coupons;
2. record full complex VNA spectra with uncertainty budget;
3. repeat across devices and sessions;
4. apply controlled perturbations corresponding to simulation variables;
5. compare intra-device repeatability, inter-device variability and predicted Jacobians;
6. test sparse-tone subsets only after full-spectrum validation.

## Governance
SARA may propose candidate discriminators and experiment order.
PRIME authorizes execution and prevents unregistered parameter tuning.
ECHO stores config/mesh/binary/output hashes, transformation history, model context and physical measurement provenance.
OVERWATCH displays sensitivity, uncertainty and evidence status.

## Claims boundary
DRAFT ONLY.
NO NUMERICAL EXECUTION AUTHORIZED BY THIS DOCUMENT.
NO LAB EXECUTION AUTHORIZED BY THIS DOCUMENT.
NO SCIENTIFIC GATE CHANGED.
NO H2 PROMOTION.
NO FULL CAMPAIGN AUTHORIZATION.

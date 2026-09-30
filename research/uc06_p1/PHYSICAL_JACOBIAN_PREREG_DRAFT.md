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

## Primary outputs
For parameter x and each retained frequency point:
- J_TE,x = dS_TE/dx
- J_TM,x = dS_TM/dx
- J_delta,x = d(S_TM-S_TE)/dx
- magnitude sensitivity
- wrapped phase sensitivity
- resonance movement where evaluable
- numerical-conditioning telemetry

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
ECHO stores config/mesh/binary/output hashes and physical measurement provenance.
OVERWATCH displays sensitivity, uncertainty and evidence status.

## Claims boundary
DRAFT ONLY.
NO NUMERICAL EXECUTION AUTHORIZED BY THIS DOCUMENT.
NO LAB EXECUTION AUTHORIZED BY THIS DOCUMENT.
NO SCIENTIFIC GATE CHANGED.
NO H2 PROMOTION.
NO FULL CAMPAIGN AUTHORIZATION.

# RFC frequency-exchange hypothesis — evidence-controlled research note

Date: 2026-10-20
Authority: CRE1AWS
Status: HYPOTHESIS / SIMULATED ONLY / REQUIRES LAB VALIDATION

## Objective
Test whether paired resonant-field excitations can cause reproducible energy redistribution and coupled electromagnetic, thermal, mechanical, electrical or magnetic material responses. Historical frequency pairs were reported by the researcher; original experimental records are currently unavailable. Do not treat these as independently reproduced observations.

## Historical researcher-reported pairs (GHz)
- 0.953 and 0.242
- 0.396 and 0.993
- 3.96993 and 9.53242

Do not infer that 'convergence' denotes linear-solver convergence. Distinguish physical response, mode coupling, and numerical convergence. No unique physical exchange law has been established.

## Palace simulation evidence
Campaign: UC06 P1 reconstruction, Palace 0.17.0, 9.2–10.8 GHz nominal frequency sweep. Previously inspected completed cases A027–A035 (nine EXIT0 job records). EXIT0 and recorded S-parameters do not establish numerical convergence, energy conservation, multiphysics material change, or laboratory performance.

A036 (TM 60-degree) was still running at last verified inspection, with provisional data through 9.54 GHz; it must not be included among completed runs until a job receipt exists. Existing 0.01 GHz frequency step does not sample 9.53242 GHz exactly. Frequencies below 9.2 GHz are outside this campaign.

## Reanalysis requirements
1. Inventory immutable job receipts, configs, solver logs, port-S, port-floquet-S, port-I, port-V, domain-E, and error-indicator files; compute SHA-256 manifests.
2. Parse channel identities, propagating versus evanescent Floquet orders, reference impedances, phase and power normalization. NaN/-inf entries require explicit interpretation, not zero-filling.
3. For each frequency, TE/TM and incidence angle, account for incident, reflected, transmitted, dissipated and unaccounted power; verify passivity/reciprocity only where applicable.
4. Compare complete channel power vectors and phase, not isolated S[8][1] magnitudes. Check convergence warnings and mesh/solver sensitivity.
5. Independently test exact 9.53242 GHz and the other five reported frequencies with matched geometry, appropriate material dispersion, excitation and boundary conditions; do not disrupt running Palace.
6. Compare field A only, B only, both and no-field controls; record phase detuning, power, thermal drift, strain, conductivity and magnetic response when instrumented.
7. Distinguish ordinary heating and measurement artifacts from coherent/nonlinear field–matter coupling. Use independent reproduction before physical claims.

## Governance
AI proposes; CRE1AWS approves; bounded execution; evidence logged. No external submission, funding claim, material-performance claim, or partner-validation assertion from this note. Public-repository material only; no confidential historical source data.

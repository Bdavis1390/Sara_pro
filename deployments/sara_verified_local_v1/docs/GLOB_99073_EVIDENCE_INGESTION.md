# Glob 99073 Evidence Ingestion Contract

**Status:** Active research-control artifact  
**Schema:** `ws-glob-evidence-1.0`  
**Effective:** 2026-08-16  
**Transform:** five-position permutation `12345 -> 31542` (`[3,1,5,4,2]`)

## Purpose

This contract makes Glob 99073 research operational inside Worldshepherd. A discovered publication, dataset, measurement, equation, identifier, security advisory, negative result, or failed search is not merely collected: it is assigned a documented Worldshepherd use and a claims-control status.

The rule is **use everything without pretending everything is evidence**.

## Required routing

Every discovery must be routed to at least one of:

- **SARA:** deterministic transform execution, ingestion, schema validation, and research workflow orchestration.
- **ECHO SENTINEL LINK:** source provenance, source identifiers, observed values, units, deltas, and evidence lineage.
- **PRIME SENTINEL:** claims gates and promotion/demotion of evidence status.
- **OVERWATCH:** replay, comparison, null-model metrics, hit-rate monitoring, false-positive monitoring, and relational-closure visualization.
- **Security hardening:** CVEs, vulnerable dependencies, parsing risks, and configuration constraints found while researching.
- **Materials / characterization:** spectroscopy, atomic/molecular levels, transition data, mechanical/material properties, and characterization methods.
- **Quantum-device characterization:** imaging, transport, dopant characterization, and other reusable device measurement techniques.
- **Negative-control corpus:** metadata/identifier collisions and unrelated number matches used to train and test discrimination.
- **Partner/opportunity intelligence:** laboratories, authors, data infrastructures, and facilities that could support validation.

## Evidence classes

| Class | Meaning | Evidence weight |
|---|---|---|
| `P2` | Physical relational closure in the same system | Candidate high-value evidence; significance still requires a null model |
| `P1` | Physical-value match/near-match with units and provenance | Candidate evidence; multiple-testing correction mandatory |
| `G1` | Exact mathematical graph closure among generated states | Structural information only; no physical causality |
| `M1` | Scientific/technical metadata collision | Zero physical-evidence weight; use as control and/or domain intelligence |
| `N0` | Incidental identifier/registry/report/product collision | Zero physical-evidence weight; retain as negative control |

## Claims-control rules

1. **No orphan discoveries.** Every source must have `worldshepherd_uses` or an explicit negative-control role.
2. **No silent promotion.** A DOI, arXiv number, CVE, CAS number, article number, page number, accession number, or product number cannot become P1/P2 evidence merely because its digits match.
3. **Preserve provenance.** Keep exact seed, contiguous window, orbit state, source identifier, observed value, unit, delta, and verification status.
4. **Preserve leading zeros.** Exact `9675` remains a four-digit seed. A derived `09675` normalization, if used, is a separate object and never replaces `9675`.
5. **Near matches need tolerance disclosure.** Record the numerical delta and the reason the tolerance is scientifically defensible.
6. **Counterevidence is first-class.** Failed exact searches, current-authority disagreements, and null-model results remain in the registry.
7. **Current authority beats memory.** Historical values may be retained, but disagreements with current authoritative compilations trigger reconciliation rather than silent substitution.
8. **No causal inference from occurrence.** The transform is not claimed to generate physical spectra without independent statistical and experimental support.
9. **Relational structure outranks raw hit count.** Shared levels, Ritz relations, transition networks, and independently derived same-system closures are the priority.
10. **Promotion gate.** A substantive scientific claim requires a predeclared null model, corrected significance, robustness to tolerances, independent datasets, and preferably experimental replication.

## Current W II calibration

The 1964 W II study reports 2,173 classified lines spanning 1756.6–6219.77 Å. For the currently expanded target graph there are 112 unique five-digit states, 41 of which fall within the corresponding W II wavenumber range.

Under a deliberately crude uniform-density baseline, the expected number of random matches is approximately:

- ±0.05 cm⁻¹: 0.218
- ±0.10 cm⁻¹: 0.436
- ±0.50 cm⁻¹: 2.181
- ±1.00 cm⁻¹: 4.362
- ±2.00 cm⁻¹: 8.724
- ±5.00 cm⁻¹: 21.810

Selected generated-state matches are:

- `30979 -> 30979.40 cm^-1`
- `41494 -> 41494.48 cm^-1`
- `39699 -> 39699.84 cm^-1`

Therefore **raw W II hit count is not presently anomalous** under this baseline. The higher-value feature is that the `39699.84` and `41494.48 cm^-1` lines share the same lower W II level (`a^4P_(3/2)`), despite their target states coming from different seed families.

The next statistical test is a **topology-preserving null**: compare the observed shared-level/transition-network closure rate against matched random target sets while preserving target count and numerical range.

## Security byproduct

The `30979` search surfaced `CVE-2026-30979`, an iccDEV heap-based buffer overflow fixed in iccDEV 2.3.1.5. This is **not** physics evidence. It is routed to Worldshepherd security hardening because ICC-profile parsing is relevant to image/steganography workflows. If iccDEV is introduced into that stack, Worldshepherd should gate versions below 2.3.1.5.

The adjacent `CVE-2026-30978` is also retained as same-component hardening intelligence.

## Source reuse examples

- `arXiv:2208.09379`: the `09379` substring is M1 metadata, but the publication contributes non-destructive X-ray fluorescence imaging methodology for dopant/quantum-device characterization.
- NIST CAS `56977-48-1`: the number is N0 metadata and becomes a negative-control partner for the historical Yb II `56977` spectroscopy occurrence.
- eLife `e79305`: article-number collision is M1, while its open-source behavioral-video-analysis methodology can inform OVERWATCH video-analysis practices.
- DOE OSTI API documentation: routed to SARA/ECHO as a machine-to-machine source-ingestion mechanism.
- LANL facility-monitoring testbed publication: routed to OVERWATCH/ECHO as precedent for remote sensor monitoring, precursor fault detection, and alarm reasoning.
- Army `Spall Strength of Tungsten Carbide`: routed to the materials database, not to number-pattern evidence.

## Machine-readable record

The canonical initial ledger for this work is:

`data/research/glob_99073_registry.json`

Future discoveries should extend that ledger rather than creating disconnected notes.

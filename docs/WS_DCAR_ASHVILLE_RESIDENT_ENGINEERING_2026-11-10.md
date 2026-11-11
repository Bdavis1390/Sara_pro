# WS-DCAR-ASH-001 — Resident-led engineering design and assurance protocol
**Date:** 2026-11-10 | **Status:** engineering proposal + synthetic calculation prototype; not a deployed field system
**Governance:** child of #283 (ACTIVE 3/3); technical dependencies #281/#282, existing WS-DCAR #525 / PR #524.
**Public scope:** Ashville, Ohio; EdgeConneX data-center proposal and separate PowerConneX 26-196-EL-BGN application.

## Purpose and protections
This is an open independent engineering effort to examine measurable harms, alternative designs and legally available options—including **NO BUILD**—with interested local participants, without attempting to influence voting or invalidate the November 3 referendum. No participant is asked how they voted. Benefits, paid apprenticeships, procurement or investment are not conditioned on political opinions, project approval or support.

The village referendum rejected Resolution 06-2026's project term summary by roughly 82%. Separate moratorium/land-use and power siting issues require legal review. Project planning is NOT authority to construct/operate or proof of environmental safety.

References:
- https://www.wosu.org/2026-11-10/heres-how-every-data-center-related-ballot-measure-fared-in-ohio
- https://courtnewsohio.gov/cases/2026/SCO/0807/260906.asp
- https://opsb.ohio.gov/cases/26-196-el-bgn
- https://puco.ohio.gov/utilities/electricity/resources/data-centers
- https://epa.ohio.gov/divisions-and-offices/surface-water/permitting/npdes-general-permits

## Design and experimental matrix
| Concern | Candidate engineering response | Minimum qualified evidence | Independent decision gate |
| --- | --- | --- | --- |
| Electric bills and grid | reduce peak load through IT job scheduling, UPS/battery coordination, thermal storage; project-funded upgrade guarantees/collateral; no unreviewed cost transfer | hourly metering/forecast, actual load ramp, tariff and interconnection agreement, cost-of-service model with sensitivity | independent utility economics review; household bill effects remain UNKNOWN before review |
| Water and wastewater | compare dry / hybrid / water-based closed-loop heat rejection; reclaimed water only if suitable and permitted | IT heat balance, local hourly weather, evaporation/blowdown/drift, raw/reclaimed intake, permits, cooling WUE, water chemistry/discharge, drought reliability | professional thermal/water engineer and qualified permits review |
| Air quality and carbon | compare no-build, reduced load, altered supply/generation, pollution-control technologies | actual generating source, dispatch, gas composition, permit limits, stack and ambient modeled NOx/PM/CO2e, upstream burden | qualified air specialist/regulator; no claim of compliant emissions from simulation alone |
| Acoustic and lighting impacts | quieter chiller/tower equipment, fan speed scheduling, acoustic enclosures, barriers, setback/site orientation, luminaire shielding | calibrated sound baseline (day/night, tonal/low-frequency/peak), mapped receptors around homes, schools and recreational areas, lighting model | independent acoustician/photometric expert, on-site confirmation |
| Land, traffic and flood | alternative physical layout and use; site setbacks, stormwater management, traffic routing and construction-hour limits | zoning, parcel, habitat, drainage and flood studies, school pedestrian safety, truck count | municipal/legal and environmental experts |
| Local jobs/prosperity | paid citizen-measurement training, independent technical co-design, local supply chain and transparent public-benefit projects | signed paid-work terms, actual hours/wages, procurement registers, legal review, independent community governance | no unsupported employment/tax/revenue claims |
| Transparency and privacy | publish evidence ledger, measurement metadata, revisions and unresolved concerns; least-privilege resident data | reviewer-selection policy, hashes, redaction log, consent records, field uncertainty & independent reproducibility | community-appointed reviewers maintain right to adverse findings |

## Concrete technical plan
1. **Survey** open-to-all technical issue intake (opt-in) with alternatives and no voter preference fields, challenge process and accessible public summary.
2. **Model** at least NO-BUILD, phased development, dry/hybrid cooling, demand-responsive supply, and alternative siting/scales with explicit uncertainty, costs, data gaps.
3. **Instrument** no site without permission. Before any field work: meter and sensor register (identity, calibration, timestamp), power-grid boundary, water in/out, acoustic receptors, weather and data custody.
4. **Verify** evidence via WS-DCAR fail-closed partner-event intake, SARA/PRIME authorization, ECHO provenance and PRE concern-to-test traceability. OVERWATCH may render clearly labeled simulations and actual results separately; no mixing.
5. **Independent specialist review** for utility tariffs, industrial thermal/water design, atmospheric emissions, acoustics and land use. Engineering results may show a mitigation is impractical.
6. **Share** report with technical conclusions, errors and dissent protected from funder veto. Commercial and community-benefit negotiations remain separate from permits and evidence review.

## Transparent starting calculation — purely synthetic
Use the isolated community-engineering prototype (Python stdlib + 7 passing unit tests, external package), to estimate from declared hypothetical assumptions:
- Annual facility energy (MWh) = IT load (MW) × 8760 h × IT utilization × PUE.
- Direct cooling water (m3/y) = annual IT energy (MWh) × WUE (L/IT-kWh). This equivalence follows 1 MWh = 1000 kWh and 1000 L = 1 m3.
- Undefined household bill and environmental compliance effects always remain **UNKNOWN** / **NOT_ASSESSED**.

Screening examples (fictional, NOT from EdgeConneX/utility/site):
| Option | IT MW | PUE | Utilization | WUE L/IT-kWh | facility MWh/y | cooling m3/y |
|---|---:|---:|---:|---:|---:|---:|
| No-build | 0 | 1.0 | 0 | 0 | 0 | 0 |
| Illustrative evaporative | 100 | 1.25 | 0.8 | 1.50 | 876,000 | 1,051,200 |
| Illustrative dry | 100 | 1.35 | 0.8 | 0.05 | 946,080 | 35,040 |
| Illustrative phased | 40 | 1.28 | 0.6 | 0.40 | 269,107 | 84,096 |

Interpretation: in this *fabricated sensitivity study* dry cooling reduces direct cooling-water demand but increases electrical consumption because assumed PUE rises. This illustrates a trade-off, not a measured savings estimate or recommendation for any Ohio site. Actual engineering requires climate, water source, cooling design, seasonal reliability, dispatch, environmental and cost evidence.

## No overclaims
WS-DCAR has software and synthetic tests, not an approved on-site system. No representation of independent validation, utility approval, emissions compliance, construction permits, or support from Ashville residents. Utility ratepayer protection mechanisms exist but no assessment of whether and how they govern this proposal has yet been completed. A possible 800 MW generating application is a maximum nameplate proposal, NOT the facility's measured demand or contracted grid load.

## Next gates (blocking)
- [ ] Obtain authoritative current planning/permit data and Ohio legal review of the referendum/moratorium.
- [ ] Publish an open invitation co-developed with genuine local stakeholders; keep all viewpoints welcome.
- [ ] Resident-informed criteria and independent conflicts charter.
- [ ] Seek only a modest consented partner data bundle with measurement boundary; retain missing evidence.
- [ ] Commission engineers to test at least two physical mitigation configurations **and** a no-build baseline.
- [ ] Report whether the proposed interventions meet independently defined targets. Negative outcomes are equally valid.

Commercial outreach status: **existing EdgeConneX draft amended in place, UNSENT**. No public or targeted voter contacts have been sent.

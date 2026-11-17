# WorldShepherd scientific evidence: corrected spin-polarization observable (Phase V)
**Date:** 2026-11-17 | **Umbrella:** #282 Science & Validation | **Status:** THIRD-PARTY PUBLISHED DATA REANALYSIS — NO ORIGINAL PHYSICAL MEASUREMENT OR ADVANCE PREDICTION.

## Source custody
- [Qiu et al. 2026 Nature Photonics paper](https://doi.org/10.1038/s41566-026-02027-6), received **2026-02-04**, published **2026-10-15**.
- [Original publisher Source Data Figure 4 XLSX](https://static-content.springer.com/esm/art%3A10.1038%2Fs41566-026-02027-6/MediaObjects/41566_2026_2027_MOESM3_ESM.xlsx): 59,599 bytes; SHA-256 `25530a1482361ebeeadb8567a2bb7715415e4a2df939e97fb5aff3c02a8c22a1`.
- [Original 42-page Supplementary Information PDF](https://static-content.springer.com/esm/art%3A10.1038%2Fs41566-026-02027-6/MediaObjects/41566_2026_2027_MOESM1_ESM.pdf): 17,252,893 bytes; SHA-256 `75c6021f50d91023df4145bc7798039a0dc331ba858f2f5cdf9331a9a9f01c5b`.
- Originals hash- and ZIP-verified on authorized workstation; original XLSX/PDF are **not** copied into this public repository.

## Correction to Phase IV
Supplementary Equation S7 defines spin polarization as the **normalized** circular transient-absorption contrast, `P(t)=(CC(t)-SC(t))/(CC(t)+SC(t))`. The earlier Phase IV fit treated `CC-SC` alone as the decay observable. It was not directly comparable with this normalized P. Use the corrected observable for interpretation.

The Figure 4a/b publisher sheet contains **148 C-MQWs** and **106 C-SQW** data records with SC, CC, and diff. columns. Reanalysis checked diff ≈ CC−SC at original source precision. After-publication model: `P(t)=A exp(-(t-t0)/tau)+C`; grid-search tau between 0.2 and 30,000 ps, linearly fit amplitude and optional offset, interleaved holdout every fifth point.

| Sample / window | Free-offset handling | Fitted tau | Within-curve holdout RMSE |
|---|---|---:|---:|
| C-MQWs / 20–4,999.54 ps | C fixed to zero | **5,371.65 ps** | 0.0062388 |
| C-MQWs / same | C free | **2,619.60 ps** | 0.0063809 |
| C-MQWs / 100–4,999.54 ps | C fixed to zero | 5,280.94 ps | 0.0092132 |
| C-MQWs / same | C free | 2,260.14 ps | 0.0069673 |
| C-SQW / 1–20 ps | C fixed to zero | 7.11 ps | 0.01083 |
| C-SQW / same | C free | 5.84 ps | 0.0120096 |

**Meaning:** With the physically normalized observable, a zero-offset fit gives ~5.37 ns, close to the paper's ~5 ns. **Not unique:** a free-offset model gives ~2.62 ns with comparable holdout error. The C-SQW source-curve fits do not reproduce the paper's reported ~16 ps value under these assumptions. Postpublication selection, instrument response, structural/sample differences, uncertainty, and fit identifiability remain unresolved. Do **not** claim exact physical lifetime replication; interleaved time samples are correlated and not independent sample replication.

## Physical mechanism, not historical priority
Supplementary Note 1 attributes improved spin preservation to a smaller interwell excess-energy step and the D’yakonov–Perel’ rate regime. The authors give roughly **0.8 eV** for direct single-well energy transfer, about **0.12 eV** minimum step energy for the cascade, and ~16 ps versus ~5 ns lifetimes. Using **authors' published inputs**, the cubic asymptotic estimate gives `16 ps*(0.8/0.12)^3 = 4740.74 ps ≈ 4.74 ns`, about **5.19% below** ~5 ns. Supplementary Fig. 18 reports an ~1.5 ps transfer time. This model arithmetic is a *postpublication* mechanism check, not earlier WorldShepherd prediction. A numerical similarity with a previously proposed dimensionless phonon-bus transfer model does not establish a shared microscopic physical mechanism.

## BTO boundary and public chronology
- [Kang et al., ACS Photonics 2026](https://doi.org/10.1021/acsphotonics.6c01514) models the effective multidomain optical response via **three tetragonal variants**. The earlier WorldShepherd two-domain scalar toy cannot reproduce its Mueller-matrix measurements or complex optical tensor. No validated source tensor `n_o/e(lambda),kappa_o/e(lambda)` has yet been ingested.
- The group had publicly presented ordinary/extraordinary BTO ellipsometry at a **2025** conference; see [KAIST's 2025 conference record](https://pure.kaist.ac.kr/en/publications/optical-characterization-of-barium-titanate-from-the-visible-to-m/). This predates the **2026-08-06** WorldShepherd BTO material screen. The screen establishes candidate-selection history, **not research priority for optical metrology**.

## Next falsifiable gate
Prospectively preregister the conditional `T_spin ∝ (ΔE)^−3` slope in its theoretical domain with multiple *new, independent* measured quantum-well energy separations, compare against competing EY/DP and combined kinetic models, and fix instrument response, background assumptions, sample geometry, temperature, and confidence procedures before acquisition. Independently acquire numeric BTO optical tensor to test three-domain Mueller predictions against held-out wavelengths. No physical or new-physics claim is authorized from current data.

**Software validation:** Portable Phase V package has **8 passing analytical unit tests** (formula, fitting and SHA fail-closed gates); this does not validate physical science. **Required review:** original paper exact fit prescription, material mechanism, source provenance, human scientific approval before PR merge or public narrative.

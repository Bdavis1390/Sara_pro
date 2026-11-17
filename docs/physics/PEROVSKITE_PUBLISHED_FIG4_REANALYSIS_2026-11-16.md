# WorldShepherd — Publisher Source Data Figure 4: bounded reanalysis

**Date:** 2026-11-16 | **Umbrella:** #282 Science & Validation  
**Claim state:** SUPPORTED BY LITERATURE + NUMERICALLY REANALYZED THIRD-PARTY DATA. Not WorldShepherd physical experimental evidence.

## Source and custody
Qiu, Huang et al., *Perovskite chiral multiple quantum wells with extended spin lifetime via efficient spin cascade*, Nature Photonics, published 2026-10-15. DOI https://doi.org/10.1038/s41566-026-02027-6

Source Data Figure 4 (public publisher file):  
https://static-content.springer.com/esm/art%3A10.1038%2Fs41566-026-02027-6/MediaObjects/41566_2026_2027_MOESM3_ESM.xlsx

Downloaded and ZIP-integrity-tested on authorized Lenovo, stored without modification as `~/worldshepherd-source-data/perovskite-2026-11-16/publisher_source_data_fig4.xlsx`. **Original SHA-256:** `25530a1482361ebeeadb8567a2bb7715415e4a2df939e97fb5aff3c02a8c22a1`; **59,599 bytes**.

The companion publisher XLSX files, Source Data Fig. 2 and Fig. 5, also passed CRC/integrity checks, SHA-256 `e891d594b30845ff1c79ec4af08ddda6e2bbdc9105d41d7d76188f916621643e` and `ae05c56461dadb86db14e0aec3384660c4474918c0e07a10db366d48de6cc9b1` respectively.

## Data extracted
Figure 4a/b workbook sheet `Figs. 4a and 4b`, original column headers:
- `C-MQWs`: `Time (ps), SC, CC, diff.` (148 rows; 0.10301 to 4999.54 ps);
- `C-SQW`: `Time (ps), SC, CC, diff.` (106 rows; 0.50425 to 966.41024 ps).
- Spot-checked `diff. = CC - SC` within source rounding; original data preserved. Extracted CSV SHA-256: `62b39c3d3de58a568464527dbaf8b68d895179c88340d78e3772ac89c922f4e6`.
- Figure 4d source-data sheet shows `glum` as a function of wavelength, with observed signed extrema of +0.0198 (R) and -0.01744 (S) at 500 nm. These are *spectral maxima*, not the article's separately reported characteristic value of 0.014.

## Exploratory curve fits: **not paper-method reproduction**
An exploratory model `y(t) = A*exp(-t/tau) + C` was fitted by a 2,800-value logarithmic tau grid with least-squares A,C, retaining every fifth point as an interleaved holdout. Models were chosen after reading the article and source data, **not** frozen in August/October historical WorldShepherd work.

| Sample | Fit window (ps) | Fitted tau with offset (ps) | Fitted tau, offset 0 (ps) | Holdout RMSE (offset model) | Constant-baseline holdout RMSE |
|---|---:|---:|---:|---:|---:|
| C-MQWs | >=20 | 1495 | 2368 | 5.1563e-5 | 5.18041e-4 |
| C-MQWs | >=50 | 1483 | 2406 | 5.4400e-5 | 5.09513e-4 |
| C-MQWs | >=100 | 1489 | 2475 | 5.9469e-5 | 5.34904e-4 |
| C-MQWs | >=200 | 1681 | 2673 | 5.2722e-5 | 4.98846e-4 |
| C-SQW | >=2 | 6.0 | 6.9 | 2.0604e-5 | 1.18539e-4 |
| C-SQW | >=5 | 6.1 | 7.6 | 2.4215e-5 | 7.2874e-5 |
| C-SQW | >=10 | 4.6 | 7.3 | 2.4971e-5 | 4.5429e-5 |

**Important:** C-SQW >20 ps is near baseline and the fitted time constant becomes non-identifiable (hitting the grid boundary); therefore omitted from comparative lifespan claims. The 1.5–2.7 ns simple-curve estimates are **not** claimed to reproduce the authors' ~5 ns spin-coherence lifetime. Need paper's observable definition, deconvolution, additional controls, errors, and fitting prescription. The interleaved holdout is within a single published series and not external validation.

## Historical prediction conclusion
Our 2026-08-06 material screen named BTO/BST ferroelectric candidate systems, but did **not** specify wavelength-resolved optical tensors, domain fractions or Mueller elements. Our 2026-10-07 dimensionless phonon CTAP/Zeno model did **not** encode chiral multiple quantum wells or measurable nanosecond spin-scattering rates. Neither historical work can be scored as a quantitative advance prediction of these specific external results.

## Gate before any publication/priority/IP claim
Reproduce the authors' method-specific spin-lifetime extraction, obtain full instrumental response and uncertainty information, compare prespecified null kinetic models, perform independent sample replication, and independently audit pre-publication provenance. No dataset or privileged WorldShepherd material is committed here. The original study's XLSX files remain hosted by the publisher under its access terms.

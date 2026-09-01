# WS-GEO-PROV / BAE Screening Bundle Index — 2026-09-01

Status: `BUNDLE DESIGN / NOT BAE VALIDATED / NOT EXTERNALLY REPRODUCED`

## Bundle purpose

Create a non-confidential, partner-screening-safe package for the `WS-GEO-PROV-001A` geospatial provenance demonstrator.

The bundle frames environmental/geospatial data as a mission-context evidence problem:

```text
source dataset -> source hash -> baseline -> comparison -> change event -> uncertainty -> null control -> human review -> audit chain -> replay -> BAE overlay
```

## Required bundle files

```text
WS-BAE-GEO-PROV-BUNDLE-001/
├── README.md
├── claims-boundary.md
├── executive-summary-nonconfidential.md
├── manifest.json
├── dataset-register.json
├── run-config.json
├── evidence-index.json
├── audit-chain.jsonl
├── null-control-report.md
├── uncertainty-report.md
├── replay-instructions.md
├── interface-control-description.md
├── overwatch-layer-mockup.md
├── threat-model.md
├── sbom-or-sbom-placeholder.json
├── build-provenance.md
├── nist-cmmc-dfars-gap-map.md
├── data-rights-and-ip-markings.md
└── external-validation-route.md
```

## Supplier/compliance gap map

This bundle must retain the following gates as gaps unless documentary evidence exists:

| Gate | Current status |
|---|---|
| SAM/CAGE status | Not asserted by this module |
| Small-business status | Not asserted by this module |
| CUI/CDI boundary | Must state no CUI/classified data used unless explicitly authorized |
| DFARS 252.204-7012 | Potential flowdown only; no compliance claim |
| CMMC 2.0 | Not certified by this module |
| NIST SP 800-171 | Not conformant by this module |
| SBOM/dependency provenance | Required before screening-ready bundle |
| Secure build/release evidence | Required before screening-ready bundle |
| Incident response | Required organizational artifact, not provided here |
| Secrets management | Required organizational artifact, not provided here |
| Data rights/IP markings | Required for all non-confidential external sharing |
| Export-control screening | Required before external technical transfer |
| Quality program | Required for hardware/platform claims; not established here |
| Facility/personnel clearance | Not asserted |

## BAE pathway alignment

| BAE pathway | Relevance |
|---|---|
| Mission Advantage | C5ISR, AI/ML, cyber, digital engineering, modeling/simulation, radar/mission-system screening angle |
| FAST Labs Technology Scouting | Relevant only if novel autonomy, AI/ML, EO/IR/RF, microelectronics, or multimodal sensing is added |
| RIVETS | Best fit for third-party software/sensor/subsystem integration evidence |
| Combat Mission Systems Virtual Proving Ground / plugfest | Synthetic interoperability and scenario replay target |
| ADAPT / ADAMS | MBSE, configuration custody, traceability, synthetic environments, and digital baseline discipline |
| Platforms & Services | Infrastructure resilience and platform environmental-context evidence |
| Space & Mission Systems | Possible remote-sensing provenance angle; speculative until a specific opportunity appears |

## Release condition

The bundle cannot be represented as externally validated until an independent reviewer can reproduce the same manifest, audit chain, outputs, failure cases, and claims boundary from the provided materials.

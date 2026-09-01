# Worldshepherd / SARA Industry Standards Conformance Baseline — 2026-09-01

## Purpose

Worldshepherd / SARA must be engineered toward meeting or exceeding relevant industry, federal, defense, software-supply-chain, application-security, AI-governance, and operational-evidence standards. This document converts that requirement into measurable gates.

The core rule is:

> A control is not marked **MET** or **EXCEEDED** until mapped evidence exists, automated checks pass where applicable, and any required independent or formal assessment evidence is attached.

This is a readiness baseline, not a certification claim.

## Claims boundary

This baseline records target standards, control intent, evidence gates, and current gaps. It does **not** establish certification, accreditation, CMMC conformity, NIST SP 800-171 implementation, DFARS satisfaction, FedRAMP authorization, ISO certification, SOC 2 attestation, BAE validation, DOE validation, supplier approval, export-control clearance, classified access, external reproduction, hardware performance, field performance, or operational authority.

## Authoritative baseline sources

| ID | Standard / framework | Source URL | Relevance |
|---|---|---|---|
| NIST_CSF_2_0 | NIST Cybersecurity Framework 2.0 | https://www.nist.gov/publications/nist-cybersecurity-framework-csf-20 | Enterprise cybersecurity governance and risk management. |
| NIST_SSDF_800_218 | NIST SP 800-218 SSDF v1.1 | https://csrc.nist.gov/pubs/sp/800/218/final | Secure software development lifecycle. |
| NIST_800_171_R3 | NIST SP 800-171 Rev. 3 | https://csrc.nist.gov/pubs/sp/800/171/r3/final | Forward-looking CUI safeguarding readiness. |
| NIST_800_171A_R3 | NIST SP 800-171A Rev. 3 | https://csrc.nist.gov/pubs/sp/800/171/a/r3/final | CUI requirement assessment procedures. |
| NIST_800_172_R3 | NIST SP 800-172 Rev. 3 / enhanced CUI guidance | https://csrc.nist.gov/projects/protecting-controlled-unclassified-information/publications | Enhanced security requirements for higher-risk CUI contexts. |
| DOD_CMMC_32_CFR_170 | DoD CMMC Program | https://dodcio.defense.gov/CMMC/About/-DoD/ | Defense contractor cybersecurity eligibility readiness. |
| NIST_800_161_R1_UPD1 | NIST SP 800-161r1-upd1 | https://csrc.nist.gov/pubs/sp/800/161/r1/upd1/final | Cybersecurity supply-chain risk management. |
| SLSA_1_2 | SLSA specification | https://slsa.dev/spec/v1.2/ | Build provenance and artifact integrity. |
| OPENSSF_SCORECARD | OpenSSF Scorecard | https://openssf.org/projects/scorecard/ | Open-source repository security posture. |
| OWASP_ASVS_5 | OWASP ASVS 5.0 | https://github.com/OWASP/ASVS/releases | Application and API security verification. |
| CYCLONEDX_1_6_PLUS | OWASP CycloneDX BOM standard | https://cyclonedx.org/specification/overview/ | SBOM/BOM and supply-chain transparency. |
| SPDX_3 | SPDX specification | https://spdx.dev/use/specifications/ | SBOM interoperability and package data exchange. |
| OPENVEX | OpenVEX specification | https://github.com/openvex/spec | Vulnerability affectedness / exploitability statements. |
| NIST_AI_RMF_1_0 | NIST AI RMF 1.0 | https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10 | AI governance and risk management. |

## Conformance posture

| Domain | Baseline expectation | Exceeding-standard expectation | Current claimable state |
|---|---|---|---|
| Cybersecurity governance | Map risks and controls to NIST CSF 2.0. | Tie each risk to CI evidence, owner review, and recovery evidence. | Target defined; no certification claim. |
| Secure SDLC | Map build/test/release practices to SSDF. | Enforce dependency evidence, tests, release-index custody, and claims-boundary output per release. | Partial internal CI evidence only. |
| CUI readiness | Maintain NIST 800-171 Rev. 3 readiness map. | Build SSP-ready evidence and assessment-ready artifacts before any CUI claim. | Gap map required; CUI conformity not claimed. |
| Enhanced defense readiness | Track 800-172 enhanced safeguards. | Optional high-assurance controls for segmented, monitored, APT-resistant environments. | Forecast/gap target only. |
| CMMC | Maintain applicability decision record. | Separate internal evidence from formal CMMC status and require recognized assessment before claim. | Readiness planning only. |
| Software supply chain | Map dependency, supplier, build, and release risk. | Attach SBOM, VEX-ready status, dependency freeze, provenance, and owner disposition. | Partial dependency evidence only. |
| Build provenance | Map SLSA source/build controls. | Add tamper-resistant provenance, release signing, and independent verification route. | SLSA level not claimed. |
| App/API security | Map endpoints to ASVS controls. | Require authn/authz, negative tests, input validation, auditability, and failure-mode tests. | Mapping required. |
| AI governance | Map AI-assisted workflows to AI RMF. | Maintain model-use boundaries, evaluations, red-team cases, and human authorization. | Governance target only. |
| Operational resilience | Keep deployment/recovery/snapshot evidence. | Gate every main push through build, deployment, backup/restore, snapshot, release identity, and artifact index. | Internal CI evidence present. |
| Partner/prime readiness | Package non-confidential evidence for reviewer screening. | Preserve no-validation claims boundary until external review or partner assessment exists. | Screening-ready design only. |
| Hardware/field/lab performance | Require repeatable measurement evidence. | Add independent lab/field reproduction before any performance claim. | Not claimed. |

## Evidence gates

Every standards record must eventually map to these evidence objects:

1. Source authority recorded.
2. Control owner assigned.
3. System boundary defined.
4. Asset inventory defined.
5. Threat model or risk record exists.
6. Implementation evidence attached.
7. Automated test or manual assessment method defined.
8. CI artifact or review artifact attached.
9. Gap, exception, or POA&M entry logged when incomplete.
10. Claims boundary attached.
11. External or formal assessment attached when the standard requires it.

## Readiness model

| Level | Meaning |
|---|---|
| L0_UNMAPPED | Standard identified but not mapped. |
| L1_CONTROL_INTENT | Control objective, owner, and applicability are defined. |
| L2_INTERNAL_EVIDENCE | Internal implementation evidence or CI artifact exists. |
| L3_REPEATABLE_CI_GATE | Automated gate validates the evidence on every relevant run. |
| L4_INDEPENDENT_REVIEW_READY | Evidence package is ready for external reviewer or assessor. |
| L5_FORMALLY_ASSESSED | A recognized third-party, government, or formal assessment record supports the claim. |

Current global readiness:

```text
L1_CONTROL_INTENT_WITH_SELECTED_L2_L3_CI_EVIDENCE
```

Target global readiness:

```text
L4_INDEPENDENT_REVIEW_READY before partner/prime submission;
L5_FORMALLY_ASSESSED only where applicable and evidenced.
```

## Minimum redlines

- No certification or conformity claim without formal evidence.
- No CUI/CDI handling claim without a documented system boundary and control evidence.
- No BAE, DOE, partner, supplier, or government validation claim from thematic overlap or internal CI evidence.
- No autonomous external action without human authorization and audit record.
- No public release package without claims-boundary text.
- No release index without artifact digest custody.
- No dependency or supplier acceptance without provenance and risk review.
- No AI capability claim without evaluation scope, limitations, and human review boundary.
- No hardware, field, laboratory, or operational-performance claim without reproducible measurement evidence.

## Immediate build sequence

1. Add a per-control standards matrix with evidence IDs.
2. Add automated secrets scanning.
3. Add dependency vulnerability scanning.
4. Generate and retain SBOM evidence.
5. Add SLSA provenance and release-signing route.
6. Add NIST CSF 2.0 / SSDF crosswalk.
7. Add CUI boundary decision record and NIST 800-171 Rev. 3 SSP skeleton.
8. Add CMMC applicability decision record.
9. Add ASVS API checklist for SARA endpoints.
10. Add AI RMF workflow-risk register.
11. Build independent-review handoff package.

## Machine-readable companion

The companion data file is:

```text
deployments/sara_verified_local_v1/standards_conformance_baseline.json
```

The companion pytest guard is:

```text
deployments/sara_verified_local_v1/tests/test_standards_conformance_baseline.py
```

These tests require the standards baseline, claims boundary, evidence gates, redlines, and non-certification posture to remain intact.

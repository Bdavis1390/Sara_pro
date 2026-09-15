# GD-06 — W-RMABM Evidence & Compliance Gap Register

**Status:** ACTIVE INTERNAL REGISTER

This register prevents internal software progress from being misreported as operational, supplier, compliance, or government validation.

| Gap | Current evidence | Required closure evidence | Gate |
|---|---|---|---|
| Deterministic synthetic mission thread | `rmabm.py`, frozen fixture, automated tests committed | CI PASS on clean runner | G1 |
| Provenance completeness | SHA-256 source fields and audit/replay digests in G1 code | Negative/tamper tests; independently reproduced evidence bundle | G2 |
| Fault tolerance/degraded state | Single stale-source fixture plus existing DDIL modules | Seeded multi-fault campaign with defined pass/fail metrics | G2 |
| Performance/scalability | Not measured for W-RMABM | Latency, throughput, memory/CPU and scale curves with environment manifest | G2 |
| Interface conformance | Internal JSON fixture only | Agreed public/partner surrogate schema; mutation/conformance suite | G2/G4 |
| Operator workload/decision effects | Not measured | Human-factors protocol and bounded comparative results | G2/G4 |
| External reproduction | None for W-RMABM | Independent rerun by prime, lab, testbed, university, or government evaluator | G4 |
| BAE integration | None | BAE-controlled evaluation result or documented integration evidence | G4/G5 |
| SDA/PWSA integration | None | SDA-controlled evaluation/integration evidence | G4/G5 |
| SSC/Golden Dome integration | None | SSC-controlled evaluation/integration evidence | G4/G5 |
| SBOM/build provenance | Existing repository tooling/workflows | W-RMABM-specific generated SBOM, build manifest, artifact digest and verifier result | G3 |
| NIST SP 800-171 | Precursor maps/scripts exist; no conformity claim | Scoped system boundary, evidence mapped to applicable requirements, independent/authorized assessment as required | G3+ |
| CMMC | No certification claimed | Applicable certification/assessment evidence if contractually required | G3+ |
| DFARS/CUI handling | Internal policies/precursor material only | Applicable contract clauses, scoped CUI environment, incident/reporting controls and evidence | G3+ |
| Data rights/IP | General claims controls exist | W-RMABM data-rights strategy, markings, open-source/license inventory, proprietary boundary | G3 |
| Export control | No W-RMABM determination recorded | Counsel/qualified export review of release package and technical data before controlled disclosure | G3 |
| Supplier status | No BAE/prime supplier status claimed | Completed and accepted supplier onboarding where applicable | G4 |
| Classification boundary | G1 intentionally synthetic/unclassified | External evaluator confirms acceptable unclassified interface/data package before testing | G4 |

## G1 release rule
W-RMABM may be described as **G1 complete** only after the new branch passes repository CI for the frozen G1 fixture and claims-boundary tests. Until then use: **G1 implementation committed; CI verification pending**.

## Blocked external claims
Do not use any of the following without objective evidence:
- BAE validated / BAE integrated / BAE selected;
- SDA or SSC validated / Golden Dome integrated;
- operational missile-warning or tracking performance proven;
- operational C2, fire-control, weapon-cueing, or engagement capability;
- CMMC certified;
- NIST SP 800-171 conformant;
- DFARS compliant;
- classified-ready;
- flight-qualified;
- government accepted or deployed.

## Highest-leverage closure sequence
1. Clean CI pass for G1.
2. Add tamper/duplication/delay/source-disagreement fault campaign.
3. Produce W-RMABM-specific SBOM/build provenance bundle.
4. Freeze reproducible benchmark environment and results.
5. Secure an unclassified external evaluation route.

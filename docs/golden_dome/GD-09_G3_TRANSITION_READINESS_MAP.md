# GD-09 — W-RMABM G3 Transition Readiness Map

**Status:** INTERNAL READINESS ARTIFACT / NO COMPLIANCE OR CLASSIFIED-ACCESS CLAIM

## Purpose
Define the evidence needed to move W-RMABM from internally verified synthetic software into an externally evaluable supplier package without confusing software maturity with acquisition, cybersecurity, export-control, data-rights, or classified-work readiness.

## G3 workstreams

| Workstream | Current posture | Required closure evidence |
|---|---|---|
| External evidence bundle | Deterministic allowlist/hash manifest implemented | Clean CI; reviewer-approved manifest and release record |
| SBOM/build provenance | Repository CI already generates software SBOM and dependency evidence | W-RMABM-specific artifact digest, build manifest, reproducible release instructions |
| Vulnerability evidence | Repository CI produces advisory evidence | Defined triage/acceptance policy and W-RMABM-scoped closure record |
| System/security boundary | No W-RMABM contract-specific CUI boundary established | Documented information types, trust boundaries, hosting model and applicable controls |
| NIST SP 800-171 | No conformity claim | Applicable-requirement assessment against a defined CUI system boundary |
| CMMC | No certification claim | Applicable certification/assessment only if required by the acquisition/contract |
| DFARS | No contract-specific compliance claim | Identify applicable clauses/flowdowns and produce scoped implementation evidence |
| Data rights | General claims controls exist | Background-IP list, third-party/license inventory, assertion table and release markings |
| Export control | No W-RMABM determination recorded | Qualified review before controlled technical-data disclosure or foreign-person access |
| Supplier onboarding | No Golden Dome/BAE/SDA/SSC supplier status claimed | Organization/vehicle-specific onboarding acceptance where applicable |
| External interface | Fictional adapter evidence only | Evaluator-approved unclassified surrogate schema and conformance result |
| Independent reproduction | Internal GitHub CI only | Reproduction by an authorized prime, lab, government/testbed or other independent evaluator |
| Classified collaboration | No clearance, classified authorization or accredited facility claimed | Program need, appropriate personnel/facility/access approvals, and authorized secure environment |

## Secure Space Network relevance
On September 3, 2026, the Department of War announced a **Secure Space Network** effort to design, produce, and deploy approximately 50 mobile Sensitive Compartmented Information Facilities and related information systems across the United States. The stated purpose is to broaden regional access to accredited secure workspaces for qualified suppliers and nontraditional companies that may later need classified collaboration.

This is strategically relevant because it may reduce the cost and geographic barrier of owning fixed secure infrastructure before a company has a validated classified requirement. It **does not** itself grant Worldshepherd a facility clearance, personnel clearance, need-to-know, classified contract, system authorization, or permission to handle classified information.

Authoritative source: https://www.war.gov/News/Releases/Release/Article/4590688/department-of-war-launches-secure-space-network-to-break-down-barriers-to-class/

## Transition sequence
1. Freeze a clean unclassified W-RMABM evidence bundle.
2. Complete data-rights, license, export, and release review.
3. Define the intended external evaluator and surrogate interface.
4. Produce scoped cyber/system-boundary evidence appropriate to that evaluation.
5. Conduct unclassified independent reproduction first.
6. Use external findings to decide whether contract-specific CUI or classified readiness investment is justified.
7. Enter secure/classified work only through an authorized program with all required access and handling approvals.

## Stop conditions
Do not spend heavily on classified infrastructure merely to improve marketing optics. Do not claim CMMC, NIST SP 800-171, DFARS, facility-clearance, personnel-clearance, CUI, or classified readiness until the relevant objective evidence exists. Do not place classified or controlled technical data in the public repository.

## Claims boundary
G3 is an acquisition and assurance-readiness gate. Internal CI success is useful software evidence but is not a substitute for external assessment, contractual applicability, certification, clearance, or government authorization.

# Claims boundary for external review

## Why this exists

Worldshepherd combines working software, internal qualification evidence, simulations, research, and partner/opportunity material. Those categories must not collapse into one another.

This document is the default external-review boundary for the repository.

## Evidence classes

### Implemented in software

Use this label only when the behavior exists in repository code and can be inspected or exercised.

Examples in the local SARA reference implementation include authenticated API routes, role checks, protected registry handling, request-size limits, local audit append behavior, readiness checks, test suites, and CI automation.

### Proven internally

Use this label only for a property demonstrated by the project's own reproducible tests or CI evidence at a specific commit.

This is stronger than "implemented" but weaker than independent validation.

### Supported by literature

Use this label when an external technical proposition is supported by credible literature but has not been demonstrated by this project.

### Simulated only

Use this label for behavior or performance shown in a model or simulation without corresponding physical validation.

### Hypothesis

Use this label when the proposition is being tested and should not be described as an achieved capability.

### Requires lab validation

Use this label when physical measurement, calibration, coupon testing, hardware-in-the-loop work, or equivalent independent laboratory evidence is still required.

### Requires partner validation

Use this label when the claimed behavior depends on an external platform, partner system, proprietary interface, facility, or integration that the project does not control.

### Requires legal review

Use this label for conclusions involving licensing, export controls, contracting, regulatory status, data rights, certification, or other legal determinations.

### Not currently claimed

Use this label where a plausible inference would overstate the project's actual evidence.

## Statements permitted for the SARA review target

Subject to verification at the cited commit, it is reasonable to say:

- the repository contains a local SARA reference implementation;
- the implementation has separate relay and administrator credential roles;
- the relay endpoint records a local authenticated request rather than executing arbitrary commands;
- administrator-only routes expose audit, registry, evidence, and self-test functions;
- protected namespaces are rejected by the generic registry patch route;
- the project includes an optional separated signing/verifying architecture using Ed25519 authorization assertions;
- the repository includes automated tests and CI workflows for software, evidence, dependency, recovery, and release checks;
- the security documentation explicitly limits the supported deployment and assurance boundary.

## Statements not established by this repository alone

Do **not** infer or state that a green repository or CI run proves:

- CMMC certification;
- organization-wide NIST SP 800-171 conformity;
- SPRS acceptance;
- RMF authorization or ATO;
- FedRAMP authorization;
- FIPS validation;
- government interoperability approval;
- cybersecurity accreditation of a production deployment;
- immutable or legally sufficient chain of custody;
- HSM/KMS-backed production key custody;
- partner/customer approval;
- field validation;
- production scalability;
- autonomous mission authority;
- demonstrated physical performance for unrelated research in the repository.

## Reviewer communication rule

When a reviewer identifies a flaw, the flaw outranks the narrative.

If evidence and description conflict, fix the description immediately and investigate the implementation. Do not defend an overbroad claim by pointing to project terminology.

## Partnership communication rule

No external person or organization should be described as a partner, adviser, supporter, validator, or endorser unless that relationship is explicitly established by that party.

A request for technical review is not a partnership. A reply is not an endorsement. A code comment is not validation. A meeting is not an agreement.

## Linus-specific boundary

Until Linus Torvalds explicitly responds, the only accurate statement is that Worldshepherd has prepared a technical-review packet suitable for requesting his criticism. Do not imply that he has seen, reviewed, approved, endorsed, or partnered with Worldshepherd.

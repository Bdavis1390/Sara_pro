# GD-12 — G4 Independent Evaluator Target Matrix

**Status:** INTERNAL CAPTURE / PUBLIC-SOURCE RESEARCH / NOT AN EXTERNAL VALIDATION CLAIM

## Objective
Identify independent organizations capable of executing the frozen W-RMABM G4 synthetic reproduction protocol without participating in Worldshepherd development. The desired evaluator is technically competent, institutionally independent, able to work with industry or commercial entities, and familiar with national-security software, mission assurance, space systems, systems engineering, or test and evaluation.

## Evaluation dimensions
Each candidate is scored 0–5 on:

1. **Independence/objectivity** — structural separation from Worldshepherd development and ability to provide objective technical assessment.
2. **Software assurance / T&E depth** — demonstrated capability in software verification, system evaluation, test, simulation, or mission assurance.
3. **Space / national-security relevance** — direct experience with space, missile defense, C4ISR, resilient mission systems, or national-security software.
4. **Industry accessibility** — explicit mechanism for commercial, private-sector, industry-sponsored, or partnership engagement.
5. **G4 protocol fit** — suitability for reproducing a deterministic synthetic software benchmark in an evaluator-controlled environment and recording evidence.

Maximum score: 25. Scores are capture-planning estimates, not probabilities of acceptance or award.

## First-wave targets

| Rank | Organization | Independence | SW assurance / T&E | Space / natsec relevance | Industry accessibility | G4 fit | Total | Recommended route |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | The Aerospace Corporation | 5 | 5 | 5 | 4 | 5 | **24/25** | Commercial/industry engagement or business-development inquiry requesting independent synthetic software reproduction only |
| 2 | Georgia Tech Research Institute (GTRI) | 5 | 5 | 5 | 5 | 4 | **24/25** | Partner-with-GTRI / technology-capability inquiry; request unclassified software T&E reproduction |
| 3 | Virginia Tech National Security Institute / Hume Center | 4 | 4 | 5 | 5 | 5 | **23/25** | Sponsored research or industry partnership inquiry; ask for evaluator-controlled reproduction and scorecard completion |
| 4 | Carnegie Mellon University Software Engineering Institute (SEI) | 5 | 5 | 4 | 4 | 5 | **23/25** | Private-sector contact route; frame as objective software/system evaluation rather than product endorsement |
| 5 | MITRE National Security Engineering Center (NSEC) | 5 | 5 | 5 | 3 | 4 | **22/25** | Defense/intelligence mission-area inquiry; likely sponsor/FFRDC constraints should be resolved before technical handoff |
| 6 | Johns Hopkins University Applied Physics Laboratory (APL) | 5 | 5 | 5 | 2 | 4 | **21/25** | Strategic reserve; strongest if routed through a government sponsor, BAA, cooperative activity, or other permitted mechanism |

## Why these organizations

### 1. The Aerospace Corporation
Public-source basis:
- the space-focused FFRDC explicitly describes itself as an independent and unconflicted technical partner;
- public industry material states that commercial and industry customers can access testing and evaluation, modeling and simulation, analysis, technical consulting, and technology development through multiple engagement models;
- Aerospace publicly describes independent software testing, modeling, simulation, testbed development, and mission-readiness verification for national-security space systems.

**Capture assessment:** best combination of space specificity, independence, software T&E, and a commercial engagement path.

### 2. Georgia Tech Research Institute
Public-source basis:
- GTRI describes itself as a nonprofit objective partner working with both government and industry;
- its systems portfolio includes space systems, mission analysis, air and missile defense, training, test and evaluation, hardware-in-the-loop, hybrid, and real-time simulation;
- its contact form explicitly includes “Partner with GTRI” and “Technology or Capability Inquiry.”

**Capture assessment:** highly accessible and technically strong for a bounded unclassified reproduction task.

### 3. Virginia Tech NSI / Hume Center
Public-source basis:
- research areas include cybersecurity, resilience, autonomy, space systems, advanced C4ISR, mission engineering, AI assurance, validation and test and evaluation, data fusion, and assured communications;
- the Hume Center explicitly supports industry-sponsored research, research contracts, IRAD, and joint proposals.

**Capture assessment:** especially strong for an evaluator-controlled academic reproduction with a traceable methodology and student/faculty research context.

### 4. CMU Software Engineering Institute
Public-source basis:
- SEI is a federally funded research and development center focused on objective software engineering, cyber, and AI for national security;
- it publicly states that it works with government, university labs, and industry and provides a private-sector contact route;
- its CERT and Software Solutions work includes system/platform evaluation, secure development, software assurance, mission-critical systems, and resilience.

**Capture assessment:** strongest pure-software assurance fit; less directly space-specific than the top three.

### 5. MITRE NSEC
Public-source basis:
- MITRE describes NSEC as delivering impartial and independent systems thinking and technical expertise for national security;
- MITRE also works across aerospace, information integration, protection, automation, and space-related systems.

**Capture assessment:** highly credible technically, but FFRDC sponsorship and conflict constraints may make unsolicited commercial evaluation less direct.

### 6. Johns Hopkins APL
Public-source basis:
- APL is a UARC with deep air and missile defense, space, AI, systems engineering, software, and validation experience;
- APL publicly describes testing and validating AI technologies and working with commercial partners, but most UARC work is sponsor-driven and subject to conflict restrictions.

**Capture assessment:** strategically valuable, but best approached through an aligned sponsor or formal collaboration mechanism rather than as the first cold evaluation request.

## First-contact message requirements
Any outreach derived from this matrix must state all of the following:

- evaluation is **unclassified and synthetic only**;
- Worldshepherd is requesting **independent reproduction**, not endorsement;
- the evaluator chooses or controls the challenge seed and environment;
- the evaluator may decline or modify the protocol if institutional policy requires;
- no real threat data, operational missile-tracking data, fire-control information, weapon-cueing logic, classified interfaces, CUI, export-controlled material, or proprietary government/vendor data are requested or supplied;
- passing the protocol establishes only `INDEPENDENTLY REPRODUCED — SYNTHETIC SOFTWARE BEHAVIOR ONLY`;
- no government, Golden Dome, Space Force, SDA, SSC, MDA, BAE, prime-contractor, compliance, deployment, or operational validation is claimed.

## Release decision rule
Do not transmit an external evaluation bundle until:

1. the G4-prep branch CI remains green;
2. release manifest generation passes leakage checks;
3. the evaluator confirms a permissible engagement path;
4. the exact commit/ref to be evaluated is frozen and recorded;
5. a human release review authorizes the external handoff.

## Current recommended sequence
1. Aerospace commercial/industry inquiry.
2. GTRI partner/technology-capability inquiry in parallel.
3. Virginia Tech NSI/Hume sponsored-research inquiry.
4. CMU SEI private-sector inquiry.
5. MITRE NSEC only after engagement/sponsor constraints are understood.
6. APL through sponsor-aligned or formal collaboration route.

This matrix is a capture-planning artifact. It does not establish willingness, availability, cost, schedule, eligibility, government sponsorship, or any external validation.
# PRE Requirement Delta — USSOCOM UxSAI Mission Autonomy

Record ID: PRE-RD-2026-UXSAI-001  
Recorded: 2026-09-07  
Status: CONFIRMED DEMAND; current-cycle submission gate NOT MET

## Source

- Title: PEO-SDA UxSAI Mission Autonomy Systems Assessment Event
- Agency: USSOCOM / PEO-SDA, facilitated by SOFWERX
- Event page: https://events.sofwerx.org/uxsaimissionautonomy
- Assessment criteria: https://swx-strapi-events-images.s3.us-east-1.amazonaws.com/Ux_SAI_Mission_Autonomy_Assessment_Criteria_82da2ccf65.pdf
- Q&A transcript: https://swx-strapi-events-images.s3.us-east-1.amazonaws.com/Ux_SAI_Mission_Autonomy_AE_QA_Telecon_Transcript_Ux_SAI_Responses_8ea3dd6b04.pdf
- Solicitation/event identifier: UxSAI Mission Autonomy Assessment Event
- Source status: OFFICIAL_SOURCE_VERIFIED
- Retrieved UTC: 2026-09-07T12:55:00Z
- Submission deadline: 2026-09-08 23:59 ET

## Requirement statement

Provide mature, modular, decentralized and collaborative mission-autonomy software for heterogeneous multi-platform, multi-domain unmanned systems. The solution must operate as an application inside the Government-owned CHAOS baseline, support ISR-T mission threads, integrate through Government SDK/interface specifications after down-select, and be configurable and sustainable without continuing vendor dependency.

The highest-weight gateway is integration and interoperability. Government criteria call for a containerized, hot-reloadable component; open-interface and MOSA posture; portability across AMD64 and ARM; applicable ROS 2, PX4/MAVLink or ArduPilot integration evidence; mission planning and dynamic retasking; multi-agent coordination; intermittent-link state synchronization; deterministic authorization/safety verification; FDIR; auditable DDIL behavior; human-machine authorities; and a virtual demonstration.

## Recurrence and horizons

- Recurrence: VERY HIGH across collaborative autonomy, open C2, DDIL operations, ISR, autonomous logistics, maritime autonomy and government-owned software baselines.
- 0-90 days: create a provider-neutral governed mission-autonomy integration harness and measurable synthetic ISR-T scenario.
- 3-12 months: integrate with a mature mission-autonomy/autopilot stack and two compute architectures; produce repeatable virtual demonstration evidence.
- 12-24+ months: pursue CHAOS-like Government integration, platform/range validation and transition partnerships.

## Affected Worldshepherd lanes

- SARA governed orchestration
- PRIME SENTINEL human authorization and deterministic policy gates
- ECHO SENTINEL LINK telemetry and decision provenance
- OVERWATCH observability and common operating picture
- DDIL/degraded-state testing
- MOSA/open C2 adapters
- collaborative autonomy
- configuration custody
- simulation-to-field discrepancy accounting
- machine-readable qualification evidence

## Existing capability and capability status

Existing evidence is limited to internally tested software and CI patterns for governed workflow execution, authorization, audit/provenance, configuration identity, degraded-network fault campaigns and replayable verification.

Capability status:
- IMPLEMENTED IN SOFTWARE for bounded repository-tested controls only
- PROVEN INTERNALLY for the exact tests and environments retained with evidence
- REQUIRES PARTNER VALIDATION for external autonomy-stack integration
- REQUIRES LAB VALIDATION for platform or hardware behavior

No current evidence establishes:
- a complete TRL 6 mission-autonomy application;
- CHAOS SDK conformance;
- integration with Government reference architectures;
- ROS 2/PX4/ArduPilot platform integration;
- multi-platform ISR-T performance;
- government acceptance, ATO, NIST SP 800-171 conformity or operational effectiveness.

## Current-cycle gate decision

DO NOT represent Worldshepherd as independently submission-ready for the September 8, 2026 event.

The Q&A requires:
- TRL 6 or higher;
- a complete mission-autonomy solution, even when components come from multiple vendors;
- a team arrangement established before the white-paper deadline;
- readiness to demonstrate the stated capability virtually in the vendor's environment.

Worldshepherd currently lacks sufficient evidence for those gates. A last-minute standalone submission would overstate maturity. A teamed submission is only credible if an established autonomy provider has already accepted Worldshepherd's bounded verifier/governance contribution before the deadline.

## Experiment or demonstration needed

Build a Governed Heterogeneous Mission Autonomy Harness with:
1. at least two simulated platforms and a swappable external autonomy/planner component;
2. containerized application boundary and versioned open adapter contract;
3. mission intent, task catalog, dynamic retasking and peer-to-peer handoff;
4. communications loss/intermittency, GNSS denial, stale/conflicting world-state inputs, platform loss and low-energy faults;
5. PRIME-style pre-delegated authority and deterministic action gates independent of any learned component;
6. ECHO-style decision, configuration and telemetry provenance;
7. OVERWATCH-style operator state, intervention and replay;
8. documented portability plan for AMD64 and ARM and a future ROS 2/PX4/ArduPilot bridge.

## Evidence target

- adapter conformance and integration time;
- mission completion and safe-abstention rate;
- authorization-policy compliance;
- peer state-rejoin correctness;
- fault detection/isolation/recovery timing;
- human override and escalation behavior;
- decision/provenance completeness;
- deterministic replay;
- configuration and SBOM identity;
- performance on at least two compute architectures;
- negative evidence and simulation-to-platform discrepancy retention.

## Partner needed

A U.S.-based, mature mission-autonomy provider with TRL 6+ evidence, a virtual ISR-T demonstration, open-interface integration experience and a plausible path to ROS 2/PX4/ArduPilot or equivalent platform interfaces.

## BAE Systems teaming assessment

These are planning estimates, not evidence of BAE interest, acceptance or partnership.

1. BAE-led solution with Worldshepherd as bounded technology provider:
   - Strategic fit: HIGH
   - Current-cycle feasibility: LOW because no verified team exists before the deadline.
2. Joint integrated solution:
   - Strategic fit: VERY HIGH
   - Current-cycle feasibility: LOW for the same team and maturity gates.
3. Worldshepherd verifier/provenance insertion into a BAE-led autonomy or integration environment:
   - Strategic fit: VERY HIGH
   - Preferred future route after bounded integration evidence.
4. Co-development / IR&D-style synthetic demonstration:
   - Strategic fit: HIGHEST
   - Preferred preparation route for later CHAOS, collaborative-autonomy and proving-ground opportunities.

Proposed future division of labor:
- Mature platform/autonomy partner: mission planner, collaborative behaviors, perception/autopilot interfaces, representative ISR-T scenario and platform evidence.
- Worldshepherd: deterministic authority gates, evidence lineage, configuration custody, DDIL fault campaigns, operator intervention, audit trace and qualification package.

Best public BAE engagement route remains FAST Labs Technology Scouting or Mission Advantage when a reviewed, non-confidential demonstration packet exists. No additional BAE email is authorized by this record.

## Likely future programs

- USSOCOM UxSAI/CHAOS follow-on integration
- collaborative heterogeneous autonomy
- autonomous warfare proving-ground and virtual test environments
- maritime/littoral ISR autonomy
- Group 1/2 UAS autonomy
- autonomous logistics and degraded C2
- service MOSA/open-autonomy insertion efforts

## Claims boundary

- Prediction and thematic fit do not upgrade capability maturity.
- Internal CI is not TRL 6, Government acceptance, operational validation, platform integration or compliance.
- No BAE or Government partnership is claimed.
- No submission, agreement, data-rights commitment, funding obligation or protected-data exchange has occurred.

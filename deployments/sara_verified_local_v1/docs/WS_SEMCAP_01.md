# WS-SEMCAP-01 — Governed Semantic Edge Communications Qualification Profile

Status: QUALIFICATION PROFILE IMPLEMENTED; PERFORMANCE NOT VALIDATED

WS-SEMCAP-01 is the first domain profile for WS-QX/EVIDENCE-01. It is designed to measure mission-aware semantic edge communications without treating compression alone as mission success.

## Comparison arms

- B0: full-frame encoded stream baseline.
- B1: conventional detector / ROI transmission baseline.
- B2: mission-aware semantic transmission candidate.

The exact codec, encoder settings, source sequence, mission card, hardware, link emulator, and receiver configuration must be recorded in the run manifest.

## Mandatory dimensions

- Q_P: perception quality.
- Q_R: contextual / spatiotemporal reasoning.
- Q_S: semantic selection fidelity.
- Q_C: communications efficiency.
- Q_D: degraded-link behavior.
- Q_E: evidence/provenance completeness.
- Q_X: receiver reconstruction / retained mission utility.

Where all are mandatory, overall qualification fails if any mandatory dimension fails. An average score cannot hide a failed dimension.

## Core measurements

For identical source sequences and mission conditions record:

- baseline transmitted bits
- semantic transmitted bits
- mission utility for baseline and candidate
- sensor-to-semantic-packet latency
- measured power on identified embedded hardware
- critical-event misses
- false semantic selections
- receiver reconstruction fidelity
- link state / bandwidth / loss / interruption regime
- provenance completeness

Reduction = 1 - semantic_bits / baseline_bits.

Utility retention = semantic_mission_utility / baseline_mission_utility.

A high reduction result with unacceptable utility retention is a failure, not a successful compression claim.

## DDIL sweep

Qualification should test controlled bandwidth degradation and interruption. Each transition must preserve evidence of link state, selection behavior, queued/dropped semantic units, recovery/resynchronization, and receiver state.

## Suppression evidence

Where technically practical, the system should preserve why potentially relevant observations were suppressed, summarized, delayed, or transmitted. This is evidence for assurance; it does not imply that every discarded pixel can be reconstructed.

## DV019 boundary

This profile is informed by the recurring semantic-ISR problem class, but publication of this profile does not establish DARPA DV019 qualification or Direct-to-Phase-II eligibility. Those require the program-specific evidence actually demanded by the solicitation and the proposer's prior work.

## Reuse

The same profile pattern can be specialized for EO/IR, event cameras, radar, sonar, scientific instruments, autonomous logistics telemetry, and space downlink. Domain-specific utility functions and baselines must be declared rather than silently reused across domains.

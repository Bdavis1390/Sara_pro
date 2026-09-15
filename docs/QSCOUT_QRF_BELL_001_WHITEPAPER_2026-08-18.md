# QSCOUT One-Page Whitepaper — QRF-BELL-001

**Status:** Submission-ready draft pending QSCOUT feasibility response  
**Prepared:** 2026-08-18  
**Author:** Brandon Ray Davis  
**Research organization:** Worldshepherd / Brandon Davis Solutions  
**Requested collaboration:** Sandia Quantum Scientific Computing Open User Testbed (QSCOUT)

## Title

**Evidence-Governed Reproducibility of a Frozen Bell-State Workload on a White-Box Trapped-Ion Quantum Testbed**

## Intended research

Worldshepherd proposes a small, non-proprietary reproducibility and evidence-custody study using a frozen two-qubit Bell-state benchmark, `QRF-BELL-001`. The objective is **not** to demonstrate quantum advantage. The scientific question is whether a simple, fully specified logical circuit can be executed and independently analyzed on physical trapped-ion hardware while retaining sufficient calibration, runtime, program, and result provenance to support a defensible comparison with simulator baselines and later with a second independent quantum provider.

`QRF-BELL-001` prepares `|00>`, applies a Hadamard to qubit 0, applies a controlled-X from qubit 0 to qubit 1, and measures both qubits in the computational basis. The logical workload and analysis policy are frozen before physical execution. Worldshepherd has already implemented ideal/noisy simulation, immutable program/result/configuration digests, a provider-neutral gate-model evidence record, and statistical cross-run reproduction using predeclared total-variation-distance and Bhattacharyya-fidelity thresholds. Independent runs must retain distinct result identities; negative or anomalous results are preserved rather than discarded.

QSCOUT is scientifically valuable for this study because its white-box model exposes calibration parameters, runtime details, measurement outcomes, native trapped-ion gate behavior, and operator collaboration that are often unavailable or opaque on commercial cloud systems. The proposed first phase intentionally uses ordinary gate-level access rather than custom pulses. If QSCOUT scientists identify a useful system-characterization extension, a later phase could compare the standard Bell workload under controlled gate/calibration variations, but no such extension is required for the minimum study.

A successful project is defined by execution of the frozen protocol with adequate provenance and a scientifically defensible reproducibility conclusion—even if the physical results fail the predeclared agreement thresholds. QSCOUT data would be retained under Sandia's data/publication policy and separately ingested into Worldshepherd's evidence-governed review process. QSCOUT participation would not be represented as Sandia endorsement, certification, deployment readiness, or proof of quantum advantage.

## QSCOUT capabilities required

- two physical trapped-ion qubits from the available QSCOUT register;
- ordinary gate-level preparation of a Bell state using QSCOUT-supported native/compiled operations;
- computational-basis measurement with enough repeated shots to form a sampled output distribution;
- device/backend and run identity;
- relevant calibration parameters and runtime details available under normal QSCOUT user access;
- retained measurement outcomes and circuit/Jaqal representation or equivalent execution record;
- at least one independently identified repeat run if capacity permits;
- collaboration with QSCOUT staff to ensure the logical Bell workload is mapped correctly without post-result retuning;
- optional controlled noise/calibration variation only if scientifically useful and feasible within the short-project window.

The minimum workload is intentionally shallow and should not require long reservations, custom pulse development, large qubit counts, proprietary data, or controlled information.

## Immediate feasibility questions

1. Is this bounded Bell-state reproducibility/evidence-custody study suitable for the remaining FY2026 short-project capacity?
2. Would QSCOUT prefer a one-page whitepaper submission immediately, or additional feasibility discussion first?
3. Is the Worldshepherd / Brandon Davis Solutions organizational path suitable for the Sandia **Private Company** user-agreement template if selected?
4. What shot count / repeat structure would QSCOUT recommend for a statistically meaningful but resource-light study?
5. Which calibration/runtime fields can normally be retained by an external user for publication/reproducibility analysis?

## Claims boundary

This whitepaper proposes open, non-proprietary quantum information processing research only. It does not request or imply quantum advantage, Sandia/QSCOUT endorsement, certification, hardware ownership, mission readiness, or deployment authority. A QSCOUT result remains external hardware evidence subject to separate Worldshepherd ingest and identified-human technical review.
# Quantum External Access Capture Matrix — 2026-08-19

**Project:** Worldshepherd Quantum Readiness Fabric (QRF)  
**Frozen workload:** `QRF-BELL-001`  
**Mission state:** SARA-QRF remains 55/100 `NO_GO_BELOW_97` until governed real-hardware evidence closes external gates.  
**Purpose:** Manage all real-QPU access routes under one provider-neutral capture plan without treating outreach, account setup, proposals, program acceptance, or payment as hardware evidence.

## Ranking method

This is a **Worldshepherd capture priority**, not an objective market ranking. Priority favors:

1. near-term probability of obtaining a genuine QPU run;
2. evidence richness (backend identity, calibration/runtime metadata, result provenance);
3. support for repeat/cross-provider comparison;
4. institutional credibility / independent scientific review;
5. low resource burden for the two-qubit Bell workload;
6. urgency of an expiring access window.

## Current ranked access routes

| Rank | Route | Modality / value | Current status | Primary blocker | Evidence yield if successful | Immediate next action |
|---:|---|---|---|---|---|---|
| **1** | **Sandia QSCOUT** | Trapped-ion, white-box testbed; calibration/runtime visibility | Feasibility inquiry sent; one-page whitepaper prepared | Remaining FY2026 capacity + feasibility approval + user agreement | **Very high** — device/run identity, calibration/runtime context, measurements, operator collaboration, repeatability | Await feasibility reply; if positive, submit `QSCOUT_QRF_BELL_001_WHITEPAPER_2026-08-18.md` immediately |
| **2** | **ORNL QCUP** | Merit-reviewed multi-provider access; quantum/classical benchmarking | OLCF ticket `OLCFHELP-27387` redirected to `qcup@ornl.gov`; proposal sent; technical proposal package ready | PI/institution eligibility + project approval | **Very high** — potential multi-provider execution under one DOE user program | Await QCUP response; confirm industry/PI agreement route; submit formal project application when eligible |
| **3** | **IBM Quantum Open Plan** | Direct gate-model access; existing hardened IBM adapter | Adapter/runbook implemented; no IBM Quantum/IBMid account or provisioning evidence found in Gmail | IBM Quantum account/Open Plan instance and local credential provisioning | **High** for first hardware gate; lower white-box depth than testbeds | Establish account/Open Plan locally; never paste token into chat; run `QRF-BELL-001` only after verified plan/instance provenance |
| **4** | **Amazon Braket** | On-demand multi-provider QPU access (AQT, IonQ, IQM, Rigetti; plus QuEra analog) | Braket evidence contract implemented; no AWS/Braket account evidence found in Gmail | AWS account/IAM + enable Braket + third-party device terms | **High** — task/device ARN, provider, result, timing/cost/S3 custody; strong provider breadth | If AWS access is created, prefer a minimal on-demand Rigetti or IQM Bell task before any Hybrid Job or reservation |
| **5** | **Berkeley Lab AQT** | Superconducting full-stack collaborative testbed; deep control/validation access | Direct collaboration inquiry sent; normal user-call cycle currently being restructured | Collaboration acceptance + institutional agreement/CRADA path | **Very high** if accepted — deep stack access, characterization/validation, hardware/software collaboration | Await AQT response; do not force an outdated LOI cycle while the program is restructured |
| **6** | **IonQ direct** | Gate-model trapped-ion; provider-neutral IonQ v0.4 adapter implemented | Technical/APNT outreach sent; no QPU-access provisioning notice found | Direct IonQ project/API access and QPU permission | **High** for second-provider reproduction | Await access/commercial response or use IonQ through QCUP/Braket if that path becomes available first |

## Official-source constraints retained

### QSCOUT

- QSCOUT states that DOE funding redirection will discontinue the program by the end of FY2026 and that only a few short user projects may fit before then.
- Prospective short projects are instructed to contact `qscout@sandia.gov` before submission for feasibility.
- Industry, academia, and government teams may apply; approved non-proprietary users receive testbed/staff access at no fee under the applicable user agreement.
- QSCOUT advertises white-box access including calibration parameters, runtime details, results, and operator interaction.

Primary sources:
- https://www.sandia.gov/quantum/quantum-information-sciences/projects/qscout/
- https://www.sandia.gov/quantum/quantum-information-sciences/projects/qscout-call-for-proposals-2024/

### QCUP

- QCUP resources are granted to approved projects; users/accounts follow project approval.
- Proposals are accepted year-round and reviewed by the Quantum Resource Utilization Council plus independent referees.
- Proposed work must be open, fundamental research and may not use export-controlled, PHI, or other controlled data.
- OLCF explicitly encourages quantum/classical comparative projects.
- OLCF support confirmed `qcup@ornl.gov` is the correct program contact for this proposal.

Primary sources:
- https://www.olcf.ornl.gov/olcf-resources/compute-systems/quantum-computing-user-program/quantum-computing-user-support-documentation/
- https://docs.olcf.ornl.gov/quantum/quantum_access.html
- https://www.olcf.ornl.gov/olcf-resources/compute-systems/quantum-computing-user-program/quantum-classical-computing-hybrid-allocations/

Prepared package:
- `docs/QCUP_QRF_BELL_001_PROPOSAL_2026-08-18.md`

### IBM Quantum Open Plan

- IBM continues to expose an Open Plan with real-QPU allocation; a 2026 promotion offers eligible active Open Plan users additional minutes when opted in.
- Worldshepherd's IBM adapter must verify the actual active instance and plan before QPU submission.
- No IBM Quantum or IBMid provisioning/account notice was found in the connected mailbox, so access is not assumed.

Primary source:
- https://quantum.cloud.ibm.com/docs/en/guides/plans-overview

### Amazon Braket

- Braket provides on-demand access to multiple QPU providers through one AWS service.
- Enabling third-party QPUs requires Braket/IAM setup and acceptance of third-party-device terms.
- Current official device documentation lists gate-model QPUs from providers including AQT, IonQ, IQM, and Rigetti; QuEra is available for analog Hamiltonian simulation.
- Current published on-demand gate-QPU pricing is $0.30 per task plus a provider-specific per-shot charge. As of this capture, Rigetti Cepheus is $0.000425/shot and IQM Garnet is $0.00145/shot.
- Therefore a single 1,024-shot Bell task is approximately $0.7352 on Rigetti or $1.7848 on IQM Garnet; 4,096 shots are approximately $2.0408 or $6.2392 respectively, excluding minor S3/other AWS charges.
- This makes Braket a low-cost direct fallback for the first physical Bell run once an AWS account is established.
- AWS Cloud Credit for Research explicitly supports Braket, but published eligibility is limited to eligible researchers at accredited research institutions; Worldshepherd eligibility is not assumed.
- No AWS/Braket account evidence was found in the connected mailbox; Amazon retail-account messages are not AWS-account evidence.

Primary sources:
- https://docs.aws.amazon.com/braket/latest/developerguide/braket-enable-overview.html
- https://docs.aws.amazon.com/braket/latest/developerguide/braket-using.html
- https://docs.aws.amazon.com/braket/latest/developerguide/braket-submit-tasks.html
- https://aws.amazon.com/braket/pricing/
- https://aws.amazon.com/braket/quantum-computing-research/

### AQT

- AQT's normal annual user-program call is being restructured; the program currently invites direct collaboration discussions instead.
- Teams from academia, industry, and government have historically participated with full-stack hardware/software access.
- Non-proprietary collaborations are designed around publishable research and institutional agreements.

Primary sources:
- https://aqt.lbl.gov/about-aqt/collaborate-with-us/
- https://aqt.lbl.gov/about-aqt/collaborate-with-us/user-letter-of-intent-and-proposal-guide/

## Evidence sequence — whichever route succeeds first

1. **Freeze provider-specific execution configuration before seeing hardware results.**
2. Execute `QRF-BELL-001` on one named physical QPU.
3. Retain immutable raw/normalized program, backend/device, job/run, calibration/configuration, shot/result and timing/cost identities where exposed.
4. Re-hash locally through the external evidence ingest path.
5. Complete identified-human technical review bound to the exact ingest decision.
6. If accepted, classify only as **single external hardware** evidence; do not jump directly to mission readiness.
7. Repeat on the same backend with a distinct result identity.
8. Execute on a second independent provider/modality where scientifically comparable.
9. Evaluate cross-provider sampled distributions under predeclared TVD/Bhattacharyya thresholds.
10. Preserve negative, anomalous and non-reproducing outcomes.

## Current do-not-overclaim boundary

The following do **not** satisfy `SARA-QRF-EXT-01`:

- proposal preparation;
- program eligibility;
- outreach transmission;
- account creation;
- payment or research credits;
- simulator/emulator execution;
- vendor willingness to engage;
- a reserved slot without a completed run;
- provider marketing or benchmark claims;
- one lab's endorsement of the research question.

Only a governed retained result from a named physical QPU can begin to close the first hardware gate.

## Immediate operational priority

**P1 — QSCOUT:** time-critical; await feasibility response and submit the prepared whitepaper immediately if invited.  
**P2 — QCUP:** await direct program feedback; confirm PI/institution/industry agreement path and submit the project form.  
**P3 — IBM Open Plan:** establish self-service account/access locally if available, because this can close the first hardware gate independently of proposal timelines.  
**P4 — Braket:** once an AWS account exists, a small Rigetti/IQM on-demand Bell task is inexpensive enough to be a practical immediate hardware fallback.  
**P5 — AQT:** pursue if collaboration response is positive; very strong evidence depth but less predictable scheduling.  
**P6 — IonQ direct:** keep open, but use whichever IonQ access path (direct, QCUP or Braket) produces the first governed physical result.

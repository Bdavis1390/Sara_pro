# DV019 -> WS-SEMCAP-01 Claims-Controlled Crosswalk

Purpose: use the DV019 semantic-ISR problem as a requirements source without representing WS-SEMCAP as program-qualified.

| Requirement class | WS-SEMCAP evidence field / dimension | Current WS-QX 0.1 state |
|---|---|---|
| EO/video semantic or ROI output | Q_P, Q_S + raw evidence | PROFILE ONLY; performance not validated |
| Mission/context/spatiotemporal reasoning | Q_R | PROFILE ONLY |
| Transmitted-data reduction vs declared baseline | Q_C + baseline_bits/semantic_bits | METRIC IMPLEMENTED; no qualifying measurement claimed |
| Retained mission utility | Q_X + utility ratio | METRIC IMPLEMENTED; no physical result claimed |
| Embedded latency | latency_ms + hardware binding | FIELD IMPLEMENTED; measurement absent |
| Embedded power | power_w + hardware binding | FIELD IMPLEMENTED; measurement absent |
| Constrained/DDIL behavior | Q_D + link profile/fault evidence | PROFILE ONLY |
| Receiver reconstruction | Q_X + reconstruction_fidelity | METRIC IMPLEMENTED; measurement absent |
| Decision/evidence traceability | Q_E + WS-QX envelope | IMPLEMENTED IN SOFTWARE |
| UAS/platform integration | hardware/platform evidence | NOT CURRENTLY CLAIMED |
| Phase-I-equivalent prior evidence | external/program evidence package | NOT CURRENTLY CLAIMED |
| Direct-to-Phase-II eligibility | program-specific determination | NOT CURRENTLY CLAIMED |

This crosswalk is not a compliance matrix and does not establish eligibility. Program requirements must be reverified against the controlling solicitation before submission.

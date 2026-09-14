# WS-CISNET v0.1 — Cislunar Resilient Networking Testbed

Status: IMPLEMENTED AS SIMULATION SCAFFOLD / REQUIRES EXTERNAL HARDWARE VALIDATION  
Date: 2026-09-13

## Purpose

WS-CISNET v0.1 turns the cislunar communications architecture into an executable, evidence-producing testbed. It models a three-node path:

`A (lunar asset) -> B (cislunar relay) -> C (Earth ground station)`

Each leg has an optical primary path and RF resilience path. A relay buffer provides store-and-forward behavior. PRIME-style policy authorizes links, ECHO-style provenance records route decisions and faults in a SHA-256 hash chain, and a simple link-survival score drives proactive fallback.

This is deliberately an aggregate flow simulator. It does **not** claim physical-layer, BPv7, BPSec, cryptographic, LunaNet certification, optical terminal, or flight capability.

## External standards anchor

The intended integration target is the LunaNet Interoperability Specification (LNIS) Version 5, published by NASA/ESA/JAXA. NASA describes LunaNet as an interoperable network of cooperating networks supporting communications, PNT, and other services around and on the Moon. A future integration step is NASA HDTN/BPv7 rather than inventing a proprietary bundle protocol.

## CISNET-DEMO-01 acceptance campaign

Payload: 100 GB decimal. Benchmark input rates are 622 Mbps optical, 80–100 Mbps RF. These are test inputs only; they are not Worldshepherd hardware claims.

Injected disturbances:

1. Earth-facing optical cloud outage.
2. Lunar-side optical pointing loss.
3. Optical degradation below the PRIME policy survival floor.
4. Relay restart with nonvolatile store assumption.
5. RF congestion.
6. Late optical weather outage.

PASS gates:

- no silent data loss;
- destination byte count equals source payload;
- at least one optical-to-RF failover on each leg;
- automatic recovery to the preferred path after faults clear;
- relay store-and-forward continues across contact disruption;
- all route changes are policy-authorized in the simulation control plane;
- ECHO evidence chain verifies end-to-end;
- completion inside the configured timeout.

## Claims control

| Claim | State |
|---|---|
| Three-node hybrid RF/optical simulation | IMPLEMENTED IN SOFTWARE |
| Deterministic route-policy gate | IMPLEMENTED IN SOFTWARE |
| Hash-chained local event provenance | IMPLEMENTED IN SOFTWARE |
| Aggregate store-and-forward model | IMPLEMENTED IN SOFTWARE |
| BPv7/HDTN integration | REQUIRES LAB VALIDATION |
| BPSec cryptographic protection | NOT CURRENTLY IMPLEMENTED |
| LunaNet conformance/certification | NOT CURRENTLY CLAIMED |
| 622 Mbps Worldshepherd optical terminal | NOT CURRENTLY CLAIMED |
| Flight-qualified cislunar network | NOT CURRENTLY CLAIMED |

## Run

From the repository root:

```bash
python -m cisnet.cli --payload-gb 100 --max-time 5000
python -m pytest -q tests/test_cisnet.py
```

The CLI exits non-zero if the transfer does not complete, data are dropped, or the evidence chain fails verification.

## Next engineering increments

- **CISNET-002:** HDTN/BPv7 integration using a real contact plan and bundle generator/sink.
- **CISNET-003:** replace aggregate link flags with time-tagged contact plans, one-way light time, queue limits, and bundle expiration.
- **CISNET-004:** implement BPSec-backed integrity/confidentiality and real identity/key management.
- **CISNET-005:** add weather/pointing/jitter-driven optical link-budget model.
- **CISNET-006:** integrate SARA endpoints for policy approval, ECHO evidence emission, and OVERWATCH telemetry.
- **CISNET-007:** hardware-in-the-loop with two network interfaces and an optical emulator before any cislunar hardware claim.

## Substantial milestone definition

CISNET becomes more than a paper architecture when the same 100-GB fault campaign is run through real BPv7/HDTN processes, all bundles arrive after repeated link loss and restart, BPSec verifies, the ECHO evidence record can be independently checked, and the run is reproducible from a pinned configuration. That is the next evidence gate.

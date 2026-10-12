# WS-CISNET HDTN v0.2 — standards-based DTN integration gate

Status: IMPLEMENTED IN REPOSITORY / REAL BPv7 DISRUPTION PROOF PASS / UPSTREAM REGRESSION RE-RUN IN CI
Date: 2026-09-14

## What changed

WS-CISNET v0.1 proved Worldshepherd's hybrid optical/RF resilient-routing concept in an aggregate simulator. v0.2 moves the evidence boundary to an external standards implementation by pinning and building NASA's High-rate Delay Tolerant Networking (HDTN) software in CI and executing real Bundle Protocol Version 7 application traffic through it.

The integration pins NASA/HDTN at commit `7fbe90cdbe3c8c737efaacb5985f881f95fc7d2a` rather than following an unbounded moving branch. CI installs the Linux build dependencies, checks out that exact revision, disables BPSec only for the v0.2 runtime gate, disables optional x86/RDSEED acceleration for runner portability, and compiles the required HDTN applications from source.

## Cislunar contact-plan artifacts

`integrations/hdtn/ws-cisnet-contact-plan.json` is an HDTN-format engineering contact plan for three logical nodes:

- node 1: lunar asset;
- node 2: cislunar relay;
- node 3: Earth gateway.

The schedule contains deliberate gaps and reduced-rate windows so routing/storage experiments can verify store-and-forward behavior across disruption. The rate values are engineering test inputs only. They are not claims of Worldshepherd optical hardware performance.

`integrations/hdtn/ws-bpv7-delay-contact-plan.json` is the narrower v0.2 runtime proof plan. Its destination-facing contact opens at 20 seconds, providing a deterministic disruption window for the BPv7 evidence gate.

The contact-plan OWLT values are test values chosen to match HDTN's integer field style. They are not precision lunar ephemeris or propagation models.

## Real BPv7 disruption proof

GitHub Actions workflow `WS CISNET BPv7 Disruption Proof`, run `34796587217`, completed successfully against the v0.2 pull-request integration state. The proof used the exact pinned NASA HDTN source revision and generated a deterministic 8 MiB payload.

Observed evidence:

- Bundle Protocol version: 7;
- payload size: 8,388,608 bytes;
- source SHA-256: `1c482c59880cfa1df40873503e7a6541cb2e89fe33e06ff9fdf6f9fc61a2189e`;
- destination SHA-256: `1c482c59880cfa1df40873503e7a6541cb2e89fe33e06ff9fdf6f9fc61a2189e`;
- bytes present at destination during the scheduled pre-contact observation: `0`;
- configured egress contact opening: `20 s`;
- completed delivery: `22 s` after the timed HDTN run began;
- contact-plan SHA-256: `d8e8f7a6806c6bdd32fdec45c60b0c0ae000b5766247a634fa1825f0d87e4c27`;
- ECHO evidence-chain verification: `true`;
- proof result: `PASS`.

The evidence artifact also preserves the HDTN, sender, and receiver logs. This proves byte-identical BPv7 application data delivery through the pinned NASA HDTN runtime while the configured destination-facing contact is unavailable and then becomes available. It does **not** prove a physically separated lunar network, an optical-space link, LunaNet certification, BPSec-protected transport, or flight qualification.

## Upstream regression gate

The broader `WS CISNET HDTN v0.2` workflow also compiles the upstream unit and integrated test executables. An earlier CI attempt invoked those executables outside HDTN's documented build working directory. Several upstream tests resolve fixture files by relative path, so that invocation produced fixture-not-found failures that were not evidence of a BPv7 runtime defect.

The workflow now changes into the pinned HDTN `build` directory before executing the upstream test binaries, matching NASA HDTN's documented invocation. The corrected upstream regression run remains a separate gate: its result must be reported as observed rather than inferred from the successful Worldshepherd BPv7 proof.

## Evidence gates

The v0.2 evidence set separates Worldshepherd's runtime proof from the upstream regression suite:

1. Worldshepherd contact-plan artifacts parse as valid JSON — PASS;
2. upstream source revision exactly matches the pinned commit — PASS;
3. NASA HDTN configures on a clean GitHub-hosted runner — PASS;
4. required NASA HDTN runtime applications compile from source — PASS;
5. deterministic BPv7 payload enters the HDTN topology — PASS;
6. complete destination payload is absent during the scheduled contact gap — PASS;
7. payload is delivered after contact availability — PASS;
8. destination SHA-256 exactly matches source SHA-256 — PASS;
9. ECHO evidence chain verifies — PASS;
10. broad upstream HDTN unit/integrated regression suite from the documented build working directory — CI RE-RUN GATE.

## Claims control

| Claim | State |
|---|---|
| WS-CISNET aggregate resilient-network simulation | IMPLEMENTED IN SOFTWARE |
| HDTN upstream revision pin | IMPLEMENTED IN SOFTWARE |
| HDTN-format cislunar engineering contact plan | IMPLEMENTED IN SOFTWARE |
| Clean-runner NASA HDTN source configuration/build | PROVEN INTERNALLY |
| Real BPv7 byte-identical transfer through pinned NASA HDTN | PROVEN INTERNALLY |
| Scheduled-contact-gap behavior in the v0.2 HDTN runtime proof | PROVEN INTERNALLY |
| ECHO hash-chain for the BPv7 proof record | PROVEN INTERNALLY |
| Full upstream HDTN unit/integrated regression suite under corrected WS gate | REQUIRES CI VALIDATION |
| Three independently running DTN routing/storage nodes | NOT YET CLAIMED |
| Relay restart persistence across a disrupted route | NOT YET CLAIMED |
| BPSec-protected Worldshepherd BPv7 transport | NOT YET CLAIMED |
| LunaNet conformance or certification | NOT CURRENTLY CLAIMED |
| Flight-qualified cislunar communications | NOT CURRENTLY CLAIMED |

## Why BPSec remains outside v0.2

NASA HDTN exposes BPSec configuration and includes BPSec codec/security-context tests, but v0.2 deliberately isolates transport and disruption evidence from operational security-policy evidence. A successful unprotected BPv7 transfer cannot be promoted into a BPSec claim by implication.

The security promotion belongs to v0.3: enable BPSec in the runtime build, provide explicit security-policy/key configuration, verify a protected positive-control transfer, verify rejection under a tampered or wrong-key negative control, and preserve those results in the provenance chain.

## Next promotion gate — v0.3

The next substantial gate is a physically separated lab topology of independently running DTN nodes:

`source-side HDTN -> persistent relay HDTN -> destination-side HDTN`

The relay must retain BPv7 data while the downstream contact is unavailable, survive a controlled relay restart, resume forwarding after contact restoration, and deliver a byte-identical payload. BPSec integrity protection is then added with a negative-control tamper/wrong-key test. ECHO must bind node/configuration hashes, upstream revision, bundle/payload evidence, contact-plan evidence, restart evidence, security-control result, and final delivery into one machine-verifiable record.

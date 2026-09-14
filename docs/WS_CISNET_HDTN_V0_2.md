# WS-CISNET HDTN v0.2 — standards-based DTN integration gate

Status: IMPLEMENTED IN REPOSITORY / EXTERNAL HDTN BUILD VALIDATION PENDING CI  
Date: 2026-09-13

## What changed

WS-CISNET v0.1 proved Worldshepherd's hybrid optical/RF resilient-routing concept in an aggregate simulator. v0.2 moves the evidence boundary toward an actual standards implementation by pinning and building NASA's High-rate Delay Tolerant Networking (HDTN) software in CI.

The integration pins NASA/HDTN at commit `7fbe90cdbe3c8c737efaacb5985f881f95fc7d2a` rather than following an unbounded moving branch. The CI job installs the documented Linux build dependencies, checks out that exact revision, disables BPSec only for this first build gate, disables optional x86/RDSEED acceleration for runner portability, compiles HDTN, then executes the upstream unit and integrated test binaries.

## Cislunar contact-plan artifact

`integrations/hdtn/ws-cisnet-contact-plan.json` is an HDTN-format contact plan for three logical nodes:

- node 1: lunar asset;
- node 2: cislunar relay;
- node 3: Earth gateway.

The schedule contains deliberate gaps and reduced-rate windows so future HDTN routing/storage experiments can verify store-and-forward behavior across disruption. The rate values are engineering test inputs only. They are not claims of Worldshepherd optical hardware performance.

The current contact-plan OWLT value is an integer one-second-per-hop test value chosen to match the field style in HDTN's public sample plan. It is not a precision lunar ephemeris or propagation model.

## Evidence gates

The `WS CISNET HDTN v0.2` workflow must demonstrate all of the following before the integration claim is promoted:

1. the Worldshepherd contact-plan artifact is valid JSON;
2. the upstream source revision exactly matches the pinned commit;
3. NASA HDTN configures successfully on a clean GitHub-hosted Ubuntu runner;
4. NASA HDTN compiles from source;
5. the upstream HDTN unit-test binary passes;
6. the upstream HDTN integrated-test binary passes.

## Claims control

| Claim | State |
|---|---|
| WS-CISNET aggregate resilient-network simulation | IMPLEMENTED IN SOFTWARE |
| HDTN upstream revision pin | IMPLEMENTED IN SOFTWARE |
| HDTN-format three-node cislunar contact plan | IMPLEMENTED IN SOFTWARE |
| Clean-runner NASA HDTN source build | REQUIRES CI VALIDATION |
| Upstream HDTN unit/integrated tests under WS gate | REQUIRES CI VALIDATION |
| Worldshepherd BPv7 end-to-end payload transfer through its own three-node plan | NOT YET CLAIMED |
| BPSec under Worldshepherd policy/key management | NOT YET CLAIMED |
| LunaNet conformance or certification | NOT CURRENTLY CLAIMED |
| Flight-qualified cislunar communications | NOT CURRENTLY CLAIMED |

## Why BPSec is disabled at this gate

NASA HDTN documents BPSec support, but its current build path requires an OpenSSL FIPS configuration. v0.2 separates two evidence questions: first, can Worldshepherd reproducibly pin, compile, and execute the NASA HDTN test suite; second, can the resulting lab topology pass authenticated and encrypted BPv7 traffic under BPSec. The second question becomes the v0.3 security gate rather than silently weakening the claim.

## Next promotion gate

The next promotion requires real BPv7 application traffic to traverse a Worldshepherd-controlled HDTN topology using a generated contact plan, survive at least one scheduled outage, arrive byte-identical at the destination, and produce a machine-verifiable ECHO evidence record containing source revision, contact plan hash, payload hash, delivery hash, and test result.

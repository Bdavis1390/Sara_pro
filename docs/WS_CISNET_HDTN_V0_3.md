# WS-CISNET HDTN v0.3 — independent-node persistence and security promotion

Status: MULTINODE PERSISTENT-RELAY BPv7 PROOF PASS / BPSec SECURITY GATE PENDING
Date: 2026-09-14

## Objective

v0.3 promotes WS-CISNET from a single HDTN routing runtime plus application endpoints to a laboratory DTN composed of multiple independently running NASA HDTN routing/storage processes.

The first v0.3 gate is deliberately transport/persistence focused. It proves that BPv7 data can be accepted by a source-side HDTN node, transferred to a separate relay HDTN node, survive loss of the source-side node and a controlled relay process restart, then resume toward a third HDTN node and arrive byte-identical at the destination application.

BPSec is the second v0.3 gate. It is not implied by the persistence proof and remains unclaimed until its own positive and negative controls pass.

## Topology

The CI topology is:

`BPv7 source app -> HDTN node 1 -> persistent HDTN relay node 2 -> HDTN node 3 -> BPv7 sink app`

All three HDTN instances run as distinct OS processes with unique TCPCLv4 and internal ZMQ ports. Node 2 uses persistent on-disk storage and has separate initial/restore configurations:

- `node2-initial.json`: `tryToRestoreFromDisk=false`, `autoDeleteFilesOnExit=false`;
- `node2-restore.json`: `tryToRestoreFromDisk=true`, `autoDeleteFilesOnExit=false`.

This is a process-isolated laboratory topology on one GitHub-hosted CI machine. It is not a claim of physically separated spacecraft or ground stations.

## Scheduled disruption and restart sequence

`multinode-contact-plan.json` deliberately separates the first and second routing contacts:

- node 1 -> node 2: available from 0–20 s;
- node 2 -> node 3: available from 30–180 s;
- node 3 -> destination node 4: available from 0–180 s.

The workflow starts all three HDTN instances and the destination receiver, injects a deterministic 8 MiB BPv7 file, waits while the downstream relay contact is unavailable, then:

1. verifies the complete destination file is not present;
2. records the relay storage footprint;
3. stops node 1 so the source-side router can no longer resend after the relay restart;
4. cleanly stops relay node 2 while its persistent store is retained;
5. verifies the destination still lacks the complete file;
6. restarts node 2 with disk restoration enabled;
7. waits for the restored relay to forward once the downstream contact becomes available;
8. requires destination size and SHA-256 to equal the source;
9. records an ECHO hash-chain evidence record plus all node/application logs.

## Observed proof — GitHub Actions run 34797872375

The multinode proof completed successfully against Worldshepherd head commit `d09adde39f83c1bd586620656fd07b86fbf61497` and pinned NASA HDTN commit `7fbe90cdbe3c8c737efaacb5985f881f95fc7d2a`.

Machine-verifiable evidence:

- Bundle Protocol version: 7;
- payload size: 8,388,608 bytes;
- source SHA-256: `d0cf10c30a9f38a917b3f2d58287236c22153119fffd661f24fa86ed8bf6a0ac`;
- destination SHA-256: `d0cf10c30a9f38a917b3f2d58287236c22153119fffd661f24fa86ed8bf6a0ac`;
- destination bytes before restart: `0`;
- destination bytes after relay stop / before restore: `0`;
- relay restart timestamp: `17 s`;
- completed delivery timestamp: `48 s`;
- relay store footprint immediately before restart: `8,454,144 bytes`;
- relay store footprint after delivery: `8,454,144 bytes`;
- contact-plan SHA-256: `587198214baf35668e90eb5d06517799814970eee46680929e5e41e26503e860`;
- ECHO ledger verification: `true`;
- source-side HDTN process confirmed stopped before relay restore: `true`;
- result: `PASS`.

The retained relay logs strengthen the persistence evidence beyond checking file existence. Before shutdown, node 2 had accepted 17 bundles totaling 8,390,682 bundle bytes, reported 17 bundles in storage, and had sent zero bundles to egress. After restart, the restored relay logged completion of its disk restore and subsequently sent and acknowledged all 17 bundles / 8,390,682 bundle bytes downstream.

The destination receiver then completed `payload.bin`; its SHA-256 exactly matched the source. This rules out a successful result caused merely by a source-side retransmission after the relay restart because node 1 had already been stopped.

The uploaded proof artifact is `ws-cisnet-v0-3-multinode-persistence`, artifact ID `10330278097`, digest `sha256:706cb5f36e74d7ea04560449d1f41c9aa9fb827138b333e705c19e51e12cf0e5`. It preserves the ECHO evidence JSON plus source, node1, node2-initial, node2-restored, node3 and receiver logs.

## Evidence gates

The persistence gate now records:

- all v0.3 JSON topology artifacts parse successfully — PASS;
- NASA HDTN exact pinned revision checkout — PASS;
- `hdtn-one-process`, `bpsendfile`, and `bpreceivefile` clean-runner build — PASS;
- destination lacks the complete payload before relay restart — PASS;
- relay persistent store populated before restart — PASS;
- node 1 stopped before relay restoration — PASS;
- relay node 2 restarted with `tryToRestoreFromDisk=true` — PASS;
- restored relay forwards all 17 stored bundles downstream — PASS;
- destination payload size exactly equals source payload size — PASS;
- destination SHA-256 exactly equals source SHA-256 — PASS;
- ECHO evidence chain verifies — PASS;
- node/application logs and artifact digest retained — PASS.

## Claims control

| Claim | State |
|---|---|
| v0.2 real BPv7 transfer through pinned NASA HDTN | PROVEN INTERNALLY in v0.2 evidence |
| Three independently running HDTN routing/storage processes configured | IMPLEMENTED IN SOFTWARE |
| TCPCLv4 chained source -> relay -> destination topology | PROVEN INTERNALLY |
| Persistent relay configuration with explicit restore mode | PROVEN INTERNALLY |
| Byte-identical BPv7 delivery after source shutdown and relay restart | PROVEN INTERNALLY |
| Bundle residency in relay persistent storage across restart | PROVEN INTERNALLY |
| Restored relay forwarding of all 17 stored bundles | PROVEN INTERNALLY |
| BPSec integrity-protected Worldshepherd transfer | NOT YET CLAIMED |
| BPSec negative-control rejection | NOT YET CLAIMED |
| Physically distributed lunar/space network | NOT CURRENTLY CLAIMED |
| LunaNet conformance/certification | NOT CURRENTLY CLAIMED |
| Flight qualification | NOT CURRENTLY CLAIMED |

## BPSec promotion after persistence

NASA HDTN exposes BPSec policy configuration to HDTN and BP applications and provides integrity/confidentiality examples. Worldshepherd does not count the existence of that upstream capability as a Worldshepherd security demonstration.

The next v0.3 security subgate must independently demonstrate:

1. HDTN runtime compiled with BPSec enabled in an environment satisfying its actual build/runtime requirements;
2. an explicit BIB integrity policy and CI-only test key configuration for the source and security acceptor;
3. successful protected BPv7 delivery through the Worldshepherd topology;
4. a negative control in which a wrong key, invalid policy, or deliberately modified protected bundle is rejected rather than silently accepted;
5. provenance binding policy/config hashes, key identifier/hash (never production secret key material), HDTN revision, payload hashes, positive-control result, negative-control result, and ECHO chain.

FIPS validation is a separate evidence question. A functional BPSec run will not be labeled FIPS-compliant unless the cryptographic module/configuration itself is separately validated.

Confidentiality/BCB is a later extension after the BIB integrity gate is reproducible.

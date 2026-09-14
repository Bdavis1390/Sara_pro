# WS-CISNET HDTN v0.3 — independent-node persistence and security promotion

Status: IMPLEMENTED IN REPOSITORY / MULTINODE CI PROOF PENDING
Date: 2026-09-14

## Objective

v0.3 promotes WS-CISNET from a single HDTN routing runtime plus application endpoints to a laboratory DTN composed of multiple independently running NASA HDTN routing/storage processes.

The first v0.3 gate is deliberately transport/persistence focused. It must prove that a bundle can be accepted by a source-side HDTN node, transferred to a separate relay HDTN node, survive loss of the source-side node and a controlled relay process restart, then resume toward a third HDTN node and arrive byte-identical at the destination application.

BPSec is the second v0.3 gate. It is not implicitly claimed by the persistence proof.

## Topology

The CI topology is:

`BPv7 source app -> HDTN node 1 -> persistent HDTN relay node 2 -> HDTN node 3 -> BPv7 sink app`

All three HDTN instances run as distinct OS processes with unique TCPCLv4 and internal ZMQ ports. Node 2 uses persistent on-disk storage and has separate initial/restore configurations:

- `node2-initial.json`: `tryToRestoreFromDisk=false`, `autoDeleteFilesOnExit=false`;
- `node2-restore.json`: `tryToRestoreFromDisk=true`, `autoDeleteFilesOnExit=false`.

This is a process-isolated laboratory topology on one CI host. It is not a claim of physically separated spacecraft or ground stations.

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

A passing run therefore requires delivery after the source-side HDTN process has already been removed and after the relay process has been reconstructed from persistent storage.

## Evidence requirements

The multinode gate is PASS only when all of the following hold:

- all v0.3 JSON topology artifacts parse successfully;
- NASA HDTN is checked out at the repository-pinned revision;
- `hdtn-one-process`, `bpsendfile`, and `bpreceivefile` compile on the clean runner;
- the destination does not contain the complete payload before relay restart;
- relay storage files exist before restart;
- node 1 is stopped before relay restoration begins;
- relay node 2 stops and restarts using `tryToRestoreFromDisk=true`;
- destination payload size exactly equals source payload size;
- destination SHA-256 exactly equals source SHA-256;
- the ECHO evidence chain verifies;
- node, sender, receiver, contact-plan and source-revision provenance are preserved.

## Claims control

| Claim | State |
|---|---|
| v0.2 real BPv7 transfer through pinned NASA HDTN | PROVEN INTERNALLY in v0.2 evidence |
| Three independently running HDTN routing/storage processes configured | IMPLEMENTED IN SOFTWARE |
| TCPCLv4 chained source -> relay -> destination topology | IMPLEMENTED IN SOFTWARE |
| Persistent relay configuration with explicit restore mode | IMPLEMENTED IN SOFTWARE |
| Byte-identical delivery after source shutdown and relay restart | REQUIRES CI VALIDATION |
| Proven bundle residency in relay persistent storage across restart | REQUIRES CI VALIDATION |
| BPSec integrity-protected Worldshepherd transfer | NOT YET CLAIMED |
| BPSec negative-control rejection | NOT YET CLAIMED |
| Physically distributed lunar/space network | NOT CURRENTLY CLAIMED |
| LunaNet conformance/certification | NOT CURRENTLY CLAIMED |
| Flight qualification | NOT CURRENTLY CLAIMED |

## BPSec promotion after persistence

NASA HDTN exposes BPSec policy configuration to HDTN and BP applications and provides integrity/confidentiality examples. Worldshepherd will not count the existence of that upstream capability as a Worldshepherd security demonstration.

The next v0.3 security subgate must independently demonstrate:

1. HDTN runtime compiled with BPSec enabled in an environment satisfying its OpenSSL/FIPS requirements;
2. an explicit BIB integrity policy and key configuration for the source and security acceptor;
3. successful protected BPv7 delivery through the Worldshepherd multinode topology;
4. a negative control in which a wrong key, invalid policy, or deliberately modified protected bundle is rejected rather than silently accepted;
5. provenance binding the policy hashes, key identifiers (never secret key material), HDTN revision, payload hashes, positive-control result, negative-control result, and ECHO chain.

Confidentiality/BCB is a later extension after the BIB integrity gate is reproducible.

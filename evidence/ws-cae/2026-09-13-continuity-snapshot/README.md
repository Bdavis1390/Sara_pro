# WS-CAE four-chain continuity snapshot proof

Status: public research evidence; not a chain endorsement, certification, standards-body adoption, or claim of full post-quantum security.

This directory preserves the deterministic four-chain continuity snapshot that was independently reproduced in Python and Node.js and keylessly attested through Sigstore in GitHub Actions.

## Snapshot

Subjects:
- Algorand
- Bitcoin
- Ethereum
- Sui

Snapshot ID:

`sha256:dbdbb6f1588c7c380f91e8d4d054f0bb2ab19df9ed5d36ee7dd40bf9dd1cd3e7`

SCITT-oriented snapshot statement SHA-256:

`e3011d9a2ef7246ee8ce056a2a66e85144d7f7ceef4e0d4a2c5cecaf9e65a9eb`

## Independent reproduction

The `WS-CAE Continuity Cross-Language Vectors` workflow independently reproduced the snapshot ID using a Node.js standard-library implementation after the Python implementation generated the snapshot. The same run passed the continuity-specific Python suite.

## Sigstore proof

The `WS-CAE DATL Transparency Attestation` workflow:
1. built the four-chain snapshot and SCITT-oriented statement;
2. created a predicate binding the exact snapshot ID, statement digest, date, manifest count, and subjects;
3. used Cosign keyless signing with GitHub Actions OIDC;
4. verified the attestation against the repository/workflow identity;
5. produced a Sigstore v0.3 bundle containing transparency-log material.

The preserved files in this directory are copied from that successful workflow artifact. The cryptographic bundle is public verification material and contains no wallet keys, cryptocurrency signing keys, secrets, transactions, or asset-control authority.

## Boundary

The snapshot records evidence-backed migration/authority classifications at the stated observation date. It does not prove that the underlying evidence is complete or permanently current. It does not establish post-quantum security of any named ecosystem as a whole. Relying parties must independently review evidence and critical dependencies.

# WorldShepherd — Scientific execution-custody integration contract v0.1

**State:** proposed operational interface contract; a narrow **standalone signed ECHO scientific-event inclusion verification adapter** now exists under `tools/claim_evidence_gate/scientific_echo_witness.py` with test-only ECHO signing. **No live SARA ingestion, PRIME scientific authorization or operational activation** is implemented. Child of #281 Platform & Assurance and #282 Science & Validation; no fourth top-level task. Public-safe architecture only.

## Authority and evidence are separate trust boundaries

Existing source-of-truth:
- \`docs/CLAIMS_AND_EVIDENCE_POLICY.md\`
- \`deployments/sara_verified_local_v1/docs/ECHO_CHECKPOINT_V1_7_DESIGN.md\`
- \`docs/WS_RESTRICTION_PROVENANCE_G6B.md\`
- \`tools/claim_evidence_gate/README.md\`

The installed SARA/ECHO checkpoint path is a working reference for **signed semantic evidence inclusion** in a locally maintained checkpoint ledger. It is **not** a validated scientific process-attestation service. This contract proposes using its established public-key separation, predecessor linkage, explicit key pinning, and independent verification conventions for *new scientific execution events*, subject to implementation and tests.

## Required authority chain

\`\`\`text
PREREG: claim, controls, null, test and falsification rules
    |
    v independently retained pre-run freeze digest (not a file shipped with result)
PRIME: scope-limited authorization (external signer; SARA accepts only verified authorization)
    |
    v authorized experiment invocation + bounded resource budget
SARA / controlled execution adapter
    |
    v receipt: the bytes consumed, executable identity, result digest and status
ECHO: verified semantic-event ingestion, checkpoint with predecessor chain
    |
    v signed checkpoint + separate verifier-supplied trusted key fingerprint
OVERWATCH: reconciliation and negative-evidence visibility
    |
    v SCIENTIFIC REVIEW, never automatically promoted by custody alone
\`\`\`

## Proposed semantic event (conceptual contract; do not treat as an implemented API)

The canonical *scientific execution* event must be immutable at the evidence layer and include:

| Field | Required meaning |
| --- | --- |
| \`schema\` | Versioned namespace distinct from restriction-event schemas |
| \`event_id\` / \`run_id\` | Unique persistent identity, replay-safe |
| \`claim_id\` / \`prereg_sha256\` | Exact claim to evaluate and separately frozen preregistration digest |
| \`prime_authorization_id\` | External scope-limited authority reference; verification mandatory |
| \`executor_identity\` / \`code_sha256\` | Measured executor identity; self-reported executable hash is **insufficient** |
| \`configuration_sha256\` / \`input_sha256\` | Hashes of actual bytes passed to the computation |
| \`result_sha256\` / \`status\` | Output digest, exit status, nonconvergence/negative outcomes where relevant |
| \`environment_identity\` | Interpreter/container/firmware and dependency identity, as applicable |
| \`time_boundary\` | Start/end as source-reported metadata; independent clock trust requires separate evidence |
| \`event_semantic_sha256\` | Domain-separated digest of stable event fields |
| \`echo_checkpoint\` | Signed checkpoint and membership witness verified separately |
| \`limitations\` | Unproven or unauthenticated aspects, including physical instrumentation |

The **witness verification** must:
1. Verify PRIME authorization using configured allowed, nonrevoked public keys and the exact bounded action scope **before** execution; never ingest or persist a PRIME private signing key in SARA.
2. Bind a preregistration digest to an externally held pre-run freeze; do not accept a hash and its purported anchor from the same mutable package as independent proof.
3. Bind the actual configuration bytes read by the trusted executor, preserving input/output negative evidence and return status; reject mismatched or missing bytes.
4. Ingest a semantically stable execution record, reject event-ID reuse with differing content, and retain deterministic replay behavior.
5. Verify ECHO checkpoint membership, signature, predecessor chain, and key fingerprint against a **separate pinned fingerprint** (not one copied from the untrusted bundle).
6. Reject missing, revoked, malformed, substituted, reordered, or stale witness evidence and treat lost ECHO connectivity as a defined degraded state.
7. Reconcile every event against PRE claim IDs, run IDs, control requirements, and the raw-evidence manifest without rewriting failed records.
8. Require human scientific review for novelty, calibrations, uncertainty, measurement validity, theorem soundness, numerical convergence and independent replication.

## Distinct acceptance labels

- **FILE INTEGRITY:** on-disk recorded bytes match SHA-256.
- **LOCAL EXECUTION REPRODUCIBLE:** an independent rerun of the bounded software operation produces the recorded output from recorded bytes; current \`bounded_execution.py\` is a self-reporting reference.
- **PRE-RUN FREEZE VALIDATED:** an authenticated, separately controlled preregistration record predates an authorized execution.
- **TRUSTED EXECUTION BOUND:** a verified authority and trusted executor/controller provide evidence that the recorded bytes were actually used, under a defined threat model.
- **SIGNED EVENT CUSTODY:** an execution event's exact semantic digest was included in an independently verified ECHO checkpoint.
- **SCIENTIFICALLY VALIDATED:** requires domain-appropriate independent controls/measurements/review; **never implied** by any of the previous labels.

A green CI check, valid cryptographic signature, passing software fixture, or signed checkpoint cannot by itself establish experimental energy transfer or novel physical phenomena.

## Negative acceptance tests before any integration promotion

- Tampered/absent/replayed/revoked PRIME authorization; scope or budget escalation.
- Missing pre-run freeze or an anchor supplied only with the result.
- Executor identity mismatch, configuration substitution after authorization, environment mismatch.
- Swapped input, changed output, forged local receipt and fabricated timestamps.
- ECHO witness whose signature verifies under a **bundle-provided but unpinned** key.
- Wrong checkpoint chain, removed event, replacement event, duplicate ID with new semantics.
- Failed or inconclusive control disguised by a later PASS; nonconverged numerical solver reported as successful.
- Offline/degraded replay without correct once-per-semantic-record reconciliation.
- Attempted scientific-status upgrade solely from verification or custody pass.

## Implementation / release boundary

1. Treat \`bounded_execution.py\` and its tests as a local synthetic execution demonstration only.
2. Build a narrow verifier adapter reusing vetted SARA/PRIME and ECHO verification APIs. Keep the scientific event schema separately versioned and domain-separated.
3. Demonstrate actual protected CI on the exact candidate commit with replay, bad-key, tamper, revocation, recovery, and negative-evidence cases.
4. Require an identified owner to approve schema, privilege, privacy, custody and public-release boundaries before a protected merge or operational activation.
5. Retain the original Palace campaign, unpublished scientific artifacts, contact information, credentials and partner-controlled data outside public source. Do not move data into public CI as a convenience.

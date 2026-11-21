# WorldShepherd Claim-Evidence Gate — Standalone v0.3 Prototype

**Scope:** software-level validation of a structured research evidence envelope. It does not certify science, instrument calibration, operational security, mathematical correctness, originality, or independent replication.

**State:** candidate review implementation under #281 Platform & Assurance and #282 Science & Validation. Not installed in canonical SARA. The fixture is entirely **synthetic** and does not establish a physical RF effect.

## Reproduce the demo

Requires Python 3.12+ and its standard library. From the repository root:

```bash
python -m unittest discover -s tools/claim_evidence_gate/tests -v

PIN="$(cat tools/claim_evidence_gate/examples/PREREG_PIN.sha256)"
python tools/claim_evidence_gate/claim_gate.py \
  --prereg tools/claim_evidence_gate/examples/preregistration.json \
  --package tools/claim_evidence_gate/examples/package.json \
  --root tools/claim_evidence_gate/examples \
  --pinned-prereg-sha256 "$PIN" \
  --out /tmp/ws-claim-gate-audit.json
```

Expected synthetic example: 3 matching SHA-256 artifact digests, **3 SHA-256-verifiable run configuration bindings**, 2 self-declared passing synthetic control records, 1 inconclusive synthetic simulation record, and `integrity=PASS`. **This is structural consistency only.** All scientific result promotion still requires identified human review.

## Validated in the current prototype

- SHA-256 of declared artifact files matches claimed hashes.
- Every run must provide `config_artifact` (`path`, `sha256`) and `config_sha256`; the bytes at the referenced path must match **both** hashes. Unavailable, symlinked, traversing, or altered configuration files fail closed, and cannot support a control or evidence-class promotion.
- Preregistration canonical JSON digest matches the caller-supplied pin.
- Required control records exist, have verifiable artifacts and PASS outcomes; a failed run cannot be masked by a different passing run of the same required control.
- Summary event IDs and outcome totals reconcile with records.
- Rejects unsafe artifact paths (including traversal and symlink paths), malformed event fields, missing inputs, unexpected evidence classes and unsupported status promotions.
- Always reports `claim_automatically_proven: false`, `external_independence_verified: false` and `requires_human_review: true`.

## Explicitly NOT verified

- The in-repository example pin is *not* externally timestamped or independently anchored. Use a trusted separately retained preregistration digest for real experiments.
- The prototype verifies actual **recorded** configuration file bytes, but it does **not** prove an experiment or executable consumed that configuration, that the bytes were frozen before execution, or that the snapshot is immutable. This remains a documented integration blocker for operational use.
- Outcome PASS/FAIL labels are supplied by the record; the tool does not execute physical controls or prove test correctness.
- A string in `independent_attestation_anchor` is not verified as a cryptographic signature.
- File reads have a potential time-of-check/time-of-use race on hostile mutable filesystems; use immutable snapshots and stronger custody controls for untrusted sources.
- No environment, scientific method, calibration, measurement uncertainty, numerical convergence, mathematical proof, independent peer review, or lab instrumentation is checked.
- This prototype is not an approved production API and does not confer certification or compliance.

## Integration path

1. Validate exact-commit source through reviewable GitHub CI.
2. Independently bind runtime execution and its environment identity to the already verified recorded configuration bytes, retaining an immutable pre-run custody record.
3. Add an externally verified ECHO witness and preregistration freeze.
4. Separate structural integrity from scientific-domain validation gates.
5. Integrate into canonical SARA only after PRIME authorization contract and OVERWATCH reporting/rollback tests pass.




## Dedicated PRIME-scoped synthetic scientific authorization (candidate)

\`scientific_prime_authorization.py\` defines \`WS-PRIME-SCIENTIFIC-EXECUTION-AUTHZ-V1\` and \`SCIENTIFIC_EXECUTION_SYNTHETIC\` independently of the canonical \`REQUALIFICATION_RELEASE\` assertion. The verifier uses the existing **canonical** \`PrimeSentinelVerifier.verify_detached_signature\` and its revoked/unknown-key rejection, but introduces a domain-separated signing message and a strictly bounded synthetic-science scope. The signing private key is not accepted or stored by the verifier.

The grant binds **claim ID, caller-provided preregistration digest, exact run ID, actual configuration/input bytes, executor source digest, 15-minute maximum lifetime, nonce, one named operation and maximum number of samples**. The caller must separately provide and trust the signing-key fingerprint; merely using the public key included in an untrusted grant is not independent validation.

The \`integration/test_scientific_prime_authorization.py\` suite uses an ephemeral test Ed25519 signer and checks expired, revoked, future-dated, stale/replayed-in-memory, mismatched payload, tampered signatures, bad source digest, over-budget input, and attempted substitution of an existing non-science PRIME action.

**Remaining authorization boundaries:**
- **No production grant issuer exists in this candidate.** Real operator authorization and approved signing-key ownership must be designed and reviewed before operational use.
- \`verify_scientific_authorization\` verifies a proposed grant and returns \`authorized_run_executed=false\`. It does **not** call \`run_bounded\`, change canonical SARA, or modify the signed ECHO-science event.
- The optional consumed nonce/ID sets are **caller-managed negative-test hooks** only. They are neither a durable reservation/consumption ledger nor a concurrency control; **replay resistance is not established**.
- A caller-supplied preregistration digest is checked for equality, but no independently timestamped pre-run freeze is provided or validated.
- Execution with verified in-memory configuration bytes, fail-closed grant reservation, and independent postexecution witness remain separate required integration steps.
- No real-world laboratory instrument, telescope, RF apparatus, material or compute job has been authorized or executed by this candidate.

## Signed ECHO scientific-event inclusion candidate

\`scientific_echo_witness.py\` reuses **canonical** \`worldshepherd_sara.echo_event_store.semantic_sha256\`, \`AuditRecord\`, and \`worldshepherd_sara.echo_checkpoint_verify.verify_bundle\`. It constructs a narrowly scoped scientific-event candidate after the bounded runner's receipt is locally reproduced, then checks whether the **exact semantic event** appears in the final checkpoint of a **complete, predecessor-verified Ed25519-signed ECHO checkpoint chain** (beginning at sequence 1) under a separately supplied **trusted** key fingerprint.

The separate \`integration/test_scientific_echo_witness.py\` suite uses an isolated ECHO event store and a disposable test-only Ed25519 signer. It checks valid membership, wrong key pin, corrupted signature/manifest, missing event, altered semantic fields, forged authorization flags, replay timestamp stability, invalid preregistration pin, source/raw receipt tampering, and same-ID/different-content conflict. Its chain tests additionally reject missing genesis, reversed checkpoints, repeated sequence numbers, incorrect predecessor links, and changed key fingerprints. The CI \`signed-echo-witness\` job installs the canonical SARA runtime package and exercises **real cryptographic verification**, not a stub.

Run in a supported Python environment with the canonical package installed:

\`\`\`bash
python -m pip install -c deployments/sara_verified_local_v1/constraints-ci.txt -e deployments/sara_verified_local_v1
python -m unittest discover -s tools/claim_evidence_gate/integration -v
\`\`\`

**Critical distinctions:**
- A valid checkpoint proves only inclusion of the exact semantic event under the **supplied pinned key**. It does not establish that the key is independently controlled, that signer identity is hardware-backed, or that event contents correspond to physical truth.
- The positive test's trusted key fingerprint is provided by its own isolated test setup; this is **not third-party witnessing or external preregistration anchoring**.
- The adapter has **no live ECHO ingestion**, no dedicated authorization issuance, no PRIME signature verification and no deployment to production SARA.
- The event permanently says \`prime_authorization_verified=false\` and \`preexecution_freeze_verified=false\`. The verifier's receipt permanently reports \`third_party_witness_verified=false\`, \`independent_process_attestation_verified=false\`, and \`scientific_claim_proven=false\`.
- Signatures and local evidence checks remain separate from measurement validation and scientific review.

## Bounded execution/custody reference (separate from the v0.3 claim gate)

\`bounded_execution.py\` demonstrates a **fixed synthetic affine transform**. It reads configuration and input bytes once into memory, hashes those exact byte objects, and uses the same objects for deterministic calculation. It writes a self-reported receipt and output in a new run-specific directory. The verifier rereads configuration, input and output bytes; verifies their digests; independently recomputes the fixed calculation; checks the recorded code digest against the locally installed module; and refuses a receipt that claims independent witnessing. It does **not** authenticate an external instrument or certify that a separate physical process obeyed these settings.

To reproduce without modifying tracked fixtures:

\`\`\`bash
TMP="$(mktemp -d)"
cp tools/claim_evidence_gate/examples/bounded_exec/*.json "$TMP/"
python tools/claim_evidence_gate/bounded_execution.py run \
  --root "$TMP" --config config.json --input input.json --run-id demo1
python tools/claim_evidence_gate/bounded_execution.py verify \
  --root "$TMP" --receipt runs/demo1.receipt.json
rm -rf "$TMP"
\`\`\`

The bounded runner has **no arbitrary-execution feature**, reads files only within the selected root, rejects symlinks and traversal, and fails if an existing run would be overwritten. The additional regression tests exercise malformed configuration, bad input, incorrect output, forged self-attestation, source substitution, and post-run tampering.

### Limits of this reference

- The receiver has **not** authenticated which operating-system process produced the original receipt. The source digest only compares the current verifier to a self-reported source identity.
- No independent clock, ECHO checkpoint, externally pinned public-key identity, isolated hardware or remote attestation is involved.
- A process with write access to all local files can replace inputs, output and a self-reported receipt; recomputing a digest is not a substitute for externally trusted custody.
- The bounded runner is **not wired into** \`claim_gate.py\` or the canonical SARA runtime. The existing v0.3 audit still evaluates declared software evidence and must not claim this separate test ran for an unrelated scientific artifact.
- File-based validation on a hostile mutable filesystem remains susceptible to TOCTOU races. The reference does not attempt sandbox process isolation or guarantee durable transactional writes.
- This test establishes only bounded synthetic software behavior. No material property, resonant-field effect, numerical solver convergence, mathematical theorem, scientific novelty or independent laboratory result is established.

**Next trust boundary:** define a PRIME-authorized invocation that binds a pre-run digest; emit an ECHO-consumable semantic event including exact execution identity and read-byte hashes; verify inclusion in a signed checkpoint against a separately pinned ECHO public-key fingerprint; separately evaluate whether physical instrumentation actually used the intended settings.

**Security:** public repository, synthetic fixtures only. Never commit original private Palace archives, unpublished laboratory raw data, partner IP, credentials, regulated material, or private contact details.

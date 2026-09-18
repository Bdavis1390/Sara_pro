# WS-RESTRICTION-PROVENANCE G6 — SIGNED ECHO WITNESS VERIFICATION

Status: **MERGED ON PROTECTED MAIN / PROVEN INTERNALLY FOR TESTED SIGNED-WITNESS INVARIANTS**

## Objective

G6 closes the authenticity gap left intentionally open by G4 and G5.

G4 binds `PRIME_SENTINEL` into the restriction identity. G5 binds fingerprint-key epoch provenance. Those controls detect inconsistent or stale application-level evidence, but a party able to rewrite the entire bounded record can still recompute an internally consistent unkeyed `restriction_id`.

G6 adds a stronger acceptance boundary:

> a restriction record is witness-verified only when its exact semantic event is included in an Ed25519-signed ECHO checkpoint whose public key matches a separately supplied trusted fingerprint.

## Reuse of existing ECHO trust machinery

G6 does not introduce a second signing stack.

It reuses:

- ECHO semantic event hashing;
- ECHO Merkle checkpoint membership;
- Ed25519 checkpoint signatures;
- checkpoint key IDs and public-key fingerprints;
- existing fail-closed checkpoint verification.

The verifier requires `expected_checkpoint_key_fingerprint_sha256` from outside the checkpoint bundle. The bundle cannot establish trust in its own embedded key.

## Witness receipt

A successful verification returns a bounded receipt containing:

- restriction ID;
- stable SARA/ECHO event ID;
- authority;
- restriction fingerprint-key epoch ID;
- checkpoint ID and sequence;
- checkpoint digest;
- Ed25519 signer key ID;
- trusted signer public-key fingerprint.

Raw restricted content, safe summaries, and unrestricted metadata are not added to the receipt.

## Adversarial boundary

The G6 tests include a deliberately stronger forgery than G4/G5:

1. change a safe semantic field in the restriction record;
2. recompute the application-level restriction ID;
3. recompute the stable outbox event ID;
4. confirm ordinary restriction projection now accepts the self-consistent forged record;
5. require the signed-witness verifier to reject it because that exact semantic event was never included in the trusted signed checkpoint.

Additional fail-closed cases include:

- wrong out-of-band signer fingerprint;
- checkpoint signature tampering;
- checkpoint omission of the target event.

## Executable 10x metric

G6 declares four unsigned-authenticity residual classes at the G5 boundary:

1. fully rewritten self-consistent safe evidence accepted without signed inclusion;
2. signer trust derived only from material embedded in the evidence bundle;
3. checkpoint signature tampering not checked at the restriction-verification boundary;
4. a restriction event can be treated as witnessed even when omitted from the signed checkpoint.

Baseline residual units: **4**.

10x threshold: **<= 0.4 residual units**.

Because the count is integral, the practical G6 pass condition is **0/4 residual authenticity classes open**.

This is a bounded authenticity metric. It is not a universal security multiplier.

## Claims boundary

G6 establishes local cryptographic signer verification under a separately trusted Ed25519 public-key fingerprint and signed ECHO checkpoint inclusion.

It does not establish:

- independent third-party witnessing;
- HSM, TPM, KMS, or offline-root custody;
- signer non-compromise;
- immutable/WORM external retention;
- anti-rollback against a privileged operator who controls both storage and signing key;
- policy correctness;
- certification;
- customer/government acceptance;
- independent external reproduction.

Those remain later gates.

## Next gate

G7 should address **secret/signing-key custody and rollback resistance**: reduce software/filesystem key-custody exposure, define independent or hardware-backed custody where justified, and measure whether privileged local compromise can forge or roll back trusted evidence.


## Protected-main evidence state

G6A merged through PR #434 and was retained unchanged through combined PR #442. Its required signed-witness tests and the full Verified Local deployment/recovery/evidence qualification passed before the combined assurance baseline advanced. Claims remain limited to the documented local signed-checkpoint inclusion and trust-fingerprint invariants.

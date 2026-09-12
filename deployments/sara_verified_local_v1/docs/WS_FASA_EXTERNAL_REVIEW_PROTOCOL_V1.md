# WS-FASA External Review Protocol v1

**Status:** REVIEW PROCEDURE / NO AUTHORITY / NO READINESS / NO EXECUTION  
**Applies to:** Worldshepherd Frontier AI Safety Assurance (WS-FASA) independent-review evidence lane  
**Current internally tested reviewer-CLI baseline:** `ce0076c8063e4e692f5041e5389ac9d75ea8b6cb`  
**Claims rule:** No evidence, no claim.

## 1. Purpose

This protocol defines a reproducible procedure for an external human reviewer to verify a serialized Worldshepherd independent-review evidence bundle without requiring access to Worldshepherd runtime state, registries, signing keys, network services, or execution adapters.

A successful verification establishes only that the supplied evidence bundle passed the local evidence-reproduction checks implemented at the pinned software revision. It does **not** authenticate a live monitor, authorize an action, approve an action, create FASA readiness, promote a model or capability, execute a side effect, establish immutable/WORM retention, prove external anchoring, or constitute third-party certification.

The reviewing person or organization remains independent of the evaluated AI system. An AI system under evaluation must never be the sole judge of whether that system is safe.

## 2. Mandatory revision pin

The reviewer MUST identify the exact immutable Git commit being evaluated. A branch name, tag name, release label, screenshot, or verbal description is insufficient as the sole software identity.

Record:

- repository: `Bdavis1390/Sara_pro`
- commit SHA: `<REVIEWED_COMMIT_SHA>`
- reviewer bundle SHA-256: `<BUNDLE_FILE_SHA256>`
- bundle-declared `bundle_digest_sha256`: `<BUNDLE_DECLARED_DIGEST>`
- review date/time with timezone
- reviewer name and organization, if applicable

The internally tested CLI baseline for this protocol is `ce0076c8063e4e692f5041e5389ac9d75ea8b6cb`. Review of any later commit requires the reviewer to record that later SHA and should use CI/test evidence corresponding to that exact SHA rather than assuming equivalence with this baseline.

## 3. Evidence inventory

The serialized `WS-INDEPENDENT-REVIEW-EXPORT-BUNDLE-V1` is expected to carry the evidence needed for local reproduction, including the independent review package, independent evaluator report, independent checkpoint corroboration, FASA admission evidence, OVERWATCH attestation and provenance receipt, the signed local ECHO checkpoint bundle, the expected checkpoint public-key fingerprint, and the bundle digest.

The checkpoint material is verification material. A reviewer does not require, and MUST NOT be given merely for this procedure, an ECHO private signing key.

For chain-of-custody purposes, preserve the originally received bundle unchanged. Perform experiments or deliberate corruption only on copies.

## 4. Review environment

Use a clean environment containing the repository at the exact recorded commit and its pinned dependencies. The evidence-verification step is intended to be run offline.

Recommended preparation from the repository root:

```bash
git checkout --detach <REVIEWED_COMMIT_SHA>
cd deployments/sara_verified_local_v1
python -m pip install -e .
```

Before verification, disable unnecessary network connectivity or run in an isolated environment if practical. The reviewer CLI itself requires no network access, registry access, signer, authorization service, readiness service, or execution service.

## 5. Preserve and hash the received bundle

Hash the original file before running the verifier:

```bash
sha256sum review-bundle.json
```

Record the resulting file digest in the review record. Do not confuse this whole-file digest with the bundle's internal canonical `bundle_digest_sha256`; both are useful and serve different evidence purposes.

## 6. Run the offline verifier

From `deployments/sara_verified_local_v1` after installing the pinned package, run:

```bash
python -m worldshepherd_sara.independent_review_cli review-bundle.json > review-result.json
echo $?
```

The CLI emits one deterministic JSON result to stdout.

Exit semantics are:

| Exit | Meaning |
|---:|---|
| `0` | The serialized bundle produced `status=PASS` and `code=VERIFIED`. |
| `1` | Parsing, size, UTF-8, JSON, schema, or evidence reproduction failed. |
| `2` | The bundle could not be read from the supplied path. |

A zero exit is necessary for successful reproduction but is not an authorization or certification signal.

## 7. Required result checks

For a reproduced result, the reviewer MUST confirm all of the following in `review-result.json`:

- `status` is `PASS`.
- `code` is `VERIFIED`.
- `verification_scope` is `LOCAL_EVIDENCE_REPRODUCTION_ONLY`.
- `monitor_verification_status` remains `UNVERIFIED` unless monitor identity is established by a separate independent mechanism outside this result.
- `approval_status` is `NOT_APPROVED_BY_THIS_RESULT`.
- `authorization_effect` is `NONE`.
- `readiness_effect` is `NONE`.
- `execution_effect_applied` is `false`.
- the returned `bundle_digest_sha256` matches the verified bundle's declared digest.

Any contrary authority/readiness/execution field is a review failure, not a stronger PASS.

## 8. What the verifier reproduces

The verifier is intended to reconstruct and compare the evidence path rather than trust summary objects at face value. The review should therefore treat PASS as evidence that, for the supplied bundle and pinned code revision, the following local checks reproduced consistently:

1. strict serialized-input parsing and schema validation;
2. FASA admission-evidence integrity;
3. independent evaluator reconstruction and binding;
4. deterministic OVERWATCH decision/provenance relationship represented by the included evidence;
5. signed local ECHO checkpoint verification against the supplied expected public-key fingerprint;
6. checkpoint corroboration reconstruction;
7. cross-bound independent review-package reconstruction and subject/evidence binding; and
8. bundle-level digest verification.

This does not prove that the real-world source producing any input was honest, uncompromised, independently operated, continuously available, or physically isolated. Those are separate assurance questions.

## 9. Subject-binding inspection

In addition to the machine PASS, the human reviewer SHOULD inspect that the evidence consistently refers to the intended review subject, including where applicable:

- model ID;
- model version;
- action ID;
- capability level;
- policy ID and evaluation ID;
- OVERWATCH monitor identity/reference;
- observation/evidence identifiers;
- OVERWATCH decision digest;
- ECHO/checkpoint digest; and
- checkpoint public-key fingerprint.

A self-consistent but substituted model, model version, action, monitor, observation, or digest must not be accepted as equivalent to the intended subject.

## 10. Optional fail-closed challenge

A reviewer may strengthen confidence in the reproduction procedure by making a disposable copy and altering one bounded field at a time, such as the action ID, model ID/version, decision digest, checkpoint digest, signature material, or expected checkpoint fingerprint.

Expected result: verification fails closed. Preserve the original bundle unchanged and clearly label challenge copies as intentionally corrupted test artifacts.

A successful adversarial challenge demonstrates behavior of the verifier against that mutation; it does not independently prove the underlying system safe.

## 11. Failure handling

Any nonzero exit, `status=FAIL`, malformed output, digest mismatch, subject mismatch, unverifiable checkpoint, unexpected schema drift, or inability to reproduce the environment is a failed or inconclusive review. Do not reinterpret failure as approval and do not bypass the verifier to obtain a favorable result.

Preserve at minimum:

- the original bundle;
- whole-file SHA-256;
- pinned repository commit SHA;
- `review-result.json`;
- process exit code;
- Python/package environment information;
- reviewer date/time and identity; and
- discrepancies, exceptions, or unexplained observations.

If a corrected bundle is later supplied, retain the failed bundle and result as separate evidence and review the corrected bundle as a new artifact.

## 12. Independent claims boundary

A PASS supports only the narrow claim:

> At the recorded software revision, the supplied Worldshepherd review bundle reproduced the implemented local admission-integrity, evaluator-binding, deterministic OVERWATCH/checkpoint corroboration, cross-binding, and bundle-integrity checks.

A PASS does **not** by itself support any of the following claims:

- that Worldshepherd prevents catastrophic AI outcomes;
- that the evaluated AI or model is generally safe;
- that a live OVERWATCH monitor is authenticated or uncompromised;
- that evidence storage is immutable/WORM or externally anchored;
- that the reviewer bundle grants human approval or PRIME authorization;
- that FASA readiness has been granted;
- that any action was or may be executed;
- that containment has been executed or independently demonstrated in a live consequential environment;
- that a regulator, standards body, laboratory, customer, or independent third party has certified the system; or
- that internal CI is a substitute for independent external evaluation.

## 13. Reviewer record / sign-off template

```text
WS-FASA EXTERNAL REVIEW RECORD

Reviewer:
Organization:
Review date/time + timezone:
Repository: Bdavis1390/Sara_pro
Reviewed commit SHA:
Bundle filename:
Whole-file SHA-256:
Bundle-declared digest:
Verifier command:
Verifier exit code:
Verifier status/code:

Subject checked:
  Model ID:
  Model version:
  Action ID:
  Capability level:
  Policy/evaluation IDs:

Checkpoint checked:
  Expected public-key fingerprint:
  Checkpoint/signature verification reproduced: YES / NO / INCONCLUSIVE

Optional fail-closed challenge performed: YES / NO
Challenge description/result:

Exceptions or discrepancies:

Conclusion (choose one):
  REPRODUCED
  NOT REPRODUCED
  INCONCLUSIVE

Authority statement:
  This review record does not authorize or approve an action, create FASA
  readiness, promote a model/capability, or execute a side effect.

Reviewer signature / attestation:
```

## 14. Promotion rule

External reproduction may improve the evidence class only when the reviewer is genuinely independent, the exact software and bundle identities are recorded, the procedure is reproducible, exceptions are disclosed, and the resulting record is retained with provenance.

Independent reproduction is evidence. It is not unilateral authority. Human authority and the existing PRIME/FASA promotion gates remain separate.

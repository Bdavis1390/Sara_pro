# Worldshepherd Protected Evaluation Artifact Protocol v1

## Purpose

Protected evaluation content must remain outside the public repository. The repository may contain only control metadata, cryptographic hashes, evaluator references, schemas, and code required to validate a protected run.

## Required separation

The public manifest records the suite identifier/version, target lane, task count, task-set SHA-256, grader SHA-256, control assertions, and an evaluator-controlled artifact reference. It must not contain raw tasks, answer keys, hidden grader targets, or solutions.

The protected task artifact is supplied only at evaluation time by the evaluator-controlled environment. `evals/protected_artifact_loader.py` verifies the exact artifact bytes against the manifest SHA-256 before parsing any task. A mismatch, count disagreement, duplicate task ID, malformed tool allowlist, invalid approval subset, or invalid step budget fails closed.

## Run sequence

1. Freeze the protected task set and grader before the candidate run.
2. Compute exact SHA-256 hashes for both artifacts.
3. Publish only the manifest metadata and hashes to the repository.
4. Keep the raw task and grader artifacts under evaluator-controlled access outside the repository.
5. At run time, validate the public manifest and then load the external task artifact through the hash-verifying loader.
6. Execute the existing bounded protected-suite runner under explicit tool allowlists and step budgets.
7. Preserve every run, including failures, for reliability/integrity accounting.
8. Use an independent final-state evaluator; controller self-reported success is not sufficient.
9. Feed only independently adjudicated results into reliability, experience, and learning-gate calculations.

## Claims boundary

A valid manifest and hash-matched protected artifact establish evaluation integrity controls, not AGI capability. Promotion still requires the configured capability thresholds, adequate sample sizes, valid long-horizon evidence, reliability/integrity thresholds, and genuine independent replication.

## Security boundary

No secret, credential, raw holdout content, answer key, hidden grader target, or private evaluator endpoint belongs in the public repository. Credentials remain environment-injected at execution time, and evaluator-controlled artifacts should be mounted or otherwise supplied by the evaluation environment rather than committed.

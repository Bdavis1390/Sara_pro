# Worldshepherd Evaluator Handoff Manifest v1

Status: **candidate implementation supporting issue #155**.

## Purpose

Give an independent evaluator enough stable, machine-readable information to decide whether it can reproduce a bounded Worldshepherd software evaluation without reconstructing the project from email.

The manifest addresses recurring evaluator diligence questions:

- How large is the delivered code/package surface?
- What exact release/commit is being evaluated?
- What Python/software dependencies are required?
- What hardware assumptions are being made?
- How will the evaluator receive/install/run it?
- Which synthetic fixtures or input data are supplied?
- Where are expected-result semantics defined?
- What exact behavior is in scope?
- What completion window is being requested?
- Is there an existing government/customer contract or another relationship that could create a conflict-of-interest concern?
- Which claims remain explicitly outside the handoff?

## Evidence-first behavior

`evaluator_handoff.py` does not guess missing diligence facts.

It computes the package inventory directly from the selected tree and reads Python/dependency requirements from the selected package's `pyproject.toml`. Other evaluator-specific fields are explicit inputs.

A generated manifest is bound to:

- repository identity;
- release ref;
- exact 40-character commit SHA;
- resolved package root;
- file/byte/text-line inventory;
- declared project requirements;
- hardware requirements supplied for the engagement;
- delivery method;
- install/run instructions;
- fixture references;
- expected-results reference;
- claims-boundary references;
- evaluation scope;
- evaluation window;
- conflict/contract disclosure state;
- non-claims.

The complete manifest receives a canonical SHA-256 digest.

## Code/package inventory

The inventory reports:

- total file count;
- total bytes;
- UTF-8 text file count;
- UTF-8 text line count;
- file counts by suffix;
- excluded generated/dependency directory names.

Default exclusions include `.git`, `.venv`, `__pycache__`, build/dist directories, `node_modules`, and pytest cache material.

The inventory is **not** a runtime performance metric. It does not measure memory consumption, execution latency, throughput, CPU/GPU demand, deployment scale, or operational effectiveness.

## Project requirements

The generator reads the selected package's `[project]` metadata from `pyproject.toml`, including:

- project name/version;
- `requires-python`;
- runtime dependencies;
- test dependencies.

For the current canonical SARA package, the authoritative requirement remains whatever is present in the exact selected commit. The generator does not hard-code a newer requirement onto an older release.

## Hardware requirements

At least one `--hardware-requirement` is mandatory.

This is deliberate: a handoff must not silently imply that arbitrary hardware is adequate, nor invent a specialized-hardware requirement that has not been established. The engagement owner supplies a bounded statement suitable to the exact evaluation.

Example for a software-only synthetic evaluation, if independently confirmed for the selected release:

```text
Evaluator-selected general-purpose host sufficient to install and execute the declared Python/test environment; no physical sensor, accelerator, or specialized mission hardware is part of this evaluation scope.
```

Do not copy that example into an external package unless it is correct for the selected release and evaluation.

## Fixtures and expected results

At least one fixture reference and one expected-results reference are required.

The expected-results reference should define assertions and adjudication semantics, not merely state that the software is expected to pass.

The evaluator should retain failed, malformed, tampered, denied, replayed, recovery, and discrepancy cases relevant to the frozen protocol.

## Contract / conflict disclosure

The manifest uses one explicit state:

- `NO_CURRENT_CONTRACT_CLAIMED`
- `CONTRACT_EXISTS_DISCLOSED`
- `DISCLOSURE_RESTRICTED`
- `UNKNOWN_REQUIRES_REVIEW`

This field exists for evaluator conflict screening. It does not establish contractual status by itself.

Use `NO_CURRENT_CONTRACT_CLAIMED` only when current documentary/project records support that statement. Use `UNKNOWN_REQUIRES_REVIEW` rather than guessing when the record is incomplete. A restricted disclosure should state that restriction without inventing the hidden relationship.

The evaluator independently decides whether any disclosed relationship impairs independence or creates an organizational conflict.

## Example CLI shape

From the selected canonical package root:

```bash
python -m worldshepherd_sara.evaluator_handoff \
  --artifact-id WS-SARA-EVAL-CANDIDATE \
  --release-ref refs/heads/review/example \
  --release-commit "$(git rev-parse HEAD)" \
  --hardware-requirement "<bounded evaluator hardware statement>" \
  --delivery-method "Git checkout pinned to the declared commit" \
  --fixture fixtures/<frozen-fixture>.json \
  --expected-results-ref tests/<expected-results-spec>.md \
  --evaluation-scope "<bounded software behavior only>" \
  --evaluation-window "<requested window or TO_BE_AGREED>" \
  --contract-status UNKNOWN_REQUIRES_REVIEW \
  --output build/evaluator-handoff.json
```

The example intentionally contains placeholders. A generated external package should contain resolved facts, not placeholders represented as readiness evidence.

## Relationship to frozen release work

This manifest is a **handoff component**, not the frozen evaluator release itself.

Issue #155 remains authoritative for:

- selecting the exact frozen release;
- dependency/environment lock;
- clean-environment install/run validation;
- challenge/fixture freeze;
- adversarial cases;
- discrepancy retention;
- evaluator-controlled inputs;
- external custody and attestation.

A generated handoff manifest can make those facts inspectable once they exist; it cannot close them by documentation alone.

## Non-claims

A valid manifest does not establish:

- independent reproduction;
- evaluator acceptance;
- government/customer acceptance;
- CMMC/NIST/DFARS compliance;
- classified/CUI authorization;
- physical capability;
- operational effectiveness;
- customer or contract status beyond authoritative records;
- absence of evaluator conflict unless the evaluator independently determines it.

The purpose is simple: make the evaluation package precise enough that an external technical organization can say **yes, no, or here is exactly what is still missing**.

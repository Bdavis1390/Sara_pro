# in-toto Witness #789 — non-zero command outcomes and evidence generation

Date: 2026-09-12

Claims state: **SOURCE-REVIEWED DESIGN CANDIDATE / NOT UPSTREAM ACCEPTED**

Upstream issue: `in-toto/witness#789`

## Executive finding

Witness issue #789 asks for `witness run` to accept selected non-zero command exit codes so security/compliance tools can still produce signed evidence when a non-zero code means "findings present" rather than "the tool failed to execute."

Source review shows the underlying problem is slightly deeper than a CLI flag.

The command-run attestor in `in-toto/go-witness` already captures an `*exec.ExitError` and stores its `ExitCode` in the command-run attestation object. It then returns that same execution error. `in-toto/witness` calls `witness.RunWithExports(...)`; any returned error is propagated before the CLI marshals/writes the signed collection.

Therefore the data needed for truthful evidence already exists, but the execution outcome is currently coupled to the attestation pipeline's success/failure control path.

## Required semantic separation

Worldshepherd recommends treating three states independently:

1. **Command outcome** — the wrapped process exited with code N or a signal.
2. **Evidence-generation outcome** — Witness successfully observed, assembled, and signed the attestation/collection.
3. **Wrapper/CI outcome** — the `witness` process returns a code to its caller.

Conflating these states causes false negatives in provenance: a scanner can run correctly, find violations, return its documented findings code, and yet Witness can refuse to emit the signed evidence describing that result.

The attestation should never rewrite the observed command exit code to make a CI job appear successful.

## Source evidence

Current `go-witness/attestation/commandrun/commandrun.go` behavior is approximately:

- start/wait for the child command;
- if the wait error is `*exec.ExitError`, store `exitErr.ExitCode()` in `CommandRun.ExitCode`;
- capture stdout/stderr;
- return the execution error.

Current `witness/cmd/run.go` behavior is approximately:

- construct the built-in command-run attestor;
- call `witness.RunWithExports(...)`;
- if that returns an error, return immediately;
- otherwise marshal/write/store signed outputs.

This means a non-zero child exit can be accurately observed but still suppress the final collection.

## Preferred contract

A bounded design should make the user's intent explicit without confusing provenance with process success.

### `--accept-exit-codes`

Interpret this flag as **which observed command exit codes are permitted to complete the attestation pipeline**.

Examples:

- default: `0`
- `--accept-exit-codes 0,2,100,101`
- optionally `--accept-exit-codes '*'` if maintainers want an all-outcomes evidence mode.

For an accepted non-zero code:

- the command-run attestation records the real non-zero exit code;
- downstream/product/post-product attestors are allowed to complete;
- the collection may be signed and stored;
- policy can later evaluate that recorded exit code.

For a non-accepted code, existing fail-fast behavior can remain unless maintainers choose a broader "always attest" policy.

## CLI return-code policy must be separate

Issue discussion also asks whether `witness run` should pass through the child exit code.

That decision should not be overloaded into `--accept-exit-codes` without explicit documentation.

Two coherent contracts exist:

### Contract A — accepted means wrapper success

If the child exits with an allowed code, Witness emits evidence and returns 0. This is convenient for scanners where codes 2/100/101 are domain success states.

### Contract B — always preserve child status

Witness emits evidence for allowed codes but returns the child's actual exit code. This maximizes transparency but means CI callers still need to interpret domain-specific codes.

Worldshepherd preference: **separate evidence acceptance from wrapper status**. If maintainers want both behaviors, use a distinct return-code/pass-through option rather than silently rewriting status.

## Implementation boundary

Because the execution error originates in `go-witness`, a robust solution may require a library-level distinction between:

- child-process non-zero outcome; and
- attestor operational failure.

Possible bounded approaches:

1. Add accepted-exit-code configuration to the command-run attestor and return `nil` for configured codes while retaining the observed `ExitCode` field.
2. Return a typed command-outcome error that the higher-level runner can classify without treating it as an attestation infrastructure failure.
3. Refactor the runner result to carry both command outcome and attestation error independently.

Option 1 is smallest; option 3 is architecturally cleanest but wider. The upstream maintainers should choose the compatibility surface.

## Regression matrix

At minimum test:

| Child result | Allowed set | Signed evidence | Recorded exit code | Attestation-system error |
| --- | --- | --- | ---: | --- |
| 0 | default `{0}` | yes | 0 | no |
| 2 | default `{0}` | no/current compatibility | 2 | command outcome only |
| 2 | `{0,2}` | yes | 2 | no |
| 100 | `{0,100,101}` | yes | 100 | no |
| nonexistent executable | any | no | n/a | yes |
| signing failure after child exits | any | no/partial per contract | actual child code | yes |
| signal termination | explicit policy required | preserve signal/derived code | truthful | not silently converted |

Also verify stdout/stderr, materials/products, and signed collection contents remain available for accepted non-zero outcomes.

## Security/provenance invariant

> Allowing evidence generation for a non-zero command outcome must never convert the attested exit code itself to zero or hide the distinction between command findings and Witness infrastructure failure.

This is the key Worldshepherd value-add: the system should preserve inconvenient evidence rather than suppressing it because the wrapped tool reported a finding.

## Contribution decision

**Classification: P1 / CROSS-REPO DESIGN + REGRESSION CANDIDATE.**

Internal screening score: **91/100**.

No open implementation PR matching #789 was found. A maintainer has engaged in the issue discussion and is considering return-code semantics, so Worldshepherd should contribute a precise contract/test matrix rather than unilaterally choosing CLI behavior.

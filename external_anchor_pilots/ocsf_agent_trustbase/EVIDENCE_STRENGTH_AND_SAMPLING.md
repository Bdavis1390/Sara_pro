# Evidence strength and sampling-state treatment

**Status:** provisional / non-normative implementation guidance for `ocsf/ocsf-schema#1724`.

This document records the current pilot interpretation of two issue-thread areas that are useful to make executable before final OCSF field names exist: evidence strength and declared-versus-observed sampling/runtime configuration.

## 1. Evidence strength

The #1724 discussion proposes a descriptive `verification_id` vocabulary:

- `0` — Unknown
- `1` — Locally computed
- `2` — Provider asserted
- `3` — Third-party attested
- `4` — Not observable
- `99` — Other

The important design property is that this vocabulary describes **what kind of evidence the producer holds**. It does not decide whether that evidence is sufficient for a relying party's control.

The pilot therefore checks only a few internally testable consistency rules:

1. A locally computed claim (`1`) must carry a content fingerprint.
2. A structurally not-observable claim (`4`) must not simultaneously claim a locally computed content fingerprint.
3. Hosted or remote models represented as provider asserted (`2`) or not observable (`4`) remain identifiable by an `ai_provider` / `name` / `version` tuple in the provisional fixture vocabulary.
4. The verifier accepts `0`, `1`, `2`, `3`, `4`, and `99` only.

No policy ranking is applied. In particular, the pilot does **not** treat `1` or `3` as universally sufficient, and does not treat `2` or `4` as universally insufficient.

## 2. Declared versus observed sampling/runtime state

The #1724 issue discussion identifies sampling and runtime settings as part of the configuration whose declared and executed/observed forms can diverge. Examples include:

- `temperature`, `top_p`, `top_k`, and related decoding controls;
- `max_output_tokens` and stop configuration;
- constraints, grammars, or other distribution-modifying layers;
- runtime binding such as engine or sampler identity where observable.

The pilot does not validate preferred values or fill implementation defaults. Instead `analyze_sampling_delta.py` computes a structural diff between two objects while preserving three distinct conditions:

- changed value;
- declared only / missing from observation;
- observed only / absent from declaration.

That distinction matters because a field that is structurally unavailable is not equivalent to an empty/default value.

## 3. Producer as witness, consumer as judge

A configuration delta is evidence, not a verdict. A gateway rewriting `max_output_tokens` from 4096 to 1024, a caller overriding temperature, or a runtime-added grammar are all surfaced as differences. Whether that difference is allowed, anomalous, malicious, or operationally expected is left to downstream policy and correlation with activity/findings.

This keeps the pilot aligned with the broader #1724 principle that the producer should emit declared and observed state rather than compute a security conclusion about itself.

## 4. Current executable coverage

`verify_evidence_strength.py` + `evidence_strength_fixtures.json` currently exercise six expectations:

- local adapter digest — pass;
- provider-asserted hosted-model tuple — pass;
- not-observable hosted-model tuple — pass;
- locally computed claim without a digest — fail;
- not-observable claim that simultaneously asserts a local digest — fail;
- unsupported verification ID — fail.

`analyze_sampling_delta.py` + `sampling_delta_fixtures.json` currently exercise five reporting scenarios:

- stable sampling configuration;
- gateway token-cap rewrite;
- caller temperature override;
- runtime-only constraint appearance;
- runtime binding represented as structurally unavailable.

These are harness semantics only. Final OCSF object names, requirements, enum placement, and class relationships remain upstream decisions.

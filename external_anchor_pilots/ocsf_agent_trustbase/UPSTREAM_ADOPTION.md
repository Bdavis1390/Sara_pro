# Upstream Adoption Plan — OCSF Agent Trust-Base Conformance

**Status:** implementation support for discussion in `ocsf/ocsf-schema#1724`; not an OCSF specification.

## Why this package exists

The upstream issue is already doing the hard schema-design work. This package focuses on the part that can reduce maintainer burden after the class shape stabilizes: reproducible semantic test vectors and structural checks.

The pilot deliberately reuses OCSF concepts already present on `main` rather than inventing parallel vocabulary:

- `ai_agent.uid`
- `ai_agent.instance_uid`
- `ai_agent.version`
- `ai_agent.charter`
- `ai_agent.ai_model`
- `record_integrity.attestation_list`
- `attestation.chain_uid`
- `attestation.prev_event`
- `attestation.fingerprint`
- `attestation.signatures`

## Current contribution boundary

What is ready now:

1. Six semantic pass/fail vectors covering session baseline, mid-session dependency change, adapter digest divergence, missing closure, broken chain linkage, and unsafe credential material.
2. A standalone verifier for the provisional invariants discussed in issue #1724.
3. A separate checker that confirms an OCSF checkout still exposes the existing semantic anchors used by this pilot.

What is **not** ready to claim:

- final event-class name or `uid`
- final proposed class field names
- acceptance of admission/closure activity mapping
- canonical-serialization compliance
- signature-verification compliance
- OCSF maintainer endorsement

## Upstream translation sequence

Once the class PR for #1724 is available:

1. Replace provisional fixture keys with the accepted class/object attributes.
2. Preserve the semantic distinction between declared configuration and executed/observed state.
3. Preserve chain semantics already provided by `record_integrity`; do not create a second chaining model.
4. Confirm genesis behavior and `prev_event` linkage against the accepted wording.
5. Translate the admission/closure vectors into the accepted activity mapping, if maintainers retain that design.
6. Run the OCSF schema compiler against the full fork.
7. Run OCSF compatibility validation where classification IDs or existing attributes are affected.
8. Run OCSF server validation to ensure the schema can be consumed by `ocsf-server`.
9. Add an `Unreleased` changelog entry and DCO-sign all commits before opening the upstream PR.
10. Keep the PR focused on one coherent class/test contribution and respond to CI/reviewer findings until clean.

## Suggested maintainer handoff

A concise offer to OCSF maintainers:

> I can take the conformance-test/fixture slice for the agent trust-base inventory proposal. I have a provisional harness with six semantic vectors covering per-emission chain continuity, declared-vs-observed state, admission/closure pairing, content fingerprints, remote-model identity handling, and credential hygiene. It is intentionally non-normative today. Once the class fields stabilize, I can translate the fixtures to the accepted OCSF shape and run them alongside the existing compiler/server validation path.

## Commands

Run the current semantic fixtures:

```bash
python external_anchor_pilots/ocsf_agent_trustbase/verify_trustbase.py \
  external_anchor_pilots/ocsf_agent_trustbase/fixtures.json
```

Check an OCSF checkout for the current anchors this pilot depends on:

```bash
python external_anchor_pilots/ocsf_agent_trustbase/verify_upstream_shape.py \
  /path/to/ocsf-schema
```

For a true upstream fork, also follow OCSF's own verification commands and CI requirements from its current `CONTRIBUTING.md` and GitHub workflows.

## Success criteria

This effort moves from **CONTACT READY** to **UTILIZED BY OCSF** only when at least one of the following occurs:

- an OCSF maintainer asks us to adapt or contribute the fixtures;
- an OCSF working group uses the harness or vectors in discussion/review;
- the tests or equivalent checks are incorporated into an OCSF PR, CI path, example package, or documentation;
- an OCSF maintainer explicitly requests continued implementation support.

Until then, the artifact remains a useful external contribution candidate, not evidence of an OCSF partnership or adoption.

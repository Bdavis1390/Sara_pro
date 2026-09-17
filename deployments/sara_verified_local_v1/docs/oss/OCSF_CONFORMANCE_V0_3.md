# Worldshepherd OCSF conformance evidence v0.3

Status: **PINNED UPSTREAM OCSF TOOLKIT EVENT-VALIDATION PASS**

This evidence record covers seven derived OCSF event projections generated from the frozen Worldshepherd interoperability corpus v0.1. It does not modify the frozen source corpus and does not upgrade any partner, production, certification, or government-acceptance claim.

## Validation basis

- Worldshepherd source branch: `interop/ocsf-gemara-fixtures-v1`
- Source corpus: `fixtures/standards_interop/corpus_v0_1.json`
- Frozen corpus digest: `sha256:702ed3ed00edd77b12a04061bcadba5c62e894787d88db3bcb0b1a6e7b736ac7`
- OCSF schema repository: `ocsf/ocsf-schema`
- OCSF schema commit: `c1ab05a382ffc97250997ffe010f3f715a097c2a`
- OCSF schema version at that commit: `1.10.0-dev`
- OCSF schema compiler repository: `ocsf/ocsf-schema-compiler`
- OCSF schema compiler commit: `865887a9ee88580c471062f93da115e7599fa31d`
- OCSF Toolkit repository: `ocsf/ocsf-toolkit`
- OCSF Toolkit commit: `a99619fcd148791a6a9fe5f82c1e0d839f658591`
- GitHub Actions workflow: `Worldshepherd OCSF Conformance v0.3`
- Passing workflow run: `34797074242`

## Scope

Seven frozen Worldshepherd cases are transformed into seven derived synthetic OCSF event instances. The derivation is separate from the source fixture and does not change the frozen source evidence digest.

The four remote-tool cases map to OCSF `API Activity` and retain the required API, source-endpoint, actor, authorization, metadata, classification, status, and timestamp material.

The two local-process cases and the one explicitly hostless file case intentionally map to OCSF `Base Event` because the frozen source fixtures do not contain a truthful device identity. The pinned OCSF schema requires `device` for the more specific system activity classes. Worldshepherd therefore does not fabricate a device merely to satisfy a validator. The source process/file semantics and Worldshepherd correlation identifiers remain preserved under `unmapped.worldshepherd`.

## Truth-preserving fallback discovered during validation

The first validation attempt demonstrated that `File System Activity` required a `device` attribute for the hostless file fixture. A subsequent attempt showed the same requirement for `Process Activity` when the source process cases lacked device identity.

The corrective action was not to invent an endpoint. Instead, those source cases were projected as the concrete generic OCSF `Base Event`, whose upstream definition is intended for events that are not otherwise representable by a more specific class. Regression tests now enforce the absence of fabricated `device`, `actor`, `file`, or `process` top-level fields in those generic projections while requiring the original semantics to remain recoverable from `unmapped.worldshepherd`.

## Validation result

The passing workflow successfully completed all of the following gates:

1. installed the Worldshepherd test package;
2. ran the OCSF projection, frozen-corpus, and correlation-grain regression tests;
3. deterministically generated all seven derived event instances;
4. checked out the exact upstream OCSF schema revision;
5. checked out and built the exact upstream OCSF schema compiler revision;
6. compiled the pinned OCSF schema, including its platform extensions;
7. checked out and built the exact upstream OCSF Toolkit revision with Go 1.25;
8. validated each of the seven derived event instances using the official toolkit with `--validate --fail-on-validation-errors`.

The official OCSF Toolkit event-validation step completed successfully for all seven events.

## Correlation and provenance boundary

Worldshepherd keeps event, session, turn, invocation, policy-decision, and evidence-digest identities distinct. Native fields that do not have a settled OCSF location are kept under `unmapped.worldshepherd` rather than injected into the standardized top-level namespace.

The source fixture digest remains the provenance anchor for the frozen Worldshepherd evidence. The derived OCSF event has its own canonical digest recorded by the projection manifest; a standards projection therefore does not silently replace the source evidence identity.

## Claims boundary

This result establishes **event-instance conformance of these seven derived synthetic events against the pinned compiled OCSF schema using the pinned official OCSF Toolkit**.

It does **not** establish:

- OCSF certification or endorsement;
- OCSF maintainer acceptance of Worldshepherd mappings;
- partner validation;
- production interoperability;
- government acceptance;
- operational security accreditation;
- conformance for events outside the frozen synthetic fixture scope;
- acceptance of proposal-stage AI-agent/tool fields not present in the pinned upstream schema.

Any future change to the source corpus, projection logic, OCSF schema commit, compiler commit, toolkit commit, or validation policy requires a new evidence run. The frozen source corpus remains versioned rather than silently mutated.

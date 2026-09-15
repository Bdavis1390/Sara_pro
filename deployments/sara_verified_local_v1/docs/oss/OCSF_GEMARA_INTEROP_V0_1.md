# Worldshepherd OCSF/Gemara interoperability fixture corpus v0.1

Status: **INTERNAL IMPLEMENTATION / EXTERNAL VALIDATION NOT RUN**

This corpus exercises Worldshepherd correlation, authorization, and evidence-chain invariants while tracking two upstream standards efforts:

- OCSF 1.10.0-dev and the still-open AI-tool work in OCSF PR #1729 / related agent-harness mapping discussion.
- Gemara 1.1 concepts for EvaluationLog, EnforcementLog, AuditLog, and EvidenceMapping.

The strings `OCSF-1.10.0-dev-PROPOSAL-COMPATIBLE` and `GEMARA-1.1-COMPATIBLE` are **internal mapping targets only**. They do not assert schema-validator success, standards certification, upstream acceptance, partner validation, or production interoperability. The generated records intentionally carry `external_validation_status: NOT_RUN` until the relevant upstream validators are executed against a frozen fixture set.

## Correlation contract

The fixture model preserves five distinct identity grains plus an evidence digest:

- `ws_event_uid`: one observed event.
- `ws_session_uid`: one agent/conversation/run instance.
- `ws_turn_uid`: one initiating conversational turn.
- `ws_invocation_uid`: one capability invocation.
- `ws_policy_decision_uid`: one authorization decision.
- `ws_evidence_digest`: SHA-256 over canonical JSON of the originating event.

The identifiers are not interchangeable. The model rejects a fixture that collapses these grains.

## OCSF mapping policy

Operational activity remains in the applicable OCSF-style event class. Worldshepherd does not create a parallel generic "AI action" class. Remote tools use an API Activity-shaped record; local commands use a Process Activity-shaped record; file operations use a File System Activity-shaped record.

Because OCSF `ai_tool` is still proposal-stage upstream, the corpus keeps proposed capability metadata under `worldshepherd.draft_ai_tool` instead of claiming that a released OCSF schema currently accepts that object.

Hostless producers remain hostless. The corpus does not fabricate a `device.uid` merely to satisfy a schema constraint. A genuine device identity may be added only when the producer possesses host-stable evidence for it.

Human approval and policy approval are also kept distinct: `Approved` is used for a human approval fixture and `Allowed` for a policy-authorized fixture, with the Worldshepherd policy-decision identifier retained separately from the action/event identifier.

## Gemara mapping policy

The corpus emits minimal Gemara-oriented evaluation, enforcement, and audit projections that all bind back to the originating operational event by the same SHA-256 digest. They are mapping fixtures, not claims that the minimal documents independently satisfy every required field in the upstream CUE schemas.

The next conformance gate is to transform these projections into full upstream-schema instances and run the actual Gemara CUE validation. Until that happens, the state remains `NOT_RUN` externally.

## Negative cases

The v0.1 corpus covers policy approval, human approval, denial, local process execution, file activity from a hostless producer, a declared-read-only capability observed performing a write, and an interrupted action. Tests require denial to record no action execution, interruption to remain explicit non-success, hostless events to contain no fabricated device, read-only/write mismatches to be surfaced for review, and any post-generation event tampering to break the evidence digest chain.

## Upstream contribution boundary

No upstream issue or pull request should be opened solely because these internal tests pass. Before upstreaming:

1. Freeze and externally validate the fixture corpus against the relevant upstream schema/tooling.
2. For Zeek #5076, prove the record-in-vector representation through Zeek's logging/threading serialization boundary and regress all existing writer behavior.
3. Contribute test vectors or narrowly scoped implementation evidence to existing OCSF/Gemara discussions rather than opening duplicate schema proposals.

Worldshepherd retains its own correlation identifiers where an upstream standard does not yet have a settled field. Missing upstream fields are not silently guessed or overloaded.

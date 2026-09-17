# WS-RESTRICTION-PROVENANCE G3 — POSITIVE CONTEXT SCHEMAS

Status: **IMPLEMENTED IN SOFTWARE ON BRANCH / PENDING INTERNAL VALIDATION**

## Objective

G3 closes the residual caller-controlled context channel left by G1. G1 already rejects common raw-content and secret-bearing metadata keys, but a negative denylist cannot prove that arbitrary caller-supplied strings are safe.

G3 changes the persistence contract from:

```text
bounded JSON + forbidden-key scan
```

to:

```text
bounded JSON + forbidden-key scan + exact source/processor profile + typed allowlist
```

A restriction may now persist contextual metadata or a summary only when the exact `(source_system, processor)` pair has a registered positive profile.

## Current registered profile

G3 registers one internal Worldshepherd profile:

```text
source_system = CHAT_ASSISTANT
processor     = POLICY_GATE
profile_id   = WS-RESTRICTION-CONTEXT-CHAT-ASSISTANT-V1
```

Allowed metadata fields are:

- `stage` — one of `pre_generation_policy_check`, `post_generation_policy_check`, or `connector_policy_check`;
- `claims_state` — one of the ten Worldshepherd claims-control states represented as uppercase underscore identifiers;
- `attempt` — integer `1..1000`, with booleans explicitly rejected.

The only allowed summary template is:

```text
Output was restricted; only bounded provenance is retained.
```

No external model/provider profile is claimed by G3. External provider profiles must be added only after their documented metadata contract is reviewed and translated into an explicit typed profile.

## Unknown integrations fail closed

An unregistered `(source_system, processor)` pair may still create core restriction provenance so Worldshepherd does not lose the fact that a restriction occurred. However, it may persist:

- no caller metadata;
- no caller summary.

G3 inserts the system-controlled profile marker:

```text
WS-RESTRICTION-CONTEXT-EMPTY-V1
```

This preserves the core identifiers and keyed fingerprints while preventing an unknown integration from using metadata or summary fields as a covert text channel.

## Profile binding and immutability

`context_profile` is system-managed. Callers cannot supply or override it.

The selected profile ID is inserted into the sanitized metadata before the restriction identity document is hashed. Therefore the stable `restriction_id` and SARA outbox event ID are bound to the context-validation policy that admitted the record.

Changing source/processor/profile semantics changes the evidence identity rather than silently reusing the same restriction ID.

The in-process profile registry and each profile's metadata-rule mapping are exposed as immutable mappings. Runtime code cannot add a new integration profile or widen an existing field allowlist through ordinary dictionary mutation after startup.

## Validation order

`capture_restriction()` applies controls in this order:

1. fingerprint-key validation;
2. restriction action and reason-code validation;
3. bounded source/processor and lineage identifiers;
4. safe-summary length and raw-equality checks;
5. timezone-aware timestamp validation;
6. recursive forbidden-key scan and bounded JSON normalization;
7. positive source/processor context profile validation;
8. system insertion of `context_profile`;
9. HMAC-SHA256 content fingerprints;
10. canonical evidence identity and restriction ID.

The positive profile therefore cannot bypass the existing denylist or bounded-JSON controls; it is an additional stricter layer.

## G3 acceptance tests

The adversarial suite verifies:

1. the registered internal profile accepts only its declared fields and fixed summary template;
2. the profile ID is inserted by the system and persisted in evidence;
3. the registry and per-profile field-rule mappings reject runtime mutation attempts;
4. unknown metadata fields fail closed;
5. unapproved `stage` and `claims_state` values fail closed;
6. booleans are not accepted as integers;
7. attempt values below `1` or above `1000` fail closed;
8. caller-supplied `context_profile` values are rejected;
9. arbitrary safe-summary text is rejected;
10. unregistered integrations accept only empty context;
11. context-policy failures propagate through `capture_restriction()` as provenance errors;
12. G2 observability tests continue proving that even approved summary/context values are omitted from admin projections;
13. the required build executes the G1 provenance, G2 observability, and G3 positive-schema suites together.

## Compatibility and migration boundary

G3 is a prospective capture-policy hardening within the existing `WS-RESTRICTION-PROVENANCE-V1` envelope. It does not rewrite historical records.

Previously persisted G1 records may contain denylist-sanitized metadata or caller-approved summaries that predate positive profile enforcement. G2 continues to omit those fields from administrator observability responses.

New captures after G3 must satisfy the positive profile policy. The wire structure is not otherwise changed, so existing readers remain compatible.

## Claims boundary

G3 does not establish that an external provider's metadata is safe. It provides the mechanism to register explicit schemas and includes only one reviewed internal Worldshepherd profile.

It does not provide secure erasure of transient Python strings, external policy-provider interoperability, production secret-management assurance, or adversarial proof against all covert channels. Those remain separate gates.

Until exact-head required CI, broader Verified Local validation, and protected merge complete, classify G3 as **IMPLEMENTED IN SOFTWARE / PENDING INTERNAL VALIDATION**.

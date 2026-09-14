# OpenTelemetry audit-event semantic proposal

Upstream target: `open-telemetry/semantic-conventions#2468`

Compatibility input: `open-telemetry/semantic-conventions#4102` — **DRAFT / NOT YET STANDARD**

Claims state: **SOURCE-REVIEWED SEMANTIC PROPOSAL / REQUIRES OPENTELEMETRY MAINTAINER DECISION**

## Current upstream posture

Issue #2468 remains open and unassigned. Its discussion contains an important design signal: a single broad audit namespace should not duplicate the semantics of access control, HTTP/RPC/messaging errors, configuration, backup/restore, or other domains. The useful direction is to keep any common audit layer small and map each category to focused domain conventions.

PR #4102 is a separate, still-draft compatibility input. It proposes two general rules that matter for audit telemetry:

1. attributes whose values are unbounded by nature can be explicitly annotated as such, but must not be required;
2. an attribute ending in `_ref` is a string reference to externalized content and must have a defined base attribute with the same name minus `_ref`.

Until #4102 is merged, those rules are **draft upstream behavior**, not an accepted semantic-convention contract.

## Goal

Define the smallest reusable audit-event envelope needed to correlate security-relevant events across access control, configuration changes, backup/restore, autonomous workflows, and other domain-specific events without replacing the domain semantic conventions that describe the underlying operation.

The core idea is:

> domain conventions describe **what happened**; a small audit envelope describes **why this event is security/audit relevant, who initiated it, and what the outcome was**.

This avoids creating a parallel audit namespace containing copies of HTTP, RPC, messaging, configuration, or application attributes.

## Proposed minimal attributes

Names below are a design proposal, not a claim of accepted OpenTelemetry naming.

```text
audit.event.id          string   Stable identifier for this audit record.
audit.category          enum     Broad audit classification.
audit.action            string   Bounded action identifier.
audit.outcome           enum     success | failure | unknown
audit.reason            string   Optional concise, sanitized, bounded reason/result summary.
audit.initiator.type    enum     user | service | workload | device | ai_agent | unknown
audit.initiator.id      string   Identifier for the initiating principal when appropriate.
audit.target.type       string   Optional target/resource type.
audit.target.id         string   Optional target/resource identifier.
audit.policy.id         string   Optional policy identifier involved in the decision.
audit.policy.decision   enum     allow | deny | escalate | audit_only | unknown
audit.approval.id       string   Optional human/workflow approval correlation identifier.
```

If #4102's reference-attribute convention is accepted upstream, a future optional companion may be considered:

```text
audit.reason_ref        string   External reference replacing an omitted/externally stored large reason value.
```

That candidate is valid only because `audit.reason` is also defined. Do **not** introduce unrelated names such as `audit.evidence_ref` unless an `audit.evidence` base attribute is first defined and there is real instrumentation/pipeline support for externalizing it.

## Category scope

Candidate categories inspired by IEC 62443-style audit needs are:

```text
access_control
request_error
control_system
backup_restore
configuration_change
audit_system
```

These are classification candidates, not a request to recreate each domain's schema under `audit.*`.

The upstream #2468 discussion supports a focused mapping approach:

- access-control details should reuse the relevant identity/authentication/authorization semantics;
- request errors should reuse HTTP, RPC, and messaging conventions;
- configuration changes should reuse configuration/application semantics where available;
- backup/restore should use application/domain semantics for what was backed up, destination, method, and result;
- the common audit layer should carry only cross-domain identity/classification/governance fields that truly recur.

## Reuse existing semantic conventions

The audit envelope should reuse existing attributes for the operation itself wherever available:

- identity/authentication attributes for authenticated users and services;
- HTTP/RPC/messaging attributes for request failures;
- device/resource attributes for hardware or edge components;
- `error.type` and related error conventions for failures;
- deployment/service/resource attributes for software components;
- workflow/job/task conventions if/when standardized.

Example: a denied HTTP configuration request should remain an HTTP event/span/log with ordinary HTTP and error attributes. The audit envelope only adds the security/audit classification, initiator/target correlation, policy decision, and audit event identity.

## Event vs. resource identity

`audit.event.id` should identify the audit record, not the monitored resource. Resource identity remains in standard resource/entity attributes. This prevents overloaded fields such as `audit.source` from ambiguously meaning device, process, principal, service, network peer, or telemetry emitter.

## Bounded values, privacy, and external references

Audit conventions must not imply that sensitive or arbitrarily large content should be emitted by default.

Recommended guidance:

- do not place secrets, tokens, raw credentials, full tool/request payloads, or unrestricted policy documents in audit attributes;
- use stable opaque identifiers rather than email addresses or usernames where possible;
- keep high-cardinality IDs out of metrics; audit IDs are appropriate for logs/events/traces;
- keep `audit.action` and `audit.reason` bounded at instrumentation time rather than relying only on downstream SDK truncation;
- `audit.reason` should be concise and sanitized because free-form error strings can contain sensitive information;
- large, binary, or sensitive detail belongs in an appropriate body/domain field or external store, subject to the domain's privacy/security policy;
- if #4102 is accepted and the ecosystem has offload support, `audit.reason_ref` can reference externalized reason content while preserving `audit.reason` as the defined base semantic;
- a `_ref` value is an identifier/locator, not a cryptographic proof by itself. Integrity, access control, retention, transfer, and retrieval of referenced content remain separate concerns.

### Why `audit.reason` should remain bounded

A common audit envelope should be useful without forcing every producer to emit an unbounded string. Reasons such as `policy_denied`, `approval_required`, `validation_failed`, or a short sanitized explanation can be bounded and interoperable.

If a domain requires a complete query, request body, diagnostic dump, or policy explanation, that content should use the domain's own attribute/body semantics or an external reference. The generic audit envelope should not become a payload transport.

## Example — policy-gated configuration change

```text
Event name: config.change

service.name = "controller"
config.key = "telemetry.sample_rate"
config.previous_value = "0.1"
config.new_value = "0.2"

audit.event.id = "01J..."
audit.category = "configuration_change"
audit.action = "config.update"
audit.outcome = "success"
audit.reason = "approved_change"
audit.initiator.type = "user"
audit.initiator.id = "principal-42"
audit.target.type = "service_configuration"
audit.target.id = "controller/default"
audit.policy.id = "prod-change-policy"
audit.policy.decision = "allow"
audit.approval.id = "approval-734"
```

The domain-specific configuration attributes stay outside the audit envelope.

## Example — autonomous action escalated to a human

```text
Event name: workflow.action.decision

audit.event.id = "01J..."
audit.category = "control_system"
audit.action = "tool.execute"
audit.outcome = "success"
audit.reason = "human_approval_required"
audit.initiator.type = "ai_agent"
audit.initiator.id = "planner-7"
audit.target.type = "tool"
audit.target.id = "vehicle.route.update"
audit.policy.id = "mission-safety-v4"
audit.policy.decision = "escalate"
audit.approval.id = "approval-91"
```

Here `audit.outcome=success` means the audited decision/approval flow completed successfully. The eventual tool execution result should be represented by the domain event that records execution.

## Why not one broad `audit.source` field?

`source` becomes ambiguous across distributed systems. The emitter, initiator, device, service, process, and network peer can all be different entities. Existing resource/entity semantics should identify the emitter and system components. The audit envelope should explicitly identify the **initiating principal** and optional **target** instead.

## Interoperability invariant

A consumer that only understands the audit envelope should be able to answer:

1. What audit category is this?
2. Who or what initiated it?
3. What action was attempted?
4. What resource was targeted?
5. What was the outcome?
6. Did a policy decision or approval govern it?

A consumer that understands the domain conventions should additionally be able to reconstruct operation-specific details without duplicated audit-specific schema.

## Compatibility checks against #4102

If #4102 lands substantially as drafted:

1. no common audit attribute should be marked unbounded unless the value is genuinely unbounded by nature;
2. no unbounded audit attribute should be required;
3. any proposed `*_ref` attribute must have a corresponding defined base attribute and string type;
4. `_ref` should be added only where actual instrumentation or telemetry-pipeline offload support exists;
5. the audit proposal should rely on SDK/instrumentation size limits for genuinely unbounded domain attributes, while still keeping its own common identifiers/reason summaries bounded by design.

If #4102 changes or is abandoned, this proposal should be revised rather than treating these draft mechanics as fixed OpenTelemetry policy.

## Suggested path upstream

1. Agree on the minimal-envelope concept and field semantics before final names.
2. Map at least two concrete categories to focused existing/domain conventions rather than defining a parallel audit ontology.
3. Prototype against at least two domains, e.g. access control and configuration change.
4. Validate privacy/cardinality/bounded-value guidance with existing security and logging discussions.
5. Track #4102 separately; adopt reference/unbounded mechanics only after upstream consensus.
6. Keep the initial convention intentionally small and extend only where multiple domains demonstrate the same cross-domain need.

## Submission boundary

This document is an internal source-reviewed proposal. Worldshepherd has not submitted it upstream and should not represent #4102's draft rules as accepted semantic conventions. Before any upstream contribution, re-check #2468, #4102, related focused issues, current contributor guidance, and whether maintainers prefer a concrete domain-specific prototype over a generic audit registry change.
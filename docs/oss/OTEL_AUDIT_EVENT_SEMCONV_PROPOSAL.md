# OpenTelemetry audit-event semantic proposal

Upstream target: `open-telemetry/semantic-conventions#2468`

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
audit.action            string   Human/machine-readable action identifier.
audit.outcome           enum     success | failure | unknown
audit.reason            string   Optional concise reason/result detail.
audit.initiator.type    enum     user | service | workload | device | ai_agent | unknown
audit.initiator.id      string   Identifier for the initiating principal when appropriate.
audit.target.type       string   Optional target/resource type.
audit.target.id         string   Optional target/resource identifier.
audit.policy.id         string   Optional policy identifier involved in the decision.
audit.policy.decision   enum     allow | deny | escalate | audit_only | unknown
audit.approval.id       string   Optional human/workflow approval correlation identifier.
```

Suggested audit categories aligned with IEC 62443-style needs while remaining general:

```text
access_control
request_error
control_system
backup_restore
configuration_change
audit_system
```

Projects can add or use domain-specific categories through the normal semantic-convention process rather than turning the base list into an exhaustive ontology.

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

`audit.event.id` should identify the audit record, not the monitored resource. Resource identity remains in standard resource attributes. This prevents overloaded fields such as `audit.source` from ambiguously meaning device, process, principal, service, or emitter.

## Privacy and cardinality guidance

Audit conventions must not imply that sensitive data should be emitted by default.

Recommended guidance:

- do not place secrets, tokens, raw credentials, or full tool/request payloads in audit attributes;
- use stable opaque identifiers rather than email addresses or usernames where possible;
- keep high-cardinality IDs out of metrics; audit IDs are appropriate for logs/events/traces;
- `audit.reason` should be concise and sanitized because error strings can contain sensitive information;
- payload evidence should be stored externally and referenced by digest/ID when necessary.

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

A consumer that understands the domain conventions should additionally be able to reconstruct the operation-specific details without any duplicated audit-specific schema.

## Suggested path upstream

1. Agree on the envelope concept and field semantics before final names.
2. Prototype against at least two different domains, e.g. access control and configuration change.
3. Validate privacy/cardinality guidance with the existing security and logging discussions.
4. Add category-specific examples without moving domain attributes into the audit namespace.
5. Keep the initial convention intentionally small and extend only where multiple domains demonstrate the same need.

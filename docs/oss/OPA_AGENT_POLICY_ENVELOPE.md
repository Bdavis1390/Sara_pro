# OPA AI-agent policy decision envelope

Upstream target: `open-policy-agent/opa#8851`

## Purpose

A first-party AI-agent policy guide will be most reusable if it separates:

- **PDP** — Open Policy Agent evaluates policy and returns a decision;
- **PEP** — the agent runtime/executor enforces that decision;
- **evidence/audit layer** — records the request, policy revision, decision, approval path, and resulting action outcome.

OPA should remain the policy decision point. The runtime should not assume that an `allow` result itself performs or authorizes an external side effect.

## Minimal input envelope

```json
{
  "request_id": "01J...",
  "actor": {
    "id": "agent:planner-7",
    "type": "ai_agent",
    "tenant": "example"
  },
  "action": {
    "name": "tool.execute",
    "tool": "payments.transfer",
    "operation": "create",
    "resource": "account:destination",
    "parameters": {
      "amount": 125.00,
      "currency": "USD"
    }
  },
  "context": {
    "environment": "production",
    "mission_id": "mission-123",
    "session_id": "session-456",
    "human_present": true,
    "network_state": "nominal"
  },
  "provenance": {
    "model_id": "model-name-or-digest",
    "agent_version": "git-or-build-digest",
    "tool_schema_version": "v1"
  }
}
```

The input should describe the proposed effect, not an implementation-specific callback.

## Structured decision envelope

Instead of reducing every result to a boolean, the guide can recommend a small structured result:

```json
{
  "decision": "escalate",
  "reason": "human approval required above configured transfer threshold",
  "decision_id": "dec-01J...",
  "policy": {
    "package": "agent.authz",
    "revision": "sha256:..."
  },
  "requirements": {
    "human_approval": true,
    "mfa": false
  },
  "constraints": {
    "max_amount": 100.00
  },
  "audit": {
    "severity": "medium",
    "retain": true
  }
}
```

Suggested decision vocabulary:

```text
allow
 deny
 escalate
 audit_only
```

`escalate` is important because many agentic actions should not be represented as simply allowed or denied when a human approval path exists.

## Enforcement contract

A useful guide-level invariant is:

> The executor MUST NOT perform the proposed side effect unless the current policy decision permits it and all returned requirements are satisfied.

The PEP should bind the enforced action to the evaluated action. If the tool arguments change after policy evaluation, the runtime should re-evaluate rather than treating the old decision as valid.

A simple binding can be represented with an action digest:

```text
action_digest = sha256(canonical_json(action))
```

The audit record then includes the same digest for the proposal and the executed action.

## Example Rego

```rego
package agent.authz

import rego.v1

default decision := {
  "decision": "deny",
  "reason": "no matching allow rule",
  "requirements": {},
  "constraints": {},
}

decision := {
  "decision": "allow",
  "reason": "read-only tool permitted",
  "requirements": {},
  "constraints": {},
} if {
  input.action.operation == "read"
}

decision := {
  "decision": "escalate",
  "reason": "human approval required for production write",
  "requirements": {"human_approval": true},
  "constraints": {},
} if {
  input.context.environment == "production"
  input.action.operation in {"create", "update", "delete"}
}
```

This example deliberately keeps enforcement outside OPA.

## Audit fields worth showing in the guide

```text
request_id
decision_id
actor.id
action.name
action.tool
action.operation
action_digest
policy.package
policy.revision
decision
reason
requirements_satisfied
approval_id
execution_result
execution_timestamp
```

These fields allow an operator to answer four distinct questions:

1. What did the agent propose?
2. Which policy version evaluated it?
3. What did the policy decide and require?
4. What was actually executed?

## Test cases the guide should include

- ordinary allow;
- ordinary deny;
- escalation requiring human approval;
- changed tool arguments after evaluation causing re-evaluation;
- policy bundle revision changing between two otherwise identical requests;
- malformed or missing context failing closed for sensitive operations;
- audit-only rule that records but does not block an action.

## Scope boundary

This proposal does not require OPA to become an executor, token issuer, workflow engine, or provenance database. It only gives the proposed guide a stable contract between the agent runtime and OPA and makes policy decisions auditable and enforceable by the surrounding runtime.

# Worldshepherd OPA Policy Decision Bridge v1

## Purpose

Allow SARA / PRIME evidence workflows to consume a bounded boolean decision from an Open Policy Agent (OPA) decision endpoint without reimplementing Rego or treating Worldshepherd policy formats as a replacement for OPA.

OPA remains the policy engine. Worldshepherd records the request/decision evidence and applies any additional local human-approval or consequential-action boundary required by the Worldshepherd workflow.

## Default trust boundary

The bridge is **local-first**. By default it accepts only loopback OPA endpoints:

- `127.0.0.1`
- `localhost`
- `::1`

The endpoint must use `http` or `https` and target an OPA `/v1/data/...` decision path. Credentials embedded in the URL are rejected.

Remote OPA endpoints are blocked unless the caller explicitly supplies `--allow-remote`. That flag does not establish transport security, authentication, authorization, server identity, certificate policy, or network trust; those remain deployment responsibilities and must be separately evidenced.

## Boolean decision contract

This v1 bridge intentionally accepts only a boolean OPA `result`:

```json
{
  "result": true,
  "decision_id": "optional-opa-decision-id"
}
```

The restriction is deliberate. A complex OPA result object may carry domain-specific obligations or metadata that should not be silently coerced into authorization semantics.

- `true` -> `ALLOW`
- `false` -> `DENY`
- missing `result` -> fail closed
- non-boolean `result` -> fail closed
- transport/HTTP failure -> fail closed
- malformed/non-JSON response -> fail closed

The CLI exits `0` for an OPA ALLOW and `2` for an OPA DENY. Evaluation/parsing failures raise an error rather than being converted to an allow.

## Evidence receipt

For every valid OPA response, the bridge records:

- UTC evaluation timestamp;
- exact OPA decision endpoint;
- SHA-256 of the canonical request body;
- `ALLOW` / `DENY`;
- original boolean result;
- OPA `decision_id` when supplied;
- SHA-256 of the canonical OPA response;
- an explicit claims boundary.

This supports correlation with OPA decision logs and Worldshepherd audit/evidence records without claiming that either record validates the other by itself.

## Example

Run a local OPA server separately, then:

```bash
ws-opa-policy-eval \
  --endpoint http://127.0.0.1:8181/v1/data/worldshepherd/allow \
  --input fixture.json \
  --output opa-decision-receipt.json
```

Example input:

```json
{
  "actor": "identified-operator",
  "action": "read",
  "resource": "synthetic-evidence"
}
```

## Relationship to PRIME

An OPA ALLOW is **not** automatically a PRIME authorization for a consequential action.

OPA can answer whether its configured policy permits the supplied input. PRIME/SARA may still require independently satisfied conditions such as:

- identified-human approval;
- role/authority evidence;
- workflow state;
- freshness/replay constraints;
- protected-resource scope;
- prohibited-action checks;
- local safety or legal gates.

This separation prevents a successful external policy evaluation from bypassing Worldshepherd's human-authorization boundary.

## Claims boundary

A bridge receipt establishes only what the configured OPA endpoint returned for the hashed request at the recorded time.

It does **not** establish:

- correctness, completeness, approval, freshness, or legal sufficiency of the OPA policy;
- identity or trustworthiness of a remote OPA service merely because `--allow-remote` was used;
- OPA or CNCF endorsement, partnership, adoption, or certification;
- customer/government authorization;
- automatic permission for a consequential action;
- independent validation of Worldshepherd.

For the Worldshepherd Assurance Composite Benchmark, this work can support policy-interoperability and decision-evidence dimensions only after the implementation passes exact-head CI and an evaluator exercises it against an actual OPA policy bundle or decision service. Unit tests alone do not earn maximum evidence points.

# Worldshepherd W3C / OpenTelemetry Trace Correlation v1

## Purpose

Provide a standards-native way to correlate Worldshepherd evidence with an existing distributed trace without turning trace metadata into identity, authorization, or trust evidence.

The implementation uses the official `opentelemetry-api` package and its W3C Trace Context propagator. Worldshepherd does not define a proprietary trace identifier format.

## Supported input

The v1 receipt accepts:

- required `traceparent`;
- optional `tracestate`;
- optional SHA-256 digest of the Worldshepherd evidence object being correlated.

The OpenTelemetry W3C Trace Context propagator validates/extracts the context. Invalid or all-zero trace/span identifiers are rejected.

## Receipt

A valid receipt records:

- trace ID;
- parent span ID;
- trace flags;
- remote-context flag;
- normalized trace state when present;
- SHA-256 binding of the supplied propagation headers;
- optional evidence SHA-256;
- UTC timestamp;
- explicit claims boundary.

Example:

```bash
ws-trace-context-receipt \
  --traceparent 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01 \
  --tracestate vendorname=opaquevalue \
  --evidence-sha256 <64-lowercase-hex> \
  --output trace-correlation-receipt.json
```

## Security / authority boundary

A valid trace context establishes **correlation only**.

It does not establish:

- user or workload identity;
- authentication;
- authorization;
- human approval;
- integrity or authenticity of the upstream request;
- correctness of telemetry;
- customer/government acceptance;
- operational trustworthiness.

PRIME/SARA authorization and ECHO evidence-integrity/custody controls remain separate gates.

## Competitive-benchmark relevance

This targets Assurance Composite Benchmark A11 (observability / trace correlation) and part of A13 (standards-native exchange).

Maximum interoperability/evidence credit requires more than this implementation: exact-head CI must pass and the correlation receipt must be exercised across a real service/process boundary using externally generated trace context. A local unit test alone is not an end-to-end distributed tracing result.

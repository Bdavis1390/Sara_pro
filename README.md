# Sara_pro

Worldshepherd SARA development repository.

## Evidence-governed runtime

On `agent/evidence-governed-physical-engineering`, launch with:

```bash
./scripts/start_interface.sh
```

The launcher starts `worldshepherd_sara.evidence_server:app`, which exposes the existing SARA interface plus append-only evidence-registry endpoints under `/v1/evidence/*`.

Evidence creation is limited to operator/admin tokens; evidence read/export/metrics are admin-only. Records are validated before persistence, duplicate identifiers are rejected, corrections use explicit supersession, and local SHA-256 raw-data objects are verified when available.

The evidence layer does not validate any propulsion, materials, FIELD-SKIN, or anomalous-physics claim by itself. It enforces provenance and claims-control boundaries around those programs.

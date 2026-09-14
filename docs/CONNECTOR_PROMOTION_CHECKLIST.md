# Connector Promotion Checklist

Use this checklist before promoting the connector-control branch.

- [ ] `data/worldshepherd_connectors.v2.json` validates.
- [ ] Connector and tool IDs are unique.
- [ ] Unknown actions are denied.
- [ ] External writes require human approval.
- [ ] Operator role cannot use admin-only connectors.
- [ ] Data-class ceilings are enforced.
- [ ] Credential data remains outside the connector manifest and policy engine.
- [ ] Approved proposals produce an ECHO SHA-256 envelope.
- [ ] Dry-run evaluator performs no external action.
- [ ] CI compile step passes.
- [ ] CI policy tests pass.
- [ ] Branch diff contains no secrets or generated environment files.
- [ ] Existing SARA admin/operator authentication remains the only live gateway authentication path.
- [ ] Live connector execution, when added, records provenance and uses the existing SARA audit boundary.

Promotion target order:

1. `worldshepherd-sspadawanzz-admin`
2. local integration/smoke test
3. `main` only after the admin branch passes its established validation path

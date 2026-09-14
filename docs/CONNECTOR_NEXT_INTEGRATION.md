# Connector Next Integration

The next integration step is to call the connector policy engine from the existing authenticated SARA gateway.

Required behavior:

- expose connector health and catalog views through the current admin surface
- evaluate proposed connector actions before execution
- preserve current admin/operator role separation
- write minimal authorization results to the existing audit trail
- keep connector execution separate from authorization
- run smoke tests before promotion

No new gateway implementation is included in this branch yet.

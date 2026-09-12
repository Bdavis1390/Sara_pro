# NATS Server #8270 — recheck existing clients against the **new** pinned certificate set

Upstream: `nats-io/nats-server#8270`

Claims state: **SOURCE-REVIEWED PATCH DESIGN / REQUIRES UPSTREAM TEST EXECUTION**

## Confirmed defect in current `server/reload.go`

`recheckPinnedCerts(curOpts, newOpts)` correctly detects whether the pin set changed, but for ordinary NATS, MQTT, and WebSocket client connections it populates `protoToPinned` from **`curOpts`**:

```go
if !reflect.DeepEqual(newOpts.TLSPinnedCerts, curOpts.TLSPinnedCerts) {
    protoToPinned[NATS] = curOpts.TLSPinnedCerts
}
if !reflect.DeepEqual(newOpts.MQTT.TLSPinnedCerts, curOpts.MQTT.TLSPinnedCerts) {
    protoToPinned[MQTT] = curOpts.MQTT.TLSPinnedCerts
}
if !reflect.DeepEqual(newOpts.Websocket.TLSPinnedCerts, curOpts.Websocket.TLSPinnedCerts) {
    protoToPinned[WS] = curOpts.Websocket.TLSPinnedCerts
}
```

The same function then iterates connected clients and disconnects those that do not match the selected set. Because the selected set is the old one, an already-connected client whose certificate was removed by the reload still passes.

The adjacent leaf, route, and gateway branches already recheck against `newOpts`, which establishes the intended direction of comparison.

## Minimal patch

Replace only the three incorrect assignments:

```diff
 if !reflect.DeepEqual(newOpts.TLSPinnedCerts, curOpts.TLSPinnedCerts) {
-    protoToPinned[NATS] = curOpts.TLSPinnedCerts
+    protoToPinned[NATS] = newOpts.TLSPinnedCerts
 }
 if !reflect.DeepEqual(newOpts.MQTT.TLSPinnedCerts, curOpts.MQTT.TLSPinnedCerts) {
-    protoToPinned[MQTT] = curOpts.MQTT.TLSPinnedCerts
+    protoToPinned[MQTT] = newOpts.MQTT.TLSPinnedCerts
 }
 if !reflect.DeepEqual(newOpts.Websocket.TLSPinnedCerts, curOpts.Websocket.TLSPinnedCerts) {
-    protoToPinned[WS] = curOpts.Websocket.TLSPinnedCerts
+    protoToPinned[WS] = newOpts.Websocket.TLSPinnedCerts
 }
```

This preserves the existing reload architecture and changes only the policy snapshot used to authorize existing client connections.

## Required regression tests

For each of NATS, MQTT, and WebSocket client protocols:

1. Configure pin set A and connect a client presenting certificate A.
2. Reload to pin set B, excluding certificate A.
3. Assert the existing A connection is closed.
4. Assert a new A connection is rejected.
5. Assert a B connection is accepted after reload.
6. Reload from A to a set containing A and B and assert A remains connected.
7. Reload from a non-empty set to an empty set and validate the intended documented semantics of an empty pin set; the test should codify current contract rather than infer it.

Add a positive control for leaf/route/gateway behavior only if inexpensive; those paths already use `newOpts` and serve as useful consistency references.

## Security invariant

After successful configuration reload:

> **Every existing and new connection must be evaluated against the same effective pinned-certificate policy.**

There must be no interval where the resolver/config state says certificate A is revoked while an existing A session remains authorized because it was checked against the previous snapshot.

## Worldshepherd mapping

This is a PRIME/ECHO policy-state consistency defect: configured authorization state and effect-producing session state diverge. The narrow fix is preferable to adding a separate reconciliation layer in Worldshepherd; upstream NATS should enforce its own reload contract, while Worldshepherd can monitor reload and disconnect evidence.

## Submission boundary

No matching implementation PR was found in the 2026-09-12 duplicate check. Re-check immediately before upstream submission. Run the relevant NATS TLS/reload test suite and protocol-specific tests before calling this patch validated or upstream-ready.

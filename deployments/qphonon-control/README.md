# WS-QPHONON V0.3 deployment infrastructure

This deployment is a **non-networked evidence/execution guard**, not a quantum-device controller.

## Trust boundary

The guard:
- verifies ECHO event integrity and configuration binding;
- persists event/approval replay state across process restarts;
- enforces monotonic evidence sequences;
- verifies detached OpenSSH signatures against a root-managed allowed-signers file;
- consumes an approval ID exactly once;
- returns an execution eligibility decision.

The guard does **not**:
- possess an approval private key;
- authenticate raw laboratory sensors;
- open a TCP/UDP listening port;
- directly actuate phononic or quantum hardware;
- convert generic-QPU evidence into phononic evidence;
- establish L3 physical capability.

## Host layout

- code: `/opt/worldshepherd/qphonon` — root owned
- state: `/var/lib/worldshepherd/qphonon/state.sqlite3` — service-account owned, mode 0600
- signer policy: `/etc/worldshepherd/qphonon/allowed_signers` — root managed, read-only to service
- launcher: `/usr/local/bin/ws-qphonon-guard`

The intended service account is `ws-qphonon` with no login shell.

## Approval signing

Use an external Ed25519-capable OpenSSH key under human custody. The private key must remain outside the guard.

The canonical approval payload is signed under the namespace:

`worldshepherd-qphonon-approval`

The deployment guard verifies the signature with `ssh-keygen -Y verify`, then applies the PRIME/execution checks and durable replay claim.

## L3 boundary

A fully functioning V0.3 deployment is **deployment infrastructure evidence only**.

L3 phononic evidence still requires a relevant partner laboratory, physical phononic hardware, frozen pre-run criteria, actual measured results, uncertainty, ECHO provenance, a precommitted holdout result, and independent reproduction.

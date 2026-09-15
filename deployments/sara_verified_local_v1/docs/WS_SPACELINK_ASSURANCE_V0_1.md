# Worldshepherd SpaceLink Assurance v0.1

Status: **DRAFT / INTERNAL SOFTWARE VALIDATION ONLY**

## Purpose

Worldshepherd SpaceLink Assurance v0.1 establishes a vendor-neutral, claims-controlled software boundary for ingesting satellite ground-network contact state, converting that state into Worldshepherd mission evidence, and preparing human-authorized reservation proposals without executing provider writes.

The first provider schema mapped is AWS Ground Station because its public API and digital-twin documentation provide an authoritative, testable interface surface.

## Architecture

```text
provider contact state / synthetic fixture
            |
            v
  GroundNetworkContactAdapter
            |
            v
   NormalizedSpaceContact
            |
     +------+-------+
     |              |
     v              v
mission replay   SARA/ECHO event path
     |
     v
OVERWATCH-ready normalized evidence

ContactReservationProposal
            |
            v
  HUMAN AUTHORITY BOUNDARY
            |
        [NO EXECUTOR IN v0.1]
```

## Current evidence boundary

Implemented in v0.1:

- exact normalization of the documented AWS Ground Station contact-state vocabulary;
- fail-closed rejection of unknown states;
- deterministic reduction of provider states into `AVAILABLE`, `PENDING`, `SCHEDULED`, `ACTIVE`, `SUCCEEDED`, `CANCELLED`, or `FAILED` dispositions;
- conversion of normalized contact state into the existing Worldshepherd `MissionEvent` replay model;
- non-executable reservation proposals with explicit human-authority and claims boundaries;
- explicit representation of the current AWS digital-twin limitation: scheduling/configuration/error-handling API tests are supported, but data delivery and telemetry delivery are not supported on digital-twin ground stations;
- frozen synthetic lifecycle fixtures for internal testing.

Not implemented / not claimed:

- AWS credentials, SDK client, `ReserveContact`, `CancelContact`, `UpdateContact`, or any other provider-side write;
- actual AWS digital-twin onboarding;
- RF transmission or reception;
- spectrum rights, FCC licensing, equipment authorization, or interference coordination;
- spacecraft command delivery;
- downlink or telemetry delivery;
- satellite, antenna, modem, ground-station, or inter-satellite physical performance;
- AWS, FCC, government, operator, or partner validation;
- operational readiness or certification.

## Authoritative public interface references

- AWS Ground Station API Reference: <https://docs.aws.amazon.com/ground-station/latest/APIReference/Welcome.html>
- ListContacts: <https://docs.aws.amazon.com/ground-station/latest/APIReference/API_ListContacts.html>
- ReserveContact: <https://docs.aws.amazon.com/ground-station/latest/APIReference/API_ReserveContact.html>
- Digital twin: <https://docs.aws.amazon.com/ground-station/latest/ug/digital-twin.html>

## Validation ladder

| Gate | Requirement | v0.1 state |
|---|---|---|
| SL-0 | Provider-neutral normalized contact schema | IMPLEMENTED; INTERNAL TEST REQUIRED |
| SL-1 | Authoritative provider contact-state mapping | IMPLEMENTED; INTERNAL TEST REQUIRED |
| SL-2 | Fail-closed unknown-state handling | IMPLEMENTED; INTERNAL TEST REQUIRED |
| SL-3 | Replayable contact-state mission events | IMPLEMENTED; INTERNAL TEST REQUIRED |
| SL-4 | Human-gated non-executable reservation proposal | IMPLEMENTED; INTERNAL TEST REQUIRED |
| SL-5 | Digital-twin scheduling/config/error API validation | NOT YET EXECUTED |
| SL-6 | Idempotent provider write path with dedicated PRIME authorization | NOT IMPLEMENTED |
| SL-7 | EventBridge/provider-event ingestion and failure/retry evidence | NOT IMPLEMENTED |
| SL-8 | OVERWATCH contact/link COP integration | NOT IMPLEMENTED |
| SL-9 | External GSaaS/partner validation | REQUIRES PARTNER VALIDATION |
| SL-10 | RF / flight / operational validation | REQUIRES EXTERNAL PHYSICAL VALIDATION AND ALL APPLICABLE AUTHORIZATIONS |

## PRIME integration rule

The existing PRIME SENTINEL authorization assertion in this deployment is scoped to its current explicit action vocabulary. v0.1 does **not** repurpose that assertion for satellite ground-network writes. A future SpaceLink executor must add a separately reviewed, explicit authorization action and tests before it can issue a provider-side reservation, cancellation, update, or command operation.

This is intentional fail-closed behavior.

## AWS digital-twin scope

The AWS Ground Station digital twin is appropriate for SL-5 because AWS documents that it can be used to test scheduling, configuration verification, error handling, API responses, and EventBridge events without production antenna capacity or spectrum licensing. AWS also documents that digital-twin ground stations currently do not support data delivery or telemetry delivery.

Therefore a successful SL-5 cannot be promoted into a telemetry, command-delivery, RF, or satellite-operations claim.

## Claims-control statement

The strongest defensible v0.1 claim is:

> Worldshepherd contains an internal software adapter and governance contract for normalizing documented satellite-ground-network contact state and preparing replayable, human-gated mission evidence.

Do not claim that Worldshepherd is integrated with AWS Ground Station, operates a satellite ground station, transmits on FCC-authorized spectrum, controls spacecraft, or has partner/government validation until independent evidence for those scopes exists.

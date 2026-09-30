# Worldshepherd UC06-P1 EM Provenance Contract

Status: R&D implementation contract; does not change any frozen UC06-P1 scientific gate.

## Purpose

Two nominally identical electromagnetic spectra are not scientifically comparable merely because their final numerical values look similar. Comparability requires retained transformation history plus the solver/model/hardware context that produced each result.

## Required candidate context

Each candidate evidence bundle binds:

- intent and objective;
- candidate identity and evidence class;
- simulation-validation assessment;
- geometry identity;
- mesh identity when assigned;
- solver name/version;
- solver binary SHA-256 when available;
- configuration SHA-256 when available;
- physical hardware revision, fixture, calibration, and environment identifiers when they exist;
- source receipts;
- explicit claims boundary.

## Transformation continuity

Each transformation step records:

- operation;
- tool and version;
- input digest;
- output digest;
- parameter digest when available;
- actor;
- observation time.

For sequential transformations, the prior output digest must equal the next input digest. Broken continuity rejects bundle construction.

## Stage separation

Candidate admission to Palace validation is distinct from physical authorization.

A candidate can be classified `PALACE_VALIDATION_CANDIDATE` while hardware authorization remains false. A hardware-action flag on a simulation-stage candidate is a validation blocker.

## Observation provenance

Future EM observations are stored in an append-only JSONL ledger with:

- monotonic sequence numbers;
- canonical observation digest;
- previous-record digest;
- canonical record digest;
- duplicate observation-ID rejection;
- spectral-array shape validation;
- fsync on append;
- full chain verification on read-back.

Modification of an earlier observation causes read-back verification to fail.

## PRIME boundary

The separate PRIME EM policy kernel requires all explicit gates before any future hardware action:

1. medium-to-fine convergence passed;
2. energy closure passed;
3. physical validation complete;
4. repeatability validated;
5. validated operating envelope present;
6. explicit PRIME release;
7. candidate hardware-action flag explicitly authorized.

Any missing condition fails closed to `SAFE_OPEN`.

## Current UC06-P1 status

The current retained UC06-P1 evidence remains diagnostic/simulation evidence. Overall convergence remains `NOT_ADJUDICATED`; D5 and recovery/convergence evidence remain pending. This provenance implementation does not promote H2, authorize the full campaign, or establish physical hardware capability.

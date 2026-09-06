# Actual Worldshepherd Host and Scientific Validation Status — 2026-09-06

## 1. Actual-host evidence already established

The governing SARA runtime/recovery record documents a July 24, 2026 local-host verification on the Worldshepherd host. That record reports:

- Ubuntu 22.04 LTS / Bodhi Linux 7.0 environment;
- Docker/containerd enabled and active;
- loopback-only SARA binding at `127.0.0.1:9530`;
- successful SARA health/UI, relay/admin separation, registry, self-test, and audit behavior;
- persistent `audit.jsonl` and `registry.json` across service restart;
- checksum-verified local persistent-data backup and disposable restore with digest equality;
- one controlled host reboot with automatic SARA recovery and preserved registry/audit state.

The same record explicitly leaves repeated reboot, abrupt power-loss recovery, replacement-host recovery, independent off-host retention, production security, broader integrations, and final operational-capacity approval open.

## 2. September 6 delta

The July host evidence predates the PVK v0.5 Git-controlled implementation. Therefore the current acceptance problem is a version-binding problem, not an absence-of-host-evidence problem.

The controlled branch now contains `scripts/verify_actual_host_pvk.sh`, which is designed to be executed on the actual Worldshepherd host after the branch is checked out cleanly. It deliberately uses a separate Compose project, separate Docker volume, and a loopback shadow port (default `19530`) so the historical `9530` local service need not be replaced merely to validate the candidate.

The script verifies:

1. expected branch and clean tracked deployment state;
2. actual host/kernel/OS/Docker/Compose evidence capture;
3. clean build and readiness of the current Git commit;
4. relay rejection from PVK admin endpoints;
5. administrator PVK status access;
6. PVK record append;
7. claims-linter blocking of an unsupported reactionless-propulsion statement;
8. PVK record persistence across container restart;
9. presence of PVK/audit events;
10. SHA-256 evidence manifest;
11. shadow-project cleanup.

A PASS from that script is bounded software/runtime evidence only. It does not validate any material, propulsion, electromagnetic, aerospace, sensing, energy, or medical-physics claim.

## 3. Scientific validation status

`fixtures/scientific_validation_campaigns_v1.json` separates external foundation evidence from Worldshepherd-specific validation.

### WS-AlTi

External literature supports Sc/Zr microalloying, Al3(Sc,Zr) precipitation strengthening, additive-manufacturing-specific process/microstructure effects, and the need to characterize defects and anisotropy. This supports the scientific feasibility of relevant materials mechanisms, but does not validate the Worldshepherd-specific M1-MSZ-Prime composition, programmed zoning, coupon properties, fatigue, corrosion, or aerospace qualification.

Representative literature:

- González-Rovira et al., *Materials & Design* (2025), DOI `10.1016/j.matdes.2025.114080`.
- *Journal of Alloys and Compounds* (2024), DOI `10.1016/j.jallcom.2024.173946`.
- Glerum et al., *Additive Manufacturing* (2020), DOI `10.1016/j.addma.2020.101461`.

### Adaptive metasurface

Peer-reviewed literature supports active/reconfigurable metasurfaces, dynamic phase/amplitude control, beam steering, and tunable material/control mechanisms. This validates the underlying field-control concept class, not Worldshepherd-specific RF/optical performance, broad-spectrum operation, stealth, cloaking, or cancellation.

Representative literature:

- Gu et al., *Nature Photonics* 17, 48–58 (2023), DOI `10.1038/s41566-022-01099-4`.
- Sisler et al., *Nature Nanotechnology* 19, 1491–1498 (2024), DOI `10.1038/s41565-024-01728-9`.

### Ion propulsion

Ion propulsion is externally flight-proven and based on established momentum exchange through accelerated propellant. NASA documents flight use on Deep Space 1/Dawn and maintains current in-space-propulsion state-of-the-art references. This validates the propulsion class, not a Worldshepherd-specific thruster.

Representative sources:

- NASA Dawn Ion Propulsion: `https://science.nasa.gov/mission/dawn/technology/ion-propulsion/`
- NASA Small Spacecraft In-Space Propulsion state of the art: `https://www.nasa.gov/smallsat-institute/sst-soa/in-space_propulsion/`

### Resonant electromagnetic / anomalous-force propulsion

Electromagnetic resonance and radiation pressure are established. A high-accuracy peer-reviewed EMDrive test using improved thermal, magnetic, feedthrough, vacuum, and force-balance controls found no anomalous thrust above the photon-thrust limit. Therefore Worldshepherd must treat any reactionless/electrogravitic interpretation as unresolved unless a new experiment survives stronger controls and independent replication.

Representative evidence:

- Tajmar, Neunzig & Weikert, *CEAS Space Journal* 14, 31–44 (2022), DOI `10.1007/s12567-021-00385-1`.

## 4. Advancement rule

The following transitions are allowed only with corresponding evidence:

`CONCEPT -> LITERATURE_SUPPORTED -> SIMULATED -> INTERNAL_TEST -> INDEPENDENTLY_REPLICATED -> QUALIFIED -> CERTIFIED`

External literature may advance the *foundation* classification but cannot advance a Worldshepherd-specific artifact to physical validation. A real Worldshepherd experiment must preserve setup identity, calibration, raw-data digests, environmental conditions, uncertainty, confounders, negative results, and replication status.

## 5. Immediate gates

1. Execute `scripts/verify_actual_host_pvk.sh` on the actual host and preserve the resulting `.host-pvk-evidence/<timestamp>` directory.
2. Preserve the existing July host evidence as the historical baseline; do not overwrite it.
3. Begin the first two physical campaigns with the lowest-cost decisive tests: WS-AlTi coupon characterization and a single-band adaptive-metasurface coupon/array.
4. Do not allocate extraordinary-physics maturity to resonant-EM propulsion unless a measured residual survives photon, thermal, magnetic, electrostatic, mechanical, gas-flow, cable, and calibration controls and is independently replicated.

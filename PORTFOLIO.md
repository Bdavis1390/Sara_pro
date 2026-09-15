# Worldshepherd Portfolio

**Purpose:** give an engineer, partner, reviewer, or program office a reliable five-minute map of what Worldshepherd covers, where the current evidence lives, and what should *not* be inferred from breadth alone.

> **Portfolio breadth is not maturity.** Every lane inherits the claim-state rules in [`docs/CLAIMS_AND_EVIDENCE_POLICY.md`](docs/CLAIMS_AND_EVIDENCE_POLICY.md).

## Five-minute map

Worldshepherd is currently organized around four public evidence classes:

| Class | Meaning | What a reviewer should expect |
|---|---|---|
| **Canonical / runnable** | A supported repository path with explicit run/test/evidence controls | exact entry point, CI, failure boundaries, configuration and limitations |
| **Software / integration work** | Code, schemas, workflows or integration artifacts exist, but maturity is component-specific | tests and evidence must be checked per component; external integration is never inferred |
| **Research / simulation** | Models, studies, designs, equations, simulations or validation plans | assumptions, literature/simulation basis, falsification path and lab/partner gates |
| **Capture / screening / evidence history** | Opportunity, partner, qualification, transition or historical evidence artifacts | dated provenance and claims boundaries; not a product specification |

## Flagship canonical runtime

### SARA / SSPADAWANZZ Verified Local

**Repository status:** `CANONICAL`  
**Claim state:** `IMPLEMENTED IN SOFTWARE` with commit-scoped internal verification only.

Start here:

- [`runtime/README.md`](runtime/README.md) — supported operator path;
- [`runtime/manifest.json`](runtime/manifest.json) — machine-readable runtime identity;
- [`scripts/sara.sh`](scripts/sara.sh) — root setup/run/test/smoke/check wrapper;
- [`deployments/sara_verified_local_v1/`](deployments/sara_verified_local_v1/) — authoritative source/test/deployment package;
- [`docs/adr/0001-canonical-sara-runtime.md`](docs/adr/0001-canonical-sara-runtime.md) — architecture decision;
- [`.github/workflows/sara-verified-local-v1.yml`](.github/workflows/sara-verified-local-v1.yml) — implementation evidence gate.

Current public boundary: the service demonstrates governed local administration, authorization, audit, registry and relay-recording behavior. `recorded_local_only` does not mean external message delivery, arbitrary execution or third-party activation.

## Core software and integration families

| Family | Scope | Current public posture | Primary repository path / governing document |
|---|---|---|---|
| **SARA** | governed workflow/orchestration, local relay recording, administration, evidence-aware runtime | canonical runnable local software | [`runtime/README.md`](runtime/README.md) |
| **PRIME SENTINEL** | policy, authorization, signed/controlled action boundaries | implementation evidence is artifact-specific; do not generalize architecture into universal enforcement | SARA package, PRIME-related docs/workflows and capability map |
| **ECHO SENTINEL LINK** | telemetry/evidence provenance, anchoring, configuration lineage | software/provenance artifacts exist; trust boundary varies by artifact | `external_anchor_pilots/`, relevant workflows/docs |
| **OVERWATCH** | observability / common-operating-picture integration | architecture/integration lane; no single canonical standalone runtime yet | [`docs/WORLDSHEPHERD_CAPABILITY_MAP.md`](docs/WORLDSHEPHERD_CAPABILITY_MAP.md) |
| **PRE** | Requirement Delta Records, demand classification, readiness gaps, qualification evidence, partner/capture support | governance/schema and substantial software/evidence tooling exist; forecasting never upgrades capability maturity | [`docs/PRE_REQUIREMENT_DELTA_SCHEMA_V1.md`](docs/PRE_REQUIREMENT_DELTA_SCHEMA_V1.md), SARA deployment PRE tooling |
| **CISNET / resilient communications** | communications/integration experiments and DTN-adjacent work | integration/research maturity is artifact-specific | `cisnet/`, related docs/workflows |
| **HMAA / evidence services** | governed evidence/access patterns represented inside current SARA development history | software maturity is test-specific; not an external authorization claim | canonical SARA package and associated evidence/tests |

## Mission and autonomy portfolio

Worldshepherd work includes mission assurance, C2 integration, autonomous logistics, drones/VTOL concepts, humanoid/companion robotics, DDIL behavior, edge AI, sensor fusion, digital twins and CBM+.

**Public posture:** mixed software/integration/research. A repository artifact does not establish flight readiness, field readiness, safety certification, physical autonomy performance or partner acceptance.

Use the [capability map](docs/WORLDSHEPHERD_CAPABILITY_MAP.md) as the governing maturity summary; use component tests and evidence records for narrower claims.

## Communications, sensing and electromagnetic portfolio

Work includes resilient communications/APNT, distributed sensing, RF classification, antennas, adaptive metasurfaces, beamforming/null steering and programmable electromagnetic-boundary research.

**Public posture:** ranges from software/integration evidence to literature-supported, simulated, hypothesis and lab-validation-required research. Measured RF/APNT performance must come from calibrated hardware evidence or explicit partner/lab validation—not from an architecture diagram or simulation alone.

## Materials and manufacturing portfolio

Work includes additive manufacturing/DED, process zoning, manufacturing lineage, Al-Ti-family meta-alloy concepts, material-property targeting and qualification planning.

**Public posture:** research/process-integration/IP-stage depending on artifact. Coupon fabrication, microscopy, mechanical/thermal/corrosion measurements and process repeatability are required before physical-property promotion.

## Propulsion, energy and space portfolio

Work includes practical electric propulsion architectures, plasma/field research, aerospace propulsion studies, energy storage/distribution/conversion, space robotics, particulate awareness and in-space resource assessment.

**Public posture:** concept-specific. Conservation laws, power/thermal closure, calibrated thrust/efficiency measurements and independent replication govern any extraordinary propulsion claim. Space concepts require environment-specific modeling and qualification before operational language is appropriate.

## Advanced physics / computational research

The repository/history includes numerical physics, MHD/field-control, quantum-adjacent, nonlinear-material and other exploratory research.

**Public posture:** usually `SUPPORTED BY LITERATURE`, `SIMULATED ONLY`, `HYPOTHESIS` or `SPECULATIVE EXTENSION` unless a specific executable/test artifact proves more.

Mathematical consistency is not experimental validation.

## Opportunity intelligence and transition portfolio

PRE and related capture work support:

- official-source opportunity tracking;
- requirement extraction and Requirement Delta Records;
- partner screening;
- gap-to-demo analysis;
- evidence targets;
- transition/readiness planning.

Opportunity documents are dated analytical artifacts. Program status, deadlines, eligibility and solicitation requirements must be reverified against official sources before external use.

## Repository topology: now vs later

`Sara_pro` currently serves as the **Worldshepherd umbrella/incubator repository**. That is intentional until individual families meet split criteria.

Candidate future repositories:

| Candidate | Intended boundary | Split only when… |
|---|---|---|
| `worldshepherd-sara` | canonical SARA runtime, governance and release evidence | independent history/provenance, CI, security, docs, release identity and migration bridge are preserved |
| `worldshepherd-pre` | requirements intelligence / qualification engine | source-to-RDR tooling, schemas, tests and analyst-review metrics are independently reproducible |
| `worldshepherd-provenance` | ECHO/evidence custody and attestation tooling | trust model, storage/anchor interfaces, tests and failure semantics are explicit |
| `worldshepherd-labs` | simulations, numerical research and reproducible experiments | research assets have executable environments, declared assumptions and maturity metadata |
| `worldshepherd-hardware` | configuration-controlled hardware/BOM/test packages | physical configurations, BOMs, test procedures, measured evidence and export/public-release boundaries are mature enough to stand alone |
| `worldshepherd-docs` | public architecture/governance/roadmaps | canonical docs can be versioned without severing evidence links to implementation repos |

A repository name is not a maturity claim. Splitting is an information-architecture action, not evidence promotion.

## Branches are not products

The repository retains a large development history with active, merged, superseded, experimental and evidence-bearing branches. Branch presence must never be interpreted as current capability.

Branch lifecycle and deletion safeguards are defined in [`docs/BRANCH_GOVERNANCE.md`](docs/BRANCH_GOVERNANCE.md). The governing rule is simple:

> **Never delete a branch merely because its name looks old, duplicated or temporary. First prove that its unique commits/evidence are merged, superseded or deliberately retained elsewhere.**

## How to evaluate a Worldshepherd claim

For any capability, follow this chain:

```text
public statement
    ↓
claim state
    ↓
canonical code / model / configuration
    ↓
test or experiment definition
    ↓
result + uncertainty / failure evidence
    ↓
provenance / commit identity
    ↓
human review
```

If the chain breaks, lower the claim rather than filling the gap with inference.

## Where to go next

- **Run SARA:** [`runtime/README.md`](runtime/README.md)
- **See capability maturity:** [`docs/WORLDSHEPHERD_CAPABILITY_MAP.md`](docs/WORLDSHEPHERD_CAPABILITY_MAP.md)
- **Understand evidence rules:** [`docs/CLAIMS_AND_EVIDENCE_POLICY.md`](docs/CLAIMS_AND_EVIDENCE_POLICY.md)
- **Browse technical documentation:** [`docs/README.md`](docs/README.md)
- **Understand repository/branch lifecycle:** [`docs/BRANCH_GOVERNANCE.md`](docs/BRANCH_GOVERNANCE.md)
- **Contribute:** [`CONTRIBUTING.md`](CONTRIBUTING.md)
- **Security boundary:** [`SECURITY.md`](SECURITY.md)

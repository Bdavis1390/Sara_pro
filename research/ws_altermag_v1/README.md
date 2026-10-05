# WS-ALTERMAG v1.0-rc0

Status: `IMPLEMENTED IN SOFTWARE` for the bounded tests that pass.

Physical status: `SIMULATED ONLY / REQUIRES LAB VALIDATION`.

This node is the first bounded implementation of the Worldshepherd Physical Compiler / Physical Decompiler contract for altermagnet research.

It begins with a deterministic synthetic benchmark, then adds a literature-reference adapter before any DFT, transport, or laboratory backend is attached.

## B000-S — synthetic truth recovery

B000-S uses a B1g-like g-wave angular basis,

`sin(theta)^3 * cos(theta) * sin(3*phi)`,

as a literature-informed symmetry reference. The hidden amplitude and relaxation parameter in the manifest are synthetic test values and are **not** experimental CrSb material constants.

The benchmark executes:

`manifest -> state -> synthetic forward model -> noisy observations -> inverse recovery -> H0/H1 discrimination -> uncertainty/identifiability -> claims gate -> provenance digest`

The alternative hypotheses are:

- H0: relaxation/background response only;
- H1: altermagnetic-like angular contribution plus relaxation.

## B000-R — bounded literature-reference adapter

B000-R encodes only explicitly reported textual observables from:

Long et al., *Nature* 656, 854-860 (2026), DOI `10.1038/s41586-026-10902-z`.

The current adapter checks:

- `B1g` / `Y_4^-3` symmetry metadata;
- nodal planes at azimuthal `phi = 0, 60, 120 deg`;
- the basal nodal plane at `theta = 90 deg`;
- internal consistency of the reported representative frequency pair `3.41 kT` and `3.82 kT`, giving `0.41 kT` splitting at the stated orientation.

This is **not yet a raw-data reproduction**. It is a versioned reference contract that keeps the software aligned with the published symmetry and selected textual observables.

## Run

From repository root:

```bash
python -m research.ws_altermag_v1.benchmark_b000
python -m research.ws_altermag_v1.reference_b000
python -m pytest -q research/ws_altermag_v1/test_end_to_end.py
```


## B000-DATA — official source-data extraction

The Cambridge Apollo dataset for the CrSb paper is open under CC BY 4.0 and is pinned by repository DOI, archive SHA-256, and member SHA-256. The analyzer downloads or accepts the official archive, verifies its content hash, opens `fig4b.csv`, and extracts the two dominant >3 kT quantum-oscillation peaks without storing the 8.8 MB archive in this repository.

On the 2026-10-05 Lenovo execution, the 0.4-series spectrum produced `3.4175 kT` and `3.8199 kT`, a split of `0.4024 kT`. Across the six source spectra the mean extracted splitting was `0.4096 kT` (range `0.4023-0.4172 kT`), consistent with the paper's reported approximately `0.41 kT` split.

The complete bounded evidence summary is stored in `evidence/b000_data_2026-10-05.json`.

Run against the pinned official archive with:

```bash
python -m research.ws_altermag_v1.source_data_b000 \
  --fetch-to /tmp/CrSb_QOs_Repository.zip \
  --output /tmp/b000_data_evidence.json
```

This advances the software/data pipeline beyond manually encoded reference points, but it remains a re-analysis of published source data, **not an independent laboratory replication**.


## B000-DATA-INTEGRITY — fail-closed source audit

Before using the Fig. 2 panel exports for nodal-versus-antinodal validation, the pinned archive was audited byte-for-byte. The audit found that `fig2b.csv` and `fig2f.csv` are identical files, while `fig2c.csv`/`fig2g.csv` and `fig2d.csv`/`fig2h.csv` have different headers but identical data bodies.

Because the corresponding Fig. 2 panels represent different nodal and antinodal contexts in the paper, WS-ALTERMAG does **not** treat these duplicated bodies as independent validation datasets. The automated Fig. 2 comparison is therefore placed in `BLOCKED_SOURCE_DATA_AMBIGUITY` rather than forcing a positive result.

This is a repository-level byte observation only. The implementation makes no claim about why the duplication exists and does not attribute an error to the authors. See `evidence/b000_data_integrity_2026-10-05.json`.


## B000-ANGULAR — Fig. 3 node/split/node recovery

To avoid the ambiguous Fig. 2 panel pairs, the next gate uses the unambiguous Fig. 3 tilted-plane exports. The analyzer pins both the DFT dogbone profile (`fig3b.csv`) and experimental FFT spectra (`fig3d.csv`) by SHA-256, then uses the paper's angular geometry to align the exported DFT coordinate with the measured rotation series.

The branch association is explicitly **theory-guided**: local experimental FFT peaks are matched to the nearest predicted dogbone branches within a predeclared tolerance. Under that contract:

- at `alpha = -60 deg`, the predicted split is `0.0076 kT` and both branches map to the same observed `3.2210 kT` peak;
- at `alpha = 0 deg`, the predicted split is `0.0026 kT` and both branches map to the same observed `3.3951 kT` peak;
- nine off-node orientations satisfy the branch-match and minimum-splitting gates;
- predicted versus observed off-node splitting has correlation `r = 0.8614`.

The bounded B000-ANGULAR gate therefore passes. This is stronger than a manually encoded literature check, but because DFT is used to identify the experimental branches it remains a theory-guided source-data re-analysis rather than an independent experimental replication.

Evidence: `evidence/b000_angular_2026-10-05.json`.


## B000-DFT — first-principles reproduction contract

The first-principles gate is now defined but deliberately not executed. The reference lane captures the paper-native methodology: WIEN2k FP-LAPW, GGA, a `43 x 43 x 28` k-mesh, lattice parameters `a=b=4.12 A`, `c=5.47 A`, opposite initial Cr spin polarizations, SKEAF Fermi-surface frequency extraction, and the paper's stated dogbone/web energy alignments of `-0.11 eV` and `+0.015 eV`.

The contract also requires content hashes for the input structure and solver binary, verified atomic positions, solver/version capture, convergence checks, and resource clearance before execution. Current execution status is `PROPOSED_NOT_EXECUTED` because a Palace solver workload remains active on the Lenovo host.

The validator passes the **contract**, not the physics. No first-principles CrSb result is presently claimed.


## B000-STRUCTURE and backend staging

The CrSb input structure is now explicit and machine-validated rather than implicit. It uses the NiAs-type parent structure with Cr on Wyckoff 2a and Sb on 2c, lattice parameters `a=b=4.12 A`, `c=5.47 A`, and opposite initial Cr spin signs. The structure validator checks stoichiometry, fractional positions, magnetic compensation, parent symmetry and the reduced magnetic model.

For the independent open-method cross-check, Elk was selected because it is an all-electron full-potential LAPW code, making it closer to the paper-native WIEN2k methodology than a pseudopotential code. The Ubuntu 22.04 package candidate `elk-lapw 7.2.42-2` has been downloaded and extracted into temporary staging without installation or solver execution. The package, extracted binary and Cr/Sb species files are all SHA-256 pinned.

A fail-closed Elk input-template generator now renders the CrSb geometry, PBE GGA (`xctype=20`), spin-polarized initialization and `43 x 43 x 28` k-grid. It refuses to write a file literally named `elk.in` before the execution gate is cleared. The staged template SHA-256 is `981a11b818e85f6069b0f3707d098f2ee655f5bd6fa2bf90278b728ca9bf0402`.

The extracted binary is not yet runnable in isolation because its system runtime dependencies include `libxc.so.9` and `libmpi_mpifh.so.40`. Those dependencies will be installed only after the active Palace workload clears. The backend is staged under `/var/tmp`, avoiding the nearly full home filesystem.

Evidence: `evidence/b000_backend_staging_2026-10-05.json`.


## B000-CONVERGENCE and execution guard

The DFT path now has a machine-enforced execution guard rather than a prose-only warning. The guard checks competing Palace processes, work-root free space, the pinned Elk binary hash and dynamic runtime completeness before it can return execution clearance.

On the 2026-10-05 Lenovo check, the backend hash matched and `/var/tmp` had about `13.68 GiB` free, but the gate correctly returned `BLOCK_DFT_EXECUTION` because Palace remains active and the staged Elk binary still lacks `libxc.so.9` and `libmpi_mpifh.so.40`.

The predeclared convergence plan contains eight non-executed cases: three `rgkmax` basis checks at fixed `12 x 12 x 8`, four k-grid checks up through `24 x 24 x 16`, and the paper-matched `43 x 43 x 28` reference case. The initial reference `rgkmax=8.0` is not treated as validated; it may proceed only if the basis-convergence gate accepts it.

Active scratch remains targeted at `/var/tmp`. The attached 15 GB USB currently has about 12 GB free and is writable, so the storage policy is to archive completed evidence/results there instead of increasing pressure on the nearly full `/home` filesystem.

Evidence: `evidence/b000_execution_gate_2026-10-05.json`.

## Claim boundary

A passing B000-S test supports only the bounded claim that the software can recover the known hidden state of its deterministic synthetic benchmark and can fail closed against physical claim promotion.

A passing B000-R test supports only that the encoded literature reference is internally consistent with the implemented analytic symmetry basis and selected reported observables.

Neither establishes:

- independent reproduction of the CrSb experiment;
- CrSb physical performance beyond the cited literature;
- experimental altermagnetic switching by Worldshepherd;
- a fabricated Worldshepherd material or device;
- laboratory validation;
- partner validation;
- production readiness.

Those remain evidence-gated by `docs/CLAIMS_AND_EVIDENCE_POLICY.md`.

## Next gate

B000-ANGULAR now supplies the unambiguous node/split/node source-data path. Keep the separate Fig. 2 ambiguity open for provenance, then prepare the first-principles backend contract. Actual DFT execution remains deferred while the active Palace run is consuming Lenovo solver resources.

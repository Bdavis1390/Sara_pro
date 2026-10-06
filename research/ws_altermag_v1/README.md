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


## B000-STARTUP-SANITY — user-space runtime reaches Elk parser

Without installing packages system-wide and without providing an `elk.in`, the staged Elk runtime was extended with content-pinned OpenMPI/PMIx and supporting libraries under `/var/tmp`. A bounded five-second startup harness verified the exact Elk binary hash, launched it in an empty temporary directory and required it to reach the input parser.

Observed stdout:

`Elk code version 7.2.42 started`

followed by the expected controlled stop:

`Error(readinput): error opening elk.in`

No `INFO.OUT` was created, no SCF task was supplied and no DFT work was performed. Optional OpenMPI transport plugins still emit warnings for unavailable network fabrics, but they do not prevent the local zero-input initialization path from reaching Elk itself.

The gate is therefore `STARTUP_SANITY_PASS`, **not** a physics pass. Evidence: `evidence/b000_startup_sanity_2026-10-05.json`.


## B000-FIRST-CASE — fail-closed execution handoff

The first executable convergence case is now wired as `12 x 12 x 8` with `rgkmax=6.0`. The runner resolves the staged species path, fixes BLAS/OpenMP thread counts to one, re-runs the backend/hash/runtime/storage/process gates, and will create a real `elk.in` only after every gate clears.

The current Lenovo test returned exit code `3` with `BLOCK_DFT_EXECUTION` because Palace remains active. The runner created **no `elk.in`** and started **no DFT calculation**. This proves the handoff is fail-closed rather than relying on operator memory.

Once Palace clears, the same runner can be invoked first without `--execute` to obtain `READY_BUT_NOT_EXECUTED`; only an explicit `--execute` will create and launch the first convergence case.

Evidence: `evidence/b000_first_case_guard_2026-10-05.json`.


## B000-OUTPUT — evidence extraction before interpretation

The Elk output path is now prepared before any SCF run. The parser consumes `INFO.OUT` plus the dedicated `TOTENERGY.OUT`, `DTOTENERGY.OUT`, `MOMENT.OUT` and `MOMENTM.OUT` streams and hashes every file it summarizes. It also extracts the final `Moments:` block from `INFO.OUT`, including per-species/per-atom muffin-tin moments, so the two Cr local-moment magnitudes can be carried into convergence testing.

The parser deliberately keeps extraction separate from interpretation: a value can be parsed without being accepted as converged. `convergence_eval.py` compares adjacent numerical settings and converts total-energy changes from Hartree per four-atom CrSb cell to meV/atom. Advancement requires **both** the predeclared energy threshold and the Cr local-moment threshold; missing moment evidence produces `HOLD`, not a pass.

This removes another manual handoff from the future `rgkmax=6 -> 7 -> 8` progression.


## B000-OFFLOAD — verified removable-media copy

The staged Elk runtime, pinned CrSb source-data archive and local B000 evidence receipts are now copied to the attached USB under `Worldshepherd-WS-ALTERMAG/`. Because the USB is VFAT and cannot preserve the runtime's symbolic links directly, the backend tree is stored in an uncompressed tar container rather than as a flattened copy.

The backend archive SHA-256 is:

`3eceda20726e1819988aa2652a01ea8ba3168bec31edcc4a9f30c11b2b4e59d0`

The copied CrSb source-data archive retains its original pinned SHA-256:

`2e7c2e4658f151b7b52dd57df24f24fcb5a5cc2ce5d6bc07c62dbc1d66111d79`

Both primary files and all six local evidence JSON files were verified from checksum manifests on the USB. This is storage/provenance protection only and carries no physics claim.


## B000-SEQUENCE — automated basis-gate progression

The basis-convergence series is now a state machine rather than an operator checklist. `sequence_b000.py` enforces the ordered cases `rgkmax=6 -> 7 -> 8` at fixed `12 x 12 x 8`, refuses to skip an invalid prior run, requires the SCF energy target and exactly two Cr local-moment magnitudes, and evaluates the final `7 -> 8` adjacent pair against the declared energy and moment thresholds.

The coarse `6 -> 7` comparison is retained as trend evidence but is not allowed to veto an otherwise converged `7 -> 8` pair. A basis pass therefore means only that the highest-resolution adjacent pair satisfies the numerical convergence contract; it is not a physical-validation claim.

Current unit coverage verifies start-of-sequence, fail-closed invalid prior cases, convergence at the highest-resolution pair, and HOLD behavior when the final pair fails.


## B000-FERMI / B000-QO — post-SCF export is now gated

The post-SCF Fermi-surface path is now explicit. After the numerical basis and k-grid gates pass, Elk task `102` is the selected spin-resolved BXSF export path. In a collinear spin-polarized run the contract expects both `FERMISURF_UP.bxsf` and `FERMISURF_DN.bxsf`, and requires hashes for the converged `STATE.OUT` and both exported surfaces before any orbit analysis can begin.

The initial BXSF grid is `43 x 43 x 28` as a reproducibility checkpoint only. It is **not** declared quantum-oscillation converged; the orbit-extraction grid requires its own convergence study.

For the orbit extractor, two lanes are preserved:

- the paper-native SKEAF v1.3.0 r149 lane remains unpinned because the legacy WIEN2k download endpoint could not be retrieved with normal TLS verification; certificate verification was not bypassed;
- PAOFLOW 3.0.0 / `PAOFLOW.pyskeaf` is staged as an open cross-check. Its wheel SHA-256 is `27e4dbc1ae4528c769be8f0cb868d632ff525246e87e2c0a53522ccc184add8e`.

A compatibility gate is necessary: PAOFLOW 3.0.0's PySKEAF reader requires **single-band** BXSF input, whereas Elk task 102 can place multiple Fermi-crossing bands in one spin-resolved BXSF. PySKEAF 3.0.0 treats the periodic-corner equality symptom as a warning rather than a hard rejection, so the hard blocker is band splitting; reciprocal-vector units and periodic endpoint handling are additional validation requirements. Direct `Elk task 102 -> PySKEAF` execution remains blocked until a validated adapter exists.

Current QO decision: `BLOCK_QO_EXTRACTION`.


## B000-BXSF-ADAPTER — synthetic compatibility gate passed

The Elk-to-SKEAF adapter is now implemented and tested on a synthetic task-102-style two-band periodic BXSF. The transformation is explicit and provenance-visible: split to one band per file, remove Elk's duplicated periodic endpoint on each axis, convert Hartree energies to Rydberg by multiplying by two, and remove Elk's reciprocal-lattice `2*pi` factor before presenting the vectors to the SKEAF-compatible reader.

The adapted outputs were then read by the **actual pinned PAOFLOW 3.0.0 PySKEAF reader** directly from wheel SHA-256 `27e4dbc1ae4528c769be8f0cb868d632ff525246e87e2c0a53522ccc184add8e`. Both synthetic band files were accepted as `2 x 2 x 2` single-band grids.

This advances the adapter to `IMPLEMENTED_SYNTHETICALLY_VALIDATED`, but QO extraction remains blocked until a real Elk CrSb task-102 export is transformed and validated. Evidence: `evidence/b000_bxsf_adapter_2026-10-05.json` and `evidence/b000_qo_unit_contract_2026-10-05.json`.


## B000-QO-ANGLES — crystal-frame directions are reproducible

The published tilted-plane geometry is now encoded directly rather than approximated from figure axes. For sample-platform tilt `14 deg`, the mapper uses

`cos(theta) = sin(14 deg) sin(alpha)`

and the quadrant-safe form

`phi = atan2(cos(14 deg) sin(alpha), cos(alpha))`.

As a cross-check, `alpha=22 deg` maps to `theta=84.8004 deg`, `phi=21.4064 deg`, reproducing the paper's reported `84.8 deg / 21.4 deg` orientation within 0.01 degree. The twelve deposited Fig. 3 alpha orientations are now precomputed for the future orbit-extraction stage.

## B000-BAND-ALIGNMENT — raw and paper-aligned lanes stay separate

The paper's empirical Fermi-level alignment is now a named transform rather than an implicit modification of the DFT result. The contract records `-0.11 eV` for the dogbone hole sheets and `+0.015 eV` for the web electron sheets. The transform operates only on already split single-band BXSFs, writes a new aligned artifact, and refuses to overwrite the raw band file.

Automatic sheet classification remains disabled: a band must first be explicitly identified as `dogbone_hole` or `web_electron` before the corresponding shift may be applied. Raw and aligned quantum-oscillation results must both remain reportable, because the aligned lane is an empirical comparison aid rather than an ab-initio prediction.


## B000-QO-COMPARE — the experimental comparison target is frozen

The twelve Fig. 3 experimental dogbone branch pairs are now frozen into a content-addressed comparison manifest instead of being re-selected after seeing future Elk results. The target manifest SHA-256 is `4780ad0b69cc9048b5c134a342c897da85365e91315926ec3a734bf8c9e065c2`.

A computed QO result must provide two explicitly classified dogbone frequencies at every one of the twelve alpha orientations. The comparator is permutation-insensitive within each pair, but it does not perform automatic orbit classification. Missing angles, duplicate angles or invalid classifications fail closed.

The engineering comparison requires full twelve-angle coverage, both symmetry-node splittings <= `0.05 kT`, split-pattern correlation >= `0.80`, and overall matched-pair MAE <= `0.20 kT`. These thresholds are Worldshepherd reproduction gates, not uncertainty bars reported by the experiment.

A perfect frozen-target fixture returns `QO_REFERENCE_MATCH`; missing-angle and broken-node controls return `HOLD`. Raw and empirically band-aligned calculations must be evaluated as separate lanes.


## B000-ORBIT-SELECTION — no frequency-proximity shortcut

The PySKEAF output format is now parsed into theta/phi writer fields, frequency, effective mass, curvature, orbit type and copy count without assigning a physical sheet identity. A separate orbit-selection manifest begins deliberately empty and blocks dogbone comparison until real Elk bands are explicitly assigned by spin, band ID, classification basis and source BXSF hash.

This prevents an easy but invalid shortcut: choosing whichever computed orbit happens to lie nearest the experimental frequency and then calling it the dogbone. Orbit identity must be established from the calculated Fermi-surface topology before the frequency comparison is allowed.

## B000-FIRST-CASE evidence handoff

The first-case runner now performs its own bounded post-run evidence extraction. After Elk exits it hashes the outputs, writes a case summary, extracts energy and Cr local-moment evidence, and evaluates whether the result is usable by the convergence sequencer. Timeout, non-zero exit, missing SCF energy convergence, missing total energy or missing two-Cr local-moment evidence all produce `CASE_HOLD`.

This means the future first real calculation can no longer silently advance merely because the Elk process returned successfully.


## B000-HOST-CAPACITY — memory is now an explicit execution gate

The first-principles handoff now requires at least `1.0 GiB` of `MemAvailable` and `1.0 GiB` of free swap in addition to the existing Palace/process, storage, backend-hash, runtime and startup-sanity gates. These are Worldshepherd host-safety thresholds rather than material-model parameters.

The latest Lenovo snapshot reports only `0.271 GiB` available memory while the two-rank Palace recovery calculation is active, so the current decision remains `BLOCK_DFT_EXECUTION` even independently of the Palace process-name gate. This avoids assuming that a transient process exit alone makes the two-core, 3.6-GiB host safe for Elk.

Evidence: `evidence/b000_host_capacity_2026-10-05.json`.

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

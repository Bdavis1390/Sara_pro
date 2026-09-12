# WS-QPHONON L3 Partner Validation Experiment

**Purpose:** define the minimum external-hardware campaign required to promote WS-QPHONON from L2 architecture/R&D to L3 validated Worldshepherd capability.

This document is an experiment plan, not evidence that the experiment has occurred.

## Role split

### Partner laboratory supplies

- real quantum hardware based on an agreed SiV or SnV platform;
- cryogenic environment and calibrated thermometry;
- optical initialization/readout chain;
- RF/acoustic drive and measurement chain;
- phononic/mechanical resonator or equivalent agreed interface;
- device-specific safety and operating limits;
- raw measurement access sufficient for independent analysis;
- a qualified human operator who can reproduce the procedure.

### Worldshepherd supplies

- SARA experiment orchestration;
- PRIME authorization screening;
- ECHO evidence/provenance records;
- OVERWATCH drift and envelope monitoring;
- calibrated model/twin versioning;
- Bayesian parameter-estimation workflow;
- holdout prediction protocol;
- claims-state enforcement.

Worldshepherd does not require control of partner safety systems and must not bypass local laboratory interlocks.

## Phase 0 — interface and safety qualification

Required before any autonomous or semi-autonomous experiment request is executable.

Inputs:

- partner-defined actuator limits;
- thermal limits;
- laser/RF/acoustic power limits;
- emergency-stop/interlock state;
- allowed experiment classes;
- required human-approval classes.

Pass condition:

```text
all hardware actions map to a partner-approved interface
PRIME cannot exceed the partner envelope
partner local interlocks remain authoritative
```

Failure disposition: **NO HARDWARE EXECUTION**.

## Phase 1 — characterization only

Measure or independently constrain:

- spin transition frequency;
- mechanical resonance and intrinsic/effective linewidths;
- T1 and T2/T2*;
- acoustic Rabi response;
- device temperature and thermal occupation;
- drive-induced heating;
- observable out-of-manifold leakage;
- relevant detuning/drift statistics.

No coherent-transfer claim is permitted in Phase 1.

Pass condition:

- configured confidence gates satisfied;
- model discrepancy is bounded on calibration data;
- uncertainty intervals are preserved in ECHO.

## Phase 2 — holdout prediction

Before collecting the designated holdout trace, Worldshepherd freezes:

- model version;
- posterior parameter state;
- predicted observable;
- confidence/credible interval;
- experiment settings;
- pass/fail criterion.

The partner then executes the holdout experiment without refitting beforehand.

Minimum pass condition:

```text
observed holdout result falls inside the precommitted validation interval
and no PRIME or partner safety limit is violated
```

A failed holdout does not get retroactively relabeled as a pass after model refitting. The model may be improved, versioned, and tested against a new holdout.

## Phase 3 — governed intervention

Worldshepherd may propose one bounded control action or pulse family only after Phases 0–2 pass.

Examples:

- resonance retuning;
- bounded acoustic-drive adjustment;
- selection among pre-approved FAST/STIRAP/STA policy families;
- next-measurement selection for calibration.

Required controls:

- PRIME authorization record;
- partner hardware-envelope check;
- human approval where required;
- complete commanded-versus-measured actuator record;
- automatic fallback to CHARACTERIZE when drift/model discrepancy exceeds limits.

Pass condition:

```text
Worldshepherd proposal is executed within the approved envelope
measurement outcome is reproducible
provenance is complete
```

## Phase 4 — reproducibility

The qualified partner operator repeats the accepted procedure from the frozen evidence package.

Required result:

- same qualitative physical outcome;
- quantitative result within the predeclared reproducibility tolerance;
- independent record of hardware state and environmental conditions.

This phase is mandatory for L3.

## L3 promotion checklist

All boxes must be satisfied:

- [ ] real external quantum hardware used;
- [ ] partner safety envelope captured;
- [ ] Worldshepherd SARA/PRIME/ECHO/OVERWATCH participated;
- [ ] parameter-confidence gates passed;
- [ ] model holdout validation passed;
- [ ] at least one governed intervention was physically executed;
- [ ] result was reproducible;
- [ ] uncertainty bounds were reported;
- [ ] raw-data hashes and model versions were preserved;
- [ ] independent partner/human reproduced the result;
- [ ] claims ledger was updated without overstating the result.

## Minimum evidence packet

```text
campaign_id
partner_lab
hardware_identifier
hardware_configuration_hash
raw_data_hashes
instrument_calibration_references
model_version
config_version
prior
posterior
holdout_prediction
holdout_acceptance_interval
prime_decisions
partner_approvals
control_commands
measured_actuator_response
environmental_state
drift_state
measurement_results
model_discrepancy
reproduction_run
claims_state
```

## Promotion language

If the campaign passes, permitted wording should remain narrow, for example:

> Worldshepherd's governed experiment-control layer was used on partner quantum hardware to perform and reproduce the validated experiment described in campaign `<id>` under the documented operating envelope.

The result does **not** automatically justify claims of a Worldshepherd quantum computer, quantum network, fault tolerance, or general quantum advantage.

## Failure policy

Any of the following blocks L3 promotion:

- holdout prediction failure not subsequently revalidated on a fresh holdout;
- missing raw data or provenance;
- safety-envelope violation;
- irreproducible result;
- material unexplained model discrepancy;
- claimed performance requiring post-hoc exclusion of failed runs without a predeclared rule;
- partner inability to reproduce the accepted procedure.

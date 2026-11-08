# RF measurement gate — WorldShepherd WS-D14 (public, nonproprietary)

This is a **data-only validator**, not a radio transmitter, VNA driver, or proof of a new interaction.

The accompanying executable `rf_measurement_gate.py` enforces an acquisition schema and evaluates interaction terms for low-power, shielded/terminated bench observations once **real** calibrated measurements have been acquired.

## Input CSV contract

Required columns, exactly one record per run, pair, sample and condition:

`experiment_id,pair_id,replicate_id,sample_type,condition,output_frequency_hz,output_power_dbm,uncertainty_db,instrument_id,calibration_id,timestamp_utc,data_origin`

- `sample_type`: CANDIDATE or BLANK.
- `condition`: OFF, A, B, AB (all four mandatory for both sample types).
- `pair_id`: prospective pair identifier; at least one independent SHAM output-frequency control is mandatory.
- `replicate_id`: truly independent acquisition session (not duplicate instrument sweeps presented as independent).
- `calibration_id`: identifier starting `CAL-`; actual calibration certificate must be separately verified.
- `data_origin`: `SYNTHETIC_TEST` or `MEASURED_UNVERIFIED`. Mixing both types in one CSV is rejected.
- Output power is dBm and measurement uncertainty is dB. Conversions to W are explicit. Values must fit instrument's physical calibration and dynamic range. Bandwidth, phase, cable loss, environmental effects and full power balance are not validated by this CSV alone.

For each run and frequency, compute in **watts**:

`D_sample = P_AB,s - P_A,s - P_B,s + P_OFF,s`

`D_blank = P_AB,b - P_A,b - P_B,b + P_OFF,b`

`D_interaction = D_sample - D_blank`

The pipeline applies exact paired sign-flip enumeration with 3–16 independent runs (a null-symmetry assumption), then Holm correction across *all tested outputs*. The smallest attainable two-sided p-value with 3 runs is 0.25, so three repeats cannot establish a 5% sign-flip result. Even statistically significant interaction is **not proof of new physics**: ordinary intermodulation, mixer compression, amplifier spurs and nonlinear materials are expected to produce mixing. The discovery gate always remains blocked.

## Evidence chain / missing data

The CSV hash is calculated. Individual raw analyzer trace files and certificates have not been authenticated by this utility; add their measured original files, trace hashes, signed calibration records, complex S-parameters, environmental data, and a closed input/reflected/transmitted/radiated/dissipated power budget to the experiment vault before making an experimental claim.

Use a qualified RF lab, appropriate shielding and terminated instrument paths; this project does **not** authorize high-power or unlicensed transmission.

## Execution / offline regression tests

`python3 rf_measurement_gate.py --csv /path/to/your_measurement_matrix.csv --out /path/to/evaluation.json`

`python3 -m unittest -v test_rf_measurement_gate`

The tests generate explicitly labeled synthetic negative controls and known nonlinear mixing. Their purpose is to prove that the gate can detect and reject artifacts, **never** to imply that WorldShepherd has measured new effects.

The historical resonance hypotheses remain unverified until instrument data are supplied and independently reproduced. This gate protects their evidentiary status and original source controls.

**No actual RF measurements have been conducted by this software.**

# Worldshepherd Applied Work Accounting v1

## Purpose

Worldshepherd must not treat "work" as one universal scalar.

The useful unit depends on the task and the question being asked. Examples include:

- compute operations completed;
- electrical energy consumed to produce that compute;
- accelerator-hours or machine-hours committed;
- wall-clock duration;
- labor-hours;
- bytes processed or transferred;
- material mass consumed;
- dollars spent;
- units/parts/decisions produced;
- emissions associated with the work; and
- quality or success measures.

Those quantities are related, but they are not interchangeable.

## Core rule

**Preserve work as a vector of dimensioned quantities.**

A ledger may contain, for the same activity:

```text
compute:          20 Top          [floating_point_operation]
energy:            4 kWh          [electrical_input_energy]
resource-time:     2 resource-h   [H100_GPU]
wall-clock:        1 h            [elapsed_time]
data:             80 GB           [input_dataset]
output:          500 count        [accepted_result]
```

There is no automatic `total_work` across those entries.

## Same-kind conversion vs transformation

A same-kind/same-basis unit conversion changes only the representation of the same quantity.

Example:

`1 kWh = 3.6 MJ = 3.6e6 J`

That is a unit conversion inside the energy quantity kind. NIST SP 811 lists the same kWh-to-joule relation.

A compute-to-energy relation is different. For example:

`0.25 kWh / Top`

is an observed or modeled **intensity**, not a physical unit identity. It is valid only for the hardware, workload, operating conditions, measurement boundary, and evidence class that produced it.

The same caution applies even when the quantity kind is identical but the semantic basis differs. For example, `resource-h [H100_GPU]` and `resource-h [CPU_core]` are both resource-time, but any equivalence between them is workload-dependent and must be represented by an explicit benchmark/model rather than unit conversion.

Worldshepherd therefore requires an explicit `CrossKindModel` for relations such as:

- compute -> energy;
- energy -> cost;
- energy -> emissions;
- resource-time [H100_GPU] -> resource-time [CPU_core];
- resource-time -> compute;
- compute -> output;
- labor-time -> output;
- mass -> produced parts; or
- data processed -> compute required.

## Provenance requirements

Every native quantity requires:

- a unique quantity ID;
- quantity kind;
- value;
- unit;
- semantic basis;
- provenance source; and
- evidence class.

Every transformation model requires:

- model ID and version;
- input quantity kind, unit, and semantic basis;
- output quantity kind, unit, and semantic basis;
- an explicit output-per-input rate;
- provenance;
- evidence class;
- assumptions and operating conditions when applicable; and
- uncertainty when known.

A derived quantity inherits the weaker evidence class of its input and transformation model.

## Uncertainty rule

Worldshepherd must not make precision appear stronger as work is transformed.

The reference implementation conservatively carries uncertainty forward:

- input uncertainty is transformed into the output unit;
- model-rate uncertainty is added to transformed input uncertainty rather than assumed independent; and
- ratio/intensity uncertainty is reported separately from the ratio itself.

This is intentionally conservative. More sophisticated statistical propagation may be added later only when the covariance/independence assumptions are explicit and evidenced.

## Semantic-basis rule

Units alone are not enough.

`1 Top` of floating-point operations and `1 Top` of integer operations are both operation counts, but they are not assumed to have the same energetic or performance implications. A transformation calibrated for one basis cannot be applied to the other without an explicit compatible model.

Similarly:

- `resource-h [H100_GPU]` is not the same as `resource-h [CPU_core]`;
- `person-h [technician]` is not the same as `h [elapsed_time]`;
- `count [accepted_part]` is not the same as `count [model_token]`.

## Evidence classes

The reference implementation currently recognizes:

1. `ASSUMPTION`
2. `ESTIMATED`
3. `SIMULATED`
4. `BENCHMARKED`
5. `MEASURED`

Derived work may not inherit a stronger evidence state than the weakest input/model evidence supporting it.

## Multi-stage lineage

Transformations may be chained, but the chain must remain inspectable. For example:

`compute -> energy -> monetary cost`

may be useful for planning, while:

`compute -> energy -> emissions`

may be useful for environmental accounting.

Each derived quantity keeps a lineage back through the transformation model(s) to the original measured/benchmarked quantities. A weak downstream assumption (for example an estimated tariff or emissions factor) must not upgrade upstream benchmark evidence or be presented as a direct measurement.

## Decision scores

A business or mission decision may choose to normalize several quantities into a score. That score is **not physical work** and must not be represented as if compute, energy, money, time, and output were dimensionally equivalent.

Any future normalized score should therefore record:

- objective;
- normalization method;
- weights;
- reference/baseline values;
- sensitivity analysis; and
- decision authority.

## External standards alignment

This model follows the same general separation used by QUDT between quantities, quantity kinds, units, dimensions, and measurements. QUDT is useful as a vocabulary/ontology reference for later interoperability.

For physical energy conversions, Worldshepherd should prefer recognized metrology references. NIST SP 811 records `1 kWh = 3.6e6 J`.

References:

- NIST Guide to the SI, Appendix B.9: https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b9
- QUDT schema/catalog: https://qudt.org/ and https://www.qudt.org/catalog/qudt-catalog.html

## Claims boundary

Applied Work Accounting v1 is a software/data-governance model. It does not establish that a transformation rate is universally valid, that a benchmark represents production behavior, or that one resource quantity is inherently equivalent in value to another.

The rule is intentionally conservative:

> Keep native quantities native. Convert only within compatible quantity kind/basis pairs. Relate non-equivalent quantities only through explicit, evidence-bearing transformations.

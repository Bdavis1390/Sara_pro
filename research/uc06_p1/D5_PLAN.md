# UC06-P1 D5 Plan

D5 is diagnostic only and does not change any frozen convergence gate.

## Inputs
- D4 capability-attribution receipt
- A001-A018 complete coarse 3x2x3 factorial
- completed A001-A026 prefix only
- active A027-A054 recovery remains untouched

## D5-A: factorial interaction attribution
For PC1-PC3, decompose descriptive sum of squares across the balanced coarse design into:
- state
- polarization
- angle
- state x polarization
- state x angle
- polarization x angle
- state x polarization x angle

The purpose is to resolve the large PC2 variance that was not explained by any single main factor in D4. The decomposition is descriptive, not causal.

## D5-B: sparse operational frequencies
Use the complete coarse spectral manifold to greedily select a small deterministic frequency subset that best preserves all-pair complex-spectrum geometry relative to the full 161-point band.

Report after each selected frequency:
- selected frequency
- pairwise-distance correlation to full-band geometry
- optimally scaled normalized distance stress

Run both:
1. unconstrained greedy selection
2. greedy selection with 0.10 GHz minimum spacing for operational diversity

Then annotate selected frequencies with available validation-aware angle/polarization discriminability from the completed LOW_C medium/coarse pairs and coarse-only TM state separation.

## Claims boundary
- no Shannon information claim
- no causal ANOVA claim
- no hardware observability claim
- sparse-frequency results are same-data descriptive design diagnostics, not held-out generalization
- no H2 promotion
- no full-campaign authorization
- overall convergence remains not adjudicated

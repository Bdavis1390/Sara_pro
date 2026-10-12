# UC06-P1 Capability and Application Matrix

Status: diagnostic only; overall convergence not adjudicated.

## D4 quantitative anchors

- PC1 variance: 53.806054%
- PC2 variance: 43.600085%
- PC3 variance: 2.055207%
- First two PCs: 97.406139%
- First three PCs: 99.461346%
- PC1 dominant main factor: polarization (eta^2 = 0.466763)
- PC2: no strong single main-factor attribution in D4
- PC3 dominant main factor: angle (eta^2 = 0.616291)
- Strongest state separation: coarse TM 60 deg, HIGH_C vs SAFE_OPEN, RMS = 1.060468
- Strongest angle separation: coarse SAFE_OPEN TM 0 vs 60 deg, RMS = 1.836155
- Strongest modeled median polarization isolation: 70.017766 dB (A025)
- Largest state-programmable phase span: 83.953227 deg, coarse TM 30 deg
- Largest TM/TE refinement-sensitivity ratio: 45.585876, LOW_C 60 deg
- Largest validation-aware discriminability: 230.238909, LOW_C TE 0 vs 60 deg

## Current strongest application families

| Tier | Application family | Property used | Current classification |
|---|---|---|---|
| A | Angle/orientation sensing | large TE angular separation with low refinement uncertainty | strong simulation diagnostic |
| A | Polarization discrimination | high modeled co/cross isolation | strong simulation diagnostic |
| A | Reduced-order RF state representation | first 2 PCs explain 97.41%; first 3 explain 99.46% | strong coarse-ensemble diagnostic |
| A | Differential TE/TM metrology | TM refinement sensitivity 32.65x-45.59x TE in LOW_C | strong diagnostic; physical sensitivity unproven |
| B | TM state identification | strong coarse TM state separability | promising; medium/fine validation pending |
| B | Self-verifying actuator | commanded state can be checked through RF response | architecture candidate |
| B | Dual sensing/control polarization channels | TE nearly state-invariant; TM strongly state-sensitive | architecture candidate |
| B | Manifold/open-set anomaly monitoring | nominal spectra occupy low-dimensional manifold | architecture candidate |
| B | Limited phase trim/control | TM phase span about 79-84 deg | supported as limited-range control, not full arbitrary phase |
| C | General beam steering / holography | requires broad spatial phase coverage | redesign + finite array required |
| C | RF fingerprint / PUF | needs repeatability and device-to-device uniqueness | hypothesis |
| C | Wave-domain computing | needs spatially programmable multi-element operator | architecture extension |

## Functional interpretation

Current evidence supports the working architecture:

- TE: stable reference and high-value angular/polarization sensing channel.
- TM: sensitive state/control and model-discrimination channel.
- TE/TM differential: candidate self-referenced metrology channel.
- frequency: spectral fingerprint/inversion dimension.
- state: control/challenge dimension, strongest in TM.
- latent coordinates: compact operational state representation.

## Claims boundary

This file does not claim hardware validation, intrinsic manifold dimension, causal factor attribution, full beam steering, PUF behavior, absorption, topological protection, nonreciprocity, or completed convergence. Frozen medium-to-fine convergence and energy-closure gates remain unchanged and pending.

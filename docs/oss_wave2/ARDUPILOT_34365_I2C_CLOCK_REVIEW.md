# ArduPilot #34365 — STM32H7 type2 I2C clock/timing review

Date: 2026-09-12

Claims state: **SUPPORTED BY SOURCE/COUNTER DERIVATION / REQUIRES LAB VALIDATION / NOT UPSTREAM OWNED**

Upstream issue: `ArduPilot/ardupilot#34365`

## Executive finding

ArduPilot issue #34365 is a strong Worldshepherd hardware-software assurance candidate, but it should not be treated as a one-line patch opportunity.

The current issue presents a coherent source-level explanation for why STM32H7 type2 parts can run I2C1/2/3/5 from PCLK1 while ArduPilot's hardcoded `TIMINGR` constants assume a roughly 32 MHz kernel clock. For SPRacingH7RF, the issue derives approximately 415 kHz from the counter values for a requested 100 kHz bus and, more importantly, a roughly 61.5 ns SCL data-setup delay versus a 250 ns standard-mode minimum.

The reported SCL rate is a counter-only calculation rather than a scope measurement. Filters, synchronization, edge time, and clock stretching can reduce the physical bus frequency. The SCLDEL counter mismatch is more direct, but hardware verification is still required before any flight-critical claim.

## Source/configuration mismatch

The issue identifies a selector-name split in the type2 STM32H7 path:

- the ChibiOS TYPE2 clock-control path writes `STM32_I2C1235SEL`;
- ArduPilot's `stm32h7_type2_mcuconf.h` sets `STM32_I2C123SEL`;
- the `1235` selector therefore falls back to its default, PCLK1;
- frequency-selection branches contain inconsistent use of `STM32_I2C1235SEL` versus `STM32_I2C123SEL`.

For SPRacingH7RF, the issue derives PCLK1 = 130 MHz. The hardcoded H7 timing constant `0x00707CBB`, intended for an approximately 32 MHz kernel clock, then operates under a very different clock assumption.

This is exactly the kind of cross-layer configuration fault Worldshepherd should target: the build is internally self-consistent enough to compile, but the peripheral timing contract can still be wrong because a static register constant is detached from the actual selected kernel clock.

## Relationship to ArduPilot PR #34349

PR #34349 addresses the H730/H723 ADC/PLL3_R clock configuration. Its own description explicitly calls #34365 a separate I2C problem and does not fix it.

That dependency matters because the narrow #34365 repair proposed in the issue assumes PLL3_R is first brought back to the approximately 30–32 MHz range. A patch that selects PLL3_R before that clock state is corrected could simply exchange one invalid timing assumption for another.

## Proposed upstream repair layers

The issue outlines three layers, which should be treated separately.

### Layer 1 — board/family configuration

Set the selector actually consumed by the TYPE2 path, e.g. `STM32_I2C1235SEL`, to the intended PLL3_R source once the PLL3_R frequency is suitable.

### Layer 2 — ChibiOS correctness

Correct the TYPE2 frequency-selection branches to consistently test the `1235` selector and repair the reported copy/paste error in the PLL3_R branch where one I2C clock symbol is duplicated and another omitted.

This belongs as close as possible to ChibiOS upstream so future ArduPilot boards cannot silently inherit the same selector inconsistency.

### Layer 3 — eliminate the hidden timing assumption

The stronger long-term assurance improvement is to stop allowing hardcoded `TIMINGR` values to float independently of the actual kernel clock.

Preferred options, in order of increasing scope:

1. compile-time assertion that the selected I2C kernel clock matches the clock for which the constant was derived;
2. compile-time timing derivation from the configured kernel clock and bus target;
3. runtime derivation only if the clock can legitimately vary at runtime and the peripheral driver contract supports it safely.

A compile-time guard is a particularly attractive first contribution because it converts a silent hardware-timing defect into a deterministic build failure.

## Hardware validation gate

No Worldshepherd flight-critical qualification should occur without hardware evidence.

Minimum validation campaign on SPRacingH7RF:

- probe I2C2 SCL/SDA with a scope or logic analyzer;
- record actual SCL frequency and high/low times at requested 100 kHz;
- measure/setup timing around the internal BMP388 transactions;
- repeat after the PLL3_R/#34349 state used by the proposed fix;
- repeat at any supported 400 kHz setting;
- exercise cold boot, warm reboot, bootloader/application handoff, and peripheral reset;
- verify BMP388 discovery/data stability and any other active devices on affected buses;
- retain firmware commit, bootloader commit, clock configuration, waveform captures, and instrument metadata as ECHO evidence.

Pass criteria must be based on the applicable STM32 and attached-device timing requirements, not merely successful sensor enumeration.

## Worldshepherd contribution shape

The most valuable bounded contribution is not to race the issue author with an unverified code change. It is to provide:

- a compile-time clock/timing consistency guard;
- a deterministic timing calculation test for H7 family variants;
- a hardware evidence checklist and, when hardware is available, waveform-backed validation;
- a ChibiOS upstream delta review so ArduPilot does not permanently carry a private clock-selector workaround.

## Contribution decision

**Classification: PROMOTED SOURCE-REVIEW / HARDWARE-EVIDENCE LANE.**

Implementation remains **REQUIRES LAB VALIDATION** and is coupled to the resolution/state of #34349 and the relevant ChibiOS clock-selector definitions. Worldshepherd should pursue the compile-time invariant and validation framework first, then contribute code only when the clock dependency is resolved and the physical bus is measured.

# GNU Radio #8195 — Signal Source / fxpt_nco frequency quantization review

Upstream target: `gnuradio/gnuradio#8195`

Claims state: **SOURCE-REVIEWED ROOT-CAUSE CANDIDATE / NO MATCHING FIX PR FOUND / REQUIRES NUMERICAL REGRESSION VALIDATION**

## What current main does

`gr-analog/lib/sig_source_impl.cc` stores a `gr::fxpt_nco` and configures frequency with:

```cpp
d_nco.set_freq(2 * GR_M_PI * d_frequency / d_sampling_freq);
```

For sine/cosine output, `work()` delegates directly to the fixed-point NCO, which advances its internal phase on every sample.

`fxpt_nco::set_freq(float angle_rate)` converts the radians-per-sample increment using:

```cpp
d_phase_inc = gr::fxpt::float_to_fixed(angle_rate);
```

and `fxpt::float_to_fixed()` maps angle to an `int32_t` fixed-point phase where pi corresponds to 2^31 units. The conversion truncates to the integer representation.

Therefore the generated frequency is quantized by the 32-bit phase accumulator. This is not the same failure model as repeatedly adding an imprecise floating-point `1/sample_rate` value.

## Reproducing the issue's 1 Hz / 100 MS/s case analytically

For a requested frequency `f` and sample rate `Fs`, the ideal fixed-point phase increment is:

```text
ideal_increment_units = (2*pi*f/Fs) * (2^31/pi)
                      = f * 2^32 / Fs
```

At:

```text
f  = 1 Hz
Fs = 100,000,000 samples/s
```

we get:

```text
ideal_increment_units = 42.94967296
```

Current conversion truncates that to:

```text
phase_increment = 42
```

The corresponding generated frequency is:

```text
effective_f = 42 * Fs / 2^32
            = 0.9778887033462524 Hz
```

which is approximately **-2.21113%** relative error.

That predicts a steadily growing phase difference against an ideal 1 Hz reference even though the integer phase accumulator itself is deterministic and does not accumulate floating-point rounding error sample-by-sample.

## Quantization resolution

One fixed-point phase-increment unit corresponds to:

```text
frequency_quantum = Fs / 2^32
```

At 100 MS/s:

```text
frequency_quantum ~= 0.02328306436538696 Hz
```

Low requested frequencies therefore have large *relative* error even when the absolute quantization step is modest.

The exact threshold of acceptable error is an API/product decision; the source only establishes the mechanism.

## Why simply rounding instead of truncating is incomplete

Changing `float_to_fixed()` or `set_freq()` from truncation to nearest-integer would reduce bias for many values. In the 1 Hz / 100 MS/s example it would select 43 units:

```text
43 * 100,000,000 / 2^32 ~= 1.0011717677 Hz
```

which is far better than 42 units but still quantized.

A global change to `fxpt::float_to_fixed()` could affect phase/frequency behavior throughout GNU Radio, so it should not be proposed as a local Signal Source fix without compatibility analysis.

## Recommended first contribution

### 1. Add deterministic frequency-accuracy regression tests

Test Signal Source at normalized frequencies spanning several orders of magnitude, including:

```text
1 Hz @ 100 MS/s
10 Hz @ 100 MS/s
1 kHz @ 100 MS/s
frequencies exactly representable by the fixed increment
frequencies halfway between representable increments
negative frequencies
runtime frequency changes
```

Measure zero-crossing/phase progression over a sufficiently long synthetic interval without requiring real-time generation of every sample when a lower-cost analytical/test hook can prove the same state progression.

### 2. Test `fxpt_nco` directly

For a requested angle rate, verify:

```text
requested frequency
stored d_phase_inc / get_freq()
effective frequency implied by the fixed increment
```

This separates oscillator quantization from Signal Source scheduling or downstream plotting/decimation effects.

### 3. Agree on an API contract before changing implementation

Maintainers should choose among at least these directions:

- document fixed-point frequency resolution and warn for high relative-error configurations;
- round phase increment rather than truncate, with compatibility review;
- provide a higher-resolution oscillator/phase accumulator for Signal Source;
- automatically choose a higher-resolution path below a defined normalized-frequency threshold;
- add an explicit precision mode so existing deterministic behavior remains available.

## Compatibility constraints

Any production fix should test:

```text
sine/cosine phase continuity
square/triangle/saw behavior, which also call the same NCO step/get_phase path
negative frequency behavior
runtime set_frequency()
runtime set_sampling_freq()
existing exact/near-exact frequencies
performance impact at high throughput
reproducibility across platforms
```

A higher-resolution accumulator can improve low-frequency accuracy but may change the exact sample sequence that existing users rely on, so this is not automatically a bug-fix-only compatibility surface.

## Worldshepherd relevance

For SDR, sensing, phased-array, and metasurface experiments, a source oscillator's actual frequency/phase error must be explicit because downstream calibration can otherwise attribute deterministic generator bias to hardware, channel, or control-loop error.

Worldshepherd should treat this as **measurement-chain truthfulness**: requested oscillator settings and effective generated settings should be distinguishable and testable.

## Recommended status

Promote GNU Radio #8195 to **P1 / SOURCE REVIEW COMPLETE / REGRESSION-FIRST**. The source strongly supports fixed-point increment quantization as the leading mechanism for the reported low-normalized-frequency behavior, but no upstream fix should be claimed until regression measurements reproduce the predicted effective frequency and maintainers select the desired precision/compatibility contract.

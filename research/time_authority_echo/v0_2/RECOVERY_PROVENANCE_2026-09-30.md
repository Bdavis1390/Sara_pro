# TimeAuthority / ECHO v0.2 recovery provenance — 2026-09-30

## Custody anchor

- Original release: `WS_TIME_AUTHORITY_V0_2_RELEASE.zip`
- Original release SHA-256: `168f55ca588d4bfb6189375a313c0775ebe86b5a63160c46607832daa69eb695`
- Original evidence state: IMPLEMENTED IN SOFTWARE / INTERNALLY TESTED / HOSTED-EVIDENCE REPLAYED.
- Original package remains the immutable custody anchor; this Git tree is the source-control replay.

## Post-recovery portability repair

The original hosted replay test used the environment-specific path `/mnt/data/ws_time_xhost_replay_fixture.json`. During clean extraction on 2026-09-30, that test could not locate its fixture outside the original host layout.

The Git replay changes only fixture resolution to `Path(__file__).resolve().parent / 'ws_time_xhost_replay_fixture.json'`. No assertion, timing policy, uncertainty ceiling, or authority rule is weakened. Because this changes the test file bytes, the original SHA-256 list is retained as historical evidence rather than rewritten.

Fresh clean-extraction regression after the portability repair: **37 PASS / 0 FAIL**.

## Claims boundary

This work does not establish NTP/PTP/GNSS/atomic-clock/oscillator certification, trusted timestamp authority, hardware synchronization performance, field safety, regulatory timestamp assurance, or independent validation.

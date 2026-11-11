# WorldShepherd: Modern Web Guidance 1.0 — audit-only rollout

**State:** STAGED ON REVIEW BRANCH; **NOT** installed or executed on a Lenovo system.
**Scope:** browser-facing code only. This is not a Palace solver, SARA runtime, defense, or quantum-research change.
**Authority:** a baseline improvement is accepted only after code review and evidence-backed tests.

## Why this exists

Use Google's [Modern Web Guidance](https://github.com/GoogleChrome/modern-web-guidance) as an external,
reviewable source of modern browser-platform patterns. Its `legacy-scan` is a deterministic
first-pass scanner, not a security audit, compatibility certification, or proof of benefit.
Preserve existing system functionality and the current protected branch.

## Preflight gates

1. Verify a real frontend working tree and record its exact Git commit / backup identity.
   Do not assume that static sample HTML is the deployed dashboard.
2. Confirm a responsive, authorized execution host and enough free disk space for npm cache
   and private audit output. Do **not** restart or kill existing workloads.
3. Use a dedicated frontend subtree. Do **not** point a scanner at `/`, a user home,
   backup archives, or a running Palace workload.
4. Keep provider telemetry disabled: `DISABLE_TELEMETRY=1`. npm may still contact
   its registry to retrieve the package. Do not upload proprietary code or raw findings.
5. Do not enable Origin Trials, volatile single-engine web features, or auto-refactors.

## Read-only baseline scan

From a checkout containing this script, run:

```bash
bash scripts/mwg_readonly_audit.sh /absolute/path/to/frontend
```

The wrapper:
- resolves and guards the target directory;
- records CLI version, Node version, timestamp, and exit status;
- runs `legacy-scan <path> --json` at reduced CPU priority with a 180-second timeout;
- saves private output in `~/.local/state/worldshepherd/mwg/`;
- does not deliberately edit source, install to the project, create commits, run tests,
  deploy software, or alter workloads. `npx` may update its local cache.

If the target app has a compatible coding agent, `npx modern-web-guidance@latest install`
is a **separate**, explicitly reviewed integration step after the audit. The above script
is deliberately not that installation.

## Verification before any change

- Review each rule's `keepWhen` / `dropWhen` criteria and surrounding context.
  False positives and intentional compatibility fallbacks must be filtered.
- Document current browser support target. Unless explicitly changed, use Baseline
  Widely available or a tested progressive enhancement.
- Collect pre-change evidence: browser/version matrix, keyboard/screen-reader behavior,
  WCAG 2.2 AA checks, functional tests, CSP/XSS controls, LCP/INP/CLS, transfer size,
  CPU/memory and error rates.
- Refactor only one bounded component per change; record code diff, guide ID, risk,
  rollback command, and post-change results.
- Do not claim a 55% gain unless a defined metric improves by at least 55% in
  repeatable paired measurements without unacceptable regressions.
- Keep production changes on reviewed branches; no protected-main merge, deployment,
  external disclosure, or solver interruption during audit.

## Laptop connection limitation

GitHub-hosted runners are **not** Lenovo. This branch only stages a reusable audit tool.
Running it on Lenovo still requires an authenticated command channel, or a trusted
operator invoking it locally. Retain preexisting SSH keys, device identities and host
fingerprints. Avoid port forwarding to the public internet and avoid credential resets.

## Primary references

- https://developer.chrome.com/docs/modern-web-guidance/modernization-workflow
- https://github.com/GoogleChrome/modern-web-guidance

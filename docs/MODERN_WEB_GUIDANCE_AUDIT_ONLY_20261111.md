# WorldShepherd: Modern Web Guidance 1.0 — audit-only rollout

**State:** Lenovo GUI v0.8.0 audited; Codex user-level skill installed. The script and documentation remain staged in a draft PR; no GUI production code was edited.
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
3. Confirm Node.js 22 or newer (required by the published 1.0.0 CLI). Use a dedicated frontend subtree. Do **not** point a scanner at `/`, a user home,
   backup archives, or a running Palace workload.
4. The wrapper pins the npm package to `modern-web-guidance@1.0.0` for reproducibility. Keep provider telemetry disabled: `DISABLE_TELEMETRY=1`. npm may still contact
   its registry to retrieve the package. Do not upload proprietary code or raw findings.
5. Do not enable Origin Trials, volatile single-engine web features, or auto-refactors.

## Read-only baseline scan

From a checkout containing this script, run:

```bash
bash scripts/mwg_readonly_audit.sh /absolute/path/to/frontend
```

The wrapper:
- resolves and guards the target directory;
- records CLI version, Node version, timestamp, and exit status (pin: 1.0.0; Node >=22);
- runs `legacy-scan <path> --json` at reduced CPU priority with a 180-second timeout and a bounded termination grace period;
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

## Verified Lenovo execution (2026-11-11, America/New_York)

- Desktop Commander remote session **connected** on Lenovo, agent version 0.3.2.
- Verified Node v22.23.3 and npm v10.9.9.
- Scanned real frontend `/home/sspadawanzz/worldshepherd_gui_v0_8_0/gui` using `modern-web-guidance@1.0.0 legacy-scan ... --json`, with `DISABLE_TELEMETRY=1`.
- Scanner exit code **0**; **0 legacy findings**, 35 active rules, 33 guides, about 20% of total guidance corpus. This is a *partial heuristic scan*, not a clean security or accessibility certification.
- Report saved locally to `/home/sspadawanzz/.local/state/worldshepherd/mwg/lenovo-gui-v08-20261111/legacy-scan.json` (not uploaded).
- SHA-256 before/after comparison of six frontend files matched; no scan-time modifications to source code.
- Installed `modern-web-guidance` as a **user-scoped Codex agent skill** in `~/.agents/skills/modern-web-guidance`; verified the `SKILL.md` and 209 Markdown guide files. Agent guidance only, not an application deployment.
- Verified the existing Palace diagnostics bash process remained present after scan and installation; full Palace solver completion was **not** established.
- Operator identified the intermittent network route as Lenovo relying on **Samsung USB-tethered internet**. Network-path instability is a plausible cause of the earlier `fetch failed` after authentication, but its precise hop/cause has not been instrumented. Avoid unnecessary credential resets and do not treat the cloud agent as independently powered by Lenovo.

Next gate: manual accessibility and security assessment of the actual UI, benchmarked compatibility and performance tests, review of false-negative/unsupported patterns, and a separate reviewed code-change proposal. This scan and skill install do not establish the target 55% gain.

## Remote access resilience

GitHub-hosted runners are **not** Lenovo. The current audit was run through a live,
authorized Desktop Commander session. Keep Samsung USB-tether availability, physical
connection, routing, and upstream mobile network state visible when diagnosing future
session drops. Retain existing SSH keys, device identities and host fingerprints.
Avoid opening public inbound ports or resetting credentials as a first response.

## Primary references

- https://developer.chrome.com/docs/modern-web-guidance/modernization-workflow
- https://github.com/GoogleChrome/modern-web-guidance
- https://www.npmjs.com/package/modern-web-guidance

## Lenovo GUI v0.8.0 focused security review (2026-11-11)

**Security issue identified (candidate only):** The separately maintained GUI's globe detail-rendering routines used `innerHTML` with raw track metadata (label, callsign, category, operator, status and timestamps). If untrusted track data reaches that boundary, DOM-based script injection could occur. Google's 35-rule legacy scan did not detect this; its zero findings are not a clean bill of health.

**Mitigation prepared privately on Lenovo:** An isolated copy was modified to use `document.createElement`, `textContent`, `replaceChildren`, and a four-value CSS category allowlist. The original GUI files and this public repository's deployed code were **not** edited. No source patch is published here because the standalone GUI's sharing/IP status has not been reviewed.

**Private evidence locations:**

- Candidate root: `~/.local/state/worldshepherd/mwg/gui-v08-security-candidate-20261111/`
- Local patch: `gui-v08-globe-dom-safety.patch` (SHA-256 `62362bc5ddda3eabcb551ba302af06571269d5597d6380f42ab313bbb7a744ff`)
- Regression test: `tests/globe_dom_safety_regression.cjs` (SHA-256 `45e7bf95f5357f6d2aa9e347b69bf75bdba2f0dfd012291c68b4a8c227d3edea`)
- Original `gui/globe.js` SHA-256: `54277117f848cab2bf9e97ece1e6035b876099496b9597dceb53ca61395d2c80` (unchanged after review)
- Tests: isolated-copy Python `unittest discover -s tests -q` **55/55 pass** after including required launcher fixture; Node VM regression with hostile sample strings **pass**; Node `--check` **pass**. The initial one-error test run was a copy-fixture omission, not a source regression.
- Limitation: Node VM assertions establish safe DOM construction for the exercised panel; a live browser security audit and authorization tests are still needed.

**Next manual audit gates, before deployment:**
1. Verify destination URL schemes/origins for official-source links and embedded media; HTML attribute escaping alone does not validate a `javascript:` or other unsafe URL scheme.
2. Evaluate removing the administrator bearer token from browser `sessionStorage` and hardening credential lifetimes; prioritize because any remaining XSS would increase its exposure.
3. Design compatible CSP report-only deployment and keyboard-accessible tab navigation; first confirm map/Street View integrations, framing needs and supported browsers.
4. Run browser-based integration, keyboard/screen-reader, responsive, and negative-authorization tests on a dedicated reviewed build. Preserve a rollback copy.

**IP boundary:** These findings describe security behavior without publishing the standalone local GUI source. Explicitly decide where that code should live before integrating or disclosing it publicly.

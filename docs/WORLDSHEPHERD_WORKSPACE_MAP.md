# Worldshepherd Workspace Map

This map keeps Slack coordination and GitHub source-of-truth artifacts aligned.

| Operating lane | Slack coordination surface | Durable GitHub home / artifact |
|---|---|---|
| Command / portfolio | `#worldshepherd-command` | `docs/WORLDSHEPHERD_OPERATING_MODEL.md`, ADRs, umbrella issues |
| Opportunity / PRE | `#ws-opportunity-capture` | opportunity issues, PRE schemas/records, capture docs |
| Teaming | `#worldshepherd-teaming` | partner/outreach issues, screening docs, evidence links |
| Outreach / communications | `#ws-outreach-comms` | partner/outreach issues when communications affect commitments, claims, evidence, or follow-up state |
| SARA platform | `#ws-sara-platform` | `runtime/`, `deployments/sara_verified_local_v1/`, code PRs, workflows, tests |
| Evidence / validation | `#ws-evidence-validation` | research-validation issues, test artifacts, evidence docs, PR validation sections |
| AI governance / standards | `#ws-ai-governance` | governance docs, external-anchor pilots, conformance artifacts, PRs/issues |
| Autonomy / robotics | `#ws-autonomy-robotics` | research/engineering issues, validation packages, component/subproject docs |
| RF / spectrum | `#ws-rf-spectrum` | RF/metasurface research docs, simulation/test issues, evidence packages |
| Materials / manufacturing | `#ws-materials-mfg` | materials research, process/coupon evidence, qualification issues |
| Propulsion / space | `#ws-propulsion-space` | propulsion/space research docs, experiments, validation issues |
| Cyber / PQC | `#ws-cyber-pqc` | `security/`, workflows, threat/assurance docs, code/issues |
| Research watch | `#ws-research-watch` | dated research notes, requirement deltas, validation issues when action is triggered |
| Commercialization | `#ws-commercialization` | screening/productization/licensing docs and issues tied to evidence state |

## Routing rule

A Slack discussion becomes a GitHub artifact when it changes any of the following:

- architecture or policy;
- code, configuration, interface, deployment, or test behavior;
- technical maturity or claim state;
- opportunity/capture posture or reusable readiness;
- partner role, commitment, data/IP boundary, or externally consequential representation;
- public-release content;
- evidence acceptance, rejection, supersession, or reproducibility state.

Routine coordination that does not change durable state can remain Slack-only.

## Thread / issue correspondence

Prefer **one Slack parent thread ↔ one GitHub issue/PR** for consequential work. Cross-link rather than duplicating entire histories.

A GitHub acceptance decision must be understandable without private Slack access. Slack may provide context, but evidence required for acceptance belongs in or is linked from GitHub.

## Existing repository umbrellas

The repository currently uses three top-level operating umbrellas:

- **#281 — Platform & Assurance**
- **#282 — Science & Validation**
- **#283 — Growth & Externalization**

Detailed work remains child issues/PRs beneath those umbrellas; Slack channels are routing surfaces, not competing top-level programs.

## Failure handling

If Slack disconnects, continue in GitHub. If GitHub is temporarily unavailable, record the work locally and reconcile to GitHub before treating a durable state change as canonical.

See `docs/SLACK_GITHUB_CONTINUITY.md` and ADR-0002 for the governing continuity decision.
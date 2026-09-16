# Worldshepherd Discord Server Blueprint

## Objective

Discord is the primary live coordination layer for Worldshepherd. This blueprint preserves the existing operating lanes while adding explicit role, permission, bot, thread, and archival controls. GitHub remains authoritative for durable technical, governance, evidence, opportunity, and commitment state.

## Role model

Recommended roles, in descending authority:

- `CRE1AWS` — human approval authority / architect.
- `SSPADAWANZZ` — admin-operator for bounded execution.
- `SARA-BOT` — service identity for governed automation; no human credential reuse.
- `MAINTAINER` — trusted repository / operations contributor.
- `CONTRIBUTOR` — internal contributor with lane-scoped write access.
- `PARTNER-GUEST` — external collaborator with explicitly scoped channels only.
- `READ-ONLY` — visibility without write or automation authority.

Principles:

- least privilege by default;
- private channels for non-public operational work;
- partner guests never inherit internal categories automatically;
- bots receive only the permissions and channel scopes they require;
- no role below CRE1AWS/SSPADAWANZZ may approve external commitments or elevate technical claim state without the defined evidence gate.

## Category and channel layout

### 00 — CONTROL

- `#worldshepherd-command` — portfolio command, doctrine, approvals, cross-lane decisions.
- `#ws-announcements` — read-mostly operational notices and major milestones.
- `#ws-decisions` — concise decision summaries linked to GitHub ADRs/issues/PRs.

### 10 — PLATFORM & ASSURANCE

- `#ws-sara-platform` — SARA / PRIME / ECHO / OVERWATCH implementation and deployment.
- `#ws-evidence-validation` — tests, negative evidence, readiness promotion/demotion.
- `#ws-cyber-pqc` — defensive cyber, identity, provenance, SBOM, PQC migration.
- `#ws-ai-governance` — trustworthy AI, evaluation, agent governance, standards activity.

### 20 — SCIENCE & ENGINEERING

- `#ws-autonomy-robotics` — drones, humanoids, companion systems, maritime/ground/air autonomy.
- `#ws-rf-spectrum` — radar, RF, antennas, metasurfaces, spectrum and distributed sensing.
- `#ws-materials-mfg` — Al–Ti work, DED/AM, electric-machine materials, qualification.
- `#ws-propulsion-space` — propulsion, plasma, energy, space systems, environmental survivability.
- `#ws-research-watch` — external research, standards, technical developments, disconfirming evidence.

### 30 — GROWTH & EXTERNALIZATION

- `#ws-opportunity-capture` — solicitations, PRE requirement deltas, capture posture.
- `#worldshepherd-teaming` — partner diligence, division of labor, validation partners.
- `#ws-outreach-comms` — external communication state and unresolved follow-up.
- `#ws-commercialization` — productization, licensing, manufacturing transition, revenue.

### 90 — ARCHIVE / MIGRATION

- `#slack-migration-log` — temporary references to legacy Slack material that has not yet been reconciled.
- `#closed-work` — compact pointers to completed GitHub issues/PRs; not a second source of truth.

## Thread discipline

Create a thread for each consequential work item rather than running independent histories in the parent channel.

Thread title format:

`[LANE][P0-P3][STATUS] Short title`

The first substantive thread message should include:

- owner;
- GitHub issue/PR/document link when available;
- evidence class;
- decision gate;
- current state;
- next action;
- due date or external dependency when applicable.

When work becomes consequential, use **one Discord parent thread ↔ one GitHub issue/PR** whenever practical.

## Claims and readiness boundary

Discord discussion never upgrades technical maturity by itself. Physical concepts advance only through the repository-defined readiness ladder:

`requirements → analytical model → simulation → bench/coupon → subsystem → integrated demonstration → independent/partner validation → qualification/production transition`

News, partner claims, simulations, concept art, or discussion remain bounded by the applicable Worldshepherd claims-control label until reproducible evidence supports promotion.

## Bot / automation policy

`SARA-BOT` or any future integration should begin with a narrow scope:

1. post GitHub PR/issue/workflow notifications;
2. create links or thread summaries;
3. surface deadline or unresolved-follow-up alerts;
4. never merge, delete, grant privileges, send external commitments, or upgrade claim/readiness state without explicit human authorization;
5. record consequential bot actions and failures durably in GitHub.

Recommended initial permissions:

- View Channels
- Send Messages
- Create Public/Private Threads only where required
- Send Messages in Threads
- Embed Links
- Read Message History

Avoid granting Administrator, Manage Server, Manage Roles, or broad moderation permissions unless a separately reviewed automation use case requires them.

## GitHub correspondence

The three existing repository umbrellas remain the portfolio spine:

- `#281 — Platform & Assurance`
- `#282 — Science & Validation`
- `#283 — Growth & Externalization`

Discord categories route work into those durable structures; they do not replace them.

## Migration rule

Do not bulk-copy Slack history. Reconcile only information that changes current architecture, claims, evidence, opportunity posture, partner state, outreach state, or unresolved work. Preserve original source links/timestamps where available and mark uncertain migration facts as such.

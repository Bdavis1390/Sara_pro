# SCAR AOI 03 Concept v0.1 — Worldshepherd Assurance Adapter

**Opportunity:** USSF SCAR HQ0860-26-S-C008
**AOI focus:** AOI 03 — Antenna as a Service
**Official response deadline verified:** 2026-10-15 14:00 MDT
**Status:** NON-CUI CONCEPT / teaming-oriented; direct submission remains blocked unless all solicitation eligibility gates, including required Secret-or-higher clearance and active Facility Security Clearance, are verified

## 1. Positioning

Curious NerdworX / Worldshepherd should **not** position as the antenna-network prime.

The proposed role is a bounded software assurance and integration layer around a qualified commercial AaaS provider or brokered multi-provider network.

## 2. Proposed contribution

### Worldshepherd Assurance Adapter

A software layer that:

- normalizes mission/contact events from provider APIs;
- preserves configuration and scheduling provenance;
- records request/approval/execution lineage;
- detects duplicate, replayed, stale, or conflicting events;
- evaluates declared policy / authorization rules in shadow or gating modes as permitted;
- reconstructs mission/contact timelines;
- emits machine-readable evidence for rapid requalification and discrepancy review;
- supports adapter-based integration so provider-owned core networks remain provider-owned.

## 3. AOI 03 value hypothesis

A commercial ground-network solution can be operationally mature while still facing government-specific integration risk at the boundaries between:

- mission request;
- provider scheduling;
- provider capacity;
- contact execution;
- government interface;
- telemetry / status return;
- configuration changes;
- multi-provider failover.

Worldshepherd's role is to make those boundary transitions inspectable and reproducible.

## 4. Partner architecture

```text
Government / JAM-defined mission interface
                |
        provider-owned adapter
                |
      Worldshepherd assurance layer
      - provenance
      - policy/authorization evidence
      - replay/staleness checks
      - configuration custody
      - timeline reconstruction
                |
  qualified AaaS provider / broker fabric
                |
           antenna assets
```

The exact placement is subject to partner and government interface requirements.

## 5. White-paper proof points

Use only evidence that can be defended from the public repository:

- governed workflow execution;
- authorization-boundary testing;
- deterministic replay / reconstruction patterns;
- provenance and configuration lineage;
- failure injection;
- rollback/recovery evidence;
- machine-readable evaluator handoff;
- internal NIST SP 800-171 preparation artifacts.

Do **not** claim:
- JAM-CCAP interoperability before endpoint/conformance evidence exists;
- operational antenna service;
- government acceptance;
- CUI/EXPT access;
- CMMC certification;
- active JCP/DD2345;
- AaaS TRL inherited from a provider unless the provider itself substantiates it.

## 6. Non-CUI validation plan

Until protected Offeror Library access is lawfully available, develop against a synthetic interface with public assumptions only.

Test cases:

1. nominal contact request and completion;
2. duplicate request;
3. stale schedule update;
4. conflicting provider status;
5. unauthorized change;
6. provider failover;
7. network outage / delayed status;
8. configuration-version mismatch;
9. restart and evidence reconstruction.

Outputs:
- pass/fail matrix;
- event timeline;
- evidence manifest;
- unresolved assumptions;
- interface questions requiring government/partner input.

## 7. White-paper structure

1. **Executive summary** — narrow teaming contribution.
2. **AOI 03 problem statement** — commercial-network integration assurance.
3. **Partner-owned mature capability** — supplied by the selected AaaS provider.
4. **Worldshepherd bounded subsystem** — assurance/evidence adapter.
5. **Integration architecture** — interfaces and trust boundaries.
6. **Phase 1 evidence** — public/synthetic tests only unless additional access is lawfully obtained.
7. **Phase 2 qualification plan** — government/partner endpoint, conformance, service and isolation validation.
8. **Cyber / CUI posture** — state only verified status.
9. **Schedule / cost** — dependent on selected prime/team.
10. **Risks / dependencies** — explicit.

## 8. Immediate partner ask

For ATLAS, RBC Signals, KSAT, SSC Space, or another qualified provider, the concise ask is:

> Allow Worldshepherd to serve as a bounded assurance/evidence subsystem in the provider-led AOI 03 solution, with access only to the minimum non-sensitive interface/test information needed to build and demonstrate the adapter. The provider retains ownership of antenna operations, service performance, network TRL, and all core mission-service claims.

## 9. Eligibility gates

Provider-led teaming is the default executable route.

A direct Curious NerdworX submission must not be made unless the solicitation-required Secret-or-higher clearance and active Facility Security Clearance are verified at the required time, along with all other direct-offeror requirements.

Protected Offeror Library access remains separately gated by the solicitation requirements and government guidance. The repository must continue to treat CAGE/JCP/DD2345/SPRS/CUI-readiness status as unverified until documentary evidence exists.

The non-CUI technical package may be developed from public material while those gates are pursued in parallel.

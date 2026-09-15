# GD-07 — Space Data Network (SDN) Capture Lane

**Status:** PUBLIC-SOURCE CAPTURE ANALYSIS / REVERIFY BEFORE EXTERNAL USE

## Why this lane matters
The U.S. Space Force Space Systems Command (SSC) is building the Space Data Network (SDN) as a resilient, open, multi-vendor communications architecture. Public SSC statements emphasize standardized interfaces, digital models, security protocols, onboarding new providers, multi-vendor integration, and repeatable test baselines.

Those requirements provide a plausible non-hardware evaluation lane for Worldshepherd's bounded mission-assurance capabilities: provenance, configuration/interface evidence, deterministic replay, policy/human authorization, fault traceability, and integration assurance.

## Authoritative public anchors
### May 26, 2026 — SDN Backbone
SSC announced a $2.29B Firm-Fixed-Price OTA delivery order to SpaceX for the SDN Backbone, with a fully operational prototype capability required by the end of 2027. SSC stated that the recently established SDN consortium would expand its participants and work across vendors on a unified network architecture and advanced communications demonstrations.

Source: https://www.ssc.spaceforce.mil/Newsroom/Article-Display/Article/4501527/us-space-force-advances-space-data-network-backbone-for-global-warfighter-conne

### August 13, 2026 — five multi-vendor integration awards
SSC announced complementary fixed-price contracts and OTA agreements valued at $12M per company to five companies: Amazon LEO for Government, Lockheed Martin, Northrop Grumman, Rocket Lab, and York Space Systems.

The first $10M portion supports six-to-nine-month prototypes demonstrating multi-vendor interconnectivity across the SDN Backbone. The second $2M OTA portion supports six-month Space Exchange Point satellite work. SSC described physical, electrical, and data-interface standards, digital models, and security protocols as part of the onboarding/integration strategy.

Source: https://www.ssc.spaceforce.mil/Newsroom/Article-Display/Article/4572417/space-force-invests-in-resilient-multi-vendor-architecture-to-build-next-gen-sp

## Worldshepherd insertion boundary
**Pursue:**
- interface-conformance evidence and adapter governance;
- source/configuration/result provenance;
- deterministic replay of integration tests;
- stale/conflicting-source handling;
- controlled degraded-state/fault-injection evidence;
- policy/human-authorization auditability;
- digital-thread consistency and test-evidence export;
- onboarding evidence for heterogeneous providers.

**Do not claim/pursue without separate evidence:**
- optical-terminal hardware performance;
- flight-qualified satellite-bus capability;
- SDN routing performance;
- operational network control;
- government-standard interface compatibility;
- Space Force/SSC validation or consortium membership.

## Strongest initial evaluation hypothesis
Use the W-RMABM G2 interface-conformance harness as a neutral integration-assurance demonstration. Ask an authorized evaluator to provide or approve an **unclassified surrogate interface schema**. Replace one fictional adapter with that surrogate and measure:
1. conformance/rejection behavior;
2. provenance completeness;
3. deterministic replay;
4. fault/staleness traceability;
5. adapter-isolation behavior;
6. governance overhead and latency.

This would test the value proposition without requiring operational mission data or proprietary network protocols.

## Public routing hypothesis
SSC publicly identifies the U.S. Space Force Front Door as a one-stop portal for commercial companies with tested or emerging space technologies and separately lists its Small Business Office and Space Enterprise Consortium among partnership routes. Use those public channels to seek correct routing before assuming that the SDN consortium is directly open to unsolicited membership.

Source: https://www.ssc.spaceforce.mil/About-Us/Partner-With-Us

## Priority effect
SDN should be ranked alongside BAE Epoch 2 and SDA STEC as a Tier-1 external-validation lane because it explicitly emphasizes multi-vendor integration and standardized interfaces. Among the five announced SDN integration awardees, partner screening should prioritize complementarity and verified intake route rather than contract value alone.

## Claims boundary
This document is a capture hypothesis derived from public program information. It does not establish Worldshepherd participation in SDN, an SSC relationship, consortium membership, supplier status, operational compatibility, or government validation.

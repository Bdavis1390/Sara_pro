# WS-DCAR-ASH-001 / I&I-001: synthetic wet-weather flow evidence screen

**Status: software prototype, SYNTHETIC ONLY.** The CLI and unit tests are new; **no Ashville utility data, project access, partner agreement, site calibration, certified physical engineering or field impact is claimed.**

## Why this is a potentially useful narrow addition
Ashville's *2014 Ongoing Infiltration/Inflow Reduction Plan* **already envisaged** metershed flow monitoring, thresholds, quarterly event reports and an I&I dashboard. We should not duplicate or take credit for those capabilities. The only prospective value of this tool is reproducible event-to-baseline calculation with refusal of missing/invalid inputs, traceable instrument custody, independent review, and a resident-comprehensible evidence explanation.

Primary and related sources:
- Original village I&I plan (2014): https://core-docs.s3.us-east-1.amazonaws.com/documents/asset/uploaded_file/4453/ashvillevillage/3751514/i__i_ongoing_infiltration_inflow_reduction_plan_2014.pdf
- 2014 Ohio EPA findings/timeline: https://files-backend.assets.thrillshare.com/documents/asset/uploaded_file/4453/Ashvillevillage/c3108082-f98d-44ab-aa39-255a4e6e1b01/i__i_timeline.pdf?disposition=inline
- Phase 2 and Southeast Metershed RFP, posted Sep. 2025, questions due Oct. 3, 2025 (**expired, not an open bid**): https://projects.constructconnect.com/details/7254141-rfp-engineering-south-metershed-phase-2-i-i-improvements-inflow-infiltration-projects&find_loc=ohio-43103
- Oct. 8 donation as currently displayed by Village: https://www.ashvilleohio.gov/live-feed (parks $1M, pump $700k, South Metershed design $1.8M). A contemporaneous media article reported $1M/$900k/$1.6M; actual council appropriations must resolve this discrepancy before financial statements.

## Run

From repo root:

```bash
python3 -m unittest discover -s research/ws_dcar_ash_001 -p 'test_ii_screen.py' -v
```

The executable accepts JSON as input:

```bash
python3 research/ws_dcar_ash_001/ii_screen.py --input event.json --output screening.json
```

The payload **must** be labeled `SYNTHETIC_DEMONSTRATION` and contain:
- `clock_basis: "UTC"`, `interval_minutes: 60` and a `meter_id` beginning with `SYNTH-`;
- `assumed_flow_error_m3h` (illustrative instrument-error bound);
- `dry_days`: at least 3 unique ISO calendar days, without rainfall;
- `storm_day`: one distinct day with positive total rainfall;
- `records`: complete 24 hourly observations per day, each with `day`, `hour_utc`, `flow_m3h` (m³/h), and `rain_mm` (hourly mm).

For a wholly fictional test payload:
```bash
cd research/ws_dcar_ash_001
python3 -c 'from test_ii_screen import synthetic_payload; import json; print(json.dumps(synthetic_payload(), indent=2))' > event.json
python3 ii_screen.py --input event.json --output screening.json
```

## Method and interpretation
For each UTC hour `h`, calculate the median flow of the 3+ dry reference days `b[h]` and the observed storm-day flow `q[h]`. Then:
- `positive_difference_screen_m3 = sum(max(0, q[h] - b[h])) * 1h`.
- If each flow reading and baseline median can vary by `u` m³/h due to assumed instrument error, calculate a crude conservative meter-error-only sensitivity range: `sum(max(0, q[h] - b[h] +/- 2u)) * 1h`.
- Output rain total, observed flow, matched dry baseline, positive-difference screen, sensitivity range, and explicit unknown causal/remediation/regulatory results.

In the synthetic unit fixture, 3 dry days have constant 10 m³/h; four storm-day hours rise to 14 m³/h with 20 mm total assumed rainfall; `u=0.2` m³/h. The screen returns **16 m³ illustrative positive difference**, with an error-only sensitivity range **14.4–25.6 m³**. That is not an estimate of Ashville I&I.

**Important limits:** The range is **not a statistical confidence interval**, does not model ordinary weather/day-of-week baseline variation, tributary population, rainfall catchment coverage, groundwater, cross-connections, wet-weather sanitary demand, lagged response, repair effects, storm severity matching or regulatory peak thresholds. `max(0, difference)` can bias event sums upward. Coincident rainfall does not prove causality; separating infiltration from direct inflow generally requires site investigation. An independent sanitary engineer must determine any acceptable field method and decision criteria.

## No-cost feasibility gates
1. Verify current project work orders, contracted engineer, historical meter registry, 2014 dashboard implementation and access terms. Phase I is reportedly already constructed and Phase II procurement was in 2025; never assume a current bid.
2. Ask data owners (only after authorized external scoping) whether anonymized basin flow and rainfall series exist with calibration, exact meter boundary, clock provenance, configuration and uncertainties; **do not ingest resident utility-usage accounts**.
3. Compare our audit and uncertainty handling with the existing dashboard and third-party contractor tools. **If no distinct value is demonstrated, stop.**
4. Advance to independent physical validation only with a consenting utility/engineer and legally authorized scopes. No funding or field effort without written terms.
5. A resident review group may challenge and help select nonpolitical technical questions. No vote-targeted outreach or contingent payments. Results may recommend no-build or non-development remedies.

Tracking: #562; related WS-DCAR external validation #525 / PR #524 and this draft PR.

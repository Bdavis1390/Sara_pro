#!/usr/bin/env python3
"""WS-DCAR-ASH-001: synthetic wet-weather sanitary-flow screening, not field evidence.

This exercise refuses incomplete, unsynchronized, unlabeled or untrusted datasets.
A storm-associated positive flow difference is NOT proof of inflow or infiltration,
its source, regulatory compliance, remediation success, or a cost saving.
"""
import argparse
import json
import math
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path

REQUIRED_FIELDS = ('day', 'hour_utc', 'flow_m3h', 'rain_mm')


def _finite_nonnegative(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f'{field} must be a finite nonnegative number')
    return float(value)


def screen(payload):
    """Screen 3+ synthetic dry-weather days against one synthetic 24h event day.

    Hourly medians estimate matched-hour dry-weather baseline. Interval is a
    conservative meter-error-only sensitivity; NOT statistical confidence.
    No weather adjustment, demand adjustment, site compliance or causal
    separation of infiltration versus inflow is performed.
    """
    if payload.get('dataset_type') != 'SYNTHETIC_DEMONSTRATION':
        raise ValueError('Only explicitly labeled synthetic demonstration data accepted')
    if payload.get('clock_basis') != 'UTC' or payload.get('interval_minutes') != 60:
        raise ValueError('Requires synchronized hourly UTC sampling')
    meter_id = payload.get('meter_id')
    if not isinstance(meter_id, str) or not meter_id.startswith('SYNTH-'):
        raise ValueError('Requires clearly synthetic meter identifier')
    uncertainty = _finite_nonnegative(payload.get('assumed_flow_error_m3h'), 'assumed_flow_error_m3h')
    dry_days = payload.get('dry_days')
    storm_day = payload.get('storm_day')
    if not isinstance(dry_days, list) or len(dry_days) < 3 or len(set(dry_days)) != len(dry_days):
        raise ValueError('At least three unique dry days required')
    if not isinstance(storm_day, str) or storm_day in dry_days:
        raise ValueError('Exactly one distinct storm day required')
    for d in dry_days + [storm_day]:
        if not isinstance(d, str) or date.fromisoformat(d).isoformat() != d:
            raise ValueError('Dates must be ISO 8601 calendar days')
    records = payload.get('records')
    if not isinstance(records, list):
        raise ValueError('records array required')
    expected_days = set(dry_days + [storm_day])
    grouped = defaultdict(dict)
    for row in records:
        if not isinstance(row, dict) or any(field not in row for field in REQUIRED_FIELDS):
            raise ValueError('Incomplete time series row')
        day, hour = row['day'], row['hour_utc']
        if day not in expected_days or not isinstance(hour, int) or isinstance(hour, bool) or hour not in range(24):
            raise ValueError('Unexpected date or hour')
        if hour in grouped[day]:
            raise ValueError('Duplicate timestamp; refuse ambiguous sampling')
        flow = _finite_nonnegative(row['flow_m3h'], 'flow_m3h')
        rain = _finite_nonnegative(row['rain_mm'], 'rain_mm')
        if day in dry_days and rain > 0:
            raise ValueError('Dry reference day has rainfall; selection invalid')
        grouped[day][hour] = (flow, rain)
    if set(grouped) != expected_days or any(set(grouped[d]) != set(range(24)) for d in expected_days):
        raise ValueError('Missing hourly sample; no interpolation or optimistic filling')
    storm_rain = sum(grouped[storm_day][hour][1] for hour in range(24))
    if storm_rain <= 0:
        raise ValueError('Storm-day rain must be positive')
    baseline = [statistics.median(grouped[d][hour][0] for d in dry_days) for hour in range(24)]
    observed = [grouped[storm_day][hour][0] for hour in range(24)]
    differences = [observed[h] - baseline[h] for h in range(24)]
    # Each observed and median-baseline sample may differ by +/- instrument
    # error. Bounds sum absolute worst cases; they are not confidence limits.
    excess = sum(max(0.0, x) for x in differences)
    low = sum(max(0.0, x - 2 * uncertainty) for x in differences)
    high = sum(max(0.0, x + 2 * uncertainty) for x in differences)
    return {
        'study': 'WS-DCAR-ASH-001/I&I-001',
        'model_version': '0.1.0',
        'dataset_type': 'SYNTHETIC_DEMONSTRATION',
        'meter_id': meter_id,
        'baseline_dry_days': len(dry_days),
        'storm_day': storm_day,
        'storm_rain_mm': round(storm_rain, 5),
        'storm_observed_volume_m3': round(sum(observed), 5),
        'matched_dry_weather_volume_m3': round(sum(baseline), 5),
        'positive_difference_screen_m3': round(excess, 5),
        'meter_error_only_range_m3': [round(low, 5), round(high, 5)],
        'range_interpretation': 'Conservative meter-error-only sensitivity, NOT statistical confidence; dry-day variability and wet-weather sanitary demand unquantified',
        'causal_attribution': 'UNKNOWN: rain-associated excess does not establish entry point, inflow vs infiltration, or source',
        'site_field_measurement_claim': 'NONE',
        'remediation_performance_claim': 'NONE',
        'regulatory_compliance': 'NOT_ASSESSED',
        'next_evidence_gate': 'Consented calibrated basin metering, representative dry days, multiple storm events, rainfall coverage, groundwater/flow-path investigation, independent engineer review'
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding='utf-8'))
    result = screen(payload)
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('SYNTHETIC ONLY: screened rain-associated flow difference; no field claims')


if __name__ == '__main__':
    main()

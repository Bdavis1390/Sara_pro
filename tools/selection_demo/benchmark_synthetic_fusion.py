from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import statistics
import time
from pathlib import Path
from typing import Any

from worldshepherd_sara.sensor_fusion import Observation, fuse_observations


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    rank = max(1, min(len(ordered), math.ceil(0.95 * len(ordered))))
    return ordered[rank - 1]


def _cpu_model() -> str:
    try:
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            if line.lower().startswith('model name'):
                return line.split(':', 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or 'UNKNOWN'


def _build_observations(count: int, track_count: int = 16) -> list[Observation]:
    observations: list[Observation] = []
    for i in range(count):
        track = i % track_count
        cycle = i // track_count
        observations.append(
            Observation(
                observation_id=f'O{i:07d}',
                sensor_id=f'S{(i % 8) + 1:02d}',
                t_seconds=float(cycle % 5) * 0.01,
                x=float(track * 100) + float((cycle % 7) - 3) * 0.05,
                y=float(track * 80) + float((cycle % 11) - 5) * 0.05,
                confidence=0.70 + float(i % 25) / 100.0,
            )
        )
    return observations


def _payload_bytes(observations: list[Observation]) -> int:
    data = [item.model_dump(mode='json') for item in observations]
    return len(json.dumps(data, separators=(',', ':'), sort_keys=True).encode('utf-8'))


def _output_digest(tracks: Any) -> str:
    canonical = [
        {
            'track_id': t.track_id,
            'x': t.x,
            'y': t.y,
            't_seconds': t.t_seconds,
            'confidence': t.confidence,
            'source_observation_ids': list(t.source_observation_ids),
            'source_sensor_ids': list(t.source_sensor_ids),
        }
        for t in tracks
    ]
    raw = json.dumps(canonical, separators=(',', ':'), sort_keys=True).encode('utf-8')
    return 'sha256:' + hashlib.sha256(raw).hexdigest()


def _run_profile(count: int, repetitions: int, warmup: int) -> dict[str, Any]:
    observations = _build_observations(count)
    payload = _payload_bytes(observations)

    def execute():
        return fuse_observations(
            observations,
            max_spatial_distance=3.0,
            max_time_delta_seconds=0.10,
        )

    for _ in range(warmup):
        execute()

    elapsed_ms: list[float] = []
    digests: list[str] = []
    track_counts: list[int] = []
    for _ in range(repetitions):
        start = time.perf_counter_ns()
        tracks = execute()
        elapsed = (time.perf_counter_ns() - start) / 1_000_000.0
        elapsed_ms.append(elapsed)
        digests.append(_output_digest(tracks))
        track_counts.append(len(tracks))

    p50 = statistics.median(elapsed_ms)
    p95 = _p95(elapsed_ms)
    p95_seconds = max(p95 / 1000.0, 1e-12)
    payload_mb = payload / 1_000_000.0
    throughput_mb_min = payload_mb / p95_seconds * 60.0
    obs_per_second = count / p95_seconds

    return {
        'observation_count': count,
        'track_seed_count': 16,
        'result_track_count': track_counts[0],
        'serialized_input_bytes': payload,
        'serialized_input_mb_decimal': payload_mb,
        'repetitions': repetitions,
        'warmup': warmup,
        'latency_ms': {
            'min': min(elapsed_ms),
            'p50': p50,
            'p95': p95,
            'max': max(elapsed_ms),
        },
        'synthetic_function_throughput_mb_per_min_at_p95': throughput_mb_min,
        'synthetic_observations_per_second_at_p95': obs_per_second,
        'deterministic_output': len(set(digests)) == 1,
        'output_digest': digests[0],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--software-commit', default=os.environ.get('GITHUB_SHA', 'UNKNOWN'))
    args = parser.parse_args()

    profiles = [
        _run_profile(500, repetitions=10, warmup=2),
        _run_profile(2500, repetitions=7, warmup=1),
        _run_profile(10000, repetitions=5, warmup=1),
    ]

    record = {
        'schema': 'WS-SYNTHETIC-FUSION-SCALE-BENCHMARK-V1',
        'status': 'INTERNAL_BOUNDED_SYNTHETIC_BENCHMARK',
        'software_commit': args.software_commit,
        'executed_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'host': {
            'platform': platform.platform(),
            'python': platform.python_version(),
            'cpu_model': _cpu_model(),
            'logical_cpu_count': os.cpu_count(),
        },
        'profiles': profiles,
        'reference_targets': {
            'DIU_PROJ00716_latency_threshold_seconds': 5.0,
            'DIU_PROJ00716_latency_objective_seconds': 2.0,
            'DIU_PROJ00716_nominal_ingest_mb_per_min': [20.0, 30.0],
            'DIU_PROJ00716_burst_ingest_mb_per_min_approx': 5000.0,
        },
        'interpretation_rules': [
            'The benchmark measures only the in-process deterministic synthetic 2-D fusion callable on generated point observations.',
            'It excludes network transfer, API serialization/deserialization, authentication, persistence, historical retrieval, imagery/video/radar decoding, model inference, classified-domain guards, cross-domain transfer, and operator UI latency.',
            'Measured throughput therefore MUST NOT be represented as end-to-end DIU PROJ00716 throughput or operational ISR performance.',
            'The DIU values are reference targets only; meeting a numeric value in this microbenchmark does not establish compliance with the DIU requirement.',
            'No 5 GB/min load is generated; the burst target is recorded for gap analysis only.',
        ],
        'claims_boundary': 'Internal host-specific synthetic performance evidence only. Not target-device, operational, classified, real-time, safety, flight, government acceptance, or production-scale evidence.',
    }

    for profile in profiles:
        if not profile['deterministic_output']:
            record['status'] = 'FAIL_NONDETERMINISTIC_OUTPUT'

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0 if record['status'] == 'INTERNAL_BOUNDED_SYNTHETIC_BENCHMARK' else 1


if __name__ == '__main__':
    raise SystemExit(main())

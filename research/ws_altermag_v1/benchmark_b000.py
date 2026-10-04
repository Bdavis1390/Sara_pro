from __future__ import annotations

import json
import math
from pathlib import Path

from .decompiler import infer
from .evidence import decide
from .forward import synthesize
from .hypotheses import compare_am_vs_relaxation
from .schema import PhysicalState, digest


ROOT = Path(__file__).resolve().parent
DEFAULT_MANIFEST = ROOT / "manifests" / "crsb_b000.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run(manifest_path: Path = DEFAULT_MANIFEST) -> dict:
    manifest = _load(manifest_path)
    state = PhysicalState(**manifest["state"])

    truth = manifest["synthetic_truth"]
    grid = [
        (
            float(item["ef"]),
            math.radians(float(item["theta_deg"])),
            math.radians(float(item["phi_deg"])),
        )
        for item in manifest["measurement_grid"]
    ]

    measurements = synthesize(
        amplitude=float(truth["amplitude"]),
        tau=float(truth["tau"]),
        grid=grid,
        sigma=float(manifest["noise_sigma"]),
        seed=int(manifest["seed"]),
    )
    inference = infer(measurements)
    hypotheses = compare_am_vs_relaxation(measurements, inference)

    tolerance = manifest["acceptance"]
    recovered = (
        abs(inference.amplitude - float(truth["amplitude"]))
        <= float(tolerance["amplitude_abs"])
        and abs(inference.tau - float(truth["tau"]))
        <= float(tolerance["tau_abs"])
        and inference.identifiable
        and bool(hypotheses["decisive"])
    )

    evidence = decide(
        inference=inference,
        hypothesis_decisive=bool(hypotheses["decisive"]),
        execution_mode=state.execution_mode,
        test_passed=recovered,
    )

    record = {
        "program": "WS-ALTERMAG",
        "benchmark": "B000-S",
        "schema_version": "1.0-rc0",
        "state": state.as_record(),
        "synthetic_truth": truth,
        "measurements": [m.as_record() for m in measurements],
        "inference": inference.as_record(),
        "hypotheses": hypotheses,
        "acceptance": tolerance,
        "pass": recovered,
        "evidence": evidence.as_record(),
        "claim_boundary": (
            "Synthetic software validation only. This benchmark does not validate "
            "CrSb physical performance or any fabricated Worldshepherd device."
        ),
    }
    record["experiment_digest"] = digest(record)
    return record


def main() -> None:
    print(json.dumps(run(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_MANIFEST = ROOT / "manifests" / "qo_angle_plan_b000.json"


def alpha_to_theta_phi(alpha_deg: float, tilt_deg: float = 14.0) -> tuple[float, float]:
    alpha = math.radians(float(alpha_deg))
    tilt = math.radians(float(tilt_deg))

    cos_theta = math.sin(tilt) * math.sin(alpha)
    cos_theta = max(-1.0, min(1.0, cos_theta))
    theta = math.acos(cos_theta)

    # tan(phi)=cos(tilt)*tan(alpha), written with atan2 to preserve quadrant.
    phi = math.atan2(math.cos(tilt) * math.sin(alpha), math.cos(alpha))
    return math.degrees(theta), math.degrees(phi)


def build_angle_plan(path: Path = DEFAULT_MANIFEST) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    tilt = float(manifest["source"]["tilt_deg"])
    rows = []
    for alpha in manifest["fig3_alpha_deg"]:
        theta, phi = alpha_to_theta_phi(float(alpha), tilt)
        rows.append(
            {
                "alpha_deg": float(alpha),
                "theta_deg": theta,
                "phi_deg": phi,
            }
        )

    check = manifest["source"]["validation_point"]
    theta_check, phi_check = alpha_to_theta_phi(float(check["alpha_deg"]), tilt)
    tol = float(check["tolerance_deg"])
    validation_pass = (
        abs(theta_check - float(check["reported_theta_deg"])) <= tol
        and abs(phi_check - float(check["reported_phi_deg"])) <= tol
    )

    return {
        "program": manifest["program"],
        "benchmark": manifest["benchmark"],
        "tilt_deg": tilt,
        "angles": rows,
        "validation": {
            "alpha_deg": float(check["alpha_deg"]),
            "computed_theta_deg": theta_check,
            "computed_phi_deg": phi_check,
            "reported_theta_deg": float(check["reported_theta_deg"]),
            "reported_phi_deg": float(check["reported_phi_deg"]),
            "tolerance_deg": tol,
            "pass": validation_pass,
        },
        "claim_boundary": manifest["claim_boundary"],
    }


def main() -> None:
    print(json.dumps(build_angle_plan(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

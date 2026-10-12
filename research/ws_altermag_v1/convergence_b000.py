from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from .elk_input_b000 import render_elk_template


ROOT = Path(__file__).resolve().parent
DEFAULT_PLAN = ROOT / "manifests" / "convergence_b000.json"


def build_plan(plan_path: Path = DEFAULT_PLAN) -> dict:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    cases = []

    fixed_k = tuple(int(v) for v in plan["basis_convergence"]["fixed_kgrid"])
    for rgkmax in plan["basis_convergence"]["rgkmax_values"]:
        text = render_elk_template(ngridk=fixed_k, rgkmax=float(rgkmax))
        cases.append({
            "kind": "basis",
            "label": f"rgkmax-{float(rgkmax):.1f}",
            "kgrid": list(fixed_k),
            "rgkmax": float(rgkmax),
            "template_sha256": sha256(text.encode("utf-8")).hexdigest(),
        })

    fixed_rgkmax = float(plan["kgrid_convergence"]["fixed_rgkmax"])
    for grid in plan["kgrid_convergence"]["kgrids"]:
        k = tuple(int(v) for v in grid)
        text = render_elk_template(ngridk=k, rgkmax=fixed_rgkmax)
        cases.append({
            "kind": "kgrid",
            "label": "kgrid-" + "x".join(str(v) for v in k),
            "kgrid": list(k),
            "rgkmax": fixed_rgkmax,
            "template_sha256": sha256(text.encode("utf-8")).hexdigest(),
        })

    ref = plan["reference_run"]
    ref_k = tuple(int(v) for v in ref["kgrid"])
    ref_text = render_elk_template(ngridk=ref_k, rgkmax=float(ref["rgkmax"]))
    cases.append({
        "kind": "reference",
        "label": "reference-43x43x28",
        "kgrid": list(ref_k),
        "rgkmax": float(ref["rgkmax"]),
        "template_sha256": sha256(ref_text.encode("utf-8")).hexdigest(),
    })

    return {
        "program": plan["program"],
        "benchmark": plan["benchmark"],
        "execution_status": plan["execution_status"],
        "case_count": len(cases),
        "cases": cases,
        "claim_boundary": plan["claim_boundary"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    result = build_plan()

    if args.output_dir is not None:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for case in result["cases"]:
            name = case["label"] + ".elk.template"
            text = render_elk_template(
                ngridk=tuple(case["kgrid"]),
                rgkmax=float(case["rgkmax"]),
            )
            (args.output_dir / name).write_text(text, encoding="utf-8")
        (args.output_dir / "plan.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

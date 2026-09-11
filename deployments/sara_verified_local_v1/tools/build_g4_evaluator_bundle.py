from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


DEPLOYMENT_PREFIX = Path("deployments/sara_verified_local_v1")

BUNDLE_PATHS = (
    DEPLOYMENT_PREFIX / "requirements-g4-evaluator.txt",
    DEPLOYMENT_PREFIX / "worldshepherd_sara/__init__.py",
    DEPLOYMENT_PREFIX / "worldshepherd_sara/rmabm_external_evaluation.py",
    DEPLOYMENT_PREFIX / "worldshepherd_sara/rmabm.py",
    DEPLOYMENT_PREFIX / "worldshepherd_sara/mission_replay.py",
    DEPLOYMENT_PREFIX / "worldshepherd_sara/sensor_fusion.py",
    DEPLOYMENT_PREFIX / "worldshepherd_sara/prime.py",
    DEPLOYMENT_PREFIX / "worldshepherd_sara/qualification.py",
    DEPLOYMENT_PREFIX / "tools/rmabm_external_evaluation.py",
    DEPLOYMENT_PREFIX / "tests/test_rmabm_external_evaluation.py",
    Path("docs/golden_dome/GD-10_G4_EXTERNAL_REPRODUCTION_PROTOCOL.md"),
    Path("docs/golden_dome/GD-11_G4_EXTERNAL_EVALUATION_SCORECARD.md"),
    Path("docs/golden_dome/GD-13_G4_EVALUATOR_HANDOFF.md"),
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _line_count(data: bytes) -> int:
    if not data:
        return 0
    return len(data.decode("utf-8").splitlines())


def _git_revision(repo_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def _bundle_relative_path(source_path: Path) -> Path:
    try:
        return source_path.relative_to(DEPLOYMENT_PREFIX)
    except ValueError:
        return Path("docs") / source_path.name


def build_bundle(*, repo_root: Path, output: Path) -> dict:
    repo_root = repo_root.resolve()
    output = output.resolve()

    if output == repo_root or repo_root in output.parents and output == repo_root:
        raise ValueError("output must not replace repository root")

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    records: list[dict] = []
    for relative_source in BUNDLE_PATHS:
        source = (repo_root / relative_source).resolve()
        try:
            source.relative_to(repo_root)
        except ValueError as exc:
            raise ValueError(f"source escapes repository root: {relative_source}") from exc
        if not source.is_file():
            raise FileNotFoundError(relative_source)

        destination_relative = _bundle_relative_path(relative_source)
        destination = output / destination_relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        data = source.read_bytes()
        destination.write_bytes(data)
        records.append(
            {
                "path": destination_relative.as_posix(),
                "source_path": relative_source.as_posix(),
                "byte_count": len(data),
                "line_count": _line_count(data),
                "sha256": _sha256(data),
            }
        )

    records.sort(key=lambda item: item["path"])
    bundle_material = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest = {
        "schema_version": "ws-rmabm-g4-evaluator-bundle-v1",
        "source_revision": _git_revision(repo_root),
        "release_state": "REVIEW_REQUIRED_NOT_AUTHORIZED_FOR_EXTERNAL_TRANSMISSION",
        "claims_boundary": "SYNTHETIC SOFTWARE REPRODUCTION ONLY; NOT OPERATIONAL OR GOVERNMENT VALIDATION",
        "artifact_count": len(records),
        "total_bytes": sum(item["byte_count"] for item in records),
        "total_lines": sum(item["line_count"] for item in records),
        "bundle_content_sha256": _sha256(bundle_material),
        "artifacts": records,
    }
    (output / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / "README_EVALUATOR.md").write_text(
        "# W-RMABM G4 evaluator bundle\n\n"
        "Review-required synthetic-software reproduction candidate. This package does not establish external validation.\n\n"
        "Reference environment: x86-64 Linux with Python 3.12.\n\n"
        "```bash\n"
        "python3.12 -m venv .venv\n"
        ". .venv/bin/activate\n"
        "python -m pip install -r requirements-g4-evaluator.txt\n"
        "PYTHONPATH=. python -m pytest -q tests/test_rmabm_external_evaluation.py\n"
        "PYTHONPATH=. python tools/rmabm_external_evaluation.py --challenge-id evaluator-challenge --seed <EVALUATOR_SELECTED_INTEGER> --output result.json\n"
        "```\n\n"
        "The evaluator selects the final recorded seed and retains its original evidence. See the bundled GD-10, GD-11, and GD-13 documents.\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the minimal review-gated W-RMABM G4 evaluator bundle.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = build_bundle(repo_root=args.repo_root, output=args.output)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from worldshepherd_sara.evaluator_handoff import (
    ContractStatus,
    build_evaluator_handoff,
    discover_project_requirements,
    inventory_package,
    manifest_digest,
)


def make_package(tmp_path: Path) -> Path:
    root = tmp_path / "package"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        """[project]\n"
        "name = \"example-sara\"\n"
        "version = \"1.2.3\"\n"
        "requires-python = \">=3.11\"\n"
        "dependencies = [\"pydantic>=2\"]\n"
        "[project.optional-dependencies]\n"
        "test = [\"pytest>=8\"]\n""",
        encoding="utf-8",
    )
    (root / "module.py").write_text("x = 1\nprint(x)\n", encoding="utf-8")
    (root / "README.md").write_text("# Example\n\nBounded fixture.\n", encoding="utf-8")
    (root / "fixtures").mkdir()
    (root / "fixtures" / "case.json").write_text('{"ok": true}\n', encoding="utf-8")
    (root / ".venv").mkdir()
    (root / ".venv" / "ignored.py").write_text("ignored = True\n", encoding="utf-8")
    return root


def build_manifest(root: Path, **overrides):
    values = {
        "package_root": root,
        "artifact_id": "WS-SARA-EVAL-TEST",
        "repository": "Bdavis1390/Sara_pro",
        "release_ref": "test/ref",
        "release_commit": "a" * 40,
        "hardware_requirements": [
            "Evaluator-selected general-purpose host; no specialized hardware claimed by this fixture."
        ],
        "delivery_method": "Git checkout pinned to the declared commit.",
        "fixture_refs": ["fixtures/case.json"],
        "expected_results_ref": "tests/expected-results.md",
        "evaluation_scope": "Synthetic software behavior only.",
        "evaluation_window": "To be agreed with evaluator before execution.",
        "contract_status": ContractStatus.UNKNOWN_REQUIRES_REVIEW,
        "conflict_disclosure_notes": [
            "Evaluator independently determines organizational conflicts."
        ],
        "generated_utc": "2026-09-16T18:00:00Z",
    }
    values.update(overrides)
    return build_evaluator_handoff(**values)


def test_inventory_counts_real_files_and_excludes_virtualenv(tmp_path: Path):
    root = make_package(tmp_path)
    inventory = inventory_package(root)
    assert inventory.file_count == 4
    assert inventory.text_file_count == 4
    assert inventory.text_line_count > 0
    assert inventory.suffix_counts[".py"] == 1
    assert ".venv" in inventory.excluded_parts


def test_project_requirements_come_from_pyproject(tmp_path: Path):
    root = make_package(tmp_path)
    requirements = discover_project_requirements(root)
    assert requirements.project_name == "example-sara"
    assert requirements.project_version == "1.2.3"
    assert requirements.requires_python == ">=3.11"
    assert requirements.dependencies == ["pydantic>=2"]
    assert requirements.test_dependencies == ["pytest>=8"]


def test_manifest_binds_release_inventory_fixtures_and_conflict_status(tmp_path: Path):
    root = make_package(tmp_path)
    manifest = build_manifest(root)
    assert manifest.release_commit == "a" * 40
    assert manifest.code_inventory.file_count == 4
    assert manifest.fixture_refs == ["fixtures/case.json"]
    assert manifest.contract_status == ContractStatus.UNKNOWN_REQUIRES_REVIEW
    assert manifest.non_claims


def test_manifest_digest_is_deterministic_for_identical_inputs(tmp_path: Path):
    root = make_package(tmp_path)
    first = build_manifest(root)
    second = build_manifest(root)
    assert manifest_digest(first) == manifest_digest(second)
    assert len(manifest_digest(first)) == 64


def test_invalid_release_commit_is_rejected(tmp_path: Path):
    root = make_package(tmp_path)
    with pytest.raises(ValidationError):
        build_manifest(root, release_commit="not-a-commit")


def test_hardware_requirements_cannot_be_empty(tmp_path: Path):
    root = make_package(tmp_path)
    with pytest.raises(ValidationError):
        build_manifest(root, hardware_requirements=[])

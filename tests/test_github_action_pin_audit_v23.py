from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "github_action_pin_audit_v23.py"
SPEC = importlib.util.spec_from_file_location("v23", MODULE_PATH)
assert SPEC and SPEC.loader
v23 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = v23
SPEC.loader.exec_module(v23)


def test_exact_commit_sha_is_pinned():
    rows = v23.parse_workflow_text(
        "steps:\n  - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1\n",
        ".github/workflows/a.yml",
    )
    assert len(rows) == 1
    assert rows[0].pinned is True
    assert rows[0].kind == "github_action"


def test_major_tag_is_floating():
    rows = v23.parse_workflow_text(
        "steps:\n  - uses: actions/checkout@v7\n",
        ".github/workflows/a.yml",
    )
    assert len(rows) == 1
    assert rows[0].pinned is False
    assert rows[0].ref == "v7"


def test_local_action_is_accepted_as_local():
    rows = v23.parse_workflow_text(
        "steps:\n  - uses: ./.github/actions/local\n",
        ".github/workflows/a.yml",
    )
    assert rows[0].kind == "local"
    assert rows[0].pinned is True


def test_digest_pinned_docker_action_is_pinned():
    rows = v23.parse_workflow_text(
        "steps:\n  - uses: docker://alpine@sha256:" + "a" * 64 + "\n",
        ".github/workflows/a.yml",
    )
    assert rows[0].kind == "docker"
    assert rows[0].pinned is True


def test_tagged_docker_action_is_floating():
    rows = v23.parse_workflow_text(
        "steps:\n  - uses: docker://alpine:3.22\n",
        ".github/workflows/a.yml",
    )
    assert rows[0].kind == "docker"
    assert rows[0].pinned is False


def test_quotes_and_inline_comment_are_parsed():
    rows = v23.parse_workflow_text(
        '  - uses: "actions/setup-python@v7" # floating\n',
        ".github/workflows/a.yml",
    )
    assert len(rows) == 1
    assert rows[0].target == "actions/setup-python"
    assert rows[0].ref == "v7"

def test_sara_runtime_and_release_attestation_workflows_require_immutable_action_refs():
    root = Path(__file__).resolve().parents[1]
    high_trust_workflows = (
        ".github/workflows/sara-verified-local-v1.yml",
        ".github/workflows/sara-release-attestation.yml",
    )
    for workflow in high_trust_workflows:
        text = (root / workflow).read_text(encoding="utf-8")
        uses = v23.parse_workflow_text(text, workflow)
        assert uses, f"missing action references in {workflow}"
        floating = [use.raw for use in uses if not use.pinned]
        assert not floating, f"{workflow} contains floating actions: {floating}"

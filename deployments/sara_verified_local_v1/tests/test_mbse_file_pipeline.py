from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from worldshepherd_sara.legacy_file_ingest import load_file_backed_corpus
from worldshepherd_sara.mbse_file_pipeline import run_file_backed_conversion


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "fixtures" / "mbse_file_corpus_v1"
MANIFEST = CORPUS / "manifest.json"
PARAPHRASE_MANIFEST = CORPUS / "manifest_paraphrase.json"


def _assert_perfect_bounded_score(result: dict) -> None:
    assert result["metrics"] == {
        "entity_precision": 1.0,
        "entity_recall": 1.0,
        "relationship_precision": 1.0,
        "relationship_recall": 1.0,
    }
    assert result["negative_evidence"] == {
        "unsupported_entities": [],
        "unsupported_relationships": [],
        "missed_entities": [],
        "missed_relationships": [],
    }


def test_file_backed_corpus_loads_distinct_sources_with_expected_hashes():
    manifest, loaded = load_file_backed_corpus(MANIFEST)
    assert manifest["fixture_id"] == "WS-MBSE-FILE-SYNTH-002"
    assert len(loaded) == 4
    by_id = {item.artifact_id: item for item in loaded}
    for spec in manifest["legacy_artifacts"]:
        item = by_id[spec["artifact_id"]]
        assert item.sha256 == spec["expected_sha256"]
        assert item.size_bytes > 0
        assert item.relative_path == spec["path"]


def test_file_backed_conversion_recovers_frozen_graph_without_unsupported_inference():
    result = run_file_backed_conversion(MANIFEST)
    assert result["schema"] == "WS-MBSE-FILE-CONVERSION-V1"
    _assert_perfect_bounded_score(result)
    assert len(result["candidate_graph"]["nodes"]) == 5
    assert len(result["candidate_graph"]["edges"]) == 5
    assert len(result["output_digest"]) == 64


def test_held_out_paraphrase_recovers_same_graph_without_unsupported_inference():
    original = run_file_backed_conversion(MANIFEST)
    paraphrase = run_file_backed_conversion(PARAPHRASE_MANIFEST)
    _assert_perfect_bounded_score(paraphrase)
    original_edges = {
        (edge["source_node_id"], edge["target_node_id"], edge["relation"])
        for edge in original["candidate_graph"]["edges"]
    }
    paraphrase_edges = {
        (edge["source_node_id"], edge["target_node_id"], edge["relation"])
        for edge in paraphrase["candidate_graph"]["edges"]
    }
    assert original_edges == paraphrase_edges
    assert original["fixture_id"] != paraphrase["fixture_id"]


def test_candidate_graph_retains_file_provenance_on_nodes_and_edges():
    result = run_file_backed_conversion(MANIFEST)
    nodes = result["candidate_graph"]["nodes"]
    edges = result["candidate_graph"]["edges"]
    assert all(node["attributes"]["source_evidence"] for node in nodes)
    assert all(
        source["sha256"]
        for node in nodes
        for source in node["attributes"]["source_evidence"]
    )
    assert all(edge["attributes"]["source_evidence"]["sha256"] for edge in edges)


def test_neutral_model_remains_explicitly_non_sysml():
    result = run_file_backed_conversion(MANIFEST)
    boundary = " ".join(result["neutral_model"]["claims_boundary"])
    assert "No SysML/XMI/Cameo/MagicDraw compatibility" in boundary
    assert "PDF/image/diagram extraction is not implemented" in " ".join(
        result["claims_boundary"]
    )


def test_source_tampering_fails_before_extraction(tmp_path: Path):
    copied = tmp_path / "corpus"
    shutil.copytree(CORPUS, copied)
    manual = copied / "technical_manual.txt"
    manual.write_text(manual.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="artifact digest mismatch"):
        run_file_backed_conversion(copied / "manifest.json")


def test_manifest_path_escape_is_rejected(tmp_path: Path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    manifest = {
        "fixture_id": "PATH-ESCAPE-TEST",
        "legacy_artifacts": [
            {
                "artifact_id": "bad-001",
                "kind": "technical_manual_excerpt",
                "path": "../outside.txt",
            }
        ],
    }
    manifest_path = corpus / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="escapes corpus root"):
        load_file_backed_corpus(manifest_path)


def test_output_digest_is_deterministic_for_identical_frozen_sources():
    first = run_file_backed_conversion(MANIFEST)
    second = run_file_backed_conversion(MANIFEST)
    assert first["output_digest"] == second["output_digest"]

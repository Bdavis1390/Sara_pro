from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "proof/qcrypto/v1"
MANIFEST = BASE / "manifest.json"


def fail(message: str) -> None:
    raise SystemExit(f"QCRYPTO proof preservation: FAIL: {message}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        fail(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def commit_tree(commit_sha: str) -> str:
    text = git("cat-file", "-p", commit_sha)
    first = text.splitlines()[0] if text else ""
    if not first.startswith("tree "):
        fail(f"commit {commit_sha} does not expose a tree")
    return first.split()[1]


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("schema") != "WS-QCRYPTO-PROOF-BUNDLE-V1":
        fail("unsupported proof bundle schema")

    implementation = manifest["implementation"]
    publication = manifest["publication"]

    for section in (implementation, publication):
        commit_sha = section["commit_sha"]
        git("cat-file", "-e", f"{commit_sha}^{{commit}}")
        observed_tree = commit_tree(commit_sha)
        if observed_tree != section["tree_sha"]:
            fail(
                f"commit/tree mismatch for {commit_sha}: "
                f"expected {section['tree_sha']}, got {observed_tree}"
            )

    git("cat-file", "-e", publication["white_page_git_blob_sha1"])

    for item in manifest["preserved_evidence"]:
        path = ROOT / item["payload_path"]
        if not path.is_file():
            fail(f"preserved payload missing: {item['payload_path']}")
        observed = sha256(path)
        if observed != item["payload_sha256"]:
            fail(
                f"payload hash mismatch for {item['payload_path']}: "
                f"expected {item['payload_sha256']}, got {observed}"
            )

    bridge = json.loads((BASE / "bridge-evidence.json").read_text(encoding="utf-8"))
    if bridge.get("schema") != "WS-QCRYPTO-ECHO-DEPLOYED-BRIDGE-EVIDENCE-V1":
        fail("bridge evidence schema mismatch")
    if bridge.get("status") != "PASS":
        fail("bridge evidence is not PASS")
    expected_counts = {
        "MATCHED": 4,
        "SARA_ONLY": 0,
        "ECHO_ONLY": 1,
        "PAYLOAD_MISMATCH": 0,
    }
    if bridge.get("first_sync", {}).get("reconciliation_counts") != expected_counts:
        fail("bridge first-sync reconciliation mismatch")
    if bridge.get("replay_sync", {}).get("reconciliation_counts") != expected_counts:
        fail("bridge replay reconciliation mismatch")
    if bridge.get("execution_authority") is not False:
        fail("bridge evidence illegally promotes execution authority")
    if bridge.get("live_value_authorized") is not False:
        fail("bridge evidence illegally promotes live-value authority")
    if bridge.get("checkpoint_algorithm") != "Ed25519":
        fail("bridge checkpoint algorithm differs from preserved claim")

    publication_result = json.loads(
        (BASE / "publication-readiness.json").read_text(encoding="utf-8")
    )
    if publication_result.get("status") != "PASS":
        fail("publication evidence is not PASS")
    if publication_result.get("posting_status") != "GO":
        fail("publication posting status is not GO")
    if (
        publication_result.get("validated_implementation_anchor")
        != implementation["commit_sha"]
    ):
        fail("publication result does not point to the implementation anchor")
    if (
        publication_result.get("bridge_artifact_digest")
        != "sha256:"
        + next(
            item["original_archive_sha256"]
            for item in manifest["preserved_evidence"]
            if item["name"] == "qcrypto-echo-deployed-bridge-evidence"
        )
    ):
        fail("publication result does not point to the preserved bridge artifact digest")

    boundaries = manifest.get("required_boundaries", {})
    if not boundaries or any(value is not False for value in boundaries.values()):
        fail("proof manifest contains a promoted excluded claim")

    white_page = ROOT / publication["white_page_path"]
    if not white_page.is_file():
        fail("public white page is missing from the current tree")
    text = white_page.read_text(encoding="utf-8")
    for literal in (
        implementation["commit_sha"],
        "sha256:15dc39ef59a8bbe10e48f858f1bb42d34c9c35adb33045b9f7635201c5df698e",
        "No real third-party wallet, private key, exchange, bridge, network, or fund is targeted by this work.",
    ):
        if literal not in text:
            fail(f"white page lost required proof/claims literal: {literal}")

    result = {
        "schema": "WS-QCRYPTO-PROOF-PRESERVATION-RESULT-V1",
        "status": "PASS",
        "preservation_state": manifest["preservation_state"],
        "implementation_commit": implementation["commit_sha"],
        "implementation_tree": implementation["tree_sha"],
        "publication_commit": publication["commit_sha"],
        "publication_tree": publication["tree_sha"],
        "bridge_payload_sha256": sha256(BASE / "bridge-evidence.json"),
        "publication_payload_sha256": sha256(BASE / "publication-readiness.json"),
        "external_notarization": False,
        "signed_release_or_tag": False,
    }
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

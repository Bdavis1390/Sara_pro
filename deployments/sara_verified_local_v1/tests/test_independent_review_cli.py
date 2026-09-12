from __future__ import annotations

import json

from worldshepherd_sara.independent_review_verify import (
    IndependentReviewVerificationResult,
)
import worldshepherd_sara.independent_review_cli as cli


def _pass_result() -> IndependentReviewVerificationResult:
    return IndependentReviewVerificationResult(
        status="PASS",
        code="VERIFIED",
        detail="verified for test",
        bundle_digest_sha256="a" * 64,
    )


def _fail_result(code: str = "INVALID_JSON") -> IndependentReviewVerificationResult:
    return IndependentReviewVerificationResult(
        status="FAIL",
        code=code,
        detail="failed for test",
    )


def test_cli_reads_exact_file_bytes_emits_deterministic_json_and_exits_zero(
    tmp_path,
    monkeypatch,
    capsys,
):
    bundle_path = tmp_path / "review-bundle.json"
    expected = b'{"bundle":"opaque-test-input"}'
    bundle_path.write_bytes(expected)
    captured: dict[str, bytes] = {}

    def fake_verify(serialized: str | bytes) -> IndependentReviewVerificationResult:
        assert isinstance(serialized, bytes)
        captured["serialized"] = serialized
        return _pass_result()

    monkeypatch.setattr(cli, "verify_serialized_independent_review_export", fake_verify)

    exit_code = cli.main([str(bundle_path)])
    stdout = capsys.readouterr().out.strip()
    parsed = json.loads(stdout)

    assert exit_code == cli.EXIT_VERIFIED == 0
    assert captured["serialized"] == expected
    assert parsed["status"] == "PASS"
    assert parsed["code"] == "VERIFIED"
    assert parsed["authorization_effect"] == "NONE"
    assert parsed["readiness_effect"] == "NONE"
    assert parsed["execution_effect_applied"] is False
    assert stdout == json.dumps(parsed, sort_keys=True, separators=(",", ":"))


def test_cli_verification_failure_exits_one_and_preserves_non_authority(
    tmp_path,
    monkeypatch,
    capsys,
):
    bundle_path = tmp_path / "invalid-review-bundle.json"
    bundle_path.write_bytes(b"not-json")
    monkeypatch.setattr(
        cli,
        "verify_serialized_independent_review_export",
        lambda _serialized: _fail_result("INVALID_JSON"),
    )

    exit_code = cli.main([str(bundle_path)])
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == cli.EXIT_VERIFICATION_FAILED == 1
    assert parsed["status"] == "FAIL"
    assert parsed["code"] == "INVALID_JSON"
    assert parsed["approval_status"] == "NOT_APPROVED_BY_THIS_RESULT"
    assert parsed["authorization_effect"] == "NONE"
    assert parsed["readiness_effect"] == "NONE"
    assert parsed["execution_effect_applied"] is False


def test_cli_missing_file_returns_machine_readable_input_error(capsys, tmp_path):
    missing = tmp_path / "does-not-exist.json"

    exit_code = cli.main([str(missing)])
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == cli.EXIT_INPUT_READ_ERROR == 2
    assert parsed["status"] == "FAIL"
    assert parsed["code"] == "INPUT_READ_ERROR"
    assert parsed["verification_scope"] == "LOCAL_EVIDENCE_REPRODUCTION_ONLY"
    assert parsed["monitor_verification_status"] == "UNVERIFIED"
    assert parsed["authorization_effect"] == "NONE"
    assert parsed["readiness_effect"] == "NONE"
    assert parsed["execution_effect_applied"] is False


def test_cli_bounded_read_never_loads_more_than_limit_plus_one(
    tmp_path,
    monkeypatch,
    capsys,
):
    bundle_path = tmp_path / "oversized-review-bundle.json"
    bundle_path.write_bytes(b"abcdefgh")
    captured: dict[str, bytes] = {}
    monkeypatch.setattr(cli, "MAX_SERIALIZED_REVIEW_BUNDLE_BYTES", 4)

    def fake_verify(serialized: str | bytes) -> IndependentReviewVerificationResult:
        assert isinstance(serialized, bytes)
        captured["serialized"] = serialized
        return _fail_result("INPUT_TOO_LARGE")

    monkeypatch.setattr(cli, "verify_serialized_independent_review_export", fake_verify)

    exit_code = cli.main([str(bundle_path)])
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == cli.EXIT_VERIFICATION_FAILED == 1
    assert captured["serialized"] == b"abcde"
    assert len(captured["serialized"]) == 5
    assert parsed["code"] == "INPUT_TOO_LARGE"


def test_cli_pass_and_fail_results_never_claim_authority(
    tmp_path,
    monkeypatch,
    capsys,
):
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_bytes(b"{}")

    for result, expected_exit in (
        (_pass_result(), cli.EXIT_VERIFIED),
        (_fail_result("SCHEMA_VALIDATION_FAILED"), cli.EXIT_VERIFICATION_FAILED),
    ):
        monkeypatch.setattr(
            cli,
            "verify_serialized_independent_review_export",
            lambda _serialized, result=result: result,
        )
        assert cli.main([str(bundle_path)]) == expected_exit
        parsed = json.loads(capsys.readouterr().out)
        assert parsed["authorization_effect"] == "NONE"
        assert parsed["readiness_effect"] == "NONE"
        assert parsed["execution_effect_applied"] is False

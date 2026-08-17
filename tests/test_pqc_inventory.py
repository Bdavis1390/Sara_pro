from worldshepherd_sara.pqc_inventory import scan_repository


def test_inventory_classifies_public_key_protocol_and_hash_surfaces(tmp_path):
    (tmp_path / "service.py").write_text(
        "# TLS endpoint using RSA today; SHA-256 digest retained\n"
        "AUTH = 'OIDC'\n",
        encoding="utf-8",
    )
    report = scan_repository(tmp_path)

    categories = {row["category"] for row in report["findings"]}
    assert "classical_public_key" in categories
    assert "protocol_surface" in categories
    assert "symmetric_or_hash" in categories
    assert {row["scope"] for row in report["findings"]} == {"other_source"}
    assert report["actionable_count"] >= 1
    assert report["critical_count"] == 0
    assert report["status"] == "DISCOVERY_COMPLETE_REVIEW_REQUIRED"


def test_inventory_flags_private_key_material(tmp_path):
    (tmp_path / "bad.txt").write_text(
        "-----BEGIN PRIVATE KEY-----\nnot-a-real-key\n",
        encoding="utf-8",
    )
    report = scan_repository(tmp_path)

    assert report["critical_count"] == 1
    assert report["reference_critical_count"] == 0
    assert report["status"] == "CRITICAL_REVIEW_REQUIRED"


def test_ml_dsa_is_not_misclassified_as_classical_dsa(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "pqc.md").write_text(
        "Use ML-DSA (FIPS 204) as a post-quantum signature candidate.\n",
        encoding="utf-8",
    )
    report = scan_repository(tmp_path)

    pqc_tokens = {
        row["token"].upper()
        for row in report["findings"]
        if row["category"] == "pqc_standard"
    }
    classical_tokens = {
        row["token"].upper()
        for row in report["findings"]
        if row["category"] == "classical_public_key"
    }
    assert "ML-DSA" in pqc_tokens
    assert "DSA" not in classical_tokens
    assert {row["scope"] for row in report["findings"]} == {"documentation"}


def test_generated_qrf_artifacts_are_excluded_from_scan(tmp_path):
    artifacts = tmp_path / ".qrf-artifacts"
    artifacts.mkdir()
    (artifacts / "generated.json").write_text(
        '{"text": "RSA TLS PRIVATE_KEY"}\n', encoding="utf-8"
    )
    (tmp_path / "clean.py").write_text("VALUE = 1\n", encoding="utf-8")

    report = scan_repository(tmp_path)

    assert report["finding_count"] == 0
    assert report["critical_count"] == 0


def test_fail_on_private_key_control_flag_is_not_a_credential_finding(tmp_path):
    (tmp_path / "workflow.yml").write_text(
        "run: python scanner.py --fail-on-private-key\n",
        encoding="utf-8",
    )
    (tmp_path / "service.py").write_text(
        "private_key = load_secret()\n",
        encoding="utf-8",
    )

    report = scan_repository(tmp_path)
    tokens = [
        row["token"].lower()
        for row in report["findings"]
        if row["category"] == "credential_surface"
    ]

    assert tokens == ["private_key"]

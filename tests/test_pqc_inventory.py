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
    assert report["critical_count"] == 0
    assert report["status"] == "DISCOVERY_COMPLETE_REVIEW_REQUIRED"


def test_inventory_flags_private_key_material(tmp_path):
    (tmp_path / "bad.txt").write_text(
        "-----BEGIN PRIVATE KEY-----\nnot-a-real-key\n",
        encoding="utf-8",
    )
    report = scan_repository(tmp_path)

    assert report["critical_count"] == 1
    assert report["status"] == "CRITICAL_REVIEW_REQUIRED"

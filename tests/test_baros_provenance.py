from baros.provenance import installed_versions, runtime_provenance


def test_runtime_provenance_is_stable_within_process_and_hashed():
    first = runtime_provenance()
    second = runtime_provenance()
    assert first == second
    assert len(first["environment_sha256"]) == 64
    assert first["python"]["implementation"]
    assert first["python"]["version"]
    assert first["platform"]["system"]
    assert first["platform"]["machine"]


def test_expected_verification_distributions_are_explicitly_recorded():
    versions = installed_versions()
    assert set(versions) == {"numpy", "numba", "pydicom", "pymedphys", "pytest"}
    assert all(value != "NOT_INSTALLED" for value in versions.values())

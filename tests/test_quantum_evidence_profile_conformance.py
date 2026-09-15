from worldshepherd_sara.quantum_evidence_profile_conformance import run_profile_conformance


def test_quantum_mission_evidence_profile_conformance_suite_passes_all_declared_cases():
    report = run_profile_conformance(repository_root=".")
    assert report.cases_total == 10
    assert report.cases_passed == 10
    assert report.passed is True
    assert all(case.passed for case in report.cases)


def test_conformance_suite_contains_required_fail_closed_and_acceptance_cases():
    report = run_profile_conformance(repository_root=".")
    ids = {case.case_id for case in report.cases}
    assert ids == {f"QME-{index:02d}" for index in range(1, 11)}
    titles = " | ".join(case.title for case in report.cases)
    assert "digest mismatch" in titles
    assert "gate skipping" in titles
    assert "simulator" in titles
    assert "reused result identity" in titles
    assert "statistically consistent" in titles
    assert "managed QPU job" in titles
    assert "human review" in titles.lower()
    assert "canonical state" in titles
    assert "DDIL" in titles

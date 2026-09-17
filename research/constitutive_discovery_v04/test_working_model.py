from working_model import generate, compare, CLAIMS_STATE, EXECUTION_STATUS

def test_latent_state_beats_memoryless():
    r=compare(generate(n=1000,noise_std=.05))
    assert r["latent_state_required"]
    assert r["rmse_improvement_ratio"] > 2.0

def test_recovered_parameters_are_physical():
    r=compare(generate(n=1000,noise_std=.05))["one_state"]
    assert r["E_inf"] > 0
    assert r["E1"] > 0
    assert r["tau"] > 0

def test_governance_boundary_is_fail_closed():
    r=compare(generate(n=500,noise_std=.05))
    assert r["claims_state"] == CLAIMS_STATE
    assert r["execution_status"] == EXECUTION_STATUS
    assert EXECUTION_STATUS == "PROPOSED_NOT_EXECUTED"

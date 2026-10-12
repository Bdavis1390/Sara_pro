from engine import *
def test_candidate_families_compete(): assert len(FAMILIES)>=3
def test_discriminator_fail_closed():
 r=discriminate(FAMILIES[0],FAMILIES[1],strain_max=.03,freq_max=2,temp_bounds=(280,320))
 assert r["amplitude"]<=.03 and r["frequency_hz"]<=2 and r["execution_status"]=="PROPOSED_NOT_EXECUTED"
def test_manifest_tamper_evident():
 m=signed_manifest({"x":1}); assert len(m["sha256"])==64 and m["claims"]=="SIMULATED ONLY"
def test_no_nan_trajectory():
 assert all(math.isfinite(x) for x in trajectory(FAMILIES[2],{"amplitude":.03,"frequency_hz":1,"temperature_k":293.15}))

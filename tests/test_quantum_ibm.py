import pytest

from worldshepherd_sara.quantum_ibm import run_bell_on_ibm_hardware


def test_ibm_hardware_adapter_requires_injected_token_before_network_access():
    with pytest.raises(ValueError, match="token"):
        run_bell_on_ibm_hardware(token="")


def test_ibm_hardware_adapter_rejects_invalid_shots_before_network_access():
    with pytest.raises(ValueError, match="shots"):
        run_bell_on_ibm_hardware(token="placeholder", shots=0)

from types import SimpleNamespace

import worldshepherd_sara.quantum_cudaq as cudaq_adapter


class _FakeKernel:
    def __init__(self):
        self.ops = []

    def qalloc(self, count):
        self.ops.append(("qalloc", count))
        return [0, 1]

    def h(self, qubit):
        self.ops.append(("h", qubit))

    def cx(self, control, target):
        self.ops.append(("cx", control, target))

    def mz(self, qubits):
        self.ops.append(("mz", tuple(qubits)))


class _FakeCudaQ:
    def __init__(self):
        self.target = None
        self.options = None
        self.kernel = _FakeKernel()

    def set_target(self, target, **options):
        self.target = target
        self.options = options

    def get_target(self):
        return SimpleNamespace(name=self.target)

    def make_kernel(self):
        return self.kernel

    def sample(self, kernel, shots_count):
        assert kernel is self.kernel
        assert shots_count == 1000
        return {"00": 501, "11": 493, "01": 3, "10": 3}


def test_cudaq_canonical_program_digest_is_stable_sha256():
    digest = cudaq_adapter.canonical_cudaq_bell_digest()
    assert digest.startswith("sha256:")
    assert len(digest) == 71


def test_cudaq_portable_runner_uses_explicit_target_and_preserves_unverified_hardware_claim(monkeypatch):
    fake = _FakeCudaQ()
    monkeypatch.setattr(cudaq_adapter.importlib, "import_module", lambda name: fake)
    monkeypatch.setattr(cudaq_adapter.importlib.metadata, "version", lambda name: "0.15.0")

    result = cudaq_adapter.run_bell_cudaq(
        target="ionq",
        shots=1000,
        target_options={"qpu": "qpu.fixture"},
    )

    assert result.requested_target == "ionq"
    assert result.resolved_target == "ionq"
    assert result.target_options["qpu"] == "qpu.fixture"
    assert result.counts["00"] == 501
    assert result.correlated_fraction == 0.994
    assert result.result_digest.startswith("sha256:")
    assert result.evidence_class == "portable_execution_unverified_hardware_provenance"
    assert "not external-QPU evidence" in result.claim_control
    assert fake.kernel.ops == [
        ("qalloc", 2),
        ("h", 0),
        ("cx", 0, 1),
        ("mz", (0, 1)),
    ]


def test_cudaq_emulation_flag_is_preserved_as_non_hardware(monkeypatch):
    fake = _FakeCudaQ()
    monkeypatch.setattr(cudaq_adapter.importlib, "import_module", lambda name: fake)
    monkeypatch.setattr(cudaq_adapter.importlib.metadata, "version", lambda name: "0.15.0")

    result = cudaq_adapter.run_bell_cudaq(
        target="quantinuum",
        shots=1000,
        target_options={"emulate": True},
    )
    assert result.target_options["emulate"] is True
    assert result.evidence_class == "portable_execution_unverified_hardware_provenance"


def test_cudaq_runner_rejects_invalid_shots_before_optional_import():
    try:
        cudaq_adapter.run_bell_cudaq(target="qpp-cpu", shots=0)
    except ValueError as exc:
        assert "shots" in str(exc)
    else:
        raise AssertionError("invalid shots should fail before importing cudaq")

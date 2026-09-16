from cisnet.model import LinkState, LinkType
from cisnet.policy import PrimeSentinelPolicy
from cisnet.provenance import EchoLedger
from cisnet.simulator import build_reference_simulation


def test_reference_100gb_survives_fault_campaign():
    sim = build_reference_simulation(100_000_000_000)
    result = sim.run(max_time_s=5000)
    assert result.completed
    assert result.received_bytes == result.payload_bytes
    assert result.dropped_bytes == 0
    assert result.ledger_valid
    assert result.failovers >= 4
    assert result.node_restarts == 1
    assert result.max_relay_buffer_bytes > 0
    assert result.completed_at_s is not None and result.completed_at_s < 5000
    assert result.link_bytes["bc_rf"] > 0
    assert result.link_bytes["ab_rf"] > 0


def test_policy_rejects_untrusted_and_low_survival_links():
    policy = PrimeSentinelPolicy(minimum_survival=0.4)
    untrusted = LinkState("x", "A", "B", LinkType.OPTICAL, 100, trusted=False)
    weak = LinkState("y", "A", "B", LinkType.OPTICAL, 100, survival_probability=0.2)
    good = LinkState("z", "A", "B", LinkType.RF, 20, survival_probability=0.99)
    assert not policy.authorize(untrusted).allowed
    assert not policy.authorize(weak).allowed
    assert policy.select([untrusted, weak, good]).name == "z"


def test_echo_ledger_detects_integrity_chain_break():
    ledger = EchoLedger()
    ledger.append(0, "a", value=1)
    ledger.append(1, "b", value=2)
    assert ledger.verify()
    original = ledger.events[1]
    ledger.events[1] = type(original)(seq=original.seq, t_s=original.t_s, event=original.event, detail={"value": 999}, prev_hash=original.prev_hash, hash=original.hash)
    assert not ledger.verify()

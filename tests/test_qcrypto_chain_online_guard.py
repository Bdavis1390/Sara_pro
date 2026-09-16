from security.qcrypto.chain_online_guard import ChainOnlineEvidence, assess_chain_online


def evidence(**overrides):
    data = dict(
        bitcoin_reported_chain="signet",
        bitcoin_blocks=100,
        bitcoin_headers=100,
        bitcoin_verification_progress=1.0,
        ethereum_chain_id=560048,
        ethereum_execution_block_number=200,
        ethereum_consensus_head_slot=300,
        ethereum_consensus_sync_distance=0,
        ethereum_consensus_is_syncing=False,
        external_signer_boundary_defined=True,
    )
    data.update(overrides)
    return ChainOnlineEvidence(**data)


def test_fully_synced_public_testnet_observers_promote_only_to_online_and_synced():
    result = assess_chain_online(evidence())
    assert result.state == "PUBLIC_TESTNET_NODES_ONLINE_AND_SYNCED"
    assert result.synchronized is True
    assert result.node_online_evidence_valid is True
    assert result.transaction_execution_permitted is False
    assert result.validator_activation_permitted is False
    assert result.private_key_operations_permitted is False
    assert result.mainnet_permitted is False
    assert result.end_to_end_post_quantum_security_established is False


def test_valid_chain_identity_while_syncing_does_not_claim_synced():
    result = assess_chain_online(
        evidence(
            bitcoin_blocks=95,
            bitcoin_headers=100,
            bitcoin_verification_progress=0.95,
            ethereum_consensus_sync_distance=25,
            ethereum_consensus_is_syncing=True,
        )
    )
    assert result.state == "PUBLIC_TESTNET_NODES_ONLINE_SYNCING"
    assert result.synchronized is False
    assert result.node_online_evidence_valid is True


def test_bitcoin_mainnet_substitution_is_rejected():
    result = assess_chain_online(evidence(bitcoin_reported_chain="main"))
    assert result.state == "NODE_ONLINE_EVIDENCE_REJECTED"
    assert any("chain=signet" in blocker for blocker in result.blockers)


def test_ethereum_mainnet_substitution_is_rejected():
    result = assess_chain_online(evidence(ethereum_chain_id=1))
    assert result.state == "NODE_ONLINE_EVIDENCE_REJECTED"
    assert any("560048" in blocker for blocker in result.blockers)


def test_observer_stage_rejects_key_material_and_execution_switches():
    for override in (
        {"wallet_private_key_present": True},
        {"validator_private_key_present": True},
        {"live_bitcoin_broadcast_enabled": True},
        {"ethereum_validator_activation_enabled": True},
    ):
        result = assess_chain_online(evidence(**override))
        assert result.state == "NODE_ONLINE_EVIDENCE_REJECTED"
        assert result.transaction_execution_permitted is False
        assert result.validator_activation_permitted is False

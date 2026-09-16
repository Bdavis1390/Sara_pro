from security.qcrypto.chain_deployment_guard import (
    ChainDeploymentEvidence,
    assess_chain_deployment,
)


def ready_evidence(**overrides):
    data = dict(
        bitcoin_network="SIGNET",
        ethereum_network="HOODI",
        ethereum_chain_id=560048,
        bitcoin_image_digest_pinned=True,
        ethereum_execution_image_digest_pinned=True,
        ethereum_consensus_image_digest_pinned=True,
        bitcoin_persistent_storage=True,
        ethereum_execution_persistent_storage=True,
        ethereum_consensus_persistent_storage=True,
        bitcoin_healthcheck_defined=True,
        ethereum_execution_healthcheck_defined=True,
        ethereum_consensus_healthcheck_defined=True,
        bitcoin_rpc_private_only=True,
        ethereum_engine_api_private_only=True,
        ethereum_beacon_admin_private_only=True,
        external_signer_boundary_defined=True,
        rollback_plan_defined=True,
        monitoring_plan_defined=True,
        evidence_receipt_enabled=True,
    )
    data.update(overrides)
    return ChainDeploymentEvidence(**data)


def test_exact_signet_hoodi_package_can_reach_host_ready_only():
    result = assess_chain_deployment(ready_evidence())
    assert result.state == "PUBLIC_TESTNET_CHAIN_DEPLOYMENT_HOST_READY"
    assert result.bitcoin_state == "BITCOIN_SIGNET_NODE_HOST_READY"
    assert result.ethereum_state == "ETHEREUM_HOODI_NODE_HOST_READY"
    assert result.host_deployment_ready is True
    assert result.public_testnet_only is True
    assert result.mainnet_permitted is False
    assert result.private_key_operations_permitted is False
    assert result.live_value_authorized is False


def test_bitcoin_mainnet_substitution_fails_closed():
    result = assess_chain_deployment(
        ready_evidence(bitcoin_network="MAINNET", bitcoin_mainnet_enabled=True)
    )
    assert result.state == "CHAIN_DEPLOYMENT_BLOCKED"
    assert any("SIGNET" in item for item in result.blockers)
    assert any("Mainnet" in item for item in result.blockers)


def test_ethereum_mainnet_or_wrong_chain_id_fails_closed():
    result = assess_chain_deployment(
        ready_evidence(
            ethereum_network="MAINNET",
            ethereum_chain_id=1,
            ethereum_mainnet_enabled=True,
        )
    )
    assert result.state == "CHAIN_DEPLOYMENT_BLOCKED"
    assert any("HOODI" in item for item in result.blockers)


def test_wallet_or_validator_key_mounts_are_forbidden():
    wallet = assess_chain_deployment(ready_evidence(wallet_private_key_mounted=True))
    validator = assess_chain_deployment(ready_evidence(validator_private_key_mounted=True))
    assert wallet.state == "CHAIN_DEPLOYMENT_BLOCKED"
    assert validator.state == "CHAIN_DEPLOYMENT_BLOCKED"
    assert wallet.private_key_operations_permitted is False
    assert validator.private_key_operations_permitted is False


def test_live_broadcast_or_validator_activation_cannot_be_enabled():
    btc = assess_chain_deployment(ready_evidence(live_bitcoin_broadcast_enabled=True))
    eth = assess_chain_deployment(ready_evidence(ethereum_validator_activation_enabled=True))
    assert btc.state == "CHAIN_DEPLOYMENT_BLOCKED"
    assert eth.state == "CHAIN_DEPLOYMENT_BLOCKED"
    assert btc.live_value_authorized is False
    assert eth.live_value_authorized is False


def test_digest_pinning_and_health_checks_are_required():
    result = assess_chain_deployment(
        ready_evidence(
            bitcoin_image_digest_pinned=False,
            ethereum_consensus_healthcheck_defined=False,
        )
    )
    assert result.host_deployment_ready is False
    assert result.state == "CHAIN_DEPLOYMENT_BLOCKED"

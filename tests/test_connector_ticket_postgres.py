from worldshepherd_sara.connector_ticket_postgres import (
    CLAIM_SQL,
    CREATE_TABLE_SQL,
    REGISTER_SQL,
    STATUS_SQL,
    PostgresClaimStore,
)


def test_claim_sql_is_single_statement_database_time_compare_and_set():
    normalized = " ".join(CLAIM_SQL.split()).lower()
    assert normalized.startswith("update worldshepherd_connector_read_tickets")
    assert "consumed_at is null" in normalized
    assert "set consumed_at = extract(epoch from clock_timestamp())" in normalized
    assert "expires_at >= extract(epoch from clock_timestamp())" in normalized
    assert "ticket_sha256 = %s" in normalized
    assert "returning expires_at, consumed_at" in normalized


def test_register_sql_uses_database_time_plus_signed_ttl():
    normalized = " ".join(REGISTER_SQL.split()).lower()
    assert "extract(epoch from clock_timestamp()) + %s" in normalized
    assert "on conflict (ticket_id) do nothing" in normalized


def test_schema_contains_only_minimal_claim_columns():
    normalized = " ".join(CREATE_TABLE_SQL.split()).lower()
    for required in ("ticket_id", "ticket_sha256", "expires_at", "consumed_at"):
        assert required in normalized
    for forbidden in ("context", "credential", "result", "policy_envelope"):
        assert forbidden not in normalized


def test_status_query_uses_database_time_for_expiry_diagnosis():
    normalized = " ".join(STATUS_SQL.split()).lower()
    assert "ticket_sha256" in normalized
    assert "expires_at" in normalized
    assert "consumed_at" in normalized
    assert "expires_at < extract(epoch from clock_timestamp()) as expired" in normalized
    assert "where ticket_id = %s" in normalized


def test_adapter_constructor_is_connection_factory_only():
    factory = lambda: None
    store = PostgresClaimStore(factory)
    assert store._connection_factory is factory
    assert not hasattr(store, "password")
    assert not hasattr(store, "connection_string")
    assert not hasattr(store, "api_key")

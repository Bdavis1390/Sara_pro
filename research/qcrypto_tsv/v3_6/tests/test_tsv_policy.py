import unittest
from copy import deepcopy
from datetime import datetime, timezone

from worldshepherd_qcrypto_kms.tsv.policy import evaluate_tsv, Status

NOW = datetime(2026, 9, 18, 21, 50, tzinfo=timezone.utc)

BASE = {
    "smart_contract_source_public": True,
    "smart_contract_auditable": True,
    "public_permissionless_ledger": True,
    "tsv_is_us_person": True,
    "identity_verification": True,
    "wallet_verification": True,
    "ofac_screening": True,
    "aml_cft_controls": True,
    "public_notice_published_at": "2026-07-01T00:00:00Z",
    "operations_start_at": "2026-08-01T00:00:00Z",
    "tokenizer_unaffiliated_third_party": True,
    "issuer_notice_received_at": "2026-07-01T00:00:00Z",
    "symbol_trading_start_at": "2026-08-01T00:00:00Z",
    "issuer_objected_within_30_days": False,
    "primary_issuance_or_initial_offering": False,
    "rights": {
        "same_company_interest": True,
        "same_dividends": True,
        "same_voting": True,
        "same_liquidation_share": True,
    },
    "tier": 1,
    "aggregate_affiliate_symbol_count": 75,
    "aggregate_affiliate_adv_share": 0.0025,
    "prior_volume_threshold_breaches": 0,
    "transaction_publication_delay_minutes": 10,
    "public_transaction_history_days": 30,
    "transaction_data_machine_readable": True,
    "transaction_data_free_public": True,
    "transaction_data_usd_denominated": True,
    "transaction_fields_complete": True,
    "underlying_primary_exchange_stopped": False,
    "tokenized_stock_stopped": False,
    "significant_operational_event": False,
    "borrowing_on_tsv": False,
    "hypothecation": False,
    "participant_purchase_credit": False,
    "claims_sec_registered_approved_or_endorsed": False,
    "public_notice_disclaims_sec_registration": True,
    "records_current": True,
    "records_maintained_in_us": True,
    "records_human_readable": True,
    "records_usable_electronic": True,
    "post_exemption_retention_years": 3,
    "code_review": True,
    "security_audit": True,
    "post_deployment_monitoring": True,
    "authorization_controls": True,
    "stress_testing": True,
    "business_continuity": True,
    "incident_response": True,
    "market_abuse_monitoring": True,
    "risk_disclosure": True,
    "stoppage_procedures_disclosed": True,
}


def by_id(ev, cid):
    return next(f for f in ev.findings if f.control_id == cid)


class TestPolicy(unittest.TestCase):
    def test_happy_path_allows(self):
        self.assertEqual(evaluate_tsv(BASE, now=NOW).decision, "ALLOW")

    def test_private_ledger_denies(self):
        s = deepcopy(BASE); s["public_permissionless_ledger"] = False
        self.assertEqual(evaluate_tsv(s, now=NOW).decision, "DENY")

    def test_notice_under_30_days_denies(self):
        s = deepcopy(BASE); s["public_notice_published_at"] = "2026-07-15T00:00:00Z"
        self.assertEqual(by_id(evaluate_tsv(s, now=NOW), "TSV-NOTICE-001").status, Status.FAIL)

    def test_issuer_objection_denies(self):
        s = deepcopy(BASE); s["issuer_objected_within_30_days"] = True
        self.assertEqual(by_id(evaluate_tsv(s, now=NOW), "TSV-ISSUER-001").status, Status.FAIL)

    def test_primary_issuance_denies(self):
        s = deepcopy(BASE); s["primary_issuance_or_initial_offering"] = True
        self.assertEqual(by_id(evaluate_tsv(s, now=NOW), "TSV-OFFER-001").status, Status.FAIL)

    def test_rights_gap_denies(self):
        s = deepcopy(BASE); s["rights"]["same_voting"] = False
        self.assertEqual(by_id(evaluate_tsv(s, now=NOW), "TSV-RIGHTS-001").status, Status.FAIL)

    def test_tier1_symbol_limit(self):
        s = deepcopy(BASE); s["aggregate_affiliate_symbol_count"] = 76
        self.assertEqual(by_id(evaluate_tsv(s, now=NOW), "TSV-LIMIT-001").status, Status.FAIL)

    def test_tier2_limits(self):
        s = deepcopy(BASE); s["tier"] = 2; s["aggregate_affiliate_symbol_count"] = 250; s["aggregate_affiliate_adv_share"] = 0.025
        self.assertEqual(evaluate_tsv(s, now=NOW).decision, "ALLOW")

    def test_first_volume_breach_warns(self):
        s = deepcopy(BASE); s["aggregate_affiliate_adv_share"] = 0.0026; s["prior_volume_threshold_breaches"] = 0
        ev = evaluate_tsv(s, now=NOW)
        self.assertEqual(by_id(ev, "TSV-LIMIT-002").status, Status.WARN)
        self.assertEqual(ev.decision, "ALLOW_WITH_WARNINGS")

    def test_subsequent_volume_breach_denies(self):
        s = deepcopy(BASE); s["aggregate_affiliate_adv_share"] = 0.0026; s["prior_volume_threshold_breaches"] = 1
        self.assertEqual(by_id(evaluate_tsv(s, now=NOW), "TSV-LIMIT-002").status, Status.FAIL)

    def test_publication_over_ten_minutes_denies(self):
        s = deepcopy(BASE); s["transaction_publication_delay_minutes"] = 11
        self.assertEqual(by_id(evaluate_tsv(s, now=NOW), "TSV-TRANS-001").status, Status.FAIL)

    def test_underlying_halt_requires_token_halt(self):
        s = deepcopy(BASE); s["underlying_primary_exchange_stopped"] = True; s["tokenized_stock_stopped"] = False
        self.assertEqual(by_id(evaluate_tsv(s, now=NOW), "TSV-HALT-001").status, Status.FAIL)

    def test_operational_event_notification(self):
        s = deepcopy(BASE); s.update({"significant_operational_event": True, "participants_notified_immediately": True, "sec_notified_promptly": False, "remediation_tracked": True})
        self.assertEqual(by_id(evaluate_tsv(s, now=NOW), "TSV-OPS-001").status, Status.FAIL)

    def test_leverage_denies(self):
        s = deepcopy(BASE); s["participant_purchase_credit"] = True
        self.assertEqual(by_id(evaluate_tsv(s, now=NOW), "TSV-LEV-001").status, Status.FAIL)

    def test_sec_approval_claim_denies(self):
        s = deepcopy(BASE); s["claims_sec_registered_approved_or_endorsed"] = True
        self.assertEqual(by_id(evaluate_tsv(s, now=NOW), "TSV-DISC-001").status, Status.FAIL)

    def test_records_three_years(self):
        s = deepcopy(BASE); s["post_exemption_retention_years"] = 2
        self.assertEqual(by_id(evaluate_tsv(s, now=NOW), "TSV-REC-001").status, Status.FAIL)

    def test_missing_security_audit_denies(self):
        s = deepcopy(BASE); s["security_audit"] = False
        self.assertEqual(by_id(evaluate_tsv(s, now=NOW), "TSV-SAFE-001").status, Status.FAIL)

    def test_issuer_gate_not_triggered_for_affiliated_or_issuer_tokenization(self):
        s = deepcopy(BASE); s["tokenizer_unaffiliated_third_party"] = False; s["issuer_notice_received_at"] = None; s["symbol_trading_start_at"] = None
        self.assertEqual(by_id(evaluate_tsv(s, now=NOW), "TSV-ISSUER-001").status, Status.NOT_EVALUATED)


if __name__ == "__main__":
    unittest.main()

import unittest
from decimal import Decimal

from worldshepherd_qcrypto_kms.tsv.volume_limits import (
    AffiliateSymbolInventory, AffiliateVolumeObservation,
    aggregate_affiliate_symbol_counts, aggregate_affiliate_volume,
)


class TestTsvVolumeLimits(unittest.TestCase):
    def obs(self, venue, num, den=100000, tier=1):
        return AffiliateVolumeObservation.create(venue_id=venue, symbol="ABC", tier=tier, tokenized_average_daily_share_volume=num, sip_prior_month_average_daily_share_volume=den)

    def test_exact_tier1_threshold_is_within_limit(self):
        r = aggregate_affiliate_volume([self.obs("A", 250)])
        self.assertEqual(Decimal(r.aggregate_share), Decimal("0.0025"))
        self.assertFalse(r.exceeded)

    def test_affiliate_aggregation_can_exceed(self):
        r = aggregate_affiliate_volume([self.obs("A", 150), self.obs("B", 110)])
        self.assertTrue(r.exceeded)
        self.assertEqual(r.affiliate_count, 2)

    def test_inconsistent_denominator_rejected(self):
        with self.assertRaises(ValueError):
            aggregate_affiliate_volume([self.obs("A", 100, 100000), self.obs("B", 100, 90000)])

    def test_duplicate_venue_rejected(self):
        with self.assertRaises(ValueError):
            aggregate_affiliate_volume([self.obs("A", 100), self.obs("A", 100)])

    def test_symbol_inventory_aggregates_unique_symbols(self):
        a = AffiliateSymbolInventory.create("A", tier1_symbols=["AAA", "BBB"], tier2_symbols=["CCC"])
        b = AffiliateSymbolInventory.create("B", tier1_symbols=["BBB", "DDD"], tier2_symbols=["EEE"])
        r = aggregate_affiliate_symbol_counts([a, b])
        self.assertEqual(r["tier1_unique_symbols"], 3)
        self.assertEqual(r["tier2_unique_symbols"], 2)

    def test_cross_affiliate_tier_disagreement_rejected(self):
        a = AffiliateSymbolInventory.create("A", tier1_symbols=["AAA"])
        b = AffiliateSymbolInventory.create("B", tier2_symbols=["AAA"])
        with self.assertRaises(ValueError):
            aggregate_affiliate_symbol_counts([a, b])

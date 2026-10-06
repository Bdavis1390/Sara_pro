import unittest

from research.ws_market_v0_1.ws_market import (
    Agent,
    DuplicateEventError,
    EventLedger,
    NewsEvent,
    classify_bid_shading,
    run_sealed_bid_market,
)


class MarketTests(unittest.TestCase):
    def scenario(self):
        agents = [
            Agent("a", "widget", 10.0, 1.0),
            Agent("b", "widget", 8.0, 1.0),
            Agent("c", "widget", 7.0, 0.5),
        ]
        news = [
            NewsEvent("news-1", "widget", 2.0, 1),
            NewsEvent("news-2", "other", 100.0, 2),
        ]
        return agents, news

    def test_nominal_efficiency_and_second_price(self):
        agents, news = self.scenario()
        result, ledger = run_sealed_bid_market(
            asset="widget",
            agents=agents,
            news=news,
            reserve_price=1.0,
        )
        self.assertEqual(result.winner_id, "a")
        self.assertEqual(result.clearing_price, 10.0)
        self.assertEqual(result.allocative_efficiency, 1.0)
        self.assertTrue(ledger.verify())

    def test_deterministic_replay_digest(self):
        agents, news = self.scenario()
        result_1, ledger_1 = run_sealed_bid_market(
            asset="widget",
            agents=agents,
            news=news,
        )
        result_2, ledger_2 = run_sealed_bid_market(
            asset="widget",
            agents=reversed(agents),
            news=reversed(news),
        )
        self.assertEqual(result_1, result_2)
        self.assertEqual(ledger_1.digest(), ledger_2.digest())

    def test_duplicate_event_rejected(self):
        ledger = EventLedger()
        ledger.append("x", "news", {"v": 1})
        with self.assertRaises(DuplicateEventError):
            ledger.append("x", "news", {"v": 2})

    def test_shading_classifier(self):
        agents, news = self.scenario()
        result, _ = run_sealed_bid_market(
            asset="widget",
            agents=agents,
            news=news,
        )
        labels = {
            classification.agent_id: classification.label
            for classification in classify_bid_shading(result)
        }
        self.assertEqual(labels["a"], "near_value")
        self.assertEqual(labels["c"], "underbid")


if __name__ == "__main__":
    unittest.main()

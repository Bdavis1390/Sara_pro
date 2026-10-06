import unittest

from research.ws_market_v0_2.agent_probe import (
    AgentDescriptor,
    AgentProbeError,
    ExperimentManifest,
    FunctionAgentAdapter,
    ProbeObservation,
    run_probe,
)


class AgentProbeTests(unittest.TestCase):
    def manifest(self):
        return ExperimentManifest(
            experiment_id="exp-1",
            seed=7,
            market_mechanism="sealed_bid_second_price",
            code_revision="deadbeef",
            prompt_template_hash="prompt-hash",
            scenario_hash="scenario-hash",
            agents=(
                AgentDescriptor("agent-b", "test", "b", "1"),
                AgentDescriptor("agent-a", "test", "a", "1"),
            ),
        )

    def adapters(self):
        return [
            FunctionAgentAdapter(
                AgentDescriptor("agent-a", "test", "a", "1"),
                lambda obs: {
                    "bid": obs["market_state"]["reference"] + 1,
                    "reason_code": "A",
                },
            ),
            FunctionAgentAdapter(
                AgentDescriptor("agent-b", "test", "b", "1"),
                lambda obs: {
                    "bid": obs["market_state"]["reference"] - 1,
                    "reason_code": "B",
                },
            ),
        ]

    def observations(self):
        return [
            ProbeObservation(
                "obs-1",
                {"asset": "widget", "reference": 10},
                ({"headline": "supply shock", "delta": 1},),
            ),
            ProbeObservation(
                "obs-2",
                {"asset": "widget", "reference": 12},
            ),
        ]

    def test_manifest_digest_is_order_independent_for_agent_declarations(self):
        manifest = self.manifest()
        reversed_manifest = ExperimentManifest(
            experiment_id=manifest.experiment_id,
            seed=manifest.seed,
            market_mechanism=manifest.market_mechanism,
            code_revision=manifest.code_revision,
            prompt_template_hash=manifest.prompt_template_hash,
            scenario_hash=manifest.scenario_hash,
            agents=tuple(reversed(manifest.agents)),
        )
        self.assertEqual(manifest.digest(), reversed_manifest.digest())

    def test_probe_records_same_envelope_when_adapter_order_changes(self):
        manifest = self.manifest()
        run_a, ledger_a = run_probe(
            manifest,
            self.adapters(),
            self.observations(),
        )
        run_b, ledger_b = run_probe(
            manifest,
            reversed(self.adapters()),
            self.observations(),
        )
        self.assertEqual(run_a, run_b)
        self.assertEqual(ledger_a.digest(), ledger_b.digest())
        self.assertTrue(ledger_a.verify())

    def test_descriptor_mismatch_fails_closed(self):
        manifest = self.manifest()
        adapters = self.adapters()
        adapters[0] = FunctionAgentAdapter(
            AgentDescriptor("agent-a", "wrong-provider", "a", "1"),
            adapters[0].function,
        )
        with self.assertRaises(AgentProbeError):
            run_probe(manifest, adapters, self.observations())

    def test_duplicate_observation_fails_closed(self):
        observation = self.observations()[0]
        with self.assertRaises(AgentProbeError):
            run_probe(
                self.manifest(),
                self.adapters(),
                [observation, observation],
            )

    def test_adapter_cannot_mutate_recorded_observation(self):
        adapters = self.adapters()

        def mutating_agent(observation):
            observation["market_state"]["reference"] = -999
            observation["news"].append({"headline": "injected"})
            return {"bid": 1, "reason_code": "MUTATOR"}

        adapters[0] = FunctionAgentAdapter(
            adapters[0].descriptor,
            mutating_agent,
        )
        _, ledger = run_probe(
            self.manifest(),
            adapters,
            self.observations(),
        )
        self.assertTrue(ledger.verify())
        observed = [
            event.payload
            for event in ledger.events
            if event.kind == "observation"
        ][0]
        self.assertEqual(observed["market_state"]["reference"], 10)
        self.assertEqual(len(observed["news"]), 1)

    def test_returned_action_mutation_cannot_corrupt_ledger(self):
        run, ledger = run_probe(
            self.manifest(),
            self.adapters(),
            self.observations(),
        )
        run.records[0].action["bid"] = -12345
        self.assertTrue(ledger.verify())

    def test_non_object_action_fails_closed(self):
        adapters = self.adapters()
        adapters[0] = FunctionAgentAdapter(
            adapters[0].descriptor,
            lambda obs: ["not", "an", "object"],
        )
        with self.assertRaises(AgentProbeError):
            run_probe(self.manifest(), adapters, self.observations())


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
import os
import unittest
from unittest.mock import patch

from runtime.deliberative_controller import Action, DeliberativeController, Verification
from runtime.http_json_transport import HTTPJSONEndpoint, HTTPJSONTransport
from runtime.protected_suite_runner import FinalAdjudication, ProtectedTask, run_protected_suite


class _FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return b'{"success":true,"recoverable":false,"feedback":"pass"}'


class HTTPTransportTests(unittest.TestCase):
    def test_plain_http_rejected_except_explicit_localhost(self):
        with self.assertRaises(ValueError):
            HTTPJSONEndpoint("http://example.com/model")
        endpoint = HTTPJSONEndpoint("http://127.0.0.1:9000/model", allow_local_http=True)
        self.assertEqual(endpoint.url, "http://127.0.0.1:9000/model")

    def test_credentials_are_loaded_from_environment_at_call_time(self):
        endpoint = HTTPJSONEndpoint(
            "https://example.invalid/model",
            bearer_token_env="WS_TEST_TOKEN",
        )
        transport = HTTPJSONTransport(endpoint)
        with patch.dict(os.environ, {"WS_TEST_TOKEN": "secret-token"}, clear=False):
            with patch("urllib.request.urlopen", return_value=_FakeResponse()) as mocked:
                result = transport("verifier", {"x": 1})
                self.assertTrue(result["success"])
                request = mocked.call_args.args[0]
                self.assertEqual(request.get_header("Authorization"), "Bearer secret-token")

    def test_missing_credential_fails_closed(self):
        endpoint = HTTPJSONEndpoint(
            "https://example.invalid/model",
            bearer_token_env="WS_MISSING_TOKEN_FOR_TEST",
        )
        transport = HTTPJSONTransport(endpoint)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("WS_MISSING_TOKEN_FOR_TEST", None)
            with self.assertRaises(RuntimeError):
                transport("planner", {"x": 1})


class ProtectedSuiteRunnerTests(unittest.TestCase):
    def controller(self):
        attempts = {"count": 0}

        def planner(contract, trace):
            attempts["count"] += 1
            return Action(tool="echo", arguments={"value": attempts["count"]})

        def verifier(contract, action, result, trace):
            if result["value"] == 1:
                return Verification(False, True, "repair once")
            return Verification(True, False, "controller verifier accepts")

        return DeliberativeController(
            tools={"echo": lambda value: {"value": value}},
            planner=planner,
            verifier=verifier,
        )

    def test_suite_emits_recovery_trace_with_independent_final_state(self):
        task = ProtectedTask(
            task_id="protected-1",
            goal="reach value two",
            success_criteria="final value equals two",
            allowed_tools={"echo"},
            max_steps=3,
        )

        def final_eval(contract, run):
            passed = run.final_result == {"value": 2}
            return FinalAdjudication(passed, "none" if passed else "major", "independent check")

        records = run_protected_suite(
            self.controller(),
            [task],
            final_eval,
            planner_identity="provider-a:planner",
            final_state_evaluator_identity="provider-b:grader",
        )
        self.assertEqual(records[0]["controller_status"], "SUCCESS")
        self.assertTrue(records[0]["independent_final_state_pass"])
        self.assertEqual(len(records[0]["steps"]), 2)
        self.assertFalse(records[0]["steps"][0]["verification"]["success"])

    def test_same_planner_and_final_evaluator_identity_rejected(self):
        task = ProtectedTask(
            task_id="protected-2",
            goal="x",
            success_criteria="x",
            allowed_tools={"echo"},
        )
        with self.assertRaises(ValueError):
            run_protected_suite(
                self.controller(),
                [task],
                lambda contract, run: FinalAdjudication(True, "none", "pass"),
                planner_identity="same:model",
                final_state_evaluator_identity="same:model",
            )


if __name__ == "__main__":
    unittest.main()

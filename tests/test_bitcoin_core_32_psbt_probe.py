import importlib.util
import pathlib
import unittest


PROBE_PATH = pathlib.Path(__file__).resolve().parents[1] / "external_anchor_pilots" / "bitcoin_core_32_psbt_probe.py"
SPEC = importlib.util.spec_from_file_location("bitcoin_core_32_psbt_probe", PROBE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class BitcoinCore32ProbeHelpersTest(unittest.TestCase):
    def test_parse_json_values(self):
        self.assertEqual(MODULE.parse_cli_output('{"a":1}'), {"a": 1})
        self.assertEqual(MODULE.parse_cli_output('[1,2]'), [1, 2])
        self.assertEqual(MODULE.parse_cli_output('123'), 123)
        self.assertIs(MODULE.parse_cli_output('true'), True)
        self.assertIsNone(MODULE.parse_cli_output(''))

    def test_parse_unquoted_bitcoin_cli_scalars(self):
        self.assertEqual(MODULE.parse_cli_output('bcrt1qexample'), 'bcrt1qexample')
        self.assertEqual(MODULE.parse_cli_output('cHNidP8BAHECAAAAAQ=='), 'cHNidP8BAHECAAAAAQ==')
        self.assertEqual(MODULE.parse_cli_output('02000000000100'), '02000000000100')

    def test_json_arg_preserves_named_rpc_types(self):
        self.assertEqual(MODULE.json_arg(True), 'true')
        self.assertEqual(MODULE.json_arg(False), 'false')
        self.assertEqual(MODULE.json_arg(None), 'null')
        self.assertEqual(MODULE.json_arg({"a": 1}), '{"a":1}')
        self.assertEqual(MODULE.json_arg([{"a": 1}]), '[{"a":1}]')
        self.assertEqual(MODULE.json_arg(2), '2')

    def test_upstream_pin_is_exact(self):
        self.assertEqual(MODULE.PINNED_UPSTREAM_TAG, 'v32.0rc1')
        self.assertEqual(
            MODULE.PINNED_UPSTREAM_COMMIT,
            'd0231bb01d83178224bf7b198ba04f78cc2c89ef',
        )

    def test_probe_cannot_self_promote_claim(self):
        self.assertEqual(MODULE.CASE_CLAIM_CLASS, 'NOT CURRENTLY CLAIMED')


if __name__ == '__main__':
    unittest.main()

from __future__ import annotations
import json, unittest
from types import SimpleNamespace
from worldshepherd_qcrypto_kms.bitcoin_core_interop import BitcoinCoreCLI, BitcoinCoreInteropError, cross_check_prepared_with_core


class CP:
    def __init__(self, stdout, returncode=0, stderr=""):
        self.stdout, self.returncode, self.stderr = stdout, returncode, stderr


class CoreInteropTests(unittest.TestCase):
    def test_mainnet_is_not_an_allowed_interop_target(self):
        with self.assertRaises(BitcoinCoreInteropError):
            BitcoinCoreCLI(network="MAINNET")

    def test_cross_check_binds_core_txid_and_descriptor(self):
        calls=[]
        def runner(args, **kwargs):
            calls.append(args)
            method=args[-1] if args[-1] in {"getnetworkinfo"} else args[-2] if len(args)>1 and args[-2] in {"decodepsbt","analyzepsbt","getdescriptorinfo"} else None
            if method == "getnetworkinfo": return CP(json.dumps({"version":310100,"subversion":"/Satoshi:31.1/"}))
            if method == "decodepsbt": return CP(json.dumps({"tx":{"txid":"aa"*32}}))
            if method == "analyzepsbt": return CP(json.dumps({"next":"signer"}))
            if method == "getdescriptorinfo": return CP(json.dumps({"descriptor":"wpkh(k)#12345678","hasprivatekeys":False,"isrange":False,"issolvable":True}))
            raise AssertionError(args)
        cli=BitcoinCoreCLI(network="SIGNET", runner=runner)
        prepared=SimpleNamespace(network="SIGNET", txid="aa"*32)
        r=cross_check_prepared_with_core(prepared, b"psbt\xff\x00", cli=cli, descriptors=["wpkh(k)#12345678"])
        self.assertTrue(r.pass_interop)
        self.assertTrue(r.txid_match)
        self.assertFalse(r.to_dict()["broadcast_performed"])

    def test_mismatched_txid_fails_interop(self):
        def runner(args, **kwargs):
            if "getnetworkinfo" in args: return CP(json.dumps({"version":310100,"subversion":"/Satoshi:31.1/"}))
            if "decodepsbt" in args: return CP(json.dumps({"tx":{"txid":"bb"*32}}))
            if "analyzepsbt" in args: return CP(json.dumps({}))
            raise AssertionError(args)
        cli=BitcoinCoreCLI(network="REGTEST", runner=runner)
        prepared=SimpleNamespace(network="REGTEST", txid="aa"*32)
        r=cross_check_prepared_with_core(prepared,b"psbt\xff\x00",cli=cli)
        self.assertFalse(r.pass_interop)

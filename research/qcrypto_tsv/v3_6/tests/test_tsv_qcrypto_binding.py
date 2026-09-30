import unittest
from pathlib import Path
from datetime import datetime, timezone

from tests.test_tsv_policy import BASE
from tests.test_tsv_runtime import full_notice
from worldshepherd_qcrypto_kms.source_integrity import build_source_manifest
from worldshepherd_qcrypto_kms.tsv.runtime import authorize_bundle
from worldshepherd_qcrypto_kms.tsv_qcrypto_binding import bind_tsv_authorization, TsvQcryptoBindingError

ROOT=Path(__file__).resolve().parents[1]
PKG=ROOT/'worldshepherd_qcrypto_kms'
T=datetime(2026,9,18,21,50,tzinfo=timezone.utc)
Q='e0c7c968f6d8f31278d677c881d3dea4173452ffd4b8ba07850d70970fc654bc'
TSV='7c1ee785f82c5180a7920d8d34889698b3367680788aa4d80b80ed51a1babefe'
PQ='79a124693b6c959ea9e1cf43d8fcd2e4bdf5309b562a502cec793f286fd090d3'


class TestTsvQcryptoBinding(unittest.TestCase):
    def test_binding_is_deterministic_and_source_bound(self):
        auth=authorize_bundle(BASE, full_notice(), now=T)
        manifest=build_source_manifest(PKG)
        a=bind_tsv_authorization(auth, package_root=PKG, source_manifest=manifest, parent_qcrypto_zip_sha256=Q, parent_tsv_zip_sha256=TSV, external_pq_receipt_sha256=PQ)
        b=bind_tsv_authorization(auth, package_root=PKG, source_manifest=manifest, parent_qcrypto_zip_sha256=Q, parent_tsv_zip_sha256=TSV, external_pq_receipt_sha256=PQ)
        self.assertEqual(a.binding_sha256,b.binding_sha256)
        self.assertEqual(a.qcrypto_source_manifest_sha256,manifest['manifest_sha256'])

    def test_bad_parent_hash_rejected(self):
        auth=authorize_bundle(BASE, full_notice(), now=T)
        manifest=build_source_manifest(PKG)
        with self.assertRaises(TsvQcryptoBindingError):
            bind_tsv_authorization(auth, package_root=PKG, source_manifest=manifest, parent_qcrypto_zip_sha256='x', parent_tsv_zip_sha256=TSV)

class TestTsvExternalBinding(unittest.TestCase):
    def test_external_tsv_bundle_changes_binding(self):
        auth=authorize_bundle(BASE, full_notice(), now=T)
        manifest=build_source_manifest(PKG)
        a=bind_tsv_authorization(auth, package_root=PKG, source_manifest=manifest, parent_qcrypto_zip_sha256=Q, parent_tsv_zip_sha256=TSV, external_pq_receipt_sha256=PQ)
        b=bind_tsv_authorization(auth, package_root=PKG, source_manifest=manifest, parent_qcrypto_zip_sha256=Q, parent_tsv_zip_sha256=TSV, external_pq_receipt_sha256=PQ, external_tsv_execution_bundle_sha256='b3773256881b1690587378d651d4d637bdc3c9d581ba204905e4675852d16625')
        self.assertNotEqual(a.binding_sha256, b.binding_sha256)
        self.assertEqual(b.external_tsv_execution_bundle_sha256, 'b3773256881b1690587378d651d4d637bdc3c9d581ba204905e4675852d16625')

    def test_bad_external_tsv_bundle_hash_rejected(self):
        auth=authorize_bundle(BASE, full_notice(), now=T)
        manifest=build_source_manifest(PKG)
        with self.assertRaises(TsvQcryptoBindingError):
            bind_tsv_authorization(auth, package_root=PKG, source_manifest=manifest, parent_qcrypto_zip_sha256=Q, parent_tsv_zip_sha256=TSV, external_tsv_execution_bundle_sha256='bad')

class TestTsvAdversarialExternalBinding(unittest.TestCase):
    def test_adversarial_external_bundle_and_core_change_binding(self):
        auth=authorize_bundle(BASE, full_notice(), now=T)
        manifest=build_source_manifest(PKG)
        a=bind_tsv_authorization(auth, package_root=PKG, source_manifest=manifest, parent_qcrypto_zip_sha256=Q, parent_tsv_zip_sha256=TSV, external_pq_receipt_sha256=PQ)
        b=bind_tsv_authorization(
            auth, package_root=PKG, source_manifest=manifest,
            parent_qcrypto_zip_sha256=Q, parent_tsv_zip_sha256=TSV,
            external_pq_receipt_sha256=PQ,
            external_tsv_adversarial_bundle_sha256='551ca894c536219189a554517cf9126e8d168ab19cb96fc5320ee03a2bb79c95',
            tsv_control_core_sha256='4b4e1c85b80b8ad5b9326cbacec0a8754dcc80ec98cf2b2e7bc917cd921d8341',
        )
        self.assertNotEqual(a.binding_sha256,b.binding_sha256)
        self.assertEqual(b.external_tsv_adversarial_bundle_sha256,'551ca894c536219189a554517cf9126e8d168ab19cb96fc5320ee03a2bb79c95')

    def test_bad_adversarial_hash_rejected(self):
        auth=authorize_bundle(BASE, full_notice(), now=T)
        manifest=build_source_manifest(PKG)
        with self.assertRaises(TsvQcryptoBindingError):
            bind_tsv_authorization(auth, package_root=PKG, source_manifest=manifest, parent_qcrypto_zip_sha256=Q, parent_tsv_zip_sha256=TSV, external_tsv_adversarial_bundle_sha256='bad')

class TestTsvResilienceExternalBinding(unittest.TestCase):
    def test_resilience_external_bundle_and_core_change_binding(self):
        auth=authorize_bundle(BASE, full_notice(), now=T)
        manifest=build_source_manifest(PKG)
        a=bind_tsv_authorization(auth, package_root=PKG, source_manifest=manifest, parent_qcrypto_zip_sha256=Q, parent_tsv_zip_sha256=TSV)
        b=bind_tsv_authorization(
            auth,package_root=PKG,source_manifest=manifest,parent_qcrypto_zip_sha256=Q,parent_tsv_zip_sha256=TSV,
            external_tsv_resilience_bundle_sha256='1'*64,tsv_resilience_core_sha256='2'*64,
        )
        self.assertNotEqual(a.binding_sha256,b.binding_sha256)
        self.assertEqual(b.external_tsv_resilience_bundle_sha256,'1'*64)

    def test_bad_resilience_hash_rejected(self):
        auth=authorize_bundle(BASE, full_notice(), now=T)
        manifest=build_source_manifest(PKG)
        with self.assertRaises(TsvQcryptoBindingError):
            bind_tsv_authorization(auth,package_root=PKG,source_manifest=manifest,parent_qcrypto_zip_sha256=Q,parent_tsv_zip_sha256=TSV,external_tsv_resilience_bundle_sha256='bad')

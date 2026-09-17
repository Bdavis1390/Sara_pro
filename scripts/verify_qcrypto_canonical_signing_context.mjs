#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

const DOMAIN_TAG = Buffer.concat([
  Buffer.from('WS-QCRYPTO-AUTH-BINDING-V1', 'utf8'),
  Buffer.from([0]),
]);

const FIELD_ORDER = [
  'schema',
  'network_id',
  'authority_domain_separator',
  'chain',
  'adapter_class',
  'authority_id',
  'authority_layer',
  'declared_migration_requirement',
  'policy_minimum_requirement',
  'effective_migration_requirement',
  'envelope_version',
  'policy_minimum_envelope_version',
  'key_epoch',
  'policy_minimum_key_epoch',
  'policy_version',
  'policy_requires_recovery_evidence',
  'classical_algorithm_id',
  'pq_algorithm_id',
  'classical_required_for_acceptance',
  'pq_required_for_acceptance',
  'replay_domain',
  'replay_sequence',
  'payload_digest',
  'evidence_digest',
  'recovery_commitment_digest',
];

function fail(message) {
  throw new Error(message);
}

function frameText(value) {
  if (typeof value !== 'string') {
    fail(`canonical value must be string, got ${typeof value}`);
  }
  const encoded = Buffer.from(value, 'utf8');
  const length = Buffer.alloc(4);
  length.writeUInt32BE(encoded.length, 0);
  return Buffer.concat([length, encoded]);
}

function canonicalPreimage(fields) {
  const count = Buffer.alloc(2);
  count.writeUInt16BE(FIELD_ORDER.length, 0);
  const pieces = [DOMAIN_TAG, count];
  for (const name of FIELD_ORDER) {
    if (!Object.hasOwn(fields, name)) {
      fail(`missing canonical field: ${name}`);
    }
    pieces.push(frameText(name));
    pieces.push(frameText(fields[name]));
  }
  if (Object.keys(fields).length !== FIELD_ORDER.length) {
    fail('canonical field set contains unexpected entries');
  }
  return Buffer.concat(pieces);
}

function verifyDecision(label, decision) {
  if (decision.ready !== true || decision.verdict !== 'CANONICAL_SIGNING_CONTEXT_READY') {
    fail(`${label}: decision is not ready`);
  }
  if (typeof decision.context_digest !== 'string' || decision.context_digest.length !== 64) {
    fail(`${label}: invalid context digest`);
  }
  if (typeof decision.canonical_preimage_hex !== 'string') {
    fail(`${label}: missing canonical preimage`);
  }

  const preimage = canonicalPreimage(decision.canonical_fields);
  const preimageHex = preimage.toString('hex');
  if (preimageHex !== decision.canonical_preimage_hex) {
    fail(`${label}: Node reconstruction does not match Python preimage`);
  }

  const digest = createHash('sha256').update(preimage).digest('hex');
  if (digest !== decision.context_digest) {
    fail(`${label}: Node SHA-256 does not match Python context digest`);
  }
  return digest;
}

const path = process.argv[2];
if (!path) {
  fail('usage: verify_qcrypto_canonical_signing_context.mjs <evidence.json>');
}

const evidence = JSON.parse(readFileSync(path, 'utf8'));
if (evidence.schema !== 'WS-QCRYPTO-CANONICAL-SIGNING-CONTEXT-EVIDENCE-V1') {
  fail('unexpected evidence schema');
}
if (evidence.status !== 'PASS') {
  fail('evidence status is not PASS');
}

const digests = new Set();
digests.add(verifyDecision('baseline', evidence.baseline));
for (const [name, decision] of Object.entries(evidence.binding_variants)) {
  digests.add(verifyDecision(`binding_variants.${name}`, decision));
}

if (digests.size !== evidence.summary.expected_distinct_context_digest_count) {
  fail(
    `distinct digest count mismatch: Node=${digests.size} expected=${evidence.summary.expected_distinct_context_digest_count}`,
  );
}

console.log('canonical_context_node_verification: PASS');
console.log('verified_context_count:', digests.size);

#!/usr/bin/env node

// Independent Node.js verifier for WS-CAE continuity interoperability vectors.
// Standard library only; no imports from the Python reference implementation.

import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const repo = resolve(here, '..');
const examples = resolve(repo, 'ws_cae', 'examples');
const vectors = JSON.parse(readFileSync(resolve(examples, 'continuity_interop_vectors.json'), 'utf8'));
const manifest = JSON.parse(readFileSync(resolve(examples, 'continuity_manifest_reference.json'), 'utf8'));

function sha256(buf) {
  return createHash('sha256').update(buf).digest();
}

function canonical(value) {
  if (value === null) return 'null';
  if (typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new Error('non-finite numbers are unsupported');
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (typeof value === 'object') {
    const keys = Object.keys(value).sort();
    return '{' + keys.map(k => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
  }
  throw new Error(`unsupported JSON type: ${typeof value}`);
}

function contentId(value) {
  return 'sha256:' + sha256(Buffer.from(canonical(value), 'utf8')).toString('hex');
}

function leafHash(contentIdValue) {
  return sha256(Buffer.concat([Buffer.from([0]), Buffer.from(contentIdValue, 'ascii')]));
}

function nodeHash(left, right) {
  return sha256(Buffer.concat([Buffer.from([1]), left, right]));
}

function largestPowerOfTwoLessThan(n) {
  if (n < 2) throw new Error('n must be >= 2');
  let k = 1;
  while ((k << 1) < n) k <<= 1;
  return k;
}

function treeHash(leaves) {
  if (leaves.length === 0) return sha256(Buffer.alloc(0));
  if (leaves.length === 1) return leaves[0];
  const k = largestPowerOfTwoLessThan(leaves.length);
  return nodeHash(treeHash(leaves.slice(0, k)), treeHash(leaves.slice(k)));
}

function rootHash(ids) {
  return 'sha256:' + treeHash(ids.map(leafHash)).toString('hex');
}

function proofPath(leaves, index) {
  if (leaves.length === 1) return [];
  const k = largestPowerOfTwoLessThan(leaves.length);
  if (index < k) return [...proofPath(leaves.slice(0, k), index), treeHash(leaves.slice(k))];
  return [...proofPath(leaves.slice(k), index - k), treeHash(leaves.slice(0, k))];
}

const failures = [];
const gotManifestId = contentId(manifest);
if (gotManifestId !== vectors.canonical_manifest.expected_content_id) {
  failures.push(`manifest content id mismatch: ${gotManifestId}`);
}

const ids = vectors.transparency.content_ids;
for (const [sizeText, expected] of Object.entries(vectors.transparency.roots)) {
  const size = Number(sizeText);
  const got = rootHash(ids.slice(0, size));
  if (got !== expected) failures.push(`root mismatch at size ${size}: ${got}`);
}

const iv = vectors.transparency.inclusion;
const gotPath = proofPath(ids.slice(0, iv.tree_size).map(leafHash), iv.leaf_index).map(
  b => 'sha256:' + b.toString('hex')
);
if (JSON.stringify(gotPath) !== JSON.stringify(iv.audit_path)) {
  failures.push(`inclusion path mismatch: ${JSON.stringify(gotPath)}`);
}

if (failures.length) {
  console.error(JSON.stringify({ spec: vectors.spec, passed: false, failures }, null, 2));
  process.exit(1);
}

console.log(JSON.stringify({
  spec: vectors.spec,
  passed: true,
  implementation: 'nodejs-stdlib-independent',
  canonical_manifest_content_id: gotManifestId,
  verified_root_sizes: Object.keys(vectors.transparency.roots).map(Number),
  verified_inclusion_tree_size: iv.tree_size,
  verified_inclusion_leaf_index: iv.leaf_index
}, null, 2));

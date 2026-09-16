import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const vectorPath = join(here, 'poo_v3_vectors.json');
const document = JSON.parse(readFileSync(vectorPath, 'utf8'));

if (document.schema !== 'WS-POO-INTEROP-VECTORS-V1') {
  throw new Error(`unsupported vector schema: ${document.schema}`);
}
if (document.claim_boundary !== 'INTERNAL_SECOND_LANGUAGE_REPRODUCTION_NOT_INDEPENDENT_EXTERNAL_VALIDATION') {
  throw new Error('claims boundary missing or changed');
}

function canonicalize(value) {
  if (value === null || typeof value !== 'object') {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map(canonicalize).join(',')}]`;
  }
  const keys = Object.keys(value).sort();
  return `{${keys.map((key) => `${JSON.stringify(key)}:${canonicalize(value[key])}`).join(',')}}`;
}

function sha256Hex(payload) {
  return createHash('sha256').update(canonicalize(payload), 'utf8').digest('hex');
}

let checked = 0;
for (const vector of document.vectors) {
  const actual = sha256Hex(vector.payload);
  if (actual !== vector.expected_sha256) {
    throw new Error(`${vector.name}: expected ${vector.expected_sha256}, got ${actual}`);
  }
  checked += 1;
}

if (checked < 7) {
  throw new Error(`insufficient interoperability vector coverage: ${checked}`);
}

console.log(JSON.stringify({
  schema: document.schema,
  vectors_checked: checked,
  second_language_internal_reproduction: true,
  independent_external_validation: false,
  global_superiority_established: false,
}));

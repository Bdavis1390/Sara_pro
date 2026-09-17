#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "${ROOT}/../.." && pwd)"
cd "$ROOT"

sha="${GITHUB_SHA:-$(git -C "$REPO_ROOT" rev-parse HEAD)}"
short_sha="${sha:0:12}"
run_key="${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-0}-${short_sha}"
export COMPOSE_PROJECT_NAME="poo-prime-hybrid-pq-${run_key//[^a-zA-Z0-9_.-]/-}"
export SARA_HOST_PORT="${POO_PRIME_HYBRID_SARA_PORT:-19590}"
export PRIME_SENTINEL_HOST_PORT="${POO_PRIME_HYBRID_A_PORT:-19591}"
export PRIME_SENTINEL_B_HOST_PORT="${POO_PRIME_HYBRID_B_PORT:-19592}"
export PRIME_SENTINEL_PQ_HOST_PORT="${POO_PRIME_HYBRID_PQ_PORT:-19593}"
export SARA_BUILD_COMMIT="$sha"
export SARA_RELEASE_ID="poo-prime-hybrid-pq-${short_sha}"
export PRIME_SENTINEL_SIGNING_KEY_ID="PS-POO-HYBRID-A-${short_sha}"
export PRIME_SENTINEL_B_SIGNING_KEY_ID="PS-POO-HYBRID-B-${short_sha}"
export PRIME_SENTINEL_PQ_SIGNING_KEY_ID="PS-POO-HYBRID-PQ-${short_sha}"
export SARA_BASE_URL="http://127.0.0.1:${SARA_HOST_PORT}"
prime_a_url="http://127.0.0.1:${PRIME_SENTINEL_HOST_PORT}"
prime_b_url="http://127.0.0.1:${PRIME_SENTINEL_B_HOST_PORT}"
prime_pq_url="http://127.0.0.1:${PRIME_SENTINEL_PQ_HOST_PORT}"
evidence_dir="${POO_PRIME_HYBRID_PQ_EVIDENCE_DIR:-${ROOT}/poo_prime_hybrid_pq_evidence}"
secret_dir="$(mktemp -d "${RUNNER_TEMP:-/tmp}/poo-prime-hybrid-pq.XXXXXX")"
key_a="${secret_dir}/prime-a-ed25519.pem"
key_b="${secret_dir}/prime-b-ed25519.pem"
key_pq="${secret_dir}/prime-pq-mldsa65-seed.bin"
token_a_file="${secret_dir}/prime-a-token"
token_b_file="${secret_dir}/prime-b-token"
token_pq_file="${secret_dir}/prime-pq-token"
env_backup="${secret_dir}/env.backup"
env_existed=0

mkdir -p "$evidence_dir"
rm -f "$evidence_dir"/*.json
if [[ -f .env ]]; then cp .env "$env_backup"; env_existed=1; fi

compose=(
  docker compose
  -f compose.yaml
  -f compose.poo-prime.yaml
  -f compose.poo-prime-quorum.yaml
  -f compose.poo-prime-hybrid-pq.yaml
  --profile prime-sentinel
  --profile prime-sentinel-pq
)
cleanup() {
  "${compose[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  if [[ "$env_existed" -eq 1 ]]; then cp "$env_backup" .env 2>/dev/null || true; chmod 600 .env 2>/dev/null || true; else rm -f .env; fi
  rm -rf "$secret_dir"
}
trap cleanup EXIT

wait_http() {
  local url="$1"
  for _ in $(seq 1 60); do
    if curl -fsS "$url" >/dev/null 2>&1; then return 0; fi
    sleep 1
  done
  return 1
}

admin_token="$(openssl rand -hex 32)"
relay_token="$(openssl rand -hex 32)"
prime_a_token="$(openssl rand -hex 32)"
prime_b_token="$(openssl rand -hex 32)"
prime_pq_token="$(openssl rand -hex 32)"
openssl genpkey -algorithm ED25519 -out "$key_a"
openssl genpkey -algorithm ED25519 -out "$key_b"
python3 - "$key_pq" <<'PY'
import sys
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PrivateKey
open(sys.argv[1],'wb').write(MLDSA65PrivateKey.generate().private_bytes_raw())
PY
printf '%s\n' "$prime_a_token" > "$token_a_file"
printf '%s\n' "$prime_b_token" > "$token_b_file"
printf '%s\n' "$prime_pq_token" > "$token_pq_file"
chmod 600 "$key_a" "$key_b" "$key_pq" "$token_a_file" "$token_b_file" "$token_pq_file"
uid="${PRIME_SENTINEL_CONTAINER_UID:-10001}"
if [[ "$(id -u)" -eq 0 ]]; then
  chown "${uid}:${uid}" "$key_a" "$key_b" "$key_pq" "$token_a_file" "$token_b_file" "$token_pq_file"
elif command -v sudo >/dev/null 2>&1; then
  sudo chown "${uid}:${uid}" "$key_a" "$key_b" "$key_pq" "$token_a_file" "$token_b_file" "$token_pq_file"
else
  echo "ERROR: unable to set hybrid signer secret ownership" >&2; exit 1
fi
export PRIME_SENTINEL_PRIVATE_KEY_HOST_PATH="$key_a"
export PRIME_SENTINEL_SERVICE_TOKEN_HOST_PATH="$token_a_file"
export PRIME_SENTINEL_B_PRIVATE_KEY_HOST_PATH="$key_b"
export PRIME_SENTINEL_B_SERVICE_TOKEN_HOST_PATH="$token_b_file"
export PRIME_SENTINEL_PQ_PRIVATE_KEY_HOST_PATH="$key_pq"
export PRIME_SENTINEL_PQ_SERVICE_TOKEN_HOST_PATH="$token_pq_file"

cat > .env <<EOF
SARA_RELAY_TOKEN=${relay_token}
SARA_ADMIN_TOKEN=${admin_token}
SARA_BIND_HOST=127.0.0.1
SARA_PORT=9530
SARA_HOST_PORT=${SARA_HOST_PORT}
SARA_DATA_DIR=/var/lib/sara
SARA_MODE=poo-prime-hybrid-pq-ci
SARA_LOG_LEVEL=info
SARA_BUILD_COMMIT=${sha}
SARA_RELEASE_ID=${SARA_RELEASE_ID}
PRIME_SENTINEL_PUBLIC_KEYS_JSON={}
PRIME_SENTINEL_REVOKED_KEY_IDS=
PRIME_SENTINEL_PQ_PUBLIC_KEYS_JSON={}
PRIME_SENTINEL_PQ_REVOKED_KEY_IDS=
PRIME_SENTINEL_HOST_PORT=${PRIME_SENTINEL_HOST_PORT}
EOF
chmod 600 .env

"${compose[@]}" up -d --build prime-sentinel prime-sentinel-b prime-sentinel-pq
wait_http "${prime_a_url}/readyz"
wait_http "${prime_b_url}/readyz"
wait_http "${prime_pq_url}/readyz"
curl -fsS "${prime_a_url}/v1/public-key" > "${secret_dir}/public-a.json"
curl -fsS "${prime_b_url}/v1/public-key" > "${secret_dir}/public-b.json"
curl -fsS "${prime_pq_url}/v1/public-key" > "${secret_dir}/public-pq.json"
python3 - "${secret_dir}/public-a.json" "${secret_dir}/public-b.json" "${secret_dir}/public-pq.json" .env <<'PY'
import json,sys
from pathlib import Path
a=json.load(open(sys.argv[1],encoding='utf-8')); b=json.load(open(sys.argv[2],encoding='utf-8')); pq=json.load(open(sys.argv[3],encoding='utf-8'))
assert a['algorithm']=='Ed25519' and b['algorithm']=='Ed25519'
assert a['fingerprint_sha256'] != b['fingerprint_sha256']
assert pq['schema']=='WS-PRIME-SENTINEL-PQ-PUBLIC-KEY-V1'
assert pq['algorithm']=='ML-DSA-65' and pq['standard']=='FIPS-204'
assert len({a['key_id'],b['key_id'],pq['key_id']})==3
p=Path(sys.argv[4]); lines=p.read_text().splitlines()
lines=[x for x in lines if not x.startswith('PRIME_SENTINEL_PUBLIC_KEYS_JSON=') and not x.startswith('PRIME_SENTINEL_PQ_PUBLIC_KEYS_JSON=')]
lines.append("PRIME_SENTINEL_PUBLIC_KEYS_JSON='"+json.dumps({a['key_id']:a['public_key_b64url'],b['key_id']:b['public_key_b64url']},separators=(',',':'))+"'")
lines.append("PRIME_SENTINEL_PQ_PUBLIC_KEYS_JSON='"+json.dumps({pq['key_id']:pq['public_key_b64url']},separators=(',',':'))+"'")
p.write_text('\n'.join(lines)+'\n'); p.chmod(0o600)
open('/tmp/hybrid-public-meta.json','w').write(json.dumps({'a':a,'b':b,'pq':pq},sort_keys=True,separators=(',',':')))
PY

"${compose[@]}" up -d --build sara
wait_http "${SARA_BASE_URL}/readyz"
admin_header=( -H "Authorization: Bearer ${admin_token}" -H 'Content-Type: application/json' )

sara_container="$("${compose[@]}" ps -q sara)"
docker inspect "$sara_container" > "${secret_dir}/sara-inspect.json"
python3 - "${secret_dir}/sara-inspect.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1],encoding='utf-8'))[0]
env={}
for item in r['Config'].get('Env') or []:
    k,sep,v=item.partition('=')
    if sep: env[k]=v
assert env.get('POO_REQUIRE_PRIME_AUTHORIZATION')=='1'
assert env.get('POO_REQUIRE_PRIME_QUORUM')=='1'
assert env.get('POO_PRIME_QUORUM_THRESHOLD')=='2'
assert env.get('POO_REQUIRE_PRIME_HYBRID_PQ')=='1'
for name in ('PRIME_SENTINEL_PRIVATE_KEY_FILE','PRIME_SENTINEL_SERVICE_TOKEN_FILE','PRIME_SENTINEL_SERVICE_TOKEN','PRIME_SENTINEL_SIGNING_KEY_ID','PRIME_SENTINEL_DATA_DIR'):
    assert env.get(name,'')=='', (name,env.get(name))
mounts={m['Destination'] for m in r.get('Mounts',[])}
for forbidden in ('/run/worldshepherd-prime-sentinel/ed25519-private.pem','/run/worldshepherd-prime-sentinel-b/ed25519-private.pem','/run/worldshepherd-prime-sentinel-pq/mldsa65-seed.bin','/var/lib/prime-sentinel'):
    assert forbidden not in mounts, forbidden
PY

curl -fsS -H "Authorization: Bearer ${admin_token}" "${SARA_BASE_URL}/admin/poo/registry" > "${secret_dir}/policy.before.json"
python3 - "${secret_dir}/policy.before.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1],encoding='utf-8'))
assert r['prime_authorization_required'] is True
assert r['prime_quorum_required'] is True and r['prime_quorum_threshold']==2
assert r['prime_hybrid_pq_required'] is True
assert r['registry']['states']==[] and r['registry']['commits']=={}
PY

PYTHONPATH="${REPO_ROOT}:${ROOT}" python3 - "${secret_dir}/durable.json" "${secret_dir}/issue.json" <<'PY'
import hashlib,json,sys
from dataclasses import asdict
from security.poo.bootstrap_audit_projection import bootstrap_commit_readiness_audit_projection
from security.poo.bootstrap_governance_guard import evaluate_governed_bootstrap_commit
from security.poo.coc_guard import COCEvidence,evaluate_coc
from security.poo.ownership_guard import OwnershipEvidence
from security.poo.registry_guard import registry_digest
from worldshepherd_sara.poo_registry_commit import POO_APPROVAL_INTENT,POO_DURABLE_COMMIT_REQUEST_SCHEMA
asset='asset:prime-hybrid-pq-stack'; claimant='claimant:prime-hybrid-pq-stack'; key='key:prime-hybrid-pq-stack'
coc=COCEvidence(asset_id=asset,claimant_id=claimant,control_key_fingerprint=key,custody_reference='custody:hybrid-pq',custody_point_reference='point:hybrid-pq',challenge_reference='challenge:hybrid-pq',observed_at='2026-09-17T07:00:00Z',expires_at='2026-09-18T07:00:00Z',asset_binding_verified=True,claimant_binding_verified=True,custody_or_control_verified=True,challenge_response_verified=True,custody_chain_verified=True,freshness_verified=True,not_revoked=True)
own=OwnershipEvidence(asset_id=asset,claimant_id=claimant,title_reference='title:hybrid-pq',control_key_fingerprint=key,work_reference='work:hybrid-pq',concept_reference='concept:hybrid-pq',coc_reference=evaluate_coc(coc).digest,stake_reference='stake:hybrid-pq',issued_at='2026-09-17T07:00:00Z',expires_at='2026-09-18T07:00:00Z',asset_fingerprint_bound=True,claimant_identity_bound=True,title_or_provenance_bound=True,pow_verified=True,poc_concept_verified=True,coc_verified=True,pos_bond_verified=True,freshness_verified=True,not_revoked=True)
d=evaluate_governed_bootstrap_commit([],own,coc,expected_registry_digest=registry_digest([])); assert d.ready and d.commit_decision
p=bootstrap_commit_readiness_audit_projection(d,asset_id=asset)
durable={'schema':POO_DURABLE_COMMIT_REQUEST_SCHEMA,'governance_projection':p,'candidate_states':[asdict(s) for s in d.commit_decision.candidate_states],'approval_intent':POO_APPROVAL_INTENT,'approval_reference':'approval:prime-hybrid-pq-stack:001'}
raw=json.dumps(p,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
issue={'asset_id':p['asset_id'],'governance_projection_digest':'sha256:'+hashlib.sha256(raw).hexdigest(),'source_decision_digest':p['source_digest'],'expected_registry_digest':p['expected_registry_digest'],'candidate_registry_digest':p['candidate_registry_digest'],'candidate_state_digest':p['candidate_state_digest'],'lifetime_seconds':300}
json.dump(durable,open(sys.argv[1],'w'),sort_keys=True,separators=(',',':'))
json.dump(issue,open(sys.argv[2],'w'),sort_keys=True,separators=(',',':'))
PY

unsigned_status="$(curl -sS -o "${secret_dir}/unsigned.json" -w '%{http_code}' -X POST "${SARA_BASE_URL}/admin/poo/registry/commit" "${admin_header[@]}" --data-binary @"${secret_dir}/durable.json")"
[[ "$unsigned_status" == "403" ]]

issue_one() {
  local url="$1" token="$2" rid="$3" out="$4"
  curl -fsS -X POST "${url}/v1/poo-technical-state-commit" -H "Authorization: Bearer ${token}" -H "X-Prime-Sentinel-Request-Id: ${rid}" -H 'Content-Type: application/json' --data-binary @"${secret_dir}/issue.json" > "$out"
}
rid_a="PSREQ-HYBRID-A-${run_key}"; rid_b="PSREQ-HYBRID-B-${run_key}"; rid_pq="PSREQ-HYBRID-PQ-${run_key}"
issue_one "$prime_a_url" "$prime_a_token" "$rid_a" "${secret_dir}/issued-a.json"
issue_one "$prime_b_url" "$prime_b_token" "$rid_b" "${secret_dir}/issued-b.json"
issue_one "$prime_pq_url" "$prime_pq_token" "$rid_pq" "${secret_dir}/issued-pq.json"

python3 - "${secret_dir}/durable.json" "${secret_dir}/issued-a.json" "${secret_dir}/issued-b.json" "${secret_dir}/issued-pq.json" "${secret_dir}/single.json" "${secret_dir}/quorum.json" "${secret_dir}/hybrid.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); a=json.load(open(sys.argv[2]))['assertion']; b=json.load(open(sys.argv[3]))['assertion']; pq=json.load(open(sys.argv[4]))['assertion']
json.dump({'schema':'WS-POO-PRIME-AUTHORIZED-DURABLE-COMMIT-REQUEST-V1','durable_commit':d,'prime_authorization':a},open(sys.argv[5],'w'),sort_keys=True,separators=(',',':'))
json.dump({'schema':'WS-POO-PRIME-QUORUM-DURABLE-COMMIT-REQUEST-V1','durable_commit':d,'prime_authorizations':[a,b]},open(sys.argv[6],'w'),sort_keys=True,separators=(',',':'))
json.dump({'schema':'WS-POO-PRIME-HYBRID-PQ-DURABLE-COMMIT-REQUEST-V1','durable_commit':d,'prime_authorizations':[a,b],'pq_authorization':pq},open(sys.argv[7],'w'),sort_keys=True,separators=(',',':'))
PY
single_status="$(curl -sS -o "${secret_dir}/single-response.json" -w '%{http_code}' -X POST "${SARA_BASE_URL}/admin/poo/registry/commit-prime-authorized" "${admin_header[@]}" --data-binary @"${secret_dir}/single.json")"
quorum_status="$(curl -sS -o "${secret_dir}/quorum-response.json" -w '%{http_code}' -X POST "${SARA_BASE_URL}/admin/poo/registry/commit-prime-quorum-authorized" "${admin_header[@]}" --data-binary @"${secret_dir}/quorum.json")"
[[ "$single_status" == "403" && "$quorum_status" == "403" ]]

curl -fsS -H "Authorization: Bearer ${admin_token}" "${SARA_BASE_URL}/admin/registry" > "${secret_dir}/registry.before-hybrid.json"
python3 - "${secret_dir}/registry.before-hybrid.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1],encoding='utf-8'))['registry']
assert 'POO_TECHNICAL_REGISTRY' not in r
assert 'PRIME_SENTINEL_POO_AUTHORIZATIONS' not in r
assert 'PRIME_SENTINEL_PQ_POO_AUTHORIZATIONS' not in r
PY

curl -fsS -X POST "${SARA_BASE_URL}/admin/poo/registry/commit-prime-hybrid-pq-authorized" "${admin_header[@]}" --data-binary @"${secret_dir}/hybrid.json" > "${secret_dir}/committed.json"
curl -fsS -H "Authorization: Bearer ${admin_token}" "${SARA_BASE_URL}/admin/registry" > "${secret_dir}/registry.after.json"
curl -fsS -H "Authorization: Bearer ${admin_token}" "${SARA_BASE_URL}/v1/audit?limit=100" > "${secret_dir}/audit.after.json"

"${compose[@]}" restart prime-sentinel prime-sentinel-b prime-sentinel-pq sara
wait_http "${prime_a_url}/readyz"; wait_http "${prime_b_url}/readyz"; wait_http "${prime_pq_url}/readyz"; wait_http "${SARA_BASE_URL}/readyz"
issue_one "$prime_a_url" "$prime_a_token" "$rid_a" "${secret_dir}/issued-a.retry.json"
issue_one "$prime_b_url" "$prime_b_token" "$rid_b" "${secret_dir}/issued-b.retry.json"
issue_one "$prime_pq_url" "$prime_pq_token" "$rid_pq" "${secret_dir}/issued-pq.retry.json"
cmp "${secret_dir}/issued-a.json" "${secret_dir}/issued-a.retry.json"
cmp "${secret_dir}/issued-b.json" "${secret_dir}/issued-b.retry.json"
cmp "${secret_dir}/issued-pq.json" "${secret_dir}/issued-pq.retry.json"
curl -fsS -X POST "${SARA_BASE_URL}/admin/poo/registry/commit-prime-hybrid-pq-authorized" "${admin_header[@]}" --data-binary @"${secret_dir}/hybrid.json" > "${secret_dir}/committed.retry.json"

python3 - "${secret_dir}/hybrid.json" "${secret_dir}/hybrid.tampered.json" <<'PY'
import json,sys
b=json.load(open(sys.argv[1])); s=b['pq_authorization']['signature_b64url']; b['pq_authorization']['signature_b64url']=('A' if s[:1]!='A' else 'B')+s[1:]
json.dump(b,open(sys.argv[2],'w'),sort_keys=True,separators=(',',':'))
PY
tamper_status="$(curl -sS -o "${secret_dir}/tamper-response.json" -w '%{http_code}' -X POST "${SARA_BASE_URL}/admin/poo/registry/commit-prime-hybrid-pq-authorized" "${admin_header[@]}" --data-binary @"${secret_dir}/hybrid.tampered.json")"
[[ "$tamper_status" == "409" ]]

python3 - "${secret_dir}/committed.json" "${secret_dir}/committed.retry.json" "${secret_dir}/registry.after.json" "${secret_dir}/audit.after.json" /tmp/hybrid-public-meta.json "$evidence_dir/result.json" "$sha" "$unsigned_status" "$single_status" "$quorum_status" <<'PY'
import json,sys
first=json.load(open(sys.argv[1])); retry=json.load(open(sys.argv[2])); reg=json.load(open(sys.argv[3]))['registry']; audit=json.load(open(sys.argv[4]))['records']; pub=json.load(open(sys.argv[5]))
commit=first['commit']; assert commit['status']=='COMMITTED'; assert retry['commit']['status']=='ALREADY_COMMITTED'; assert retry['commit']['commit_id']==commit['commit_id']
assert commit['classical_quorum_threshold']==2 and commit['classical_quorum_size']==2
assert commit['pq_algorithm']=='ML-DSA-65' and commit['pq_standard']=='FIPS-204'
assert commit['hybrid_cryptographic_authorization_verified'] is True
assert commit['single_classical_signer_sufficient'] is False and commit['pq_only_sufficient'] is False and commit['algorithm_downgrade_permitted'] is False
assert len(reg['POO_TECHNICAL_REGISTRY']['states'])==1 and len(reg['POO_TECHNICAL_REGISTRY']['commits'])==1
assert len(reg['PRIME_SENTINEL_POO_AUTHORIZATIONS'])==2 and len(reg['PRIME_SENTINEL_PQ_POO_AUTHORIZATIONS'])==1
assert len([x for x in audit if x.get('event')=='poo_technical_registry_committed'])==1
assert len([x for x in audit if x.get('event')=='prime_sentinel_poo_quorum_authorizations_consumed'])==1
assert len([x for x in audit if x.get('event')=='prime_sentinel_poo_hybrid_pq_authorization_consumed'])==1
result={
 'schema':'WS-POO-PRIME-HYBRID-PQ-STACK-EVIDENCE-V1','evidence_status':'INTERNAL_CI_GENERATED_UNSIGNED','result':'PASS','tested_head_sha':sys.argv[7],
 'prime_hybrid_pq_required':True,'classical_quorum_threshold':2,'isolated_signer_process_count':3,'classical_signer_process_count':2,'pq_signer_process_count':1,
 'distinct_classical_key_count':2,'pq_algorithm':'ML-DSA-65','pq_standard':'FIPS-204','pq_key_fingerprint_sha256':pub['pq']['fingerprint_sha256'],
 'unsigned_commit_http_status':int(sys.argv[8]),'single_signer_commit_http_status':int(sys.argv[9]),'classical_only_quorum_http_status':int(sys.argv[10]),
 'lower_assurance_routes_blocked_before_mutation':True,'poo_state_count':1,'poo_commit_count':1,'consumed_classical_authorization_count':2,'consumed_pq_authorization_count':1,
 'technical_commit_audit_count':1,'classical_quorum_audit_count':1,'hybrid_pq_audit_count':1,
 'restart_signer_a_issuance_idempotent':True,'restart_signer_b_issuance_idempotent':True,'restart_pq_issuance_idempotent':True,'restart_commit_idempotent':True,'tampered_pq_replay_rejected':True,
 'classical_quorum_cryptographic_authorization_verified':True,'pq_cryptographic_authorization_verified':True,'hybrid_cryptographic_authorization_verified':True,
 'single_classical_signer_sufficient':False,'pq_only_sufficient':False,'algorithm_downgrade_permitted':False,'sara_signer_private_material_exposed':False,
 'legal_title_changed':False,'live_value_moved':False,'credential_rotated':False,'external_transfer_executed':False,
 'claims_boundary':'Verified-local hybrid authorization: two isolated Ed25519 PRIME signer processes plus one isolated FIPS 204 ML-DSA-65 signer process. This is internal software/deployment evidence, not independent organizations, not legal title, not live-value authority, and not independent third-party validation.'
}
json.dump(result,open(sys.argv[6],'w'),sort_keys=True,indent=2)
PY

echo "POO_PRIME_HYBRID_PQ_STACK: PASS"

#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "${ROOT}/../.." && pwd)"
cd "$ROOT"

sha="${GITHUB_SHA:-$(git -C "$REPO_ROOT" rev-parse HEAD)}"
short_sha="${sha:0:12}"
run_key="${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-0}-${short_sha}"
project="poo-prime-quorum-${run_key//[^a-zA-Z0-9_.-]/-}"
export COMPOSE_PROJECT_NAME="$project"
export SARA_HOST_PORT="${POO_PRIME_QUORUM_SARA_PORT:-19580}"
export PRIME_SENTINEL_HOST_PORT="${POO_PRIME_QUORUM_A_PORT:-19581}"
export PRIME_SENTINEL_B_HOST_PORT="${POO_PRIME_QUORUM_B_PORT:-19582}"
export SARA_BUILD_COMMIT="$sha"
export SARA_RELEASE_ID="poo-prime-quorum-${short_sha}"
export PRIME_SENTINEL_SIGNING_KEY_ID="PS-POO-QUORUM-A-${short_sha}"
export PRIME_SENTINEL_B_SIGNING_KEY_ID="PS-POO-QUORUM-B-${short_sha}"
export SARA_BASE_URL="http://127.0.0.1:${SARA_HOST_PORT}"
prime_a_url="http://127.0.0.1:${PRIME_SENTINEL_HOST_PORT}"
prime_b_url="http://127.0.0.1:${PRIME_SENTINEL_B_HOST_PORT}"
evidence_dir="${POO_PRIME_QUORUM_EVIDENCE_DIR:-${ROOT}/poo_prime_quorum_evidence}"
secret_dir="$(mktemp -d "${RUNNER_TEMP:-/tmp}/poo-prime-quorum.XXXXXX")"
key_a="${secret_dir}/prime-a-ed25519.pem"
key_b="${secret_dir}/prime-b-ed25519.pem"
token_a_file="${secret_dir}/prime-a-token"
token_b_file="${secret_dir}/prime-b-token"
env_backup="${secret_dir}/env.backup"
env_existed=0

mkdir -p "$evidence_dir"
rm -f "$evidence_dir"/*.json
if [[ -f .env ]]; then
  cp .env "$env_backup"
  env_existed=1
fi

compose=(
  docker compose
  -f compose.yaml
  -f compose.poo-prime.yaml
  -f compose.poo-prime-quorum.yaml
  --profile prime-sentinel
)

cleanup() {
  "${compose[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  if [[ "$env_existed" -eq 1 ]]; then
    cp "$env_backup" .env 2>/dev/null || true
    chmod 600 .env 2>/dev/null || true
  else
    rm -f .env
  fi
  rm -rf "$secret_dir"
}
trap cleanup EXIT

admin_token="$(openssl rand -hex 32)"
relay_token="$(openssl rand -hex 32)"
prime_a_token="$(openssl rand -hex 32)"
prime_b_token="$(openssl rand -hex 32)"
openssl genpkey -algorithm ED25519 -out "$key_a"
openssl genpkey -algorithm ED25519 -out "$key_b"
printf '%s\n' "$prime_a_token" > "$token_a_file"
printf '%s\n' "$prime_b_token" > "$token_b_file"
chmod 600 "$key_a" "$key_b" "$token_a_file" "$token_b_file"
uid="${PRIME_SENTINEL_CONTAINER_UID:-10001}"
if [[ "$(id -u)" -eq 0 ]]; then
  chown "${uid}:${uid}" "$key_a" "$key_b" "$token_a_file" "$token_b_file"
elif command -v sudo >/dev/null 2>&1; then
  sudo chown "${uid}:${uid}" "$key_a" "$key_b" "$token_a_file" "$token_b_file"
else
  echo "ERROR: unable to set PRIME quorum secret ownership" >&2
  exit 1
fi
export PRIME_SENTINEL_PRIVATE_KEY_HOST_PATH="$key_a"
export PRIME_SENTINEL_SERVICE_TOKEN_HOST_PATH="$token_a_file"
export PRIME_SENTINEL_B_PRIVATE_KEY_HOST_PATH="$key_b"
export PRIME_SENTINEL_B_SERVICE_TOKEN_HOST_PATH="$token_b_file"
unset PRIME_SENTINEL_PUBLIC_KEYS_JSON || true

cat > .env <<EOF
SARA_RELAY_TOKEN=${relay_token}
SARA_ADMIN_TOKEN=${admin_token}
SARA_BIND_HOST=127.0.0.1
SARA_PORT=9530
SARA_HOST_PORT=${SARA_HOST_PORT}
SARA_DATA_DIR=/var/lib/sara
SARA_MODE=poo-prime-quorum-ci
SARA_LOG_LEVEL=info
SARA_BUILD_COMMIT=${sha}
SARA_RELEASE_ID=${SARA_RELEASE_ID}
PRIME_SENTINEL_PUBLIC_KEYS_JSON={}
PRIME_SENTINEL_REVOKED_KEY_IDS=
PRIME_SENTINEL_HOST_PORT=${PRIME_SENTINEL_HOST_PORT}
EOF
chmod 600 .env

wait_http() {
  local url="$1"
  for _ in $(seq 1 60); do
    if curl -fsS "$url" >/dev/null 2>&1; then return 0; fi
    sleep 1
  done
  return 1
}

"${compose[@]}" up -d --build prime-sentinel prime-sentinel-b
wait_http "${prime_a_url}/readyz"
wait_http "${prime_b_url}/readyz"

curl -fsS "${prime_a_url}/v1/public-key" > "${secret_dir}/public-a.json"
curl -fsS "${prime_b_url}/v1/public-key" > "${secret_dir}/public-b.json"
python3 - "${secret_dir}/public-a.json" "${secret_dir}/public-b.json" \
  "$PRIME_SENTINEL_SIGNING_KEY_ID" "$PRIME_SENTINEL_B_SIGNING_KEY_ID" \
  > "${secret_dir}/public-values.txt" <<'PY'
import json,sys
records=[]
for path,kid in ((sys.argv[1],sys.argv[3]),(sys.argv[2],sys.argv[4])):
    r=json.load(open(path,encoding='utf-8'))
    assert r['schema']=='WS-PRIME-SENTINEL-PUBLIC-KEY-V1'
    assert r['algorithm']=='Ed25519'
    assert r['key_id']==kid
    records.append(r)
assert records[0]['fingerprint_sha256'] != records[1]['fingerprint_sha256']
for r in records:
    print(r['public_key_b64url'])
    print(r['fingerprint_sha256'])
PY
public_a="$(sed -n '1p' "${secret_dir}/public-values.txt")"
fingerprint_a="$(sed -n '2p' "${secret_dir}/public-values.txt")"
public_b="$(sed -n '3p' "${secret_dir}/public-values.txt")"
fingerprint_b="$(sed -n '4p' "${secret_dir}/public-values.txt")"
python3 - .env "$PRIME_SENTINEL_SIGNING_KEY_ID" "$public_a" \
  "$PRIME_SENTINEL_B_SIGNING_KEY_ID" "$public_b" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])
keys={sys.argv[2]:sys.argv[3],sys.argv[4]:sys.argv[5]}
lines=[x for x in p.read_text().splitlines() if not x.startswith('PRIME_SENTINEL_PUBLIC_KEYS_JSON=')]
lines.append("PRIME_SENTINEL_PUBLIC_KEYS_JSON='"+json.dumps(keys,separators=(',',':'))+"'")
p.write_text('\n'.join(lines)+'\n')
p.chmod(0o600)
PY

"${compose[@]}" up -d --build sara
wait_http "${SARA_BASE_URL}/readyz"

sara_container="$("${compose[@]}" ps -q sara)"
[[ -n "$sara_container" ]] || { echo "ERROR: SARA container missing" >&2; exit 1; }
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
for name in ('PRIME_SENTINEL_PRIVATE_KEY_FILE','PRIME_SENTINEL_SERVICE_TOKEN_FILE','PRIME_SENTINEL_SERVICE_TOKEN','PRIME_SENTINEL_SIGNING_KEY_ID','PRIME_SENTINEL_DATA_DIR'):
    assert env.get(name,'')=='', (name,env.get(name))
mounts={m['Destination'] for m in r.get('Mounts',[])}
for forbidden in ('/run/worldshepherd-prime-sentinel/ed25519-private.pem','/run/worldshepherd-prime-sentinel/service-token','/var/lib/prime-sentinel','/run/worldshepherd-prime-sentinel-b/ed25519-private.pem','/run/worldshepherd-prime-sentinel-b/service-token','/var/lib/prime-sentinel-b'):
    assert forbidden not in mounts, forbidden
PY

admin_header=( -H "Authorization: Bearer ${admin_token}" -H 'Content-Type: application/json' )
curl -fsS -H "Authorization: Bearer ${admin_token}" "${SARA_BASE_URL}/admin/poo/registry" > "${secret_dir}/policy.before.json"
python3 - "${secret_dir}/policy.before.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1],encoding='utf-8'))
assert r['prime_authorization_required'] is True
assert r['prime_quorum_required'] is True
assert r['prime_quorum_threshold']==2
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
asset='asset:prime-quorum-stack'; claimant='claimant:prime-quorum-stack'; key='key:prime-quorum-stack'
coc=COCEvidence(asset_id=asset,claimant_id=claimant,control_key_fingerprint=key,custody_reference='custody:quorum',custody_point_reference='point:quorum',challenge_reference='challenge:quorum',observed_at='2026-09-17T07:00:00Z',expires_at='2026-09-18T07:00:00Z',asset_binding_verified=True,claimant_binding_verified=True,custody_or_control_verified=True,challenge_response_verified=True,custody_chain_verified=True,freshness_verified=True,not_revoked=True)
own=OwnershipEvidence(asset_id=asset,claimant_id=claimant,title_reference='title:quorum',control_key_fingerprint=key,work_reference='work:quorum',concept_reference='concept:quorum',coc_reference=evaluate_coc(coc).digest,stake_reference='stake:quorum',issued_at='2026-09-17T07:00:00Z',expires_at='2026-09-18T07:00:00Z',asset_fingerprint_bound=True,claimant_identity_bound=True,title_or_provenance_bound=True,pow_verified=True,poc_concept_verified=True,coc_verified=True,pos_bond_verified=True,freshness_verified=True,not_revoked=True)
d=evaluate_governed_bootstrap_commit([],own,coc,expected_registry_digest=registry_digest([])); assert d.ready and d.commit_decision
p=bootstrap_commit_readiness_audit_projection(d,asset_id=asset)
durable={'schema':POO_DURABLE_COMMIT_REQUEST_SCHEMA,'governance_projection':p,'candidate_states':[asdict(s) for s in d.commit_decision.candidate_states],'approval_intent':POO_APPROVAL_INTENT,'approval_reference':'approval:prime-quorum-stack:001'}
raw=json.dumps(p,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
issue={'asset_id':p['asset_id'],'governance_projection_digest':'sha256:'+hashlib.sha256(raw).hexdigest(),'source_decision_digest':p['source_digest'],'expected_registry_digest':p['expected_registry_digest'],'candidate_registry_digest':p['candidate_registry_digest'],'candidate_state_digest':p['candidate_state_digest'],'lifetime_seconds':300}
json.dump(durable,open(sys.argv[1],'w'),sort_keys=True,separators=(',',':'))
json.dump(issue,open(sys.argv[2],'w'),sort_keys=True,separators=(',',':'))
PY

unsigned_status="$(curl -sS -o "${secret_dir}/unsigned.json" -w '%{http_code}' -X POST "${SARA_BASE_URL}/admin/poo/registry/commit" "${admin_header[@]}" --data-binary @"${secret_dir}/durable.json")"
[[ "$unsigned_status" == "403" ]] || { echo "ERROR: unsigned route returned ${unsigned_status}" >&2; exit 1; }

request_a="PSREQ-POO-QUORUM-A-${run_key}"
request_b="PSREQ-POO-QUORUM-B-${run_key}"
issue_one() {
  local url="$1" token="$2" request_id="$3" output="$4"
  curl -fsS -X POST "${url}/v1/poo-technical-state-commit" \
    -H "Authorization: Bearer ${token}" \
    -H "X-Prime-Sentinel-Request-Id: ${request_id}" \
    -H 'Content-Type: application/json' \
    --data-binary @"${secret_dir}/issue.json" > "$output"
}
issue_one "$prime_a_url" "$prime_a_token" "$request_a" "${secret_dir}/issued-a.json"
issue_one "$prime_b_url" "$prime_b_token" "$request_b" "${secret_dir}/issued-b.json"

python3 - "${secret_dir}/durable.json" "${secret_dir}/issued-a.json" "${secret_dir}/single.json" "${secret_dir}/quorum.json" "${secret_dir}/issued-b.json" <<'PY'
import json,sys
durable=json.load(open(sys.argv[1])); a=json.load(open(sys.argv[2]))['assertion']; b=json.load(open(sys.argv[5]))['assertion']
json.dump({'schema':'WS-POO-PRIME-AUTHORIZED-DURABLE-COMMIT-REQUEST-V1','durable_commit':durable,'prime_authorization':a},open(sys.argv[3],'w'),sort_keys=True,separators=(',',':'))
json.dump({'schema':'WS-POO-PRIME-QUORUM-DURABLE-COMMIT-REQUEST-V1','durable_commit':durable,'prime_authorizations':[a,b]},open(sys.argv[4],'w'),sort_keys=True,separators=(',',':'))
PY

single_status="$(curl -sS -o "${secret_dir}/single-response.json" -w '%{http_code}' -X POST "${SARA_BASE_URL}/admin/poo/registry/commit-prime-authorized" "${admin_header[@]}" --data-binary @"${secret_dir}/single.json")"
[[ "$single_status" == "403" ]] || { echo "ERROR: single-signer route returned ${single_status}" >&2; exit 1; }
python3 - "${secret_dir}/quorum.json" "${secret_dir}/one-quorum.json" <<'PY'
import json,sys
b=json.load(open(sys.argv[1])); b['prime_authorizations']=b['prime_authorizations'][:1]; json.dump(b,open(sys.argv[2],'w'),sort_keys=True,separators=(',',':'))
PY
one_quorum_status="$(curl -sS -o "${secret_dir}/one-quorum-response.json" -w '%{http_code}' -X POST "${SARA_BASE_URL}/admin/poo/registry/commit-prime-quorum-authorized" "${admin_header[@]}" --data-binary @"${secret_dir}/one-quorum.json")"
[[ "$one_quorum_status" == "422" ]] || { echo "ERROR: one-assertion quorum returned ${one_quorum_status}" >&2; exit 1; }

curl -fsS -H "Authorization: Bearer ${admin_token}" "${SARA_BASE_URL}/admin/registry" > "${secret_dir}/registry.before-quorum.json"
python3 - "${secret_dir}/registry.before-quorum.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1],encoding='utf-8'))['registry']
assert 'POO_TECHNICAL_REGISTRY' not in r
assert 'PRIME_SENTINEL_POO_AUTHORIZATIONS' not in r
PY

curl -fsS -X POST "${SARA_BASE_URL}/admin/poo/registry/commit-prime-quorum-authorized" "${admin_header[@]}" --data-binary @"${secret_dir}/quorum.json" > "${secret_dir}/committed.json"
curl -fsS -H "Authorization: Bearer ${admin_token}" "${SARA_BASE_URL}/admin/registry" > "${secret_dir}/registry.after.json"
curl -fsS -H "Authorization: Bearer ${admin_token}" "${SARA_BASE_URL}/v1/audit?limit=100" > "${secret_dir}/audit.after.json"

"${compose[@]}" restart prime-sentinel prime-sentinel-b sara
wait_http "${prime_a_url}/readyz"
wait_http "${prime_b_url}/readyz"
wait_http "${SARA_BASE_URL}/readyz"

issue_one "$prime_a_url" "$prime_a_token" "$request_a" "${secret_dir}/issued-a.retry.json"
issue_one "$prime_b_url" "$prime_b_token" "$request_b" "${secret_dir}/issued-b.retry.json"
cmp "${secret_dir}/issued-a.json" "${secret_dir}/issued-a.retry.json"
cmp "${secret_dir}/issued-b.json" "${secret_dir}/issued-b.retry.json"
curl -fsS -X POST "${SARA_BASE_URL}/admin/poo/registry/commit-prime-quorum-authorized" "${admin_header[@]}" --data-binary @"${secret_dir}/quorum.json" > "${secret_dir}/committed.retry.json"

python3 - "${secret_dir}/quorum.json" "${secret_dir}/tampered.json" <<'PY'
import json,sys
b=json.load(open(sys.argv[1])); s=b['prime_authorizations'][1]['signature_b64url']; b['prime_authorizations'][1]['signature_b64url']=('A' if s[:1] != 'A' else 'B')+s[1:]; json.dump(b,open(sys.argv[2],'w'),sort_keys=True,separators=(',',':'))
PY
tamper_status="$(curl -sS -o "${secret_dir}/tampered-response.json" -w '%{http_code}' -X POST "${SARA_BASE_URL}/admin/poo/registry/commit-prime-quorum-authorized" "${admin_header[@]}" --data-binary @"${secret_dir}/tampered.json")"
[[ "$tamper_status" == "409" ]] || { echo "ERROR: tampered quorum replay returned ${tamper_status}" >&2; exit 1; }

curl -fsS -H "Authorization: Bearer ${admin_token}" "${SARA_BASE_URL}/admin/poo/registry" > "${secret_dir}/policy.after-restart.json"
curl -fsS -H "Authorization: Bearer ${admin_token}" "${SARA_BASE_URL}/admin/registry" > "${secret_dir}/registry.final.json"
curl -fsS -H "Authorization: Bearer ${admin_token}" "${SARA_BASE_URL}/v1/audit?limit=100" > "${secret_dir}/audit.final.json"
curl -fsS -H "Authorization: Bearer ${prime_a_token}" "${prime_a_url}/v1/poo-ledger-status" > "${secret_dir}/ledger-a.json"
curl -fsS -H "Authorization: Bearer ${prime_b_token}" "${prime_b_url}/v1/poo-ledger-status" > "${secret_dir}/ledger-b.json"

python3 - "$evidence_dir/result.json" "$sha" "$fingerprint_a" "$fingerprint_b" "$request_a" "$request_b" "$unsigned_status" "$single_status" "$one_quorum_status" "${secret_dir}/committed.json" "${secret_dir}/committed.retry.json" "${secret_dir}/policy.after-restart.json" "${secret_dir}/registry.final.json" "${secret_dir}/audit.final.json" "${secret_dir}/ledger-a.json" "${secret_dir}/ledger-b.json" <<'PY'
import datetime,json,sys
(out,sha,fp_a,fp_b,req_a,req_b,unsigned,single,oneq,committed,retry,policy,registry,audit,ledger_a,ledger_b)=sys.argv[1:]
c=json.load(open(committed)); rr=json.load(open(retry)); pol=json.load(open(policy)); reg=json.load(open(registry))['registry']; aud=json.load(open(audit))['records']; la=json.load(open(ledger_a)); lb=json.load(open(ledger_b))
assert c['commit']['status']=='COMMITTED'; assert rr['commit']['status']=='ALREADY_COMMITTED'
assert c['prime_quorum_required'] is True and c['prime_quorum_threshold']==2
assert c['commit']['quorum_threshold']==2 and c['commit']['quorum_size']==2
assert c['commit']['single_signer_sufficient'] is False
assert c['commit']['prime_quorum_cryptographic_authorization_verified'] is True
assert pol['prime_quorum_required'] is True and pol['prime_quorum_threshold']==2
poo=reg['POO_TECHNICAL_REGISTRY']; auths=reg['PRIME_SENTINEL_POO_AUTHORIZATIONS']
assert len(poo['states'])==1 and len(poo['commits'])==1 and len(auths)==2
technical=[x for x in aud if x.get('event')=='poo_technical_registry_committed']; quorum=[x for x in aud if x.get('event')=='prime_sentinel_poo_quorum_authorizations_consumed']
assert len(technical)==1 and len(quorum)==1
assert quorum[0]['payload']['quorum_threshold']==2 and quorum[0]['payload']['single_signer_sufficient'] is False
assert la['ok'] is True and lb['ok'] is True and la['signed']==1 and lb['signed']==1
record={
 'schema':'WS-POO-PRIME-QUORUM-STACK-EVIDENCE-V1',
 'evidence_status':'INTERNAL_CI_GENERATED_UNSIGNED',
 'result':'PASS',
 'tested_head_sha':sha,
 'prime_quorum_required':True,
 'prime_quorum_threshold':2,
 'isolated_signer_process_count':2,
 'distinct_signing_key_count':2,
 'signing_key_fingerprints_sha256':[fp_a,fp_b],
 'prime_request_ids':[req_a,req_b],
 'unsigned_commit_http_status':int(unsigned),
 'single_signer_commit_http_status':int(single),
 'one_assertion_quorum_http_status':int(oneq),
 'lower_assurance_routes_blocked_before_mutation':True,
 'poo_state_count':len(poo['states']),
 'poo_commit_count':len(poo['commits']),
 'consumed_prime_authorization_count':len(auths),
 'technical_commit_audit_count':len(technical),
 'quorum_authorization_audit_count':len(quorum),
 'restart_signer_a_issuance_idempotent':True,
 'restart_signer_b_issuance_idempotent':True,
 'restart_commit_idempotent':True,
 'tampered_quorum_replay_rejected':True,
 'prime_quorum_cryptographic_authorization_verified':True,
 'single_signer_sufficient':False,
 'durable_internal_state_committed':True,
 'sara_prime_private_material_exposed':False,
 'legal_title_changed':False,
 'live_value_moved':False,
 'credential_rotated':False,
 'external_transfer_executed':False,
 'executed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'claims_boundary':'Verified-local multi-key PRIME quorum profile: two isolated signer processes and two distinct trusted keys required for PoO technical-state mutation; not independent organizations, not post-quantum security, not legal title, not live-value authority, not public production, not government approval, and not independent third-party validation.'
}
json.dump(record,open(out,'w'),sort_keys=True,indent=2); open(out,'a').write('\n')
PY

echo "POO_PRIME_QUORUM_STACK: PASS"

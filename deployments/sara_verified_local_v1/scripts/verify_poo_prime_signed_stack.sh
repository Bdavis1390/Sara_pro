#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "${ROOT}/../.." && pwd)"
cd "$ROOT"

sha="${GITHUB_SHA:-$(git -C "$REPO_ROOT" rev-parse HEAD)}"
short_sha="${sha:0:12}"
run_key="${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-0}-${short_sha}"
project="poo-prime-${run_key//[^a-zA-Z0-9_.-]/-}"
export COMPOSE_PROJECT_NAME="$project"
export SARA_HOST_PORT="${POO_PRIME_SARA_PORT:-19560}"
export PRIME_SENTINEL_HOST_PORT="${POO_PRIME_SENTINEL_PORT:-19561}"
export SARA_BUILD_COMMIT="$sha"
export SARA_RELEASE_ID="poo-prime-signed-stack-${short_sha}"
export PRIME_SENTINEL_SIGNING_KEY_ID="PS-POO-STACK-${short_sha}"
export SARA_BASE_URL="http://127.0.0.1:${SARA_HOST_PORT}"
prime_url="http://127.0.0.1:${PRIME_SENTINEL_HOST_PORT}"
evidence_dir="${POO_PRIME_EVIDENCE_DIR:-${ROOT}/poo_prime_stack_evidence}"
secret_dir="$(mktemp -d "${RUNNER_TEMP:-/tmp}/poo-prime-stack.XXXXXX")"
key_file="${secret_dir}/prime-ed25519.pem"
token_file="${secret_dir}/prime-service-token"
env_backup="${secret_dir}/env.backup"
env_existed=0

mkdir -p "$evidence_dir"
rm -f "$evidence_dir"/*.json
if [[ -f .env ]]; then
  cp .env "$env_backup"
  env_existed=1
fi

cleanup() {
  docker compose -f compose.yaml -f compose.poo-prime.yaml --profile prime-sentinel down -v --remove-orphans >/dev/null 2>&1 || true
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
prime_token="$(openssl rand -hex 32)"
openssl genpkey -algorithm ED25519 -out "$key_file"
printf '%s\n' "$prime_token" > "$token_file"
chmod 600 "$key_file" "$token_file"
uid="${PRIME_SENTINEL_CONTAINER_UID:-10001}"
if [[ "$(id -u)" -eq 0 ]]; then
  chown "${uid}:${uid}" "$key_file" "$token_file"
elif command -v sudo >/dev/null 2>&1; then
  sudo chown "${uid}:${uid}" "$key_file" "$token_file"
else
  echo "ERROR: unable to set PRIME secret ownership" >&2
  exit 1
fi
export PRIME_SENTINEL_PRIVATE_KEY_HOST_PATH="$key_file"
export PRIME_SENTINEL_SERVICE_TOKEN_HOST_PATH="$token_file"

cat > .env <<EOF
SARA_RELAY_TOKEN=${relay_token}
SARA_ADMIN_TOKEN=${admin_token}
SARA_BIND_HOST=127.0.0.1
SARA_PORT=9530
SARA_HOST_PORT=${SARA_HOST_PORT}
SARA_DATA_DIR=/var/lib/sara
SARA_MODE=poo-prime-signed-stack-ci
SARA_LOG_LEVEL=info
SARA_BUILD_COMMIT=${sha}
SARA_RELEASE_ID=${SARA_RELEASE_ID}
PRIME_SENTINEL_PUBLIC_KEYS_JSON={}
PRIME_SENTINEL_REVOKED_KEY_IDS=
PRIME_SENTINEL_HOST_PORT=${PRIME_SENTINEL_HOST_PORT}
EOF
chmod 600 .env

compose=(docker compose -f compose.yaml -f compose.poo-prime.yaml --profile prime-sentinel)
"${compose[@]}" up -d --build prime-sentinel

wait_http() {
  local url="$1"
  for _ in $(seq 1 60); do
    if curl -fsS "$url" >/dev/null 2>&1; then return 0; fi
    sleep 1
  done
  return 1
}
wait_http "${prime_url}/readyz"

curl -fsS "${prime_url}/v1/public-key" > "${secret_dir}/public-key.json"
python3 - "${secret_dir}/public-key.json" "$PRIME_SENTINEL_SIGNING_KEY_ID" > "${secret_dir}/public-values.txt" <<'PY'
import json,sys
r=json.load(open(sys.argv[1],encoding='utf-8'))
assert r['schema']=='WS-PRIME-SENTINEL-PUBLIC-KEY-V1'
assert r['algorithm']=='Ed25519'
assert r['key_id']==sys.argv[2]
print(r['public_key_b64url'])
print(r['fingerprint_sha256'])
PY
public_key="$(sed -n '1p' "${secret_dir}/public-values.txt")"
public_fingerprint="$(sed -n '2p' "${secret_dir}/public-values.txt")"
python3 - .env "$PRIME_SENTINEL_SIGNING_KEY_ID" "$public_key" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); kid=sys.argv[2]; key=sys.argv[3]
lines=[x for x in p.read_text().splitlines() if not x.startswith('PRIME_SENTINEL_PUBLIC_KEYS_JSON=')]
lines.append("PRIME_SENTINEL_PUBLIC_KEYS_JSON='"+json.dumps({kid:key},separators=(',',':'))+"'")
p.write_text('\n'.join(lines)+'\n')
p.chmod(0o600)
PY

"${compose[@]}" up -d --build sara
wait_http "${SARA_BASE_URL}/readyz"

PYTHONPATH="${REPO_ROOT}:${ROOT}" python3 - "${secret_dir}/durable.json" "${secret_dir}/issue.json" <<'PY'
import hashlib,json,sys
from dataclasses import asdict
from security.poo.bootstrap_audit_projection import bootstrap_commit_readiness_audit_projection
from security.poo.bootstrap_governance_guard import evaluate_governed_bootstrap_commit
from security.poo.coc_guard import COCEvidence,evaluate_coc
from security.poo.ownership_guard import OwnershipEvidence
from security.poo.registry_guard import registry_digest
from worldshepherd_sara.poo_registry_commit import POO_APPROVAL_INTENT,POO_DURABLE_COMMIT_REQUEST_SCHEMA
asset='asset:prime-container-stack'; claimant='claimant:prime-container-stack'; key='key:prime-container-stack'
coc=COCEvidence(asset_id=asset,claimant_id=claimant,control_key_fingerprint=key,custody_reference='custody:stack',custody_point_reference='point:stack',challenge_reference='challenge:stack',observed_at='2026-09-16T07:00:00Z',expires_at='2026-09-17T07:00:00Z',asset_binding_verified=True,claimant_binding_verified=True,custody_or_control_verified=True,challenge_response_verified=True,custody_chain_verified=True,freshness_verified=True,not_revoked=True)
own=OwnershipEvidence(asset_id=asset,claimant_id=claimant,title_reference='title:stack',control_key_fingerprint=key,work_reference='work:stack',concept_reference='concept:stack',coc_reference=evaluate_coc(coc).digest,stake_reference='stake:stack',issued_at='2026-09-16T07:00:00Z',expires_at='2026-09-17T07:00:00Z',asset_fingerprint_bound=True,claimant_identity_bound=True,title_or_provenance_bound=True,pow_verified=True,poc_concept_verified=True,coc_verified=True,pos_bond_verified=True,freshness_verified=True,not_revoked=True)
d=evaluate_governed_bootstrap_commit([],own,coc,expected_registry_digest=registry_digest([])); assert d.ready and d.commit_decision
p=bootstrap_commit_readiness_audit_projection(d,asset_id=asset)
durable={'schema':POO_DURABLE_COMMIT_REQUEST_SCHEMA,'governance_projection':p,'candidate_states':[asdict(s) for s in d.commit_decision.candidate_states],'approval_intent':POO_APPROVAL_INTENT,'approval_reference':'approval:prime-container-stack:001'}
raw=json.dumps(p,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
issue={'asset_id':p['asset_id'],'governance_projection_digest':'sha256:'+hashlib.sha256(raw).hexdigest(),'source_decision_digest':p['source_digest'],'expected_registry_digest':p['expected_registry_digest'],'candidate_registry_digest':p['candidate_registry_digest'],'candidate_state_digest':p['candidate_state_digest'],'lifetime_seconds':300}
json.dump(durable,open(sys.argv[1],'w'),sort_keys=True,separators=(',',':'))
json.dump(issue,open(sys.argv[2],'w'),sort_keys=True,separators=(',',':'))
PY

request_id="PSREQ-POO-STACK-${run_key}"
curl -fsS -X POST "${prime_url}/v1/poo-technical-state-commit" \
  -H "Authorization: Bearer ${prime_token}" \
  -H "X-Prime-Sentinel-Request-Id: ${request_id}" \
  -H 'Content-Type: application/json' \
  --data-binary @"${secret_dir}/issue.json" > "${secret_dir}/issued.json"

python3 - "${secret_dir}/durable.json" "${secret_dir}/issued.json" "${secret_dir}/commit.json" <<'PY'
import json,sys
body={'schema':'WS-POO-PRIME-AUTHORIZED-DURABLE-COMMIT-REQUEST-V1','durable_commit':json.load(open(sys.argv[1])),'prime_authorization':json.load(open(sys.argv[2]))['assertion']}
json.dump(body,open(sys.argv[3],'w'),sort_keys=True,separators=(',',':'))
PY

curl -fsS -X POST "${SARA_BASE_URL}/admin/poo/registry/commit-prime-authorized" \
  -H "Authorization: Bearer ${admin_token}" -H 'Content-Type: application/json' \
  --data-binary @"${secret_dir}/commit.json" > "${secret_dir}/committed.json"
curl -fsS -H "Authorization: Bearer ${admin_token}" "${SARA_BASE_URL}/admin/registry" > "${secret_dir}/registry.json"
curl -fsS -H "Authorization: Bearer ${admin_token}" "${SARA_BASE_URL}/v1/audit?limit=100" > "${secret_dir}/audit.json"

"${compose[@]}" restart prime-sentinel sara
wait_http "${prime_url}/readyz"
wait_http "${SARA_BASE_URL}/readyz"
curl -fsS -X POST "${prime_url}/v1/poo-technical-state-commit" \
  -H "Authorization: Bearer ${prime_token}" -H "X-Prime-Sentinel-Request-Id: ${request_id}" \
  -H 'Content-Type: application/json' --data-binary @"${secret_dir}/issue.json" > "${secret_dir}/issued.retry.json"
cmp "${secret_dir}/issued.json" "${secret_dir}/issued.retry.json"
curl -fsS -X POST "${SARA_BASE_URL}/admin/poo/registry/commit-prime-authorized" \
  -H "Authorization: Bearer ${admin_token}" -H 'Content-Type: application/json' \
  --data-binary @"${secret_dir}/commit.json" > "${secret_dir}/committed.retry.json"
curl -fsS -H "Authorization: Bearer ${prime_token}" "${prime_url}/v1/poo-ledger-status" > "${secret_dir}/prime-ledger.json"

python3 - "${secret_dir}/commit.json" "${secret_dir}/tampered.json" <<'PY'
import json,sys
b=json.load(open(sys.argv[1])); s=b['prime_authorization']['signature_b64url']; b['prime_authorization']['signature_b64url']=('A' if s[:1] != 'A' else 'B')+s[1:]
json.dump(b,open(sys.argv[2],'w'),sort_keys=True,separators=(',',':'))
PY
tamper_status="$(curl -sS -o "${secret_dir}/tampered-response.json" -w '%{http_code}' -X POST "${SARA_BASE_URL}/admin/poo/registry/commit-prime-authorized" -H "Authorization: Bearer ${admin_token}" -H 'Content-Type: application/json' --data-binary @"${secret_dir}/tampered.json")"
[[ "$tamper_status" == "409" ]] || { echo "ERROR: tampered signed replay returned HTTP ${tamper_status}" >&2; exit 1; }

python3 - "$evidence_dir/result.json" "$sha" "$public_fingerprint" "$request_id" "${secret_dir}/committed.json" "${secret_dir}/committed.retry.json" "${secret_dir}/registry.json" "${secret_dir}/audit.json" "${secret_dir}/prime-ledger.json" <<'PY'
import json,sys,datetime
out,sha,fp,rid,committed,retry,registry,audit,ledger=sys.argv[1:]
c=json.load(open(committed)); r=json.load(open(retry)); reg=json.load(open(registry))['registry']; aud=json.load(open(audit))['records']; led=json.load(open(ledger))
assert c['commit']['status']=='COMMITTED'; assert r['commit']['status']=='ALREADY_COMMITTED'
assert c['commit']['commit_id']==r['commit']['commit_id']
assert c['commit']['prime_cryptographic_authorization_verified'] is True
assert c['commit']['durable_internal_state_committed'] is True
for k in ('legal_title_changed','live_value_moved','credential_rotated','external_transfer_executed'): assert c['commit'][k] is False
poo=reg['POO_TECHNICAL_REGISTRY']; auths=reg['PRIME_SENTINEL_POO_AUTHORIZATIONS']
assert len(poo['states'])==1 and len(poo['commits'])==1 and len(auths)==1
technical=[x for x in aud if x.get('event')=='poo_technical_registry_committed']; prime=[x for x in aud if x.get('event')=='prime_sentinel_poo_authorization_consumed']
assert len(technical)==1 and len(prime)==1
assert led['ok'] is True and led['records']==1 and led['signed']==1 and led['prepared']==0
record={'schema':'WS-POO-PRIME-SIGNED-STACK-EVIDENCE-V1','evidence_status':'INTERNAL_CI_GENERATED_UNSIGNED','result':'PASS','tested_head_sha':sha,'prime_signing_key_fingerprint_sha256':fp,'prime_request_id':rid,'commit_id':c['commit']['commit_id'],'poo_registry_digest':c['commit']['registry_digest'],'poo_state_count':len(poo['states']),'poo_commit_count':len(poo['commits']),'consumed_prime_authorization_count':len(auths),'technical_commit_audit_count':len(technical),'prime_authorization_audit_count':len(prime),'restart_issuance_idempotent':True,'restart_commit_idempotent':True,'tampered_signed_replay_rejected':True,'prime_cryptographic_authorization_verified':True,'durable_internal_state_committed':True,'legal_title_changed':False,'live_value_moved':False,'credential_rotated':False,'external_transfer_executed':False,'executed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'claims_boundary':'Verified-local PRIME-signed internal technical state only; not legal title, live-value authority, public production, government approval, or independent validation.'}
json.dump(record,open(out,'w'),sort_keys=True,indent=2); open(out,'a').write('\n')
PY

echo "POO_PRIME_SIGNED_STACK: PASS"

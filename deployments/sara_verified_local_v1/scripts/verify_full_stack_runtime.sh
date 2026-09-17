#!/usr/bin/env bash
set -euo pipefail
umask 077

cd "$(dirname "${BASH_SOURCE[0]}")/.."

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

[[ -f .env ]] || fail ".env is missing; run scripts/deploy_full_stack.sh first"

set -a
# shellcheck disable=SC1091
source .env
set +a

git_head="$(git rev-parse HEAD)"
[[ "${SARA_BUILD_COMMIT:-}" == "$git_head" ]] || fail "SARA_BUILD_COMMIT does not match Git HEAD"
[[ -n "${SARA_RELEASE_ID:-}" && "${SARA_RELEASE_ID}" != "UNVERIFIED" ]] || fail "release identity is not promoted"

if ! git diff --quiet -- . || ! git diff --cached --quiet -- .; then
  fail "tracked deployment subtree is dirty"
fi

container_uid="${WS_DEPLOY_CONTAINER_UID:-10001}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
evidence_root=".deployment-evidence/full-stack"
mkdir -p "$evidence_root"
chmod 0700 .deployment-evidence "$evidence_root"
evidence_dir="${evidence_root}/${stamp}-$"
if ! mkdir -m 0700 "$evidence_dir"; then
  fail "could not create unique deployment evidence directory"
fi

preflight_receipt="${evidence_dir}/preflight.json"
operator_uid="$(id -u)"
operator_gid="$(id -g)"
if [[ "$operator_uid" -eq 0 ]]; then
  python3 worldshepherd_sara/deployment_preflight.py --env .env --expected-head "$git_head" --required-uid "$container_uid" --output "$preflight_receipt" >/dev/null
else
  sudo python3 worldshepherd_sara/deployment_preflight.py --env .env --expected-head "$git_head" --required-uid "$container_uid" --output "$preflight_receipt" >/dev/null
  sudo chown "${operator_uid}:${operator_gid}" "$preflight_receipt"
  chmod 0600 "$preflight_receipt"
fi

sara_url="http://127.0.0.1:${SARA_HOST_PORT:-9530}"
prime_url="http://127.0.0.1:${PRIME_SENTINEL_HOST_PORT:-9540}"
echo_url="http://127.0.0.1:${ECHO_HOST_PORT:-9550}"

curl --fail --silent --show-error "${sara_url}/readyz" > "${evidence_dir}/sara.ready.json"
curl --fail --silent --show-error "${sara_url}/health" > "${evidence_dir}/sara.health.json"
curl --fail --silent --show-error "${prime_url}/readyz" > "${evidence_dir}/prime.ready.json"
curl --fail --silent --show-error "${prime_url}/v1/public-key" > "${evidence_dir}/prime.public-key.json"
curl --fail --silent --show-error "${echo_url}/readyz" > "${evidence_dir}/echo.ready.json"

curl --fail --silent --show-error   -H "Authorization: Bearer ${SARA_ADMIN_TOKEN}"   "${sara_url}/admin/selftest" > "${evidence_dir}/sara.selftest.json"

relay_admin_status="$(
  curl --silent --output "${evidence_dir}/sara.relay-admin-denied.json"     --write-out '%{http_code}'     -H "Authorization: Bearer ${SARA_RELAY_TOKEN}"     "${sara_url}/admin/registry"
)"
[[ "$relay_admin_status" == "403" ]] || fail "relay token was not denied administrator access"

python3 - .env "${evidence_dir}/sara.health.json" "${evidence_dir}/prime.public-key.json" <<'PY'
import json
import sys
from pathlib import Path

env = {}
for raw in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if not raw or raw.lstrip().startswith("#") or "=" not in raw:
        continue
    key, value = raw.split("=", 1)
    env[key] = value.strip().strip("'\"")
health = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
public = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
trust = json.loads(env["PRIME_SENTINEL_PUBLIC_KEYS_JSON"])
assert health["prime_sentinel_public_keys_configured"] is True
assert public["key_id"] == env["PRIME_SENTINEL_SIGNING_KEY_ID"]
assert trust[public["key_id"]] == public["public_key_b64url"]
assert len(public["fingerprint_sha256"]) == 64
PY

read_secret() {
  local path="$1"
  if [[ -r "$path" ]]; then
    cat "$path"
  elif [[ "$(id -u)" -eq 0 ]]; then
    cat "$path"
  elif command -v sudo >/dev/null 2>&1; then
    sudo cat "$path"
  else
    fail "cannot read required deployment secret file metadata"
  fi
}

prime_service_token="$(read_secret "${PRIME_SENTINEL_SERVICE_TOKEN_HOST_PATH}")"
prime_service_token="${prime_service_token%$'\n'}"
prime_request_id="PSREQ-DEPLOY-${stamp}-${git_head:0:8}"
prime_id="PRIME-DEPLOY-${git_head:0:12}"

curl --fail --silent --show-error -X POST "${prime_url}/v1/requalification-release"   -H "Authorization: Bearer ${prime_service_token}"   -H "X-Prime-Sentinel-Request-Id: ${prime_request_id}"   -H 'Content-Type: application/json'   --data "{\"prime_id\":\"${prime_id}\",\"target_environment\":\"SPACE\",\"lifetime_seconds\":300}"   > "${evidence_dir}/prime.issued.json"

docker compose exec -T sara python -c '
import json, sys
from worldshepherd_sara.prime_sentinel_authorization import (
    PrimeSentinelAuthorizationAssertion,
    PrimeSentinelVerifier,
)
record=json.load(sys.stdin)
assertion=PrimeSentinelAuthorizationAssertion.model_validate(record["assertion"])
verified=PrimeSentinelVerifier.from_environment().verify(assertion)
print(json.dumps({
    "schema":"WS-DEPLOY-PRIME-VERIFY-V1",
    "status":"PASS",
    "authorization_id":verified.authorization_id,
    "key_id":verified.key_id,
    "key_fingerprint_sha256":verified.key_fingerprint_sha256,
}, sort_keys=True))
' < "${evidence_dir}/prime.issued.json" > "${evidence_dir}/prime.verified-by-sara.json"

echo_token="$(read_secret "${ECHO_INGEST_TOKEN_HOST_PATH}")"
echo_token="${echo_token%$'\n'}"
echo_event_id="$(python3 - <<'PY'
import uuid
print("SARA-EVENT-DEPLOY-" + str(uuid.uuid4()))
PY
)"
event_timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

curl --fail --silent --show-error -X POST "${echo_url}/v1/ingest"   -H "Authorization: Bearer ${echo_token}"   -H 'Content-Type: application/json'   --data "{\"timestamp\":\"${event_timestamp}\",\"event\":\"deployment_acceptance_probe\",\"actor\":\"deployment_verifier\",\"payload\":{\"_outbox_event_id\":\"${echo_event_id}\",\"_delivery_semantics\":\"AT_LEAST_ONCE\",\"release_id\":\"${SARA_RELEASE_ID}\",\"build_commit\":\"${SARA_BUILD_COMMIT}\"}}"   > "${evidence_dir}/echo.ingest.json"

curl --fail --silent --show-error   -H "Authorization: Bearer ${echo_token}"   "${echo_url}/v1/checkpoint/public-key" > "${evidence_dir}/echo.public-key.json"

curl --fail --silent --show-error -X POST   -H "Authorization: Bearer ${echo_token}"   "${echo_url}/v1/checkpoint" > "${evidence_dir}/echo.checkpoint.json"

curl --fail --silent --show-error   -H "Authorization: Bearer ${echo_token}"   "${echo_url}/v1/checkpoint/status" > "${evidence_dir}/echo.checkpoint-status.json"

echo_fingerprint="$(python3 - "${evidence_dir}/echo.public-key.json" <<'PY'
import json, sys
from pathlib import Path
value=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert value["algorithm"] == "Ed25519"
assert len(value["fingerprint_sha256"]) == 64
print(value["fingerprint_sha256"])
PY
)"

docker compose exec -T echo python -c '
import json, sys
from worldshepherd_sara.echo_checkpoint_verify import verify_bundle
bundle=json.load(sys.stdin)
verified=verify_bundle(bundle, sys.argv[1])
print(json.dumps({
    "schema":"WS-DEPLOY-ECHO-CHECKPOINT-VERIFY-V1",
    "status":"PASS",
    "checkpoint_id":verified["checkpoint_id"],
    "checkpoint_sha256":verified["checkpoint_sha256"],
    "event_count":verified["event_count"],
    "key_id":verified["key_id"],
    "key_fingerprint_sha256":verified["key_fingerprint_sha256"],
    "signature_input_schema":verified["signature_input_schema"],
}, sort_keys=True))
' "$echo_fingerprint" < "${evidence_dir}/echo.checkpoint.json" > "${evidence_dir}/echo.checkpoint-verified.json"

inspect_dir="$(mktemp -d)"
cleanup_inspect() {
  rm -rf "$inspect_dir"
}
trap cleanup_inspect EXIT

for service in sara prime-sentinel echo; do
  container_id="$(docker compose --profile prime-sentinel --profile echo ps -q "$service")"
  [[ -n "$container_id" ]] || fail "${service} container is missing"
  docker inspect "$container_id" > "${inspect_dir}/${service}.json"
done

python3 - "$evidence_dir" "$inspect_dir" "$git_head" "${SARA_RELEASE_ID}" <<'PY'
import json
import sys
from pathlib import Path

root=Path(sys.argv[1])
inspect_root=Path(sys.argv[2])
head=sys.argv[3]
release=sys.argv[4]
security = {}

for service in ("sara", "prime-sentinel", "echo"):
    record=json.loads((inspect_root / f"{service}.json").read_text(encoding="utf-8"))[0]
    config=record["Config"]
    host=record["HostConfig"]
    labels=config.get("Labels") or {}
    assert labels.get("org.opencontainers.image.revision") == head
    assert labels.get("org.opencontainers.image.version") == release
    assert config.get("User") not in ("", "0", "root")
    assert host.get("ReadonlyRootfs") is True
    assert "ALL" in (host.get("CapDrop") or [])
    assert any(item.startswith("no-new-privileges") for item in (host.get("SecurityOpt") or []))
    for bindings in (host.get("PortBindings") or {}).values():
        for binding in bindings or []:
            assert binding.get("HostIp") == "127.0.0.1"
    security[service] = {
        "container_id": record["Id"],
        "image_id": record["Image"],
        "user": config.get("User"),
        "read_only_rootfs": True,
        "cap_drop_all": True,
        "no_new_privileges": True,
        "loopback_only_ports": True,
        "image_revision": labels.get("org.opencontainers.image.revision"),
        "image_version": labels.get("org.opencontainers.image.version"),
    }

sara=json.loads((inspect_root / "sara.json").read_text(encoding="utf-8"))[0]
prime=json.loads((inspect_root / "prime-sentinel.json").read_text(encoding="utf-8"))[0]
echo=json.loads((inspect_root / "echo.json").read_text(encoding="utf-8"))[0]

sara_env=sara["Config"].get("Env") or []
for name in (
    "PRIME_SENTINEL_PRIVATE_KEY_FILE",
    "PRIME_SENTINEL_PRIVATE_KEY_HOST_PATH",
    "PRIME_SENTINEL_SERVICE_TOKEN_FILE",
    "PRIME_SENTINEL_SERVICE_TOKEN_HOST_PATH",
    "PRIME_SENTINEL_SERVICE_TOKEN",
    "ECHO_INGEST_TOKEN_FILE",
    "ECHO_INGEST_TOKEN_HOST_PATH",
    "ECHO_CHECKPOINT_PRIVATE_KEY_FILE",
    "ECHO_CHECKPOINT_PRIVATE_KEY_HOST_PATH",
):
    assert not any(
        item.startswith(name + "=") and item.split("=", 1)[1]
        for item in sara_env
    ), f"SARA received forbidden secret ingress: {name}"

for record in (prime, echo):
    env=record["Config"].get("Env") or []
    assert not any(item.startswith("SARA_ADMIN_TOKEN=") and item.split("=",1)[1] for item in env)
    assert not any(item.startswith("SARA_RELAY_TOKEN=") and item.split("=",1)[1] for item in env)

sara_health=json.loads((root / "sara.health.json").read_text(encoding="utf-8"))
sara_selftest=json.loads((root / "sara.selftest.json").read_text(encoding="utf-8"))
prime_ready=json.loads((root / "prime.ready.json").read_text(encoding="utf-8"))
echo_ready=json.loads((root / "echo.ready.json").read_text(encoding="utf-8"))
prime_public=json.loads((root / "prime.public-key.json").read_text(encoding="utf-8"))
echo_public=json.loads((root / "echo.public-key.json").read_text(encoding="utf-8"))
echo_verified=json.loads((root / "echo.checkpoint-verified.json").read_text(encoding="utf-8"))
prime_verified=json.loads((root / "prime.verified-by-sara.json").read_text(encoding="utf-8"))
preflight=json.loads((root / "preflight.json").read_text(encoding="utf-8"))

(root / "container-security.json").write_text(
    json.dumps(
        {
            "schema": "WS-VERIFIED-LOCAL-CONTAINER-SECURITY-V1",
            "status": "PASS",
            "services": security,
        },
        sort_keys=True,
        indent=2,
    ) + "\n",
    encoding="utf-8",
)

assert sara_health["ok"] is True
assert sara_selftest["ok"] is True
assert prime_ready["ok"] is True
assert echo_ready["ok"] is True
assert echo_verified["status"] == "PASS"
assert prime_verified["status"] == "PASS"
assert preflight["status"] == "PASS"

receipt={
    "schema":"WS-VERIFIED-LOCAL-FULL-STACK-DEPLOYMENT-RECEIPT-V1",
    "status":"PASS",
    "build_commit":head,
    "release_id":release,
    "localhost_only":True,
    "container_hardening":{
        "non_root":True,
        "read_only_rootfs":True,
        "cap_drop_all":True,
        "no_new_privileges":True,
    },
    "sara":{
        "ready":True,
        "selftest":True,
        "relay_admin_separation":True,
        "prime_trust_configured":True,
    },
    "prime_sentinel":{
        "ready":True,
        "signing_transaction_verified_by_sara":True,
        "key_id":prime_public["key_id"],
        "key_fingerprint_sha256":prime_public["fingerprint_sha256"],
    },
    "echo":{
        "ready":True,
        "ingest_probe":True,
        "signed_checkpoint_verified":True,
        "key_id":echo_public["key_id"],
        "key_fingerprint_sha256":echo_public["fingerprint_sha256"],
        "signature_input_schema":echo_verified["signature_input_schema"],
    },
    "sanitized_config_sha256":preflight["sanitized_config_sha256"],
    "claims_boundary":(
        "PASS establishes the tested localhost-only SARA/PRIME/ECHO software "
        "deployment baseline at the named commit. It does not authorize public "
        "exposure, CUI/classified processing, HSM/KMS custody claims, external "
        "certification, government acceptance, or independent validation."
    ),
}
(root / "receipt.json").write_text(
    json.dumps(receipt, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)
PY

docker compose --profile prime-sentinel --profile echo ps > "${evidence_dir}/compose.ps.txt"
cleanup_inspect
trap - EXIT
sha256sum "${evidence_dir}"/* > "${evidence_dir}/SHA256SUMS"

printf 'Full-stack deployment acceptance: PASS\n'
printf 'Receipt: %s/receipt.json\n' "$evidence_dir"

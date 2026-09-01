#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${TLS_PROXY_EVIDENCE_DIR:-$ROOT/tls_proxy_evidence}"
SOURCE_SHA="${GITHUB_SHA:-$(git -C "$ROOT" rev-parse HEAD)}"
HOST_PORT="${TLS_PROXY_HOST_PORT:-19443}"
RUN_KEY="${GITHUB_RUN_ID:-local}-$$"
SAFE_KEY="${RUN_KEY//[^a-zA-Z0-9_.-]/_}"
IMAGE="sara-tls-architecture:${SOURCE_SHA:0:12}"
FRONT_NETWORK="sara_tls_front_${SAFE_KEY}"
BACK_NETWORK="sara_tls_back_${SAFE_KEY}"
DATA_VOLUME="sara_tls_data_${SAFE_KEY}"
SARA_CONTAINER="sara-tls-backend-${SAFE_KEY}"
PROXY_CONTAINER="sara-tls-proxy-${SAFE_KEY}"
ADMIN_TOKEN="$(openssl rand -hex 32)"
RELAY_TOKEN="$(openssl rand -hex 32)"
CERT_DIR="$OUT_DIR/ephemeral-cert"

mkdir -p "$OUT_DIR" "$CERT_DIR"
rm -f "$OUT_DIR"/*.json "$OUT_DIR"/*.txt "$CERT_DIR"/*

cleanup() {
  local status=$?
  if [ "$status" -ne 0 ]; then
    echo "TLS drill failed; preserving diagnostics before cleanup" >&2
    docker ps -a --no-trunc >&2 || true
    docker logs "$SARA_CONTAINER" >&2 || true
    docker logs "$PROXY_CONTAINER" >&2 || true
  fi
  docker rm -f "$SARA_CONTAINER" "$PROXY_CONTAINER" >/dev/null 2>&1 || true
  docker network rm "$FRONT_NETWORK" "$BACK_NETWORK" >/dev/null 2>&1 || true
  docker volume rm "$DATA_VOLUME" >/dev/null 2>&1 || true
  rm -rf "$CERT_DIR"
}
trap cleanup EXIT

wait_https() {
  for _ in $(seq 1 60); do
    if curl --noproxy '*' --silent --show-error --fail \
      --cacert "$CERT_DIR/cert.pem" \
      --resolve "sara.local:${HOST_PORT}:127.0.0.1" \
      "https://sara.local:${HOST_PORT}/readyz" >/dev/null 2>&1; then
      return 0
    fi
    if [ "$(docker inspect --format '{{.State.Running}}' "$PROXY_CONTAINER" 2>/dev/null || echo false)" != "true" ]; then
      docker logs "$PROXY_CONTAINER" >&2 || true
      return 1
    fi
    sleep 1
  done
  docker logs "$PROXY_CONTAINER" >&2 || true
  docker logs "$SARA_CONTAINER" >&2 || true
  return 1
}

echo "[tls] build exact tested SARA image"
docker build \
  --build-arg SARA_BUILD_COMMIT="$SOURCE_SHA" \
  --build-arg SARA_RELEASE_ID="tls-architecture-${SOURCE_SHA}" \
  -t "$IMAGE" "$ROOT" >/dev/null

# Two-zone reference topology: frontend is host-reachable through the proxy only;
# backend is Docker-internal and contains SARA plus the proxy's backend interface.
docker network create "$FRONT_NETWORK" >/dev/null
docker network create --internal "$BACK_NETWORK" >/dev/null
docker volume create "$DATA_VOLUME" >/dev/null
docker run --rm --user 0 -v "$DATA_VOLUME:/data" "$IMAGE" sh -c 'chown -R 10001:10001 /data && chmod 0700 /data'

# Ephemeral CI-only certificate. This proves the termination topology, not production identity.
openssl req -x509 -newkey rsa:2048 -sha256 -nodes \
  -keyout "$CERT_DIR/key.pem" \
  -out "$CERT_DIR/cert.pem" \
  -days 1 \
  -subj '/CN=sara.local' \
  -addext 'subjectAltName=DNS:sara.local' >/dev/null 2>&1
chmod 0755 "$CERT_DIR"
chmod 0644 "$CERT_DIR/cert.pem" "$CERT_DIR/key.pem"

# SARA exists only on the internal backend network and has NO host-published port.
docker run -d \
  --name "$SARA_CONTAINER" \
  --network "$BACK_NETWORK" \
  --network-alias sara \
  --read-only \
  --tmpfs /tmp:size=16m,mode=1777 \
  --security-opt no-new-privileges:true \
  --cap-drop ALL \
  -e SARA_RELAY_TOKEN="$RELAY_TOKEN" \
  -e SARA_ADMIN_TOKEN="$ADMIN_TOKEN" \
  -e SARA_BIND_HOST=0.0.0.0 \
  -e SARA_PORT=9530 \
  -e SARA_DATA_DIR=/var/lib/sara \
  -e SARA_MODE=tls-private-backend-reference \
  -v "$DATA_VOLUME:/var/lib/sara" \
  "$IMAGE" >/dev/null

# Proxy starts on the frontend, publishes TLS on loopback, then receives a second
# interface on the internal backend so it can reach SARA without exposing SARA.
docker run -d \
  --name "$PROXY_CONTAINER" \
  --network "$FRONT_NETWORK" \
  --read-only \
  --tmpfs /tmp:size=8m,mode=1777 \
  --security-opt no-new-privileges:true \
  --cap-drop ALL \
  --no-healthcheck \
  -p "127.0.0.1:${HOST_PORT}:8443" \
  -v "$ROOT/scripts/tls_reference_proxy.py:/proxy/tls_reference_proxy.py:ro" \
  -v "$CERT_DIR:/certs:ro" \
  "$IMAGE" \
  python /proxy/tls_reference_proxy.py \
    --port 8443 \
    --upstream-host sara \
    --upstream-port 9530 \
    --cert /certs/cert.pem \
    --key /certs/key.pem >/dev/null
docker network connect "$BACK_NETWORK" "$PROXY_CONTAINER"

wait_https

curl --noproxy '*' --silent --show-error --fail \
  --cacert "$CERT_DIR/cert.pem" \
  --resolve "sara.local:${HOST_PORT}:127.0.0.1" \
  "https://sara.local:${HOST_PORT}/health" > "$OUT_DIR/https-health.json"
curl --noproxy '*' --silent --show-error --fail \
  --cacert "$CERT_DIR/cert.pem" \
  --resolve "sara.local:${HOST_PORT}:127.0.0.1" \
  "https://sara.local:${HOST_PORT}/readyz" > "$OUT_DIR/https-readyz.json"

# Plain HTTP to the TLS listener must not succeed as an application response.
if curl --noproxy '*' --silent --fail "http://127.0.0.1:${HOST_PORT}/health" > "$OUT_DIR/plaintext-response.txt" 2>/dev/null; then
  echo 'plaintext request unexpectedly succeeded' >&2
  exit 1
fi

# Backend must expose no host binding whatsoever.
BACKEND_PORTS="$(docker port "$SARA_CONTAINER" 2>/dev/null || true)"
printf '%s' "$BACKEND_PORTS" > "$OUT_DIR/backend-published-ports.txt"
test -z "$BACKEND_PORTS"

# Verify TLS 1.2 negotiation and certificate identity from the host side.
openssl s_client -connect "127.0.0.1:${HOST_PORT}" -servername sara.local -tls1_2 < /dev/null \
  > "$OUT_DIR/tls12-session.txt" 2>&1
grep -Eq 'Protocol *: TLSv1\.2|Protocol  *: TLSv1\.2|New, TLSv1\.2' "$OUT_DIR/tls12-session.txt"
openssl x509 -in "$CERT_DIR/cert.pem" -noout -subject -issuer -dates -ext subjectAltName \
  > "$OUT_DIR/certificate-summary.txt"
grep -F 'DNS:sara.local' "$OUT_DIR/certificate-summary.txt" >/dev/null

SARA_RUNNING="$(docker inspect --format '{{.State.Running}}' "$SARA_CONTAINER")"
PROXY_RUNNING="$(docker inspect --format '{{.State.Running}}' "$PROXY_CONTAINER")"
SARA_USER="$(docker inspect --format '{{.Config.User}}' "$SARA_CONTAINER")"
PROXY_USER="$(docker inspect --format '{{.Config.User}}' "$PROXY_CONTAINER")"
PROXY_BINDING="$(docker port "$PROXY_CONTAINER" 8443/tcp)"
FRONT_INTERNAL="$(docker network inspect --format '{{.Internal}}' "$FRONT_NETWORK")"
BACK_INTERNAL="$(docker network inspect --format '{{.Internal}}' "$BACK_NETWORK")"
SARA_NETWORK_COUNT="$(docker inspect "$SARA_CONTAINER" --format '{{len .NetworkSettings.Networks}}')"
PROXY_NETWORK_COUNT="$(docker inspect "$PROXY_CONTAINER" --format '{{len .NetworkSettings.Networks}}')"
SARA_ON_BACK="$(docker inspect "$SARA_CONTAINER" --format "{{if index .NetworkSettings.Networks \"$BACK_NETWORK\"}}true{{else}}false{{end}}")"
SARA_ON_FRONT="$(docker inspect "$SARA_CONTAINER" --format "{{if index .NetworkSettings.Networks \"$FRONT_NETWORK\"}}true{{else}}false{{end}}")"
PROXY_ON_BACK="$(docker inspect "$PROXY_CONTAINER" --format "{{if index .NetworkSettings.Networks \"$BACK_NETWORK\"}}true{{else}}false{{end}}")"
PROXY_ON_FRONT="$(docker inspect "$PROXY_CONTAINER" --format "{{if index .NetworkSettings.Networks \"$FRONT_NETWORK\"}}true{{else}}false{{end}}")"
export OUT_DIR SOURCE_SHA SARA_RUNNING PROXY_RUNNING SARA_USER PROXY_USER PROXY_BINDING FRONT_INTERNAL BACK_INTERNAL SARA_NETWORK_COUNT PROXY_NETWORK_COUNT SARA_ON_BACK SARA_ON_FRONT PROXY_ON_BACK PROXY_ON_FRONT HOST_PORT

python - <<'PY'
import datetime, hashlib, json, os, pathlib
root = pathlib.Path(os.environ['OUT_DIR'])
load = lambda name: json.loads((root / name).read_text(encoding='utf-8'))
health = load('https-health.json')
ready = load('https-readyz.json')
checks = {
    'https_health_ok': health.get('ok') is True,
    'https_readiness_ok': ready.get('ok') is True and ready.get('status') == 'ready',
    'backend_has_no_host_published_port': (root / 'backend-published-ports.txt').read_text(encoding='utf-8') == '',
    'sara_container_running': os.environ['SARA_RUNNING'] == 'true',
    'proxy_container_running': os.environ['PROXY_RUNNING'] == 'true',
    'sara_non_root_user': os.environ['SARA_USER'] == 'sara',
    'proxy_non_root_user': os.environ['PROXY_USER'] == 'sara',
    'proxy_bound_loopback_only': os.environ['PROXY_BINDING'].startswith('127.0.0.1:'),
    'frontend_network_not_internal': os.environ['FRONT_INTERNAL'] == 'false',
    'backend_network_marked_internal': os.environ['BACK_INTERNAL'] == 'true',
    'sara_has_single_backend_network_only': os.environ['SARA_NETWORK_COUNT'] == '1' and os.environ['SARA_ON_BACK'] == 'true' and os.environ['SARA_ON_FRONT'] == 'false',
    'proxy_bridges_front_and_back_only': os.environ['PROXY_NETWORK_COUNT'] == '2' and os.environ['PROXY_ON_BACK'] == 'true' and os.environ['PROXY_ON_FRONT'] == 'true',
    'tls12_negotiated': 'TLSv1.2' in (root / 'tls12-session.txt').read_text(encoding='utf-8', errors='replace'),
    'certificate_san_matches_reference_name': 'DNS:sara.local' in (root / 'certificate-summary.txt').read_text(encoding='utf-8'),
}
record = {
    'schema': 'WS-SARA-TLS-PRIVATE-BACKEND-ARCHITECTURE-EVIDENCE-V1',
    'evidence_status': 'INTERNAL_CI_GENERATED_EPHEMERAL_IDENTITY',
    'result': 'PASS' if all(checks.values()) else 'FAIL',
    'executed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_build_commit': os.environ['SOURCE_SHA'],
    'public_test_endpoint': f"127.0.0.1:{os.environ['HOST_PORT']} (TLS only)",
    'backend_host_port_exposure': 'NONE',
    'network_topology': 'host -> frontend network/TLS proxy -> internal backend network -> SARA',
    'tls_minimum_version': 'TLSv1.2',
    'certificate_identity': 'sara.local — ephemeral self-signed CI certificate',
    'checks': checks,
    'evidence_sha256': {
        name: 'sha256:' + hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in ('https-health.json','https-readyz.json','tls12-session.txt','certificate-summary.txt')
    },
    'claims_boundary': (
        'This evidence validates a bounded two-zone reference topology in CI: TLS terminates at a separate non-root proxy; '
        'SARA has no host-published port and exists only on an internal backend network; the proxy bridges a frontend network '
        'to that backend. The certificate is ephemeral and self-signed. This does not establish production identity, public '
        'DNS ownership, public-CA issuance, production key/HSM custody, enterprise reverse-proxy hardening, internet exposure '
        'approval, WAF/DDoS controls, customer authorization, ATO, certification, or field readiness.'
    ),
}
(root / 'tls-private-backend-architecture.json').write_text(json.dumps(record, sort_keys=True, indent=2)+'\n', encoding='utf-8')
if record['result'] != 'PASS':
    raise SystemExit('TLS_PROXY_ARCHITECTURE: FAIL ' + json.dumps(checks, sort_keys=True))
print('TLS_PROXY_ARCHITECTURE: PASS')
PY

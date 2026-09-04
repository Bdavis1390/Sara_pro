# WS-HMAA v0.6 — Short-Lived Sandbox OAuth Credential Lifecycle

Status: IMPLEMENTED IN SOFTWARE / NOT LIVE-VALIDATED

## Objective

WS-HMAA v0.6 adds a bounded OAuth 2.0 client-credentials lifecycle for the read-only Lattice Sandbox transport introduced in v0.5. It does not perform a live Sandbox call and does not add any entity publish, task create/update, manual-control, flight-control, weapons, or arbitrary HTTP operation.

`live_environment_validated` remains false.

## Public authentication basis

Current public Anduril documentation reviewed 2026-09-04 describes the Sandbox machine-to-machine flow as:

- `POST /api/v1/oauth/token` on the Sandbox environment endpoint;
- `Content-Type: application/x-www-form-urlencoded`;
- `Anduril-Sandbox-Authorization: Bearer <SANDBOXES_TOKEN>`;
- form fields `grant_type=client_credentials`, `client_id`, and `client_secret`;
- response fields including `access_token`, `token_type`, and `expires_in`;
- cached short-lived access tokens refreshed before expiry rather than reacquired for every API request.

Official references:

- https://developer.anduril.com/guides/getting-started/authenticate
- https://developer.anduril.com/guides/getting-started/quickstart
- https://developer.anduril.com/reference/rest/oauth/create-token
- https://developer.anduril.com/guides/developer-tools/sandboxes

## Runtime environment contract

OAuth mode consumes only:

```text
LATTICE_ENDPOINT
LATTICE_CLIENT_ID
LATTICE_CLIENT_SECRET
SANDBOXES_TOKEN
```

The existing static-token mode remains supported with:

```text
LATTICE_ENDPOINT
ENVIRONMENT_TOKEN
SANDBOXES_TOKEN
```

Real credential values must remain outside the repository.

## OAuth controls

`SandboxClientCredentialsTokenProvider` adds:

- exact token path `/api/v1/oauth/token`;
- HTTPS-only, official `*.env.sandboxes.developer.anduril.com` endpoint restriction;
- blocked redirects;
- form-urlencoded client-credentials request body;
- account-level Sandbox authorization header;
- bounded token response size;
- JSON-object response validation;
- required non-empty `access_token`;
- required Bearer `token_type`;
- required positive integer `expires_in`;
- fail-closed behavior when expiry metadata is absent or invalid;
- in-memory token cache only;
- monotonic-clock expiry tracking;
- configurable pre-expiry refresh skew;
- explicit cache clearing;
- secret-redacted diagnostics and errors;
- no refresh-token persistence or support.

The provider does not make a network call on construction.

## Read-only transport integration

`SandboxReadOnlySSETransport` remains backward compatible with the v0.5 static bearer-token mode. It now also accepts an `EnvironmentTokenProvider`.

When a provider is configured, each stream request asks the provider for a currently valid short-lived bearer token. The transport itself does not persist or cache that token. All v0.5 restrictions remain in force:

- exact entity/task stream endpoint allowlist only;
- Sandbox host restriction;
- redirects blocked;
- bounded SSE parsing;
- sanitized errors;
- no write/control methods.

## Claims boundary

Passing v0.6 demonstrates that the repository contains a CI-testable, secret-safe implementation of the documented Sandbox client-credentials lifecycle. It does not establish:

- possession of valid Anduril credentials;
- successful live OAuth authentication;
- successful live SSE connectivity;
- Anduril or Hermeus review/approval;
- Quarterhorse or operational mission-system integration;
- flight-control, mission-command, task-execution, weapons, or other control authority.

## Next external evidence gate

Once legitimate Sandbox credentials are provisioned, the next governed step is a finite read-only trial:

1. load the credential variables outside the repository;
2. acquire a short-lived token through the v0.6 provider;
3. run the v0.5 finite entity/task capture;
4. preserve only secret-free HMAA evidence and diagnostics;
5. repeat the capture to demonstrate reproducibility;
6. independently review the resulting evidence chain;
7. only then create a separate attestation capable of changing Sandbox read interoperability from `live_environment_validated=false`.

Production integration remains a later and independent gate.

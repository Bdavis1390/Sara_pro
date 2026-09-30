-- WS-QCRYPTO/TSV v3.6 dedicated synthetic resilience state.
create table if not exists public.qcrypto_tsv_v36_cursor (
  stream_key text primary key,
  source_kind text not null,
  provider_id text not null,
  symbol text not null,
  session_id text not null,
  last_sequence bigint not null check (last_sequence > 0),
  last_payload_sha256 text not null check (last_payload_sha256 ~ '^[0-9a-f]{64}$'),
  last_effective_at timestamptz not null,
  state_sha256 text not null check (state_sha256 ~ '^[0-9a-f]{64}$'),
  revision bigint not null default 1 check (revision > 0),
  updated_at timestamptz not null default now(),
  test_namespace text not null default 'default'
);
alter table public.qcrypto_tsv_v36_cursor enable row level security;
create index if not exists qcrypto_tsv_v36_cursor_namespace_idx on public.qcrypto_tsv_v36_cursor(test_namespace, stream_key);

create table if not exists public.qcrypto_tsv_v36_receipt (
  id bigint generated always as identity primary key,
  test_namespace text not null,
  case_name text not null,
  decision text not null check (decision in ('ALLOW','DENY')),
  receipt_sha256 text not null check (receipt_sha256 ~ '^[0-9a-f]{64}$'),
  created_at timestamptz not null default now()
);
alter table public.qcrypto_tsv_v36_receipt enable row level security;
create index if not exists qcrypto_tsv_v36_receipt_namespace_idx on public.qcrypto_tsv_v36_receipt(test_namespace, created_at desc);

CREATE TABLE IF NOT EXISTS consistency_operations (
  operation_id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
  operation_kind TEXT NOT NULL
    CHECK(operation_kind IN ('upload', 'process', 'index', 'export')),
  idempotency_key_hash TEXT NOT NULL
    CHECK(length(idempotency_key_hash) = 64
      AND idempotency_key_hash NOT GLOB '*[^0-9a-f]*'),
  request_fingerprint TEXT NOT NULL
    CHECK(length(request_fingerprint) = 64
      AND request_fingerprint NOT GLOB '*[^0-9a-f]*'),
  artifact_id TEXT,
  artifact_version_id TEXT,
  storage_backend TEXT,
  storage_key TEXT,
  staged_object_name TEXT
    CHECK(staged_object_name IS NULL
      OR (
        length(staged_object_name) BETWEEN 1 AND 180
        AND staged_object_name NOT LIKE '%/%'
        AND staged_object_name NOT LIKE '%\%'
      )),
  original_name TEXT,
  reported_media_type TEXT,
  size_bytes INTEGER CHECK(size_bytes IS NULL OR size_bytes >= 0),
  content_sha256 TEXT
    CHECK(content_sha256 IS NULL
      OR (
        length(content_sha256) = 64
        AND content_sha256 NOT GLOB '*[^0-9a-f]*'
      )),
  state TEXT NOT NULL
    CHECK(state IN (
      'intent_recorded',
      'effect_pending',
      'effect_applied',
      'commit_pending',
      'outbox_committed',
      'converged',
      'isolated'
    )),
  attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count >= 0),
  next_attempt_at TEXT,
  last_error_code TEXT,
  row_version INTEGER NOT NULL DEFAULT 1 CHECK(row_version >= 1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(workspace_id, operation_kind, idempotency_key_hash),
  CHECK(
    operation_kind != 'upload'
    OR (
      artifact_id IS NOT NULL
      AND artifact_version_id IS NOT NULL
      AND storage_backend IS NOT NULL
      AND storage_key IS NOT NULL
      AND staged_object_name IS NOT NULL
      AND original_name IS NOT NULL
      AND reported_media_type IS NOT NULL
      AND size_bytes IS NOT NULL
      AND content_sha256 IS NOT NULL
    )
  )
);

CREATE INDEX IF NOT EXISTS consistency_operations_reconcile
  ON consistency_operations(state, next_attempt_at, updated_at, operation_id);

CREATE TABLE IF NOT EXISTS consistency_outbox (
  outbox_event_id TEXT PRIMARY KEY,
  operation_id TEXT NOT NULL REFERENCES consistency_operations(operation_id),
  effect_kind TEXT NOT NULL
    CHECK(effect_kind IN ('upload', 'process', 'index', 'export', 'notify')),
  dedupe_key TEXT NOT NULL UNIQUE
    CHECK(length(dedupe_key) = 64
      AND dedupe_key NOT GLOB '*[^0-9a-f]*'),
  state TEXT NOT NULL
    CHECK(state IN ('pending', 'leased', 'retry', 'delivered', 'isolated')),
  attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count >= 0),
  available_at TEXT NOT NULL,
  lease_until TEXT,
  last_error_code TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(operation_id, effect_kind)
);

CREATE INDEX IF NOT EXISTS consistency_outbox_delivery
  ON consistency_outbox(state, available_at, lease_until, outbox_event_id);

CREATE TABLE IF NOT EXISTS consistency_effect_receipts (
  dedupe_key TEXT PRIMARY KEY
    REFERENCES consistency_outbox(dedupe_key),
  operation_id TEXT NOT NULL REFERENCES consistency_operations(operation_id),
  effect_kind TEXT NOT NULL
    CHECK(effect_kind IN ('upload', 'process', 'index', 'export', 'notify')),
  receipt_hash TEXT NOT NULL
    CHECK(length(receipt_hash) = 64
      AND receipt_hash NOT GLOB '*[^0-9a-f]*'),
  applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS consistency_trace (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  trace_event_id TEXT NOT NULL UNIQUE,
  operation_id TEXT NOT NULL REFERENCES consistency_operations(operation_id),
  from_state TEXT,
  to_state TEXT NOT NULL,
  transition_code TEXT NOT NULL,
  error_code TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS consistency_trace_operation
  ON consistency_trace(operation_id, seq);

CREATE TRIGGER IF NOT EXISTS consistency_trace_no_update
BEFORE UPDATE ON consistency_trace
BEGIN
  SELECT RAISE(ABORT, 'consistency trace is append-only');
END;

CREATE TRIGGER IF NOT EXISTS consistency_trace_no_delete
BEFORE DELETE ON consistency_trace
BEGIN
  SELECT RAISE(ABORT, 'consistency trace is append-only');
END;

CREATE TABLE IF NOT EXISTS object_quarantine (
  quarantine_id TEXT PRIMARY KEY,
  operation_id TEXT REFERENCES consistency_operations(operation_id),
  storage_backend TEXT NOT NULL,
  storage_key TEXT NOT NULL,
  object_ref TEXT NOT NULL
    CHECK(length(object_ref) = 20
      AND object_ref NOT GLOB '*[^0-9a-f]*'),
  reason_code TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('isolated', 'released')),
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  UNIQUE(storage_backend, storage_key, reason_code)
);

CREATE INDEX IF NOT EXISTS object_quarantine_state
  ON object_quarantine(state, last_seen_at, quarantine_id);

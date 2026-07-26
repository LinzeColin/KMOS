CREATE TABLE IF NOT EXISTS restore_drill_proofs (
  proof_id TEXT PRIMARY KEY,
  backup_id TEXT NOT NULL,
  backup_manifest_sha256 TEXT NOT NULL
    CHECK(length(backup_manifest_sha256) = 64
      AND backup_manifest_sha256 NOT GLOB '*[^0-9a-f]*'),
  source_schema_version INTEGER NOT NULL CHECK(source_schema_version >= 1),
  expected_fixture_count INTEGER NOT NULL CHECK(expected_fixture_count > 0),
  restored_fixture_count INTEGER NOT NULL CHECK(restored_fixture_count >= 0),
  invariant_failures INTEGER NOT NULL CHECK(invariant_failures >= 0),
  measured_rpo_ms INTEGER NOT NULL CHECK(measured_rpo_ms >= 0),
  measured_rto_ms INTEGER NOT NULL CHECK(measured_rto_ms >= 0),
  artifact_identity_hash TEXT NOT NULL
    CHECK(length(artifact_identity_hash) = 64
      AND artifact_identity_hash NOT GLOB '*[^0-9a-f]*'),
  status TEXT NOT NULL CHECK(status IN ('passed', 'failed')),
  verified_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS restore_drill_proofs_verified
  ON restore_drill_proofs(status, source_schema_version, verified_at, proof_id);

CREATE TABLE IF NOT EXISTS workspace_retention (
  workspace_id TEXT PRIMARY KEY REFERENCES workspaces(workspace_id),
  state TEXT NOT NULL DEFAULT 'active'
    CHECK(state IN (
      'active',
      'deletion_requested',
      'blocked_hold',
      'purge_pending',
      'deleted'
    )),
  active_deletion_request_id TEXT UNIQUE,
  row_version INTEGER NOT NULL DEFAULT 1 CHECK(row_version >= 1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  deleted_at TEXT
);

INSERT INTO workspace_retention(
  workspace_id, state, active_deletion_request_id, row_version,
  created_at, updated_at, deleted_at
)
SELECT workspace_id, 'active', NULL, 1, created_at, updated_at, NULL
FROM workspaces
WHERE 1
ON CONFLICT(workspace_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS legal_holds (
  hold_id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
  reason_code TEXT NOT NULL
    CHECK(reason_code IN ('legal', 'security', 'regulatory')),
  authority_ref_hash TEXT NOT NULL
    CHECK(length(authority_ref_hash) = 64
      AND authority_ref_hash NOT GLOB '*[^0-9a-f]*'),
  state TEXT NOT NULL CHECK(state IN ('active', 'released')),
  imposed_at TEXT NOT NULL,
  released_at TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS legal_holds_one_active_reason
  ON legal_holds(workspace_id, reason_code)
  WHERE state = 'active';

CREATE TABLE IF NOT EXISTS deletion_requests (
  deletion_request_id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
  idempotency_key_hash TEXT NOT NULL
    CHECK(length(idempotency_key_hash) = 64
      AND idempotency_key_hash NOT GLOB '*[^0-9a-f]*'),
  request_fingerprint TEXT NOT NULL
    CHECK(length(request_fingerprint) = 64
      AND request_fingerprint NOT GLOB '*[^0-9a-f]*'),
  restore_proof_id TEXT NOT NULL REFERENCES restore_drill_proofs(proof_id),
  state TEXT NOT NULL
    CHECK(state IN (
      'requested',
      'revoking',
      'purge_pending',
      'retry',
      'blocked_hold',
      'completed'
    )),
  public_purge_due_at TEXT NOT NULL,
  public_purged_at TEXT,
  attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count >= 0),
  last_error_code TEXT,
  row_version INTEGER NOT NULL DEFAULT 1 CHECK(row_version >= 1),
  requested_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  completed_at TEXT,
  UNIQUE(workspace_id, idempotency_key_hash)
);

CREATE INDEX IF NOT EXISTS deletion_requests_worker
  ON deletion_requests(state, updated_at, deletion_request_id);

CREATE TABLE IF NOT EXISTS deletion_object_targets (
  deletion_request_id TEXT NOT NULL
    REFERENCES deletion_requests(deletion_request_id),
  artifact_version_id TEXT NOT NULL,
  artifact_id TEXT NOT NULL,
  storage_backend TEXT NOT NULL,
  storage_key TEXT NOT NULL,
  size_bytes INTEGER NOT NULL CHECK(size_bytes >= 0),
  sha256 TEXT NOT NULL
    CHECK(length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'),
  state TEXT NOT NULL CHECK(state IN ('pending', 'deleting', 'deleted')),
  attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count >= 0),
  last_error_code TEXT,
  deleted_at TEXT,
  PRIMARY KEY(deletion_request_id, artifact_version_id)
);

CREATE INDEX IF NOT EXISTS deletion_object_targets_worker
  ON deletion_object_targets(state, deletion_request_id, artifact_version_id);

CREATE TABLE IF NOT EXISTS publication_bindings (
  publication_id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
  subject_ref TEXT NOT NULL
    CHECK(length(subject_ref) = 20
      AND subject_ref NOT GLOB '*[^0-9a-f]*'),
  state TEXT NOT NULL CHECK(state IN ('active', 'revoked')),
  cache_state TEXT NOT NULL CHECK(cache_state IN ('active', 'purged')),
  index_state TEXT NOT NULL CHECK(index_state IN ('active', 'purged')),
  published_at TEXT NOT NULL,
  revoked_at TEXT,
  purged_at TEXT
);

CREATE INDEX IF NOT EXISTS publication_bindings_workspace_state
  ON publication_bindings(workspace_id, state, publication_id);

CREATE TABLE IF NOT EXISTS lifecycle_events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL UNIQUE,
  workspace_ref TEXT NOT NULL
    CHECK(length(workspace_ref) = 20
      AND workspace_ref NOT GLOB '*[^0-9a-f]*'),
  deletion_request_id TEXT REFERENCES deletion_requests(deletion_request_id),
  action TEXT NOT NULL,
  result_status TEXT NOT NULL,
  object_ref TEXT
    CHECK(object_ref IS NULL
      OR (
        length(object_ref) = 20
        AND object_ref NOT GLOB '*[^0-9a-f]*'
      )),
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS lifecycle_events_request
  ON lifecycle_events(deletion_request_id, seq);

CREATE TRIGGER IF NOT EXISTS lifecycle_events_no_update
BEFORE UPDATE ON lifecycle_events
BEGIN
  SELECT RAISE(ABORT, 'lifecycle events are append-only');
END;

CREATE TRIGGER IF NOT EXISTS lifecycle_events_no_delete
BEFORE DELETE ON lifecycle_events
BEGIN
  SELECT RAISE(ABORT, 'lifecycle events are append-only');
END;

CREATE TABLE IF NOT EXISTS artifact_security_assessments (
  artifact_version_id TEXT PRIMARY KEY
    REFERENCES artifact_versions(artifact_version_id) ON DELETE CASCADE,
  operation_id TEXT UNIQUE
    REFERENCES consistency_operations(operation_id),
  normalized_name TEXT NOT NULL
    CHECK(length(normalized_name) BETWEEN 1 AND 255),
  reported_media_type TEXT NOT NULL
    CHECK(length(reported_media_type) BETWEEN 1 AND 200),
  detected_media_type TEXT
    CHECK(detected_media_type IS NULL
      OR length(detected_media_type) BETWEEN 1 AND 200),
  source_size_bytes INTEGER NOT NULL CHECK(source_size_bytes >= 0),
  source_sha256 TEXT NOT NULL
    CHECK(length(source_sha256) = 64
      AND source_sha256 NOT GLOB '*[^0-9a-f]*'),
  state TEXT NOT NULL
    CHECK(state IN (
      'quarantined',
      'scanning',
      'clean',
      'attachment_only',
      'rejected',
      'timed_out',
      'scanner_error'
    )),
  reason_code TEXT NOT NULL
    CHECK(length(reason_code) BETWEEN 3 AND 80),
  scanner_engine TEXT
    CHECK(scanner_engine IS NULL
      OR length(scanner_engine) BETWEEN 1 AND 80),
  scanner_version TEXT
    CHECK(scanner_version IS NULL
      OR length(scanner_version) BETWEEN 1 AND 80),
  policy_version TEXT NOT NULL
    CHECK(length(policy_version) BETWEEN 1 AND 80),
  attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count >= 0),
  lease_until TEXT,
  row_version INTEGER NOT NULL DEFAULT 1 CHECK(row_version >= 1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  completed_at TEXT,
  CHECK(
    (state = 'scanning' AND lease_until IS NOT NULL)
    OR (state <> 'scanning' AND lease_until IS NULL)
  ),
  CHECK(
    (state IN ('quarantined', 'scanning') AND completed_at IS NULL)
    OR (
      state IN (
        'clean',
        'attachment_only',
        'rejected',
        'timed_out',
        'scanner_error'
      )
      AND completed_at IS NOT NULL
    )
  )
);

CREATE INDEX IF NOT EXISTS artifact_security_worker
  ON artifact_security_assessments(
    state, lease_until, updated_at, artifact_version_id
  );

CREATE TABLE IF NOT EXISTS artifact_security_events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL UNIQUE,
  artifact_ref TEXT NOT NULL
    CHECK(length(artifact_ref) = 20
      AND artifact_ref NOT GLOB '*[^0-9a-f]*'),
  from_state TEXT
    CHECK(from_state IS NULL OR from_state IN (
      'quarantined',
      'scanning',
      'clean',
      'attachment_only',
      'rejected',
      'timed_out',
      'scanner_error'
    )),
  to_state TEXT NOT NULL
    CHECK(to_state IN (
      'quarantined',
      'scanning',
      'clean',
      'attachment_only',
      'rejected',
      'timed_out',
      'scanner_error'
    )),
  reason_code TEXT NOT NULL CHECK(length(reason_code) BETWEEN 3 AND 80),
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS artifact_security_events_ref
  ON artifact_security_events(artifact_ref, seq);

CREATE TRIGGER IF NOT EXISTS artifact_security_events_no_update
BEFORE UPDATE ON artifact_security_events
BEGIN
  SELECT RAISE(ABORT, 'artifact security events are append-only');
END;

CREATE TRIGGER IF NOT EXISTS artifact_security_events_no_delete
BEFORE DELETE ON artifact_security_events
BEGIN
  SELECT RAISE(ABORT, 'artifact security events are append-only');
END;

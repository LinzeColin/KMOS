ALTER TABLE consistency_operations
  ADD COLUMN artifact_version_number INTEGER
    CHECK(artifact_version_number IS NULL OR artifact_version_number >= 1);

UPDATE consistency_operations
SET artifact_version_number = COALESCE(
  (
    SELECT av.version_number
    FROM artifact_versions av
    WHERE av.artifact_version_id =
      consistency_operations.artifact_version_id
  ),
  1
)
WHERE operation_kind = 'upload';

CREATE TABLE IF NOT EXISTS artifact_version_lineage (
  artifact_version_id TEXT PRIMARY KEY
    REFERENCES artifact_versions(artifact_version_id) ON DELETE CASCADE,
  parent_artifact_version_id TEXT
    REFERENCES artifact_versions(artifact_version_id),
  source_operation_id TEXT
    REFERENCES consistency_operations(operation_id),
  relation_kind TEXT NOT NULL
    CHECK(relation_kind IN ('root', 'revision')),
  created_at TEXT NOT NULL,
  CHECK(
    (relation_kind = 'root' AND parent_artifact_version_id IS NULL)
    OR
    (
      relation_kind = 'revision'
      AND parent_artifact_version_id IS NOT NULL
      AND parent_artifact_version_id != artifact_version_id
    )
  )
);

INSERT INTO artifact_version_lineage(
  artifact_version_id, parent_artifact_version_id, source_operation_id,
  relation_kind, created_at
)
SELECT
  av.artifact_version_id,
  (
    SELECT parent.artifact_version_id
    FROM artifact_versions parent
    WHERE parent.artifact_id = av.artifact_id
      AND parent.version_number < av.version_number
    ORDER BY parent.version_number DESC
    LIMIT 1
  ),
  (
    SELECT operation.operation_id
    FROM consistency_operations operation
    WHERE operation.operation_kind = 'upload'
      AND operation.artifact_version_id = av.artifact_version_id
    ORDER BY operation.created_at, operation.operation_id
    LIMIT 1
  ),
  CASE
    WHEN (
      SELECT parent.artifact_version_id
      FROM artifact_versions parent
      WHERE parent.artifact_id = av.artifact_id
        AND parent.version_number < av.version_number
      ORDER BY parent.version_number DESC
      LIMIT 1
    ) IS NULL THEN 'root'
    ELSE 'revision'
  END,
  av.created_at
FROM artifact_versions av
WHERE 1
ON CONFLICT(artifact_version_id) DO NOTHING;

CREATE INDEX IF NOT EXISTS artifact_version_lineage_parent
  ON artifact_version_lineage(parent_artifact_version_id, artifact_version_id);

CREATE TRIGGER IF NOT EXISTS artifact_version_lineage_no_update
BEFORE UPDATE ON artifact_version_lineage
BEGIN
  SELECT RAISE(ABORT, 'artifact version lineage is immutable');
END;

CREATE TABLE IF NOT EXISTS processor_registry (
  processor_name TEXT NOT NULL,
  processor_version TEXT NOT NULL,
  output_kind TEXT NOT NULL CHECK(output_kind IN ('text_extract')),
  output_media_type TEXT NOT NULL CHECK(output_media_type = 'text/plain'),
  implementation_sha256 TEXT NOT NULL
    CHECK(length(implementation_sha256) = 64
      AND implementation_sha256 NOT GLOB '*[^0-9a-f]*'),
  created_at TEXT NOT NULL,
  PRIMARY KEY(processor_name, processor_version)
);

CREATE TRIGGER IF NOT EXISTS processor_registry_no_update
BEFORE UPDATE ON processor_registry
BEGIN
  SELECT RAISE(ABORT, 'processor registry is immutable');
END;

CREATE TRIGGER IF NOT EXISTS processor_registry_no_delete
BEFORE DELETE ON processor_registry
BEGIN
  SELECT RAISE(ABORT, 'processor registry is immutable');
END;

CREATE TABLE IF NOT EXISTS artifact_processing_runs (
  processing_run_id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
  source_artifact_version_id TEXT NOT NULL
    REFERENCES artifact_versions(artifact_version_id) ON DELETE CASCADE,
  processor_name TEXT NOT NULL,
  processor_version TEXT NOT NULL,
  idempotency_key_hash TEXT NOT NULL
    CHECK(length(idempotency_key_hash) = 64
      AND idempotency_key_hash NOT GLOB '*[^0-9a-f]*'),
  derivative_id TEXT NOT NULL UNIQUE,
  generation_number INTEGER NOT NULL CHECK(generation_number >= 1),
  state TEXT NOT NULL
    CHECK(state IN (
      'pending', 'processing', 'prepared', 'converged', 'not_applicable'
    )),
  attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count >= 0),
  lease_until TEXT,
  last_error_code TEXT,
  output_storage_backend TEXT,
  output_storage_key TEXT,
  output_name TEXT,
  output_media_type TEXT,
  output_size_bytes INTEGER
    CHECK(output_size_bytes IS NULL OR output_size_bytes >= 0),
  output_sha256 TEXT
    CHECK(output_sha256 IS NULL OR (
      length(output_sha256) = 64
      AND output_sha256 NOT GLOB '*[^0-9a-f]*'
    )),
  row_version INTEGER NOT NULL DEFAULT 1 CHECK(row_version >= 1),
  requested_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  completed_at TEXT,
  FOREIGN KEY(processor_name, processor_version)
    REFERENCES processor_registry(processor_name, processor_version),
  UNIQUE(
    source_artifact_version_id,
    processor_name,
    processor_version,
    idempotency_key_hash
  ),
  UNIQUE(
    source_artifact_version_id,
    processor_name,
    processor_version,
    generation_number
  ),
  CHECK(
    state NOT IN ('prepared', 'converged')
    OR (
      output_storage_backend IS NOT NULL
      AND output_storage_key IS NOT NULL
      AND output_name IS NOT NULL
      AND output_media_type = 'text/plain'
      AND output_size_bytes IS NOT NULL
      AND output_sha256 IS NOT NULL
    )
  ),
  CHECK(state != 'converged' OR completed_at IS NOT NULL),
  CHECK(state != 'not_applicable' OR completed_at IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS artifact_processing_runs_worker
  ON artifact_processing_runs(
    state, lease_until, updated_at, processing_run_id
  );

CREATE INDEX IF NOT EXISTS artifact_processing_runs_source
  ON artifact_processing_runs(
    source_artifact_version_id, requested_at, processing_run_id
  );

CREATE TABLE IF NOT EXISTS artifact_derivatives (
  derivative_id TEXT PRIMARY KEY,
  processing_run_id TEXT NOT NULL UNIQUE
    REFERENCES artifact_processing_runs(processing_run_id)
    ON DELETE CASCADE,
  source_artifact_version_id TEXT NOT NULL
    REFERENCES artifact_versions(artifact_version_id) ON DELETE CASCADE,
  artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
  processor_name TEXT NOT NULL,
  processor_version TEXT NOT NULL,
  generation_number INTEGER NOT NULL CHECK(generation_number >= 1),
  output_kind TEXT NOT NULL CHECK(output_kind = 'text_extract'),
  storage_backend TEXT NOT NULL,
  storage_key TEXT NOT NULL,
  original_name TEXT NOT NULL,
  media_type TEXT NOT NULL CHECK(media_type = 'text/plain'),
  size_bytes INTEGER NOT NULL CHECK(size_bytes BETWEEN 0 AND 65536),
  sha256 TEXT NOT NULL
    CHECK(length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'),
  created_at TEXT NOT NULL,
  FOREIGN KEY(processor_name, processor_version)
    REFERENCES processor_registry(processor_name, processor_version),
  UNIQUE(
    source_artifact_version_id,
    processor_name,
    processor_version,
    generation_number
  ),
  UNIQUE(storage_backend, storage_key)
);

CREATE INDEX IF NOT EXISTS artifact_derivatives_source
  ON artifact_derivatives(
    source_artifact_version_id, created_at, derivative_id
  );

CREATE TRIGGER IF NOT EXISTS artifact_derivatives_no_update
BEFORE UPDATE ON artifact_derivatives
BEGIN
  SELECT RAISE(ABORT, 'artifact derivatives are immutable');
END;

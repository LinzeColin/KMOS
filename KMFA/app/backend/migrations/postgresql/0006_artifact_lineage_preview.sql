ALTER TABLE consistency_operations
  ADD COLUMN IF NOT EXISTS artifact_version_number INTEGER
    CHECK(artifact_version_number IS NULL OR artifact_version_number >= 1);

UPDATE consistency_operations operation
SET artifact_version_number = COALESCE(av.version_number, 1)
FROM artifact_versions av
WHERE operation.operation_kind = 'upload'
  AND operation.artifact_version_id = av.artifact_version_id
  AND operation.artifact_version_number IS NULL;

UPDATE consistency_operations
SET artifact_version_number = 1
WHERE operation_kind = 'upload' AND artifact_version_number IS NULL;

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
  parent.artifact_version_id,
  operation.operation_id,
  CASE
    WHEN parent.artifact_version_id IS NULL THEN 'root'
    ELSE 'revision'
  END,
  av.created_at
FROM artifact_versions av
LEFT JOIN LATERAL (
  SELECT candidate.artifact_version_id
  FROM artifact_versions candidate
  WHERE candidate.artifact_id = av.artifact_id
    AND candidate.version_number < av.version_number
  ORDER BY candidate.version_number DESC
  LIMIT 1
) parent ON TRUE
LEFT JOIN LATERAL (
  SELECT candidate.operation_id
  FROM consistency_operations candidate
  WHERE candidate.operation_kind = 'upload'
    AND candidate.artifact_version_id = av.artifact_version_id
  ORDER BY candidate.created_at, candidate.operation_id
  LIMIT 1
) operation ON TRUE
ON CONFLICT(artifact_version_id) DO NOTHING;

CREATE INDEX IF NOT EXISTS artifact_version_lineage_parent
  ON artifact_version_lineage(parent_artifact_version_id, artifact_version_id);

CREATE TABLE IF NOT EXISTS processor_registry (
  processor_name TEXT NOT NULL,
  processor_version TEXT NOT NULL,
  output_kind TEXT NOT NULL CHECK(output_kind IN ('text_extract')),
  output_media_type TEXT NOT NULL CHECK(output_media_type = 'text/plain'),
  implementation_sha256 TEXT NOT NULL
    CHECK(implementation_sha256 ~ '^[0-9a-f]{64}$'),
  created_at TEXT NOT NULL,
  PRIMARY KEY(processor_name, processor_version)
);

CREATE TABLE IF NOT EXISTS artifact_processing_runs (
  processing_run_id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
  source_artifact_version_id TEXT NOT NULL
    REFERENCES artifact_versions(artifact_version_id) ON DELETE CASCADE,
  processor_name TEXT NOT NULL,
  processor_version TEXT NOT NULL,
  idempotency_key_hash TEXT NOT NULL
    CHECK(idempotency_key_hash ~ '^[0-9a-f]{64}$'),
  derivative_id TEXT NOT NULL UNIQUE,
  generation_number INTEGER NOT NULL CHECK(generation_number >= 1),
  state TEXT NOT NULL
    CHECK(state IN (
      'pending', 'processing', 'prepared', 'converged', 'not_applicable'
    )),
  attempt_count BIGINT NOT NULL DEFAULT 0 CHECK(attempt_count >= 0),
  lease_until TEXT,
  last_error_code TEXT,
  output_storage_backend TEXT,
  output_storage_key TEXT,
  output_name TEXT,
  output_media_type TEXT,
  output_size_bytes BIGINT
    CHECK(output_size_bytes IS NULL OR output_size_bytes >= 0),
  output_sha256 TEXT
    CHECK(output_sha256 IS NULL OR output_sha256 ~ '^[0-9a-f]{64}$'),
  row_version BIGINT NOT NULL DEFAULT 1 CHECK(row_version >= 1),
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
  size_bytes BIGINT NOT NULL CHECK(size_bytes BETWEEN 0 AND 65536),
  sha256 TEXT NOT NULL CHECK(sha256 ~ '^[0-9a-f]{64}$'),
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

CREATE OR REPLACE FUNCTION kmfa_reject_lineage_registry_update()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'immutable lineage or processor registry';
END;
$$;

DROP TRIGGER IF EXISTS artifact_version_lineage_no_update
  ON artifact_version_lineage;
CREATE TRIGGER artifact_version_lineage_no_update
BEFORE UPDATE ON artifact_version_lineage
FOR EACH ROW EXECUTE FUNCTION kmfa_reject_lineage_registry_update();

DROP TRIGGER IF EXISTS processor_registry_no_update ON processor_registry;
CREATE TRIGGER processor_registry_no_update
BEFORE UPDATE ON processor_registry
FOR EACH ROW EXECUTE FUNCTION kmfa_reject_lineage_registry_update();

DROP TRIGGER IF EXISTS processor_registry_no_delete ON processor_registry;
CREATE TRIGGER processor_registry_no_delete
BEFORE DELETE ON processor_registry
FOR EACH ROW EXECUTE FUNCTION kmfa_reject_lineage_registry_update();

DROP TRIGGER IF EXISTS artifact_derivatives_no_update ON artifact_derivatives;
CREATE TRIGGER artifact_derivatives_no_update
BEFORE UPDATE ON artifact_derivatives
FOR EACH ROW EXECUTE FUNCTION kmfa_reject_lineage_registry_update();

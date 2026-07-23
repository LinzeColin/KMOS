ALTER TABLE access_tokens ADD COLUMN issuance_order BIGINT;

WITH ordered_tokens AS (
  SELECT
    token_hash,
    row_number() OVER (ORDER BY created_at, token_hash) AS issuance_order
  FROM access_tokens
)
UPDATE access_tokens
SET issuance_order = ordered_tokens.issuance_order
FROM ordered_tokens
WHERE access_tokens.token_hash = ordered_tokens.token_hash;

ALTER TABLE access_tokens ALTER COLUMN issuance_order SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS access_tokens_issuance_order
  ON access_tokens(issuance_order);

CREATE TABLE IF NOT EXISTS projects (
  project_id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL UNIQUE REFERENCES workspaces(workspace_id),
  name TEXT NOT NULL CHECK(char_length(btrim(name)) BETWEEN 1 AND 120),
  lifecycle_state TEXT NOT NULL DEFAULT 'active'
    CHECK(lifecycle_state IN ('active', 'archived')),
  row_version BIGINT NOT NULL DEFAULT 1 CHECK(row_version >= 1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS projects_lifecycle_updated
  ON projects(lifecycle_state, updated_at);

CREATE TABLE IF NOT EXISTS project_metrics (
  project_id TEXT PRIMARY KEY REFERENCES projects(project_id),
  progress INTEGER NOT NULL DEFAULT 0 CHECK(progress BETWEEN 0 AND 100),
  score INTEGER CHECK(score BETWEEN 0 AND 100),
  row_version BIGINT NOT NULL DEFAULT 1 CHECK(row_version >= 1),
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS financial_records (
  financial_record_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(project_id),
  record_type TEXT NOT NULL
    CHECK(record_type IN ('budget', 'actual', 'forecast', 'adjustment')),
  category TEXT NOT NULL CHECK(char_length(btrim(category)) BETWEEN 1 AND 120),
  amount_minor BIGINT NOT NULL CHECK(amount_minor >= 0),
  currency TEXT NOT NULL
    CHECK(currency ~ '^[A-Z]{3}$'),
  effective_date TEXT NOT NULL
    CHECK(effective_date ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'),
  source_ref TEXT,
  row_version BIGINT NOT NULL DEFAULT 1 CHECK(row_version >= 1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS financial_records_project_date
  ON financial_records(project_id, effective_date, financial_record_id);

CREATE TABLE IF NOT EXISTS artifact_versions (
  artifact_version_id TEXT PRIMARY KEY,
  artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
  project_id TEXT NOT NULL REFERENCES projects(project_id),
  version_number INTEGER NOT NULL CHECK(version_number >= 1),
  storage_backend TEXT NOT NULL CHECK(char_length(storage_backend) > 0),
  storage_key TEXT NOT NULL CHECK(char_length(storage_key) > 0),
  original_name TEXT NOT NULL CHECK(char_length(original_name) > 0),
  reported_media_type TEXT NOT NULL,
  size_bytes BIGINT NOT NULL CHECK(size_bytes >= 0),
  sha256 TEXT NOT NULL CHECK(sha256 ~ '^[0-9a-f]{64}$'),
  lifecycle_state TEXT NOT NULL DEFAULT 'active'
    CHECK(lifecycle_state IN ('active', 'quarantined', 'missing')),
  created_at TEXT NOT NULL,
  UNIQUE(artifact_id, version_number)
);

CREATE INDEX IF NOT EXISTS artifact_versions_project_created
  ON artifact_versions(project_id, created_at, artifact_version_id);

CREATE TABLE IF NOT EXISTS workspace_tasks (
  task_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(project_id),
  title TEXT NOT NULL CHECK(char_length(btrim(title)) BETWEEN 1 AND 240),
  status TEXT NOT NULL DEFAULT 'todo'
    CHECK(status IN ('todo', 'in_progress', 'done', 'cancelled')),
  sort_order INTEGER NOT NULL DEFAULT 0 CHECK(sort_order >= 0),
  due_at TEXT,
  row_version BIGINT NOT NULL DEFAULT 1 CHECK(row_version >= 1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS workspace_tasks_project_status
  ON workspace_tasks(project_id, status, sort_order, task_id);

INSERT INTO projects(
  project_id, workspace_id, name, lifecycle_state, row_version, created_at, updated_at
)
SELECT
  'project_' || workspace_id,
  workspace_id,
  project_name,
  'active',
  1,
  created_at,
  updated_at
FROM workspaces
ON CONFLICT(workspace_id) DO NOTHING;

INSERT INTO project_metrics(project_id, progress, score, row_version, updated_at)
SELECT
  'project_' || workspace_id,
  progress,
  NULL,
  1,
  updated_at
FROM workspaces
ON CONFLICT(project_id) DO NOTHING;

INSERT INTO artifact_versions(
  artifact_version_id,
  artifact_id,
  project_id,
  version_number,
  storage_backend,
  storage_key,
  original_name,
  reported_media_type,
  size_bytes,
  sha256,
  lifecycle_state,
  created_at
)
SELECT
  'artifact-version_' || artifact_id,
  artifact_id,
  'project_' || workspace_id,
  1,
  'legacy-private-filesystem',
  object_name,
  original_name,
  reported_media_type,
  size_bytes,
  sha256,
  'active',
  created_at
FROM artifacts
ON CONFLICT(artifact_id, version_number) DO NOTHING;

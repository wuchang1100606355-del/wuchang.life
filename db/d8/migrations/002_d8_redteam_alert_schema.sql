CREATE TABLE IF NOT EXISTS d8_redteam_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id TEXT,
  source TEXT,
  event_type TEXT,
  alert_level TEXT,
  title TEXT,
  summary TEXT,
  evidence_ref JSONB,
  reverse_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  affected_paths JSONB NOT NULL DEFAULT '[]'::jsonb,
  candidate_rule TEXT,
  approved_rule TEXT,
  promotion_status TEXT NOT NULL DEFAULT 'candidate',
  executable BOOLEAN NOT NULL DEFAULT FALSE,
  quarantine BOOLEAN NOT NULL DEFAULT TRUE,
  retrieval_scope TEXT NOT NULL DEFAULT 'redteam_only',
  pollution_guard BOOLEAN NOT NULL DEFAULT TRUE,
  reverse_index_only BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (executable = false),
  CHECK (quarantine = true),
  CHECK (retrieval_scope = 'redteam_only'),
  CHECK (pollution_guard = true),
  CHECK (reverse_index_only = true),
  CHECK (promotion_status IN ('candidate','approved','rejected','superseded')),
  CHECK (alert_level IN ('INFO','WARN','HOLD','BLOCK'))
);

CREATE TABLE IF NOT EXISTS d8_possible_alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id TEXT,
  source TEXT,
  event_type TEXT,
  alert_level TEXT,
  title TEXT,
  summary TEXT,
  evidence_ref JSONB,
  reverse_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  affected_paths JSONB NOT NULL DEFAULT '[]'::jsonb,
  candidate_rule TEXT,
  approved_rule TEXT,
  promotion_status TEXT NOT NULL DEFAULT 'candidate',
  executable BOOLEAN NOT NULL DEFAULT FALSE,
  quarantine BOOLEAN NOT NULL DEFAULT TRUE,
  retrieval_scope TEXT NOT NULL DEFAULT 'redteam_only',
  pollution_guard BOOLEAN NOT NULL DEFAULT TRUE,
  reverse_index_only BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (executable = false),
  CHECK (quarantine = true),
  CHECK (retrieval_scope = 'redteam_only'),
  CHECK (pollution_guard = true),
  CHECK (reverse_index_only = true),
  CHECK (promotion_status IN ('candidate','approved','rejected','superseded')),
  CHECK (alert_level IN ('INFO','WARN','HOLD','BLOCK'))
);

CREATE TABLE IF NOT EXISTS d8_boundary_revisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id TEXT,
  source TEXT,
  event_type TEXT,
  alert_level TEXT,
  title TEXT,
  summary TEXT,
  evidence_ref JSONB,
  reverse_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  affected_paths JSONB NOT NULL DEFAULT '[]'::jsonb,
  candidate_rule TEXT,
  approved_rule TEXT,
  promotion_status TEXT NOT NULL DEFAULT 'candidate',
  executable BOOLEAN NOT NULL DEFAULT FALSE,
  quarantine BOOLEAN NOT NULL DEFAULT TRUE,
  retrieval_scope TEXT NOT NULL DEFAULT 'redteam_only',
  pollution_guard BOOLEAN NOT NULL DEFAULT TRUE,
  reverse_index_only BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (executable = false),
  CHECK (quarantine = true),
  CHECK (retrieval_scope = 'redteam_only'),
  CHECK (pollution_guard = true),
  CHECK (reverse_index_only = true),
  CHECK (promotion_status IN ('candidate','approved','rejected','superseded')),
  CHECK (alert_level IN ('INFO','WARN','HOLD','BLOCK'))
);

CREATE TABLE IF NOT EXISTS d8_guard_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id TEXT,
  source TEXT,
  event_type TEXT,
  alert_level TEXT,
  title TEXT,
  summary TEXT,
  evidence_ref JSONB,
  reverse_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  affected_paths JSONB NOT NULL DEFAULT '[]'::jsonb,
  candidate_rule TEXT,
  approved_rule TEXT,
  promotion_status TEXT NOT NULL DEFAULT 'candidate',
  executable BOOLEAN NOT NULL DEFAULT FALSE,
  quarantine BOOLEAN NOT NULL DEFAULT TRUE,
  retrieval_scope TEXT NOT NULL DEFAULT 'redteam_only',
  pollution_guard BOOLEAN NOT NULL DEFAULT TRUE,
  reverse_index_only BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (executable = false),
  CHECK (quarantine = true),
  CHECK (retrieval_scope = 'redteam_only'),
  CHECK (pollution_guard = true),
  CHECK (reverse_index_only = true),
  CHECK (promotion_status IN ('candidate','approved','rejected','superseded')),
  CHECK (alert_level IN ('INFO','WARN','HOLD','BLOCK'))
);

CREATE INDEX IF NOT EXISTS idx_d8_redteam_events_run_id
ON d8_redteam_events (run_id);

CREATE INDEX IF NOT EXISTS idx_d8_redteam_events_alert_level
ON d8_redteam_events (alert_level);

CREATE INDEX IF NOT EXISTS idx_d8_redteam_events_promotion_status
ON d8_redteam_events (promotion_status);

CREATE INDEX IF NOT EXISTS idx_d8_redteam_events_reverse_refs
ON d8_redteam_events USING GIN (reverse_refs);

CREATE INDEX IF NOT EXISTS idx_d8_possible_alerts_alert_level
ON d8_possible_alerts (alert_level);

CREATE INDEX IF NOT EXISTS idx_d8_possible_alerts_reverse_refs
ON d8_possible_alerts USING GIN (reverse_refs);

CREATE INDEX IF NOT EXISTS idx_d8_boundary_revisions_promotion_status
ON d8_boundary_revisions (promotion_status);

CREATE INDEX IF NOT EXISTS idx_d8_guard_rules_promotion_status
ON d8_guard_rules (promotion_status);

CREATE OR REPLACE VIEW d8_redteam_quarantine_view AS
SELECT
  'd8_redteam_events' AS source_table,
  id,
  run_id,
  source,
  event_type,
  alert_level,
  title,
  summary,
  evidence_ref,
  reverse_refs,
  affected_paths,
  candidate_rule,
  approved_rule,
  promotion_status,
  executable,
  quarantine,
  retrieval_scope,
  pollution_guard,
  reverse_index_only,
  created_at,
  updated_at
FROM d8_redteam_events
WHERE executable = false
  AND quarantine = true
  AND retrieval_scope = 'redteam_only'
  AND pollution_guard = true
  AND reverse_index_only = true
UNION ALL
SELECT
  'd8_possible_alerts' AS source_table,
  id,
  run_id,
  source,
  event_type,
  alert_level,
  title,
  summary,
  evidence_ref,
  reverse_refs,
  affected_paths,
  candidate_rule,
  approved_rule,
  promotion_status,
  executable,
  quarantine,
  retrieval_scope,
  pollution_guard,
  reverse_index_only,
  created_at,
  updated_at
FROM d8_possible_alerts
WHERE executable = false
  AND quarantine = true
  AND retrieval_scope = 'redteam_only'
  AND pollution_guard = true
  AND reverse_index_only = true;

CREATE OR REPLACE FUNCTION d8_register_redteam_event(payload JSONB)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
  new_id UUID;
BEGIN
  INSERT INTO d8_redteam_events (
    run_id,
    source,
    event_type,
    alert_level,
    title,
    summary,
    evidence_ref,
    reverse_refs,
    affected_paths,
    candidate_rule,
    approved_rule,
    promotion_status,
    executable,
    quarantine,
    retrieval_scope,
    pollution_guard,
    reverse_index_only
  )
  VALUES (
    payload->>'run_id',
    payload->>'source',
    payload->>'event_type',
    COALESCE(payload->>'alert_level', 'INFO'),
    payload->>'title',
    payload->>'summary',
    COALESCE(payload->'evidence_ref', '{}'::jsonb),
    COALESCE(payload->'reverse_refs', '[]'::jsonb),
    COALESCE(payload->'affected_paths', '[]'::jsonb),
    payload->>'candidate_rule',
    payload->>'approved_rule',
    COALESCE(payload->>'promotion_status', 'candidate'),
    false,
    true,
    'redteam_only',
    true,
    true
  )
  RETURNING id INTO new_id;

  RETURN new_id;
END;
$$;

CREATE OR REPLACE FUNCTION d8_register_possible_alert(payload JSONB)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
  new_id UUID;
BEGIN
  INSERT INTO d8_possible_alerts (
    run_id,
    source,
    event_type,
    alert_level,
    title,
    summary,
    evidence_ref,
    reverse_refs,
    affected_paths,
    candidate_rule,
    approved_rule,
    promotion_status,
    executable,
    quarantine,
    retrieval_scope,
    pollution_guard,
    reverse_index_only
  )
  VALUES (
    payload->>'run_id',
    payload->>'source',
    payload->>'event_type',
    COALESCE(payload->>'alert_level', 'INFO'),
    payload->>'title',
    payload->>'summary',
    COALESCE(payload->'evidence_ref', '{}'::jsonb),
    COALESCE(payload->'reverse_refs', '[]'::jsonb),
    COALESCE(payload->'affected_paths', '[]'::jsonb),
    payload->>'candidate_rule',
    payload->>'approved_rule',
    COALESCE(payload->>'promotion_status', 'candidate'),
    false,
    true,
    'redteam_only',
    true,
    true
  )
  RETURNING id INTO new_id;

  RETURN new_id;
END;
$$;

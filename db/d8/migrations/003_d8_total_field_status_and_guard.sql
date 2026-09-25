CREATE TABLE IF NOT EXISTS d8_total_field_status_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id TEXT NOT NULL,
  phase TEXT NOT NULL,
  memory_count INTEGER,
  redteam_events_count INTEGER,
  possible_alerts_count INTEGER,
  hold_count INTEGER,
  warn_count INTEGER,
  info_count INTEGER,
  m1_m36_pointer TEXT,
  active_pointer TEXT,
  phase1_report TEXT,
  phase2_report TEXT,
  phase2_1_report TEXT,
  safety_flags JSONB NOT NULL DEFAULT '{}'::jsonb,
  artifacts JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS d8_guard_evaluations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id TEXT NOT NULL,
  task_name TEXT,
  task_scope JSONB NOT NULL DEFAULT '{}'::jsonb,
  matched_alerts JSONB NOT NULL DEFAULT '[]'::jsonb,
  decision TEXT NOT NULL,
  reason TEXT,
  executable BOOLEAN NOT NULL DEFAULT FALSE,
  pollution_guard BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (decision IN ('PASS','INFO','WARN','HOLD','BLOCK')),
  CHECK (executable = false),
  CHECK (pollution_guard = true)
);

CREATE INDEX IF NOT EXISTS idx_d8_total_field_status_snapshots_run_id
ON d8_total_field_status_snapshots (run_id);

CREATE INDEX IF NOT EXISTS idx_d8_total_field_status_snapshots_created_at
ON d8_total_field_status_snapshots (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_d8_guard_evaluations_run_id
ON d8_guard_evaluations (run_id);

CREATE INDEX IF NOT EXISTS idx_d8_guard_evaluations_decision
ON d8_guard_evaluations (decision);

CREATE INDEX IF NOT EXISTS idx_d8_guard_evaluations_matched_alerts
ON d8_guard_evaluations USING GIN (matched_alerts);

CREATE OR REPLACE VIEW d8_total_field_current_status AS
SELECT *
FROM d8_total_field_status_snapshots
ORDER BY created_at DESC
LIMIT 1;

CREATE OR REPLACE VIEW d8_active_possible_alerts AS
SELECT *
FROM d8_possible_alerts
WHERE executable = false
  AND quarantine = true
  AND retrieval_scope = 'redteam_only'
  AND pollution_guard = true
  AND reverse_index_only = true
  AND promotion_status = 'candidate';

CREATE OR REPLACE VIEW d8_guard_recent_evaluations AS
SELECT *
FROM d8_guard_evaluations
ORDER BY created_at DESC
LIMIT 50;

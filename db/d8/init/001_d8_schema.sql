CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS d8_memory (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  d8_id TEXT UNIQUE NOT NULL,
  d8_schema_version TEXT NOT NULL DEFAULT 'd8.2026-06-23.v1',

  domain TEXT NOT NULL,
  object_type TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'filesystem',
  source_path TEXT,
  source_uri TEXT,

  time_version TIMESTAMPTZ NOT NULL DEFAULT now(),
  actor_scope TEXT NOT NULL,
  intent TEXT NOT NULL DEFAULT 'classify_retrieve',
  risk TEXT NOT NULL DEFAULT 'internal',
  semantic_key JSONB NOT NULL DEFAULT '{}'::jsonb,

  title TEXT,
  body TEXT NOT NULL,
  body_sha256 TEXT NOT NULL,
  byte_size BIGINT NOT NULL DEFAULT 0,
  line_count INTEGER NOT NULL DEFAULT 0,

  search_vec TSVECTOR GENERATED ALWAYS AS (
    to_tsvector(
      'simple',
      coalesce(title, '') || ' ' ||
      coalesce(source_path, '') || ' ' ||
      coalesce(body, '')
    )
  ) STORED,

  embedding VECTOR(1536),

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS d8_ingest_log (
  id BIGSERIAL PRIMARY KEY,
  run_id TEXT NOT NULL,
  root_path TEXT NOT NULL,
  scanned_count INTEGER NOT NULL DEFAULT 0,
  accepted_count INTEGER NOT NULL DEFAULT 0,
  rejected_count INTEGER NOT NULL DEFAULT 0,
  inserted_count INTEGER NOT NULL DEFAULT 0,
  flags JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION d8_touch_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_d8_memory_updated_at ON d8_memory;

CREATE TRIGGER trg_d8_memory_updated_at
BEFORE UPDATE ON d8_memory
FOR EACH ROW
EXECUTE FUNCTION d8_touch_updated_at();

CREATE INDEX IF NOT EXISTS idx_d8_route
ON d8_memory (domain, object_type, actor_scope, risk, time_version DESC);

CREATE INDEX IF NOT EXISTS idx_d8_source_path
ON d8_memory (source_path);

CREATE INDEX IF NOT EXISTS idx_d8_body_sha256
ON d8_memory (body_sha256);

CREATE INDEX IF NOT EXISTS idx_d8_semantic_json
ON d8_memory USING GIN (semantic_key jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_d8_search
ON d8_memory USING GIN (search_vec);

CREATE INDEX IF NOT EXISTS idx_d8_embedding_hnsw
ON d8_memory USING hnsw (embedding vector_cosine_ops)
WHERE embedding IS NOT NULL;

CREATE OR REPLACE VIEW d8_safe_memory AS
SELECT *
FROM d8_memory
WHERE risk NOT IN ('secret', 'prod_blocked');

CREATE OR REPLACE FUNCTION d8_keyword_search(
  q TEXT,
  actor TEXT DEFAULT 'user:long',
  domain_filter TEXT DEFAULT NULL,
  limit_n INTEGER DEFAULT 20
)
RETURNS TABLE (
  id UUID,
  title TEXT,
  source_path TEXT,
  domain TEXT,
  object_type TEXT,
  risk TEXT,
  score REAL,
  snippet TEXT
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    m.id,
    m.title,
    m.source_path,
    m.domain,
    m.object_type,
    m.risk,
    ts_rank(m.search_vec, plainto_tsquery('simple', q)) AS score,
    left(regexp_replace(m.body, '[[:space:]]+', ' ', 'g'), 280) AS snippet
  FROM d8_memory m
  WHERE m.actor_scope = actor
    AND m.risk NOT IN ('secret', 'prod_blocked')
    AND (domain_filter IS NULL OR m.domain = domain_filter)
    AND m.search_vec @@ plainto_tsquery('simple', q)
  ORDER BY score DESC, m.time_version DESC
  LIMIT limit_n;
$$;

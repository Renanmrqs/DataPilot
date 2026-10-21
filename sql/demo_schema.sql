-- Demo quotas are separate from Neon's managed authentication tables.
CREATE SCHEMA IF NOT EXISTS datapilot_demo;

CREATE TABLE IF NOT EXISTS datapilot_demo.accounts (
    user_id TEXT PRIMARY KEY,
    used_questions INTEGER NOT NULL DEFAULT 0 CHECK (used_questions >= 0),
    question_limit INTEGER CHECK (question_limit >= 0),
    last_question_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS datapilot_demo.daily_usage (
    usage_date DATE PRIMARY KEY,
    used_questions INTEGER NOT NULL DEFAULT 0 CHECK (used_questions >= 0)
);

-- The API uses a server-only database connection; do not expose these tables
-- through an unauthenticated Data API. No client-facing RLS policies are granted.
ALTER TABLE datapilot_demo.accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE datapilot_demo.daily_usage ENABLE ROW LEVEL SECURITY;

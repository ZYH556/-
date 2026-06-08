"""初始化 PostgreSQL 表结构。"""
import asyncio

import asyncpg

from reflexlearn.common.config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR PRIMARY KEY,
    role VARCHAR NOT NULL DEFAULT 'student',
    tenant_id VARCHAR NOT NULL DEFAULT 'default',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS learner_profiles (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR REFERENCES users(id),
    dimensions JSONB NOT NULL DEFAULT '{}',
    version INT DEFAULT 1,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS profile_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR REFERENCES users(id),
    dimensions JSONB NOT NULL DEFAULT '{}',
    version INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS learning_goals (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR REFERENCES users(id),
    course VARCHAR,
    goal_text TEXT NOT NULL,
    status VARCHAR DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    goal_id INT REFERENCES learning_goals(id),
    type VARCHAR NOT NULL,
    status VARCHAR DEFAULT 'pending',
    plan JSONB,
    iteration_count INT DEFAULT 0,
    token_used INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id SERIAL PRIMARY KEY,
    task_id INT REFERENCES tasks(id),
    agent_name VARCHAR NOT NULL,
    io_summary JSONB,
    latency_ms INT,
    status VARCHAR,
    trace_id VARCHAR,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tool_calls (
    id SERIAL PRIMARY KEY,
    run_id INT REFERENCES agent_runs(id),
    tool VARCHAR NOT NULL,
    params JSONB,
    result JSONB,
    duration_ms INT,
    error_type VARCHAR,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS resources (
    id SERIAL PRIMARY KEY,
    task_id INT REFERENCES tasks(id),
    type VARCHAR NOT NULL,
    content TEXT,
    meta JSONB,
    quality_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS learning_paths (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS path_items (
    id SERIAL PRIMARY KEY,
    path_id INT REFERENCES learning_paths(id),
    resource_id INT REFERENCES resources(id),
    sequence INT,
    mastery_status VARCHAR DEFAULT 'not_started'
);

CREATE TABLE IF NOT EXISTS reflections (
    id SERIAL PRIMARY KEY,
    run_id INT REFERENCES agent_runs(id),
    failure_type VARCHAR,
    cause TEXT,
    fix_strategy TEXT,
    embedded_id VARCHAR,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS acl_rules (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR REFERENCES users(id),
    tenant_id VARCHAR,
    course_id VARCHAR,
    visibility VARCHAR DEFAULT 'private'
);

CREATE TABLE IF NOT EXISTS documents (
    doc_id VARCHAR PRIMARY KEY,
    title VARCHAR,
    format VARCHAR,
    user_id VARCHAR,
    tenant_id VARCHAR,
    course_id VARCHAR,
    visibility VARCHAR DEFAULT 'course',
    section_count INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS eval_runs (
    id SERIAL PRIMARY KEY,
    strategy VARCHAR,
    total_cases INT,
    completion_rate FLOAT,
    avg_correctness FLOAT,
    avg_profile_match FLOAT,
    avg_overall FLOAT,
    metrics_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS llm_billing (
    id SERIAL PRIMARY KEY,
    provider VARCHAR,
    model VARCHAR,
    task_type VARCHAR,
    input_tokens INT,
    output_tokens INT,
    cost_usd FLOAT,
    latency_ms INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""


async def main():
    dsn = get_settings().database_url
    conn = await asyncpg.connect(dsn=dsn)
    try:
        await conn.execute(SCHEMA)
        print("[OK] PostgreSQL tables created successfully.")
        tables = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
        )
        for t in tables:
            print(f"  - {t['tablename']}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

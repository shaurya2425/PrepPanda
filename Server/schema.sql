-- PrepPanda core schema
-- Run this once against the appdb database to set up all required tables.

CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS vector;

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector SCHEMA vector;

-- Users
CREATE TABLE IF NOT EXISTS core.users (
    id          UUID PRIMARY KEY,
    email       TEXT UNIQUE NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL
);

-- Chapters
CREATE TABLE IF NOT EXISTS core.chapters (
    id          UUID PRIMARY KEY,
    title       TEXT NOT NULL,
    subject     TEXT NOT NULL,
    pdf_url     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL
);

-- Nodes
CREATE TABLE IF NOT EXISTS core.nodes (
    id          UUID PRIMARY KEY,
    chapter_id  UUID NOT NULL REFERENCES core.chapters(id) ON DELETE CASCADE,
    content     TEXT NOT NULL,
    tags        TEXT[] NOT NULL DEFAULT '{}',
    importance  FLOAT NOT NULL DEFAULT 0.0,
    image_url   TEXT,
    created_at  TIMESTAMPTZ NOT NULL
);

-- User progress
CREATE TABLE IF NOT EXISTS core.user_progress (
    user_id     UUID NOT NULL REFERENCES core.users(id) ON DELETE CASCADE,
    node_id     UUID NOT NULL REFERENCES core.nodes(id) ON DELETE CASCADE,
    accuracy    FLOAT NOT NULL DEFAULT 0.0,
    attempts    INT NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, node_id)
);

-- Chat history
CREATE TABLE IF NOT EXISTS core.chat_history (
    id          UUID PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES core.users(id) ON DELETE CASCADE,
    chapter_id  UUID NOT NULL REFERENCES core.chapters(id) ON DELETE CASCADE,
    messages    JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL
);

-- Vector embeddings (pgvector)
CREATE TABLE IF NOT EXISTS vector.embeddings (
    node_id     UUID PRIMARY KEY REFERENCES core.nodes(id) ON DELETE CASCADE,
    embedding   vector.vector(3072),   -- gemini-embedding-2-preview outputs 3072 dims
    created_at  TIMESTAMPTZ NOT NULL
);

-- ================================
-- SCHEMAS
-- ================================
CREATE SCHEMA IF NOT EXISTS core;

-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- ================================
-- BOOKS
-- ================================
CREATE TABLE core.books (
    book_id        UUID PRIMARY KEY,
    title          TEXT NOT NULL,
    grade          INT NOT NULL,         -- e.g. 6–12
    subject        TEXT NOT NULL,        -- physics, biology, etc.
    created_at     TIMESTAMPTZ NOT NULL
);

-- ================================
-- CHAPTERS
-- ================================
CREATE TABLE core.chapters (
    chapter_id     UUID PRIMARY KEY,
    book_id        UUID NOT NULL REFERENCES core.books(book_id) ON DELETE CASCADE,
    chapter_number INT NOT NULL,
    title          TEXT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_chapters_book ON core.chapters(book_id);

-- ================================
-- CHUNKS (CORE RETRIEVAL UNIT)
-- ================================
CREATE TABLE core.chunks (
    chunk_id        UUID PRIMARY KEY,
    chapter_id      UUID NOT NULL REFERENCES core.chapters(chapter_id) ON DELETE CASCADE,

    content         TEXT NOT NULL,
    token_count     INT NOT NULL,
    position_index  INT NOT NULL,    -- ordering within chapter

    section_title   TEXT,            -- optional, improves retrieval

    -- Hybrid retrieval support
    tsv             tsvector,        -- for BM25 / keyword search
    embedding       vector(768),     -- adjust based on model

    created_at      TIMESTAMPTZ NOT NULL
);

-- Filtering + ordering
CREATE INDEX idx_chunks_chapter ON core.chunks(chapter_id);
CREATE INDEX idx_chunks_position ON core.chunks(chapter_id, position_index);

-- Full-text search
CREATE INDEX idx_chunks_tsv ON core.chunks USING GIN(tsv);

-- Vector index (HNSW preferred)
CREATE INDEX idx_chunks_embedding
ON core.chunks USING hnsw (embedding vector_l2_ops);

-- ================================
-- IMAGES (NOT EMBEDDED)
-- ================================
CREATE TABLE core.images (
    image_id        UUID PRIMARY KEY,
    chapter_id      UUID NOT NULL REFERENCES core.chapters(chapter_id) ON DELETE CASCADE,

    image_path      TEXT NOT NULL,   -- local path / S3 URL
    caption         TEXT,            -- optional but useful

    position_index  INT NOT NULL,    -- position in chapter

    created_at      TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_images_chapter ON core.images(chapter_id);
CREATE INDEX idx_images_position ON core.images(chapter_id, position_index);

-- ================================
-- LINKING (TEXT ↔ IMAGE)
-- ================================
CREATE TABLE core.chunk_image_links (
    chunk_id UUID NOT NULL REFERENCES core.chunks(chunk_id) ON DELETE CASCADE,
    image_id UUID NOT NULL REFERENCES core.images(image_id) ON DELETE CASCADE,
    PRIMARY KEY (chunk_id, image_id)
);
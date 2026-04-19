-- =========================================
-- ⚠️ DEV ONLY: FULL DATABASE RESET
-- This will DROP all RAG-related data
-- =========================================

-- Drop schemas (cascades all tables, indexes, constraints)
DROP SCHEMA IF EXISTS core CASCADE;

-- Drop extension (optional but keeps things clean)
DROP EXTENSION IF EXISTS vector;

-- =========================================
-- Recreate everything
-- =========================================

-- Schemas
CREATE SCHEMA core;

-- Extensions
CREATE EXTENSION vector;

-- =========================================
-- BOOKS
-- =========================================
CREATE TABLE core.books (
    book_id        UUID PRIMARY KEY,
    title          TEXT NOT NULL,
    grade          INT NOT NULL,
    subject        TEXT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL
);

-- =========================================
-- CHAPTERS
-- =========================================
CREATE TABLE core.chapters (
    chapter_id     UUID PRIMARY KEY,
    book_id        UUID NOT NULL REFERENCES core.books(book_id) ON DELETE CASCADE,
    chapter_number INT NOT NULL,
    title          TEXT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_chapters_book ON core.chapters(book_id);

-- =========================================
-- CHUNKS
-- =========================================
CREATE TABLE core.chunks (
    chunk_id        UUID PRIMARY KEY,
    chapter_id      UUID NOT NULL REFERENCES core.chapters(chapter_id) ON DELETE CASCADE,

    content         TEXT NOT NULL,
    token_count     INT NOT NULL,
    position_index  INT NOT NULL,

    section_title   TEXT,

    tsv             tsvector,
    embedding       vector(768),

    created_at      TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_chunks_chapter ON core.chunks(chapter_id);
CREATE INDEX idx_chunks_position ON core.chunks(chapter_id, position_index);
CREATE INDEX idx_chunks_tsv ON core.chunks USING GIN(tsv);

CREATE INDEX idx_chunks_embedding
ON core.chunks USING hnsw (embedding vector_l2_ops);

-- =========================================
-- IMAGES
-- =========================================
CREATE TABLE core.images (
    image_id        UUID PRIMARY KEY,
    chapter_id      UUID NOT NULL REFERENCES core.chapters(chapter_id) ON DELETE CASCADE,

    image_path      TEXT NOT NULL,
    caption         TEXT,

    position_index  INT NOT NULL,

    created_at      TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_images_chapter ON core.images(chapter_id);
CREATE INDEX idx_images_position ON core.images(chapter_id, position_index);

-- =========================================
-- LINKING
-- =========================================
CREATE TABLE core.chunk_image_links (
    chunk_id UUID NOT NULL REFERENCES core.chunks(chunk_id) ON DELETE CASCADE,
    image_id UUID NOT NULL REFERENCES core.images(image_id) ON DELETE CASCADE,
    PRIMARY KEY (chunk_id, image_id)
);
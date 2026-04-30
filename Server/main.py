"""PrepPanda API server.

Startup / shutdown
------------------
- Postgres connection pool, BucketHandler and ChunkEmbedder are created
  once at startup and stored on ``app.state`` for injection via Depends().

Environment variables
---------------------
DATABASE_URL or POSTGRES_* — Postgres connection
S3_*                       — MinIO / S3 credentials
GEMINI_API_KEY             — Google Generative AI key
ADMIN_API_KEY              — Secret key required on all /admin/* routes

Run
---
::

    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from Core.Parser.embedder import ChunkEmbedder
from Core.Storage.BucketHandler import BucketHandler
from Core.Storage.PostgresHandler import PostgresHandler
from Routers import admin as admin_router
from Routers import analysis as analysis_router
from Routers import catalog as catalog_router
from Routers import mindmap as mindmap_router
from Routers import srs as srs_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Lifespan — startup / shutdown
# ─────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("⚡ PrepPanda server starting up …")

    # Postgres
    pg = PostgresHandler()
    await pg.connect()
    app.state.pg = pg
    logger.info("✅ Postgres pool ready")

    # Bucket (MinIO / S3)
    bucket = BucketHandler()
    app.state.bucket = bucket
    logger.info("✅ BucketHandler ready")

    # Embedding model — loaded once, kept in RAM
    embedder = ChunkEmbedder()
    app.state.embedder = embedder
    logger.info("✅ ChunkEmbedder ready (dim=%d)", embedder.dim)

    yield  # ← server is live

    logger.info("🛑 Shutting down …")
    await pg.disconnect()
    logger.info("✅ Postgres pool closed")


# ─────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="PrepPanda API",
    description=(
        "NCERT textbook ingestion, smart retrieval, and mind-map generation.\n\n"
        "**Admin routes** require the `X-Admin-Key` header."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
# Multipart upload limit — 200 MB per part (default is 1 MB).
# Handled via the `MaxUploadBody` dependency in Routers/deps.py.

# ─────────────────────────────────────────────────────────────────────
# Routers
# ─────────────────────────────────────────────────────────────────────

app.include_router(admin_router.router)
app.include_router(analysis_router.router)
app.include_router(catalog_router.router)
app.include_router(srs_router.router)
app.include_router(mindmap_router.router)


# ─────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"], summary="Server health check")
async def health():
    return {"status": "ok", "version": app.version}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""SRS router — Smart Retrieval System (Q&A generation).

Endpoint
--------
POST /srs/ask
    Given a question and a chapter_id, run the full pipeline:
    retrieve → build context → Gemini → return Markdown answer.
"""

from __future__ import annotations

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from Core.SRS.generator import Generator, GeneratorResult
from Core.SRS.retriever import Retriever
from Routers.deps import EmbedDep, PgDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/srs", tags=["srs"])


# ─────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────

class AskIn(BaseModel):
    question:   str        = Field(..., min_length=3, example="What is double fertilisation?")
    chapter_id: uuid.UUID  = Field(..., example="b27a7b7e-128f-4b35-8743-e058da894ad7")


class ImageOut(BaseModel):
    image_id:       uuid.UUID
    image_path:     str
    caption:        Optional[str] = None
    position_index: int


class AskOut(BaseModel):
    question:          str
    question_normalised: str
    markdown:          str           # Final answer with real image URLs
    chunks_used:       int
    images_used:       int
    images_replaced:   int
    images:            List[ImageOut] = []


# ─────────────────────────────────────────────────────────────────────
# Route
# ─────────────────────────────────────────────────────────────────────

@router.post(
    "/ask",
    response_model=AskOut,
    summary="Answer a question from stored chapter content",
)
async def ask(
    body: AskIn,
    pg: PgDep,
    embedder: EmbedDep,
) -> AskOut:
    """
    Run the full SRS pipeline for a student question:

    1. Normalise the query
    2. Hybrid semantic + keyword search over ``core.chunks``
    3. Neighbour expansion
    4. Build a structured LLM prompt
    5. Call Gemini and return a Markdown answer

    Images linked to the retrieved chunks are embedded as Markdown
    ``![Figure N](url)`` tags in the answer.
    """
    # Validate chapter exists
    pool = pg._pool_guard()
    chapter_row = await pool.fetchrow(
        "SELECT chapter_id FROM core.chapters WHERE chapter_id = $1",
        body.chapter_id,
    )
    if not chapter_row:
        raise HTTPException(status_code=404, detail=f"Chapter {body.chapter_id} not found.")

    try:
        retriever = Retriever(pg=pg, embedder=embedder)
        generator = Generator()

        result: GeneratorResult = await generator.answer(
            query=body.question,
            chapter_id=body.chapter_id,
            retriever=retriever,
        )
    except Exception as exc:
        logger.exception("SRS pipeline failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"SRS pipeline error: {exc}")

    # Fetch the images that were used so the client can render them independently
    retrieval = await retriever.retrieve(query=body.question, chapter_id=body.chapter_id)
    images = [
        ImageOut(
            image_id=img["image_id"],
            image_path=img["image_path"],
            caption=img.get("caption"),
            position_index=img["position_index"],
        )
        for img in retrieval.images
    ]

    return AskOut(
        question=body.question,
        question_normalised=result.query_normalised,
        markdown=result.markdown,
        chunks_used=result.chunks_used,
        images_used=result.images_used,
        images_replaced=result.images_replaced,
        images=images,
    )

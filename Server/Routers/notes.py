"""Notes router — SSE streaming endpoint for AI study notes.

Endpoints
---------
POST /api/generate/notes
    Streams structured JSON note blocks via Server-Sent Events (SSE).
    Each SSE event contains one batch of blocks (5 chunks worth).
    Final event is type "done".

    When a cached result exists the endpoint returns a plain JSON response
    instead of SSE, for instant delivery.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from Routers.deps import PgDep
from Core.cache import cache_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/generate", tags=["notes"])

# Lazy singleton
_generator = None


def _get_generator():
    global _generator
    if _generator is None:
        from Core.Features.NotesGenerator import NotesGenerator
        _generator = NotesGenerator()
    return _generator


# ─────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────

class GenerateNotesRequest(BaseModel):
    chapterId: str
    prompt: Optional[str] = ""


# ─────────────────────────────────────────────────────────────────────
# Route
# ─────────────────────────────────────────────────────────────────────

@router.post(
    "/notes",
    summary="Stream AI study notes for a chapter (SSE)",
)
async def generate_notes(
    req: GenerateNotesRequest,
    pg: PgDep,
):
    """
    Streams structured note blocks via Server-Sent Events.

    Each SSE `data` event contains a JSON array of blocks for one batch.
    A final `event: done` signals completion.

    When a cached result exists, returns a JSON response with
    ``{ "cached": true, "blocks": [...] }`` for instant delivery.

    Example stream::

        data: [{"type":"concept","title":"...","content":["..."],"importance":"high"}]

        data: [{"type":"definition","term":"...","definition":"..."}]

        event: done
        data: {"total_blocks": 42}
    """
    # Parse chapter_id
    try:
        chapter_id = uuid.UUID(req.chapterId)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid chapterId: '{req.chapterId}'",
        )

    # Verify chapter exists
    ch = await pg.get_chapter(chapter_id)
    if not ch:
        raise HTTPException(
            status_code=404,
            detail=f"Chapter {chapter_id} not found.",
        )

    # ── Cache check ──────────────────────────────────────────────────
    cache_key = cache_store.make_key("notes", str(chapter_id))
    cached = cache_store.get("notes", cache_key)
    if cached is not None:
        logger.info("Cache HIT  notes %s", chapter_id)
        return JSONResponse(content={"cached": True, "blocks": cached})

    # ── Cache miss — stream and accumulate ───────────────────────────
    gen = _get_generator()

    async def _event_stream():
        total_blocks = 0
        all_blocks = []
        try:
            async for batch_blocks in gen.generate_stream(
                pg, chapter_id, api_base_url="http://localhost:8000",
            ):
                total_blocks += len(batch_blocks)
                all_blocks.extend(batch_blocks)
                yield f"data: {json.dumps(batch_blocks)}\n\n"

        except Exception as e:
            logger.error("Notes streaming failed: %s", e)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        # Cache the complete result after streaming finishes
        if all_blocks:
            await cache_store.put("notes", cache_key, all_blocks)

        yield f"event: done\ndata: {json.dumps({'total_blocks': total_blocks})}\n\n"

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

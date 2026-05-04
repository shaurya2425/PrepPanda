"""Notes generator — produce comprehensive Markdown study notes for a chapter.

Pipeline
--------
1. **Fetch** all chunks, images, and PYQ data for the chapter.
2. **Score** chunks by PYQ relevance so exam-relevant sections get deeper coverage.
3. **Batch** chunks into groups of ~6-8 for efficient Groq API calls
   (keeps each prompt under ~4 k tokens context).
4. **Summarise** each batch via Groq (llama-3.1-8b-instant), instructing
   the model to emphasise PYQ-heavy content.
5. **Attach diagrams** — each image is inserted into the notes exactly once,
   placed at the batch where its linked chunk first appears.
6. **Assemble** — stitch batch summaries + images into final Markdown.

Usage
-----
::

    from Core.Features.NotesGenerator import NotesGenerator

    gen = NotesGenerator()
    markdown = await gen.generate(pg, bucket, chapter_id)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────

GROQ_MODEL = "llama-3.1-8b-instant"
# How many chunks to pack into one Groq call
BATCH_SIZE = 5
# Max characters of chunk content per batch (keeps prompt under ~4k tokens)
BATCH_CHAR_LIMIT = 6_000
# Sequential delay between API calls (seconds) to respect Groq free-tier TPM
INTER_BATCH_DELAY = 2.0
# Max retries per batch on rate-limit / transient errors
MAX_RETRIES = 3


# ─────────────────────────────────────────────────────────────────────
# Data containers
# ─────────────────────────────────────────────────────────────────────

@dataclass
class ChunkInfo:
    """Enriched chunk ready for batching."""
    chunk_id: uuid.UUID
    position_index: int
    section_title: str
    content: str
    pyq_score: float           # aggregated PYQ relevance
    pyq_questions: List[str]   # sample PYQ questions linked to this chunk
    image_ids: List[uuid.UUID] # linked image IDs


@dataclass
class ImageInfo:
    """An image that can appear in the notes."""
    image_id: uuid.UUID
    image_path: str           # S3 URL
    caption: str
    position_index: int
    linked_chunk_ids: List[uuid.UUID]


@dataclass
class ChunkBatch:
    """A group of chunks to be summarised in one Groq call."""
    batch_index: int
    chunks: List[ChunkInfo]
    section_label: str        # heading derived from chunk section_titles
    has_pyq_content: bool     # whether any chunk in this batch has PYQ links
    image_ids: List[uuid.UUID]  # images to attach after this batch


# ─────────────────────────────────────────────────────────────────────
# Generator
# ─────────────────────────────────────────────────────────────────────

class NotesGenerator:
    """Produce comprehensive Markdown study notes for a chapter."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        key = api_key or os.environ.get("GROQ_API_KEY")
        if not key:
            raise ValueError("GROQ_API_KEY is required for notes generation.")
        self._api_key = key

    # ── Public API ──────────────────────────────────────────────────

    async def generate(
        self,
        pg,                        # PostgresHandler
        chapter_id: uuid.UUID,
        *,
        api_base_url: str = "",    # for building image proxy URLs
    ) -> List[Dict]:
        """Non-streaming wrapper — collects all blocks and returns them."""
        all_blocks: List[Dict] = []
        async for batch_blocks in self.generate_stream(
            pg, chapter_id, api_base_url=api_base_url,
        ):
            all_blocks.extend(batch_blocks)
        return all_blocks

    async def generate_stream(
        self,
        pg,
        chapter_id: uuid.UUID,
        *,
        api_base_url: str = "",
    ):
        """Async generator that yields List[Dict] of blocks per batch.

        Each yield is one batch worth of blocks (LLM output + images).
        The caller can flush them to the client immediately.
        """
        # ── 1. Fetch raw data ───────────────────────────────────────
        chapter_row, chunks, images, pyq_links = await self._fetch_data(
            pg, chapter_id,
        )
        chapter_title = chapter_row["title"]

        if not chunks:
            yield [{"type": "concept", "title": chapter_title, "content": ["No content has been ingested for this chapter yet."], "importance": "high"}]
            return

        # ── 2. Enrich chunks with PYQ + image data ──────────────────
        enriched = self._enrich_chunks(chunks, images, pyq_links)

        # ── 3. Create batches ───────────────────────────────────────
        batches = self._create_batches(enriched, images)

        # Build image lookup for attaching images to batches
        image_lookup: Dict[uuid.UUID, Dict] = {}
        for row in images:
            image_lookup[row["image_id"]] = row

        # ── 4. Process one batch at a time, yield blocks ────────────
        for i, batch in enumerate(batches):
            llm_blocks = await self._call_groq_with_retry(
                batch, chapter_title,
            )

            # Attach image blocks for this batch
            img_blocks = self._get_image_blocks(
                batch, image_lookup, api_base_url,
            )

            combined = llm_blocks + img_blocks
            logger.info(
                "Batch %d/%d done — %d blocks (streamed)",
                i + 1, len(batches), len(combined),
            )
            yield combined

            # Delay between calls to respect Groq free-tier rate limits
            if i < len(batches) - 1:
                await asyncio.sleep(INTER_BATCH_DELAY)

    @staticmethod
    def _get_image_blocks(
        batch: "ChunkBatch",
        image_lookup: Dict[uuid.UUID, Dict],
        api_base_url: str,
    ) -> List[Dict]:
        """Build image block dicts for a single batch."""
        blocks: List[Dict] = []
        for iid in batch.image_ids:
            img = image_lookup.get(iid)
            if not img:
                continue
            img_url = img.get("image_path", "")
            caption = img.get("caption") or "Diagram"
            url = img_url
            if api_base_url and img_url:
                url = f"{api_base_url}/catalog/media?url={img_url}"
            blocks.append({"type": "image", "url": url, "caption": caption})
        return blocks

    # ── Data fetching ───────────────────────────────────────────────

    async def _fetch_data(
        self, pg, chapter_id: uuid.UUID,
    ) -> Tuple[Dict, List[Dict], List[Dict], List[Dict]]:
        """Fetch chapter, chunks, images, and PYQ links in parallel."""
        pool = pg._pool_guard()

        # Run queries concurrently
        chapter_task = pool.fetchrow(
            "SELECT * FROM core.chapters WHERE chapter_id = $1",
            chapter_id,
        )
        chunks_task = pool.fetch(
            """SELECT chunk_id, chapter_id, content, token_count,
                      position_index, section_title, pyq_score
               FROM core.chunks
               WHERE chapter_id = $1
               ORDER BY position_index""",
            chapter_id,
        )
        images_task = pool.fetch(
            """SELECT i.image_id, i.image_path, i.caption, i.position_index,
                      cil.chunk_id
               FROM core.images i
               LEFT JOIN core.chunk_image_links cil ON cil.image_id = i.image_id
               WHERE i.chapter_id = $1
               ORDER BY i.position_index""",
            chapter_id,
        )
        pyq_task = pool.fetch(
            """SELECT pcm.chunk_id, pcm.relevance,
                      p.question, p.year, p.exam, p.marks
               FROM core.pyq_chunk_map pcm
               JOIN core.pyqs p ON p.pyq_id = pcm.pyq_id
               JOIN core.chunks c ON c.chunk_id = pcm.chunk_id
               WHERE c.chapter_id = $1
               ORDER BY pcm.relevance DESC""",
            chapter_id,
        )

        chapter_row, chunk_rows, image_rows, pyq_rows = await asyncio.gather(
            chapter_task, chunks_task, images_task, pyq_task,
        )

        return (
            dict(chapter_row) if chapter_row else {},
            [dict(r) for r in chunk_rows],
            [dict(r) for r in image_rows],
            [dict(r) for r in pyq_rows],
        )

    # ── Enrichment ──────────────────────────────────────────────────

    def _enrich_chunks(
        self,
        chunks: List[Dict],
        images: List[Dict],
        pyq_links: List[Dict],
    ) -> List[ChunkInfo]:
        """Combine chunks with their PYQ and image metadata."""

        # Build PYQ lookup: chunk_id → (total relevance, [questions])
        pyq_map: Dict[uuid.UUID, Tuple[float, List[str]]] = defaultdict(
            lambda: (0.0, [])
        )
        for row in pyq_links:
            cid = row["chunk_id"]
            score, qs = pyq_map[cid]
            score += float(row.get("relevance", 1.0))
            q = row.get("question", "")
            if q and q not in qs:
                qs.append(q)
            pyq_map[cid] = (score, qs)

        # Build image lookup: chunk_id → [image_id]
        img_map: Dict[uuid.UUID, List[uuid.UUID]] = defaultdict(list)
        for row in images:
            cid = row.get("chunk_id")
            if cid:
                img_map[cid].append(row["image_id"])

        enriched: List[ChunkInfo] = []
        for c in chunks:
            cid = c["chunk_id"]
            pyq_score, pyq_qs = pyq_map.get(cid, (0.0, []))
            enriched.append(ChunkInfo(
                chunk_id=cid,
                position_index=c["position_index"],
                section_title=c.get("section_title") or "",
                content=c["content"],
                pyq_score=pyq_score + float(c.get("pyq_score", 0) or 0),
                pyq_questions=pyq_qs[:3],  # cap at 3 per chunk
                image_ids=img_map.get(cid, []),
            ))

        return enriched

    # ── Batching ────────────────────────────────────────────────────

    def _create_batches(
        self,
        chunks: List[ChunkInfo],
        images: List[Dict],
    ) -> List[ChunkBatch]:
        """Group chunks into batches. Each image is assigned to exactly one batch."""

        # Track globally which images have been claimed
        claimed_images: Set[uuid.UUID] = set()

        # Build a quick lookup: image_id → ImageInfo
        image_lookup: Dict[uuid.UUID, Dict] = {}
        for row in images:
            iid = row["image_id"]
            if iid not in image_lookup:
                image_lookup[iid] = row

        batches: List[ChunkBatch] = []
        current_chunks: List[ChunkInfo] = []
        current_chars = 0

        def _flush(batch_idx: int) -> ChunkBatch:
            nonlocal current_chunks, current_chars

            # Determine section label from chunk section_titles
            titles = []
            for c in current_chunks:
                if c.section_title and c.section_title not in titles:
                    titles.append(c.section_title)
            label = " / ".join(titles) if titles else f"Section {batch_idx + 1}"

            has_pyq = any(c.pyq_score > 0 for c in current_chunks)

            # Claim images for this batch (first-come basis)
            batch_images: List[uuid.UUID] = []
            for c in current_chunks:
                for iid in c.image_ids:
                    if iid not in claimed_images:
                        claimed_images.add(iid)
                        batch_images.append(iid)

            batch = ChunkBatch(
                batch_index=batch_idx,
                chunks=list(current_chunks),
                section_label=label,
                has_pyq_content=has_pyq,
                image_ids=batch_images,
            )
            current_chunks = []
            current_chars = 0
            return batch

        batch_idx = 0
        for chunk in chunks:
            clen = len(chunk.content)

            # Flush if adding this chunk would exceed limits
            if current_chunks and (
                len(current_chunks) >= BATCH_SIZE
                or current_chars + clen > BATCH_CHAR_LIMIT
            ):
                batches.append(_flush(batch_idx))
                batch_idx += 1

            current_chunks.append(chunk)
            current_chars += clen

        # Flush remaining
        if current_chunks:
            batches.append(_flush(batch_idx))

        # Assign any unclaimed images (orphans with no chunk link)
        # to the batch closest to their position_index
        unclaimed = [
            img for iid, img in image_lookup.items()
            if iid not in claimed_images
        ]
        for img in unclaimed:
            img_pos = img.get("position_index", 0)
            best_batch = None
            best_dist = float("inf")
            for b in batches:
                for c in b.chunks:
                    d = abs(c.position_index - img_pos)
                    if d < best_dist:
                        best_dist = d
                        best_batch = b
            if best_batch is not None:
                claimed_images.add(img["image_id"])
                best_batch.image_ids.append(img["image_id"])

        return batches

    # ── Groq summarisation ──────────────────────────────────────────

    async def _summarise_batches(
        self,
        batches: List[ChunkBatch],
        chapter_title: str,
    ) -> List[List[Dict]]:
        """Call Groq sequentially for each batch with retry logic."""
        results: List[List[Dict]] = []
        for i, batch in enumerate(batches):
            blocks = await self._call_groq_with_retry(batch, chapter_title)
            results.append(blocks)
            logger.info(
                "Batch %d/%d done — %d blocks",
                i + 1, len(batches), len(blocks),
            )
            if i < len(batches) - 1:
                await asyncio.sleep(INTER_BATCH_DELAY)
        return results

    async def _call_groq_with_retry(
        self,
        batch: ChunkBatch,
        chapter_title: str,
    ) -> List[Dict]:
        """Call Groq API with exponential-backoff retry."""
        from groq import Groq

        prompt = self._build_batch_prompt(batch, chapter_title)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                client = Groq(api_key=self._api_key)
                resp = await asyncio.to_thread(
                    lambda: client.chat.completions.create(
                        model=GROQ_MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        response_format={"type": "json_object"},
                        temperature=0.3,
                        max_tokens=2048,
                    )
                )
                raw = resp.choices[0].message.content or "{}"
                return self._parse_blocks(raw, batch.batch_index)

            except Exception as e:
                err_str = str(e)
                # Rate-limited — back off and retry
                if "429" in err_str or "rate_limit" in err_str:
                    wait = 2 ** attempt + INTER_BATCH_DELAY
                    logger.warning(
                        "Rate-limited on batch %d (attempt %d/%d), "
                        "waiting %.1fs…",
                        batch.batch_index, attempt, MAX_RETRIES, wait,
                    )
                    await asyncio.sleep(wait)
                    continue

                logger.error(
                    "Groq call failed for batch %d (attempt %d): %s",
                    batch.batch_index, attempt, e,
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return self._fallback_summary(batch)

        return self._fallback_summary(batch)

    @staticmethod
    def _parse_blocks(raw: str, batch_index: int) -> List[Dict]:
        """Parse JSON blocks from an LLM response string."""
        text = raw.strip()
        # Strip markdown fencing if present
        if text.startswith("```"):
            lines = text.split("\n", 1)
            text = lines[1] if len(lines) > 1 else ""
        if text.endswith("```"):
            text = text[:-3].strip()
        if text.startswith("json"):
            text = text[4:].strip()

        try:
            data = json.loads(text)
            return data.get("blocks", [])
        except json.JSONDecodeError as e:
            logger.error(
                "JSON parse failed for batch %d: %s — raw[:200]: %s",
                batch_index, e, text[:200],
            )
            return []

    def _build_batch_prompt(
        self, batch: ChunkBatch, chapter_title: str,
    ) -> str:
        """Build the Groq prompt for summarising one batch."""

        content_blocks: List[str] = []
        pyq_callouts: List[str] = []

        for i, c in enumerate(batch.chunks, 1):
            content_blocks.append(
                f"--- Chunk {i} ({c.section_title or 'untitled'}) ---\n"
                f"{c.content[:1800]}"
            )
            if c.pyq_questions:
                pyq_callouts.append(
                    f"Chunk {i} is exam-relevant. Sample PYQs:\n"
                    + "\n".join(f"  • {q}" for q in c.pyq_questions[:2])
                )

        context = "\n\n".join(content_blocks)
        pyq_section = ""
        if pyq_callouts:
            pyq_section = (
                "\n\n**EXAM RELEVANCE (PYQ DATA)**:\n"
                + "\n".join(pyq_callouts)
            )

        return f"""You are an expert academic note generator optimized for biology and theory-heavy subjects.

Your task is to convert raw textbook chunks into structured, high-retention study notes for the chapter "{chapter_title}", section "{batch.section_label}".

STRICT RULES:
* Do NOT output long paragraphs.
* Break everything into structured blocks.
* Optimize for exam recall, not literary quality.
* Every output must be scannable within 5 seconds.
{pyq_section}

OUTPUT FORMAT:
Return ONLY a valid JSON object matching exactly this structure:
{{
  "blocks": [
    ... your blocks here ...
  ]
}}

Each block must be one of the following types:
1. "concept"
   {{ "type": "concept", "title": "...", "content": ["point 1", "point 2"], "importance": "low | medium | high" }}
2. "definition"
   {{ "type": "definition", "term": "...", "definition": "one-line precise definition" }}
3. "process" (VERY IMPORTANT FOR BIO)
   {{ "type": "process", "title": "...", "steps": [ {{"step": 1, "title": "...", "explanation": "..."}} ] }}
4. "diagram" (MANDATORY WHERE APPLICABLE)
   {{ "type": "diagram", "title": "...", "visual_hint": "describe what diagram should show", "labels": ["label1"], "explanation": "how to read" }}
5. "comparison"
   {{ "type": "comparison", "title": "...", "items": [ {{"feature": "...", "A": "...", "B": "..."}} ] }}
6. "exam_focus" (PYQ + HIGH-YIELD)
   {{ "type": "exam_focus", "points": ["frequently asked fact", "common trap"] }}
7. "memory_hook"
   {{ "type": "memory_hook", "hook": "mnemonic / analogy / shortcut" }}

INSTRUCTIONS:
* Extract ONLY high-value information.
* Convert passive text → active recall format.
* Always include:
  - at least 1 process block (if topic involves steps)
  - at least 1 diagram block (if visualizable)
  - at least 1 exam_focus block
* Prefer bullet points over sentences.
* Avoid redundancy. Keep each block atomic.

MATERIAL:
{context}

Return ONLY valid JSON (no markdown fencing):"""

    def _fallback_summary(self, batch: ChunkBatch) -> List[Dict]:
        """Simple extractive fallback if Groq fails."""
        blocks = []
        for c in batch.chunks:
            blocks.append({
                "type": "concept",
                "title": c.section_title or "Untitled",
                "content": [c.content[:200].strip() + "…"],
                "importance": "medium"
            })
        return blocks

    # ── Final assembly ──────────────────────────────────────────────

    def _assemble_blocks(
        self,
        chapter_title: str,
        chapter_number: int,
        batches: List[ChunkBatch],
        summaries: List[List[Dict]],
        images: List[Dict],
        api_base_url: str,
    ) -> List[Dict]:
        """Stitch batch summaries + images into final list of blocks."""

        # Build image lookup
        image_lookup: Dict[uuid.UUID, Dict] = {}
        for row in images:
            image_lookup[row["image_id"]] = row

        all_blocks = []

        for batch, batch_blocks in zip(batches, summaries):
            all_blocks.extend(batch_blocks)

            # Insert images for this batch
            if batch.image_ids:
                for iid in batch.image_ids:
                    img = image_lookup.get(iid)
                    if not img:
                        continue
                    img_url = img.get("image_path", "")
                    caption = img.get("caption") or "Diagram"
                    # Use the media proxy endpoint
                    if api_base_url and img_url:
                        proxy_url = (
                            f"{api_base_url}/catalog/media"
                            f"?url={img_url}"
                        )
                        all_blocks.append({
                            "type": "image",
                            "url": proxy_url,
                            "caption": caption
                        })
                    else:
                        all_blocks.append({
                            "type": "image",
                            "url": img_url,
                            "caption": caption
                        })

        return all_blocks

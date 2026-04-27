"""Generator — LLM answer generation and image post-processing.

Steps handled:
6. Call Gemini to generate a Markdown answer from the built context
7. Replace {{IMG:X.X}} placeholder tags with actual image URLs

Usage
-----
::

    from Core.SRS.generator import Generator

    gen    = Generator()
    answer = await gen.answer(
        query="What is double fertilisation?",
        chapter_id=chapter_id,
        retriever=retriever,
    )
    # answer.markdown  → final Markdown with real image URLs
    # answer.raw_llm   → raw LLM output (before image replacement)
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from google import genai

from Core.SRS.retriever import Retriever, RetrievalResult
from Core.SRS.context_builder import build_context, get_image_map

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────

DEFAULT_MODEL = "gemini-3-flash-preview"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = 4096


# ─────────────────────────────────────────────────────────────────────
# Result
# ─────────────────────────────────────────────────────────────────────

@dataclass
class GeneratorResult:
    """Final answer from the SRS pipeline."""
    query: str
    query_normalised: str
    markdown: str               # Final MD with real image URLs
    raw_llm: str                # Raw LLM output before image replacement
    chunks_used: int = 0
    images_used: int = 0
    images_replaced: int = 0


# ─────────────────────────────────────────────────────────────────────
# Generator
# ─────────────────────────────────────────────────────────────────────

class Generator:
    """Orchestrates retrieval → context → LLM → post-processing.

    Parameters
    ----------
    model : str
        Gemini model identifier.
    temperature : float
        Sampling temperature.
    max_tokens : int
        Max output tokens.
    api_key : str or None
        Google AI API key. Falls back to ``GEMINI_API_KEY`` env var.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        api_key: Optional[str] = None,
    ) -> None:
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

        key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise ValueError(
                "No API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY env var."
            )
        self._client = genai.Client(api_key=key)
        logger.info("Generator initialised with model '%s'", model)

    # ─────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────

    async def answer(
        self,
        query: str,
        chapter_id: uuid.UUID,
        retriever: Retriever,
    ) -> GeneratorResult:
        """Full pipeline: retrieve → build context → LLM → post-process.

        Parameters
        ----------
        query : str
            The student's question.
        chapter_id : uuid.UUID
            Which chapter to search in.
        retriever : Retriever
            Configured retriever instance.

        Returns
        -------
        GeneratorResult
            Final Markdown answer with images embedded.
        """
        # ── Step 1-4: Retrieve ──────────────────────────────────────
        retrieval = await retriever.retrieve(query=query, chapter_id=chapter_id)

        # ── Step 5: Build context ───────────────────────────────────
        prompt = build_context(query=query, retrieval=retrieval)

        # ── Step 6: LLM call ────────────────────────────────────────
        raw_answer = await self._call_llm(
            system=prompt["system"],
            user=prompt["user"],
        )

        # ── Step 7: Replace placeholders with real image URLs ───────
        image_map = get_image_map(retrieval.images)
        final_md, replaced_count = self._replace_images(raw_answer, image_map)

        logger.info(
            "Answer generated: %d chars, %d images replaced",
            len(final_md), replaced_count,
        )

        return GeneratorResult(
            query=query,
            query_normalised=retrieval.query_normalised,
            markdown=final_md,
            raw_llm=raw_answer,
            chunks_used=len(retrieval.chunks),
            images_used=len(retrieval.images),
            images_replaced=replaced_count,
        )

    # ─────────────────────────────────────────────────────────────────
    # Private
    # ─────────────────────────────────────────────────────────────────

    async def _call_llm(self, system: str, user: str) -> str:
        """Call Gemini and return the text response."""
        logger.info("Calling %s …", self._model)
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=[
                    {"role": "user", "parts": [{"text": f"{system}\n\n{user}"}]},
                ],
                config=genai.types.GenerateContentConfig(
                    temperature=self._temperature,
                    max_output_tokens=self._max_tokens,
                ),
            )
            text = response.text or ""
            logger.info("LLM response: %d chars", len(text))
            return text
        except Exception as e:
            logger.error("Gemini API call failed: %s", e)
            return f"*Error generating answer: {e}*"

    @staticmethod
    def _replace_images(
        markdown: str,
        image_map: Dict[str, str],
    ) -> tuple[str, int]:
        """Replace ``{{IMG:X.X}}`` tags with Markdown image syntax.

        Returns ``(final_markdown, replacement_count)``.
        """
        count = 0

        def _replacer(match: re.Match) -> str:
            nonlocal count
            tag = match.group(0)        # e.g. {{IMG:1.1}}
            fig_id = match.group(1)     # e.g. 1.1
            url = image_map.get(tag, "")
            if url:
                count += 1
                return f"![Figure {fig_id}]({url})"
            # Tag not in map — leave as-is
            return tag

        pattern = r"\{\{IMG:(\d+(?:\.\d+)*)\}\}"
        result = re.sub(pattern, _replacer, markdown)
        return result, count

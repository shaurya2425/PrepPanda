"""LLM-based chunk classification.

Asks the LLM to label a text chunk as one of the valid node types.
Falls back to ``concept`` on any failure or unrecognised response.
"""

from __future__ import annotations

import logging
from typing import Any

from Core.Embedder.constants import (
    CLASSIFICATION_PROMPT,
    DEFAULT_NODE_TYPE,
    VALID_NODE_TYPES,
)

logger = logging.getLogger(__name__)


async def classify_chunk(llm_client: Any, text: str) -> str:
    """Return a node-type label for *text* using the LLM.

    Parameters
    ----------
    llm_client
        Any object exposing ``async generate(prompt: str) -> str``.
    text
        The raw chunk content (truncated to 1 500 chars internally).

    Returns
    -------
    One of ``definition | concept | process | example``.
    """
    prompt = CLASSIFICATION_PROMPT.format(text=text[:1500])
    try:
        raw: str = await llm_client.generate(prompt)
        label = raw.strip().lower()
        # "diagram" is assigned explicitly, not by LLM
        if label in VALID_NODE_TYPES - {"diagram"}:
            return label
    except Exception:
        logger.warning("LLM classification failed; defaulting to '%s'", DEFAULT_NODE_TYPE)

    return DEFAULT_NODE_TYPE

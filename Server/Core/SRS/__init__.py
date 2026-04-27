"""SRS — Smart Retrieval System.

Three-stage pipeline:
1. ``retriever``       — normalise, embed, search, expand
2. ``context_builder`` — assemble LLM prompt with chunks + image tags
3. ``generator``       — call Gemini, replace image placeholders
"""

from Core.SRS.retriever import Retriever, RetrievalResult
from Core.SRS.context_builder import build_context, get_image_map
from Core.SRS.generator import Generator, GeneratorResult

__all__ = [
    "Retriever",
    "RetrievalResult",
    "Generator",
    "GeneratorResult",
    "build_context",
    "get_image_map",
]

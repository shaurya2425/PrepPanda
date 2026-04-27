"""Context builder — assembles the LLM prompt from retrieved chunks + images.

Takes the ``RetrievalResult`` from the Retriever and builds a
structured prompt that tells the LLM:

- Here are the relevant text chunks (ordered by position)
- Here are the associated figure captions (with placeholder tags)
- Generate an answer in Markdown

The placeholder tags (e.g. ``{{IMG:1.1}}``) are later replaced by
the Generator with actual image URLs.

Usage
-----
::

    from Core.SRS.context_builder import build_context

    prompt = build_context(
        query="What is double fertilisation?",
        retrieval=retrieval_result,
    )
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from Core.SRS.retriever import RetrievalResult

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert NCERT biology tutor.

RULES:
1. Answer the student's question using ONLY the context chunks provided below.
2. Write your answer in well-structured Markdown.
3. Use headings (##, ###), bullet points, and bold for key terms.
4. When a figure is relevant, include its placeholder tag exactly as shown
   (e.g. {{IMG:1.1}}) on its own line. The system will replace it with the
   actual image. Only use tags listed in the FIGURES section.
5. If the context does not contain enough information, say so honestly.
6. Do NOT invent information outside the given context.
"""


# ─────────────────────────────────────────────────────────────────────
# Builder
# ─────────────────────────────────────────────────────────────────────

def build_context(
    query: str,
    retrieval: RetrievalResult,
) -> Dict[str, str]:
    """Build the system + user prompt for the LLM.

    Parameters
    ----------
    query : str
        Original user question.
    retrieval : RetrievalResult
        Output from ``Retriever.retrieve()``.

    Returns
    -------
    dict
        ``{"system": str, "user": str}`` ready for the LLM call.
    """
    # ── Text context ────────────────────────────────────────────────
    context_parts: List[str] = []
    for i, chunk in enumerate(retrieval.chunks):
        section = chunk.get("section_title") or ""
        header = f"[Chunk {i + 1}]"
        if section:
            header += f" Section: {section}"
        context_parts.append(f"{header}\n{chunk['content']}")

    context_text = "\n\n---\n\n".join(context_parts)

    # ── Image captions + tags ───────────────────────────────────────
    # Deduplicate images by image_id
    seen_images: Dict[str, Dict[str, Any]] = {}
    for img in retrieval.images:
        iid = str(img["image_id"])
        if iid not in seen_images:
            seen_images[iid] = img

    figure_lines: List[str] = []
    for img in seen_images.values():
        caption = img.get("caption") or "No caption"
        # Extract figure ID from caption if possible
        fig_tag = _extract_fig_id(caption, img)
        figure_lines.append(f"- {fig_tag}: {caption}")

    figures_text = "\n".join(figure_lines) if figure_lines else "(no figures available)"

    # ── User prompt ─────────────────────────────────────────────────
    user_prompt = (
        f"## CONTEXT CHUNKS\n\n{context_text}\n\n"
        f"## FIGURES (use {{{{IMG:X.X}}}} tags to include them)\n\n{figures_text}\n\n"
        f"## STUDENT QUESTION\n\n{query}\n\n"
        f"## YOUR ANSWER (Markdown)\n"
    )

    logger.info(
        "Context built: %d chunks, %d figures, prompt ~%d chars",
        len(retrieval.chunks),
        len(seen_images),
        len(user_prompt),
    )

    return {"system": SYSTEM_PROMPT.strip(), "user": user_prompt}


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _extract_fig_id(caption: str, img: Dict[str, Any]) -> str:
    """Try to extract a figure ID tag like {{IMG:1.1}}."""
    import re
    # Try caption first: "Figure 1.1 ..." or similar
    m = re.search(r"(\d+(?:\.\d+)+)", caption)
    if m:
        return "{{IMG:" + m.group(1) + "}}"
    # Fallback: use position_index
    pos = img.get("position_index", 0)
    return "{{IMG:" + str(pos) + "}}"


def get_image_map(images: List[Dict[str, Any]]) -> Dict[str, str]:
    """Build a mapping from placeholder tag → image URL.

    Used by the Generator to replace ``{{IMG:1.1}}`` with real URLs.
    """
    import re
    mapping: Dict[str, str] = {}

    for img in images:
        caption = img.get("caption") or ""
        image_path = img.get("image_path", "")
        m = re.search(r"(\d+(?:\.\d+)+)", caption)
        if m:
            tag = "{{IMG:" + m.group(1) + "}}"
            mapping[tag] = image_path
        else:
            pos = img.get("position_index", 0)
            tag = "{{IMG:" + str(pos) + "}}"
            mapping[tag] = image_path

    return mapping

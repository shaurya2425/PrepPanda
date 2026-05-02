"""Quiz generator router.
Generates an MCQ quiz using 60% PYQ-linked chunks and 40% random chunks.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
import re
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google import genai

from Routers.deps import PgDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quiz", tags=["quiz"])

class GenerateQuizRequest(BaseModel):
    chapter_id: uuid.UUID

class QuizQuestionOut(BaseModel):
    id: int
    question: str
    options: List[str]
    correct: int
    explanation: str

@router.post("/generate", response_model=List[QuizQuestionOut], summary="Generate adaptive quiz")
async def generate_quiz(req: GenerateQuizRequest, pg: PgDep):
    """
    Generate an MCQ quiz using 60% PYQ-linked chunks and 40% random chunks.
    Uses gemini-3-flash-preview for a single-call generation.
    """
    try:
        # Fetch up to 3 PYQ-linked chunks (60% of 5)
        pyq_chunks = await pg.get_pyq_linked_chunks(req.chapter_id, limit=3)
        pyq_chunk_ids = [c["chunk_id"] for c in pyq_chunks]
        
        # Fetch up to 2 random chunks (40% of 5)
        random_chunks = await pg.get_random_chunks(req.chapter_id, limit=2, exclude_ids=pyq_chunk_ids)

        if not pyq_chunks and not random_chunks:
            raise HTTPException(status_code=404, detail="No content available for this chapter to generate a quiz.")

        # Build context
        context_blocks = []
        context_blocks.append("--- PYQ-LINKED TOPICS ---")
        for i, c in enumerate(pyq_chunks, 1):
            pyq_text = c.get("pyq_question") or ""
            context_blocks.append(f"[Topic {i} - Originally tested by: {pyq_text}]\n{c['content'][:500]}")

        context_blocks.append("\n--- RANDOM TOPICS ---")
        for i, c in enumerate(random_chunks, len(pyq_chunks) + 1):
            context_blocks.append(f"[Topic {i}]\n{c['content'][:500]}")

        context_text = "\n\n".join(context_blocks)

        prompt = f"""You are an expert exam question creator.
I will give you data about topics from a textbook chapter. Some are highly relevant because they appeared in previous year questions (PYQs), and some are random topics.

Based on this text, generate exactly 5 multiple choice questions (MCQs).
Ensure the mix is roughly 60% (3 questions) from the PYQ-linked topics and 40% (2 questions) from the random topics.

IMPORTANT RULES:
1. Each question must have exactly 4 options.
2. Only one option can be correct.
3. Provide a brief explanation for the correct answer.
4. Output MUST be valid JSON matching exactly this format:
[
  {{
    "Question": "Full question text?",
    "Option": ["Option A", "Option B", "Option C", "Option D"],
    "correct_option_idx": 0,
    "Explanation": "Brief reason why 0 is correct."
  }}
]

Here is the context:

{context_text}

Respond ONLY with valid JSON (no markdown fencing)."""

        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY not set")

        client = genai.Client(api_key=key)
        
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            config=genai.types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=4096,
                response_mime_type="application/json",
            ),
        )

        raw = response.text or ""
        
        # Parse JSON
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n", 1)
            text = lines[1] if len(lines) > 1 else ""
        if text.endswith("```"):
            text = text[:-3].strip()

        # Handle "json" code block identifier if present
        if text.startswith("json"):
            text = text[4:].strip()

        data = json.loads(text)
        
        # Transform to QuizQuestionOut
        output = []
        for idx, item in enumerate(data, 1):
            options = item.get("Option", [])
            correct_idx = item.get("correct_option_idx", 0)
            
            output.append(QuizQuestionOut(
                id=idx,
                question=item.get("Question", ""),
                options=options,
                correct=correct_idx,
                explanation=item.get("Explanation", "No explanation provided.")
            ))

        return output

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse quiz JSON: {e}\nRaw: {raw[:500]}")
        raise HTTPException(status_code=500, detail="Failed to parse LLM response into JSON.")
    except Exception as e:
        logger.error(f"Quiz generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

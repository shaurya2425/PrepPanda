"""Quiz generator router.
Generates an MCQ quiz using 60% PYQ-linked chunks and 40% random chunks.
Supports post-quiz analytics, weak topic tracking, and adaptive quiz generation.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from google import genai

from Routers.deps import PgDep
from Core.cache import cache_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quiz", tags=["quiz"])

# ── Request / Response models ────────────────────────────────────────

class GenerateQuizRequest(BaseModel):
    chapter_id: uuid.UUID

class QuizQuestionOut(BaseModel):
    id: int
    question: str
    options: List[str]
    correct: int
    explanation: str
    topic: str = "General"

class AnswerItem(BaseModel):
    question_id: int
    selected: int

class SubmitQuizRequest(BaseModel):
    chapter_id: uuid.UUID
    answers: List[AnswerItem]

class AnalyticsOut(BaseModel):
    score: int
    total: int
    accuracy: float
    strengths: List[str]
    weak_topics: Dict[str, int]
    insights: List[str]
    attempt_number: int
    per_question: List[Dict[str, Any]]

class GenerateAdaptiveRequest(BaseModel):
    chapter_id: uuid.UUID


# ── Helpers ──────────────────────────────────────────────────────────

def _analytics_key(chapter_id: str) -> str:
    return cache_store.make_key("quiz_analytics", chapter_id)


def _parse_llm_json(raw: str) -> list:
    """Best-effort JSON extraction from LLM output."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n", 1)
        text = lines[1] if len(lines) > 1 else ""
    if text.endswith("```"):
        text = text[:-3].strip()
    if text.startswith("json"):
        text = text[4:].strip()
    return json.loads(text)


def _build_questions(data: list) -> List[QuizQuestionOut]:
    """Transform raw LLM JSON into QuizQuestionOut list."""
    output = []
    for idx, item in enumerate(data, 1):
        options = item.get("Option", [])
        correct_idx = item.get("correct_option_idx", 0)
        topic = item.get("topic", "General")
        output.append(QuizQuestionOut(
            id=idx,
            question=item.get("Question", ""),
            options=options,
            correct=correct_idx,
            explanation=item.get("Explanation", "No explanation provided."),
            topic=topic,
        ))
    return output


async def _fetch_context(pg: PgDep, chapter_id: uuid.UUID):
    """Fetch PYQ-linked chunks, random chunks, and concept graph."""
    pyq_chunks = await pg.get_pyq_linked_chunks(chapter_id, limit=6)
    pyq_chunk_ids = [c["chunk_id"] for c in pyq_chunks]
    random_chunks = await pg.get_random_chunks(chapter_id, limit=4, exclude_ids=pyq_chunk_ids)

    if not pyq_chunks and not random_chunks:
        raise HTTPException(status_code=404, detail="No content available for this chapter to generate a quiz.")

    pool = pg._pool_guard()
    chapter_row = await pool.fetchrow("SELECT concept_graph FROM core.chapters WHERE chapter_id = $1", chapter_id)
    concept_graph = chapter_row["concept_graph"] if chapter_row and chapter_row.get("concept_graph") else None

    context_blocks = []
    if concept_graph:
        if not isinstance(concept_graph, str):
            concept_graph = json.dumps(concept_graph)
        context_blocks.append(f"--- CHAPTER CONCEPT GRAPH (Topic Structure) ---\n{concept_graph}\n")

    context_blocks.append("--- PYQ-LINKED TOPICS ---")
    for i, c in enumerate(pyq_chunks, 1):
        pyq_text = c.get("pyq_question") or ""
        context_blocks.append(f"[Topic {i} - Originally tested by: {pyq_text}]\n{c['content'][:500]}")

    context_blocks.append("\n--- RANDOM TOPICS ---")
    for i, c in enumerate(random_chunks, len(pyq_chunks) + 1):
        context_blocks.append(f"[Topic {i}]\n{c['content'][:500]}")

    return "\n\n".join(context_blocks)


def _get_gemini_client():
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY not set")
    return genai.Client(api_key=key)


# ── POST /quiz/generate ─────────────────────────────────────────────

@router.post("/generate", response_model=List[QuizQuestionOut], summary="Generate adaptive quiz")
async def generate_quiz(
    req: GenerateQuizRequest,
    pg: PgDep,
    force_new: bool = Query(False, description="Bypass cache and generate a fresh quiz"),
):
    """
    Generate a 10-question MCQ quiz using 60% PYQ-linked chunks and 40% random chunks.
    Each question is tagged with a topic/subtopic for analytics tracking.

    When ``force_new=True`` the cache is bypassed and a fresh quiz is stored
    under a versioned key so it doesn't overwrite the original cached quiz.
    """
    cache_key = cache_store.make_key("quiz", str(req.chapter_id))

    # Check cache (only when not forcing a new quiz)
    if not force_new:
        cached = cache_store.get("quizzes", cache_key)
        if cached is not None:
            logger.info("Cache HIT  quiz %s", req.chapter_id)
            return [QuizQuestionOut(**q) for q in cached]

    try:
        context_text = await _fetch_context(pg, req.chapter_id)

        # Use slightly higher temperature for force_new to ensure variety
        temperature = 0.7 if force_new else 0.3

        prompt = f"""You are an expert exam question creator.
I will give you data about topics from a textbook chapter. Some are highly relevant because they appeared in previous year questions (PYQs), and some are random topics.

Based on this text, generate exactly 10 multiple choice questions (MCQs).
Ensure the mix is roughly 60% (6 questions) from the PYQ-linked topics and 40% (4 questions) from the random topics.
{"IMPORTANT: Generate completely DIFFERENT questions from any previous quiz. Focus on different aspects, details, and angles of the topics." if force_new else ""}

IMPORTANT RULES:
1. Each question must have exactly 4 options.
2. Only one option can be correct.
3. Provide a brief explanation for the correct answer.
4. Each question MUST include a "topic" field — a short label identifying the specific topic or subtopic the question tests (e.g. "Recursion", "Cell Division", "Newton's Laws"). Use the concept graph above to choose appropriate topic names.
5. Output MUST be valid JSON matching exactly this format:
[
  {{
    "Question": "Full question text?",
    "Option": ["Option A", "Option B", "Option C", "Option D"],
    "correct_option_idx": 0,
    "Explanation": "Brief reason why 0 is correct.",
    "topic": "Topic Name"
  }}
]

Here is the context:

{context_text}

Respond ONLY with valid JSON (no markdown fencing)."""

        client = _get_gemini_client()
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            config=genai.types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=8192,
                response_mime_type="application/json",
            ),
        )

        raw = response.text or ""
        data = _parse_llm_json(raw)
        output = _build_questions(data)

        # Cache the result
        serialised = [q.model_dump() for q in output]
        if force_new:
            versioned_key = cache_store.make_key("quiz", str(req.chapter_id), str(time.time()))
            await cache_store.put("quizzes", versioned_key, serialised)
        else:
            await cache_store.put("quizzes", cache_key, serialised)

        # Store question texts for deduplication in adaptive quiz
        ak = _analytics_key(str(req.chapter_id))
        existing = cache_store.get("quiz_analytics", ak) or {}
        existing["last_quiz_questions"] = [q.question for q in output]
        existing["last_quiz"] = serialised
        await cache_store.put("quiz_analytics", ak, existing)

        return output

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse quiz JSON: {e}\nRaw: {raw[:500]}")
        raise HTTPException(status_code=500, detail="Failed to parse LLM response into JSON.")
    except Exception as e:
        logger.error(f"Quiz generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /quiz/submit ───────────────────────────────────────────────

@router.post("/submit", response_model=AnalyticsOut, summary="Submit quiz answers and get analytics")
async def submit_quiz(req: SubmitQuizRequest):
    """
    Evaluate submitted answers against the last generated quiz for this chapter.
    Returns detailed analytics including score, accuracy, strengths, weak topics,
    and actionable insights. Persists weak topic data in session cache.
    """
    ak = _analytics_key(str(req.chapter_id))
    stored = cache_store.get("quiz_analytics", ak) or {}
    last_quiz = stored.get("last_quiz")

    if not last_quiz:
        raise HTTPException(status_code=404, detail="No quiz found for this chapter. Generate a quiz first.")

    quiz_map = {q["id"]: q for q in last_quiz}

    # Evaluate answers
    correct_count = 0
    topic_correct: Dict[str, int] = {}
    topic_total: Dict[str, int] = {}
    per_question: List[Dict[str, Any]] = []

    for ans in req.answers:
        q = quiz_map.get(ans.question_id)
        if not q:
            continue
        topic = q.get("topic", "General")
        topic_total[topic] = topic_total.get(topic, 0) + 1
        is_correct = ans.selected == q["correct"]
        if is_correct:
            correct_count += 1
            topic_correct[topic] = topic_correct.get(topic, 0) + 1
        per_question.append({
            "question_id": ans.question_id,
            "question": q["question"],
            "selected": ans.selected,
            "correct": q["correct"],
            "is_correct": is_correct,
            "topic": topic,
            "explanation": q.get("explanation", ""),
            "options": q.get("options", []),
        })

    total = len(req.answers)
    accuracy = round((correct_count / total) * 100, 1) if total > 0 else 0.0

    # Identify strengths and weak topics
    strengths = []
    weak_topics: Dict[str, int] = {}

    for topic, total_q in topic_total.items():
        correct_q = topic_correct.get(topic, 0)
        wrong_q = total_q - correct_q
        if wrong_q > 0:
            weak_topics[topic] = wrong_q
        else:
            strengths.append(topic)

    # Build insights
    insights = []
    if strengths:
        insights.append(f"You are strong in {', '.join(strengths)}")
    if weak_topics:
        weak_names = sorted(weak_topics.keys(), key=lambda t: weak_topics[t], reverse=True)
        insights.append(f"You need to focus more on {', '.join(weak_names)}")
    if accuracy >= 90:
        insights.append("Excellent performance! You have a strong grasp of this chapter.")
    elif accuracy >= 70:
        insights.append("Good work! A bit more practice on your weak areas will help you master this chapter.")
    elif accuracy >= 50:
        insights.append("Decent effort. Focus on your weak topics and try again to improve your score.")
    else:
        insights.append("This chapter needs more study. Review the concepts and attempt a focused quiz.")

    # Persist weak topics and attempt count in session cache
    attempt_number = stored.get("attempt_number", 0) + 1
    cumulative_weak: Dict[str, int] = stored.get("weak_topics", {})
    for topic, count in weak_topics.items():
        cumulative_weak[topic] = cumulative_weak.get(topic, 0) + count

    # Reduce strength topics from cumulative weak (user improved)
    for topic in strengths:
        if topic in cumulative_weak:
            cumulative_weak[topic] = max(0, cumulative_weak[topic] - 1)
            if cumulative_weak[topic] == 0:
                del cumulative_weak[topic]

    stored["weak_topics"] = cumulative_weak
    stored["attempt_number"] = attempt_number
    await cache_store.put("quiz_analytics", ak, stored)

    return AnalyticsOut(
        score=correct_count,
        total=total,
        accuracy=accuracy,
        strengths=strengths,
        weak_topics=weak_topics,
        insights=insights,
        attempt_number=attempt_number,
        per_question=per_question,
    )


# ── POST /quiz/generate-adaptive ────────────────────────────────────

@router.post("/generate-adaptive", response_model=List[QuizQuestionOut], summary="Generate adaptive quiz focused on weak areas")
async def generate_adaptive_quiz(req: GenerateAdaptiveRequest, pg: PgDep):
    """
    Generate a new 10-question quiz that focuses ~70% on weak topics and ~30%
    on other topics. Ensures questions differ from the previous quiz.
    """
    ak = _analytics_key(str(req.chapter_id))
    stored = cache_store.get("quiz_analytics", ak) or {}
    weak_topics = stored.get("weak_topics", {})
    previous_questions = stored.get("last_quiz_questions", [])

    if not weak_topics:
        # No weak topics — fall back to a normal fresh quiz
        logger.info("No weak topics for %s — generating standard fresh quiz", req.chapter_id)
        fake_req = GenerateQuizRequest(chapter_id=req.chapter_id)
        return await generate_quiz(fake_req, pg, force_new=True)

    try:
        context_text = await _fetch_context(pg, req.chapter_id)

        weak_topics_str = ", ".join(
            f"{topic} ({count} mistake{'s' if count > 1 else ''})"
            for topic, count in sorted(weak_topics.items(), key=lambda x: x[1], reverse=True)
        )

        # Build previous-questions block for deduplication
        prev_block = ""
        if previous_questions:
            prev_list = "\n".join(f"- {q}" for q in previous_questions[:10])
            prev_block = f"""
PREVIOUSLY ASKED QUESTIONS (DO NOT REPEAT THESE):
{prev_list}
"""

        prompt = f"""You are an expert exam question creator. The student has just completed a quiz and performed poorly on certain topics. Generate a new adaptive quiz that helps them improve.

WEAK AREAS (focus ~70% of questions here — approximately 7 questions):
{weak_topics_str}

The remaining ~30% (approximately 3 questions) should cover OTHER topics from the chapter for balance.

{prev_block}

IMPORTANT RULES:
1. Generate exactly 10 multiple choice questions (MCQs).
2. Each question must have exactly 4 options.
3. Only one option can be correct.
4. Provide a brief explanation for the correct answer.
5. Each question MUST include a "topic" field — a short label identifying the specific topic or subtopic.
6. Do NOT repeat any previously asked questions. Create fresh, different questions.
7. For weak area questions, focus on different angles and deeper understanding.
8. Output MUST be valid JSON matching exactly this format:
[
  {{
    "Question": "Full question text?",
    "Option": ["Option A", "Option B", "Option C", "Option D"],
    "correct_option_idx": 0,
    "Explanation": "Brief reason why 0 is correct.",
    "topic": "Topic Name"
  }}
]

Here is the chapter context:

{context_text}

Respond ONLY with valid JSON (no markdown fencing)."""

        client = _get_gemini_client()
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            config=genai.types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=8192,
                response_mime_type="application/json",
            ),
        )

        raw = response.text or ""
        data = _parse_llm_json(raw)
        output = _build_questions(data)

        # Store as last quiz for future deduplication and submit
        serialised = [q.model_dump() for q in output]
        stored["last_quiz_questions"] = [q.question for q in output]
        stored["last_quiz"] = serialised
        await cache_store.put("quiz_analytics", ak, stored)

        # Also cache in quizzes section under versioned key
        versioned_key = cache_store.make_key("quiz", str(req.chapter_id), f"adaptive-{time.time()}")
        await cache_store.put("quizzes", versioned_key, serialised)

        return output

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse adaptive quiz JSON: {e}\nRaw: {raw[:500]}")
        raise HTTPException(status_code=500, detail="Failed to parse LLM response into JSON.")
    except Exception as e:
        logger.error(f"Adaptive quiz generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

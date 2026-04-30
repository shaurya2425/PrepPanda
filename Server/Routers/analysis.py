"""Analysis router — PYQ frequency analysis, trends, and question predictions.

Endpoints
---------
GET /analysis/books/{book_id}
    Full PYQ analysis report for a book: topic zones, trends, predicted questions.

GET /analysis/chapters/{chapter_id}
    Same analysis scoped to a single chapter.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from Core.Analysis.analyzer import PYQAnalyzer
from Routers.deps import PgDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])

# Lazy singleton — created on first request so env vars are loaded.
_analyzer: Optional[PYQAnalyzer] = None


def _get_analyzer() -> PYQAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = PYQAnalyzer()
    return _analyzer


# ─────────────────────────────────────────────────────────────────────
# Response schemas
# ─────────────────────────────────────────────────────────────────────

class TopicZoneOut(BaseModel):
    chapter_title: str
    chapter_number: int
    section_titles: List[str]
    zone_range: str
    frequency: int
    total_relevance: float
    years_seen: List[int]
    exams_seen: List[str]
    sample_questions: List[str]


class TrendItemOut(BaseModel):
    zone: TopicZoneOut
    trend: str
    year_distribution: Dict[str, int]
    recency_score: float
    streak_years: int


class PredictedQuestionOut(BaseModel):
    question: str
    marks: Optional[int] = None
    difficulty: Optional[str] = None
    confidence: float = 0.0
    reasoning: str = ""
    source_zone: Dict[str, Any] = Field(default_factory=dict)
    based_on_pyqs: List[str] = Field(default_factory=list)


class AnalysisMetricsOut(BaseModel):
    zone_radius: int
    scoring_formula: str
    total_raw_mappings: int
    zones_before_merge: int
    zones_after_merge: int
    unique_chapters_hit: int


class AnalysisReportOut(BaseModel):
    book_id: uuid.UUID
    chapter_id: Optional[uuid.UUID] = None
    total_pyqs_analysed: int
    total_zones_found: int
    metrics: AnalysisMetricsOut
    top_zones: List[TopicZoneOut]
    trends: List[TrendItemOut]
    predictions: List[PredictedQuestionOut]


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _zone_to_out(z) -> TopicZoneOut:
    return TopicZoneOut(
        chapter_title=z.chapter_title,
        chapter_number=z.chapter_number,
        section_titles=z.section_titles,
        zone_range=f"{z.zone_start}–{z.zone_end}",
        frequency=z.frequency,
        total_relevance=round(z.total_relevance, 3),
        years_seen=sorted(z.years_seen),
        exams_seen=z.exams_seen,
        sample_questions=z.sample_questions[:5],
    )


def _trend_to_out(t) -> TrendItemOut:
    return TrendItemOut(
        zone=_zone_to_out(t.zone),
        trend=t.trend,
        year_distribution={str(k): v for k, v in t.year_distribution.items()},
        recency_score=t.recency_score,
        streak_years=t.streak_years,
    )


def _prediction_to_out(p) -> PredictedQuestionOut:
    return PredictedQuestionOut(
        question=p.question,
        marks=p.marks,
        difficulty=p.difficulty,
        confidence=round(p.confidence, 3),
        reasoning=p.reasoning,
        source_zone=p.source_zone,
        based_on_pyqs=p.based_on_pyqs,
    )


def _report_to_out(r) -> AnalysisReportOut:
    return AnalysisReportOut(
        book_id=r.book_id,
        chapter_id=r.chapter_id,
        total_pyqs_analysed=r.total_pyqs_analysed,
        total_zones_found=r.total_zones_found,
        metrics=AnalysisMetricsOut(
            zone_radius=r.metrics.zone_radius,
            scoring_formula=r.metrics.scoring_formula,
            total_raw_mappings=r.metrics.total_raw_mappings,
            zones_before_merge=r.metrics.zones_before_merge,
            zones_after_merge=r.metrics.zones_after_merge,
            unique_chapters_hit=r.metrics.unique_chapters_hit,
        ),
        top_zones=[_zone_to_out(z) for z in r.top_zones],
        trends=[_trend_to_out(t) for t in r.trends],
        predictions=[_prediction_to_out(p) for p in r.predictions],
    )


# ─────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────

@router.get(
    "/books/{book_id}",
    response_model=AnalysisReportOut,
    summary="Full PYQ analysis for a book",
)
async def analyse_book(
    book_id: uuid.UUID,
    pg: PgDep,
    zone_radius: int = Query(2, ge=1, le=10, description="Chunk radius for topic zones"),
    top_k: int = Query(5, ge=1, le=20, description="Number of questions to predict"),
) -> AnalysisReportOut:
    """
    Run the complete PYQ analysis pipeline for a book:

    1. **Topic zones** — group PYQ→chunk mappings into contiguous regions,
       merge overlaps, count frequency.
    2. **Trends** — classify each zone as rising / declining / consistent
       based on year distribution.
    3. **Predictions** — use Gemini to generate new exam questions with
       full traceability (reasoning, source zone, inspiring PYQs).
    """
    book = await pg.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found.")

    analyzer = _get_analyzer()
    report = await analyzer.full_report(
        pg, book_id, zone_radius=zone_radius, top_k=top_k,
    )

    return _report_to_out(report)


@router.get(
    "/chapters/{chapter_id}",
    response_model=AnalysisReportOut,
    summary="Full PYQ analysis for a chapter",
)
async def analyse_chapter(
    chapter_id: uuid.UUID,
    pg: PgDep,
    zone_radius: int = Query(2, ge=1, le=10, description="Chunk radius for topic zones"),
    top_k: int = Query(5, ge=1, le=20, description="Number of questions to predict"),
) -> AnalysisReportOut:
    """
    Same analysis pipeline as the book-level endpoint, but scoped to a
    single chapter.
    """
    ch = await pg.get_chapter(chapter_id)
    if not ch:
        raise HTTPException(status_code=404, detail=f"Chapter {chapter_id} not found.")

    book_id = ch["book_id"]

    analyzer = _get_analyzer()
    report = await analyzer.full_report(
        pg, book_id, chapter_id=chapter_id,
        zone_radius=zone_radius, top_k=top_k,
    )

    return _report_to_out(report)

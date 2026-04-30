"""PYQ Analysis engine — topic-zone frequency, trend detection, question prediction.

Pipeline
--------
1. **Analyse** — pull all PYQ→chunk mappings, group into topic zones (±radius
   around each hit), merge overlapping zones, count frequency per zone.
2. **Detect trends** — classify each zone as rising / declining / consistent
   based on year distribution.
3. **Predict questions** — feed top zones + trends + sample PYQs to Gemini 3
   Flash Preview and get back traceable predicted questions.

Usage
-----
::

    from Core.Analysis.analyzer import PYQAnalyzer

    analyzer = PYQAnalyzer()
    report   = await analyzer.full_report(pg, book_id)
    # report.top_zones        → most-hit topic zones
    # report.trends           → rising / declining / consistent labels
    # report.predictions      → Gemini-generated questions with reasoning
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from google import genai

from Core.Storage.PostgresHandler import PostgresHandler

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────

GEMINI_MODEL = "gemini-3-flash-preview"
GEMINI_TEMPERATURE = 0.4
GEMINI_MAX_TOKENS = 8192
CURRENT_YEAR = datetime.now().year


# ─────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────

@dataclass
class TopicZone:
    """A contiguous chunk window treated as one topical unit."""

    chapter_id: uuid.UUID
    chapter_title: str
    chapter_number: int
    zone_start: int                       # position_index lower bound
    zone_end: int                         # position_index upper bound
    section_titles: List[str] = field(default_factory=list)
    representative_content: str = ""      # first chunk's content
    frequency: int = 0                    # distinct PYQ count
    total_relevance: float = 0.0
    years_seen: List[int] = field(default_factory=list)
    exams_seen: List[str] = field(default_factory=list)
    sample_questions: List[str] = field(default_factory=list)
    # internal tracking — not serialised
    _pyq_ids: Set[uuid.UUID] = field(default_factory=set, repr=False)


@dataclass
class TrendItem:
    """Trend classification for a topic zone."""

    zone: TopicZone
    trend: str                            # "rising" | "declining" | "consistent" | "one-shot"
    year_distribution: Dict[int, int] = field(default_factory=dict)
    recency_score: float = 0.0           # higher = more recent emphasis
    streak_years: int = 0                 # consecutive recent years


@dataclass
class PredictedQuestion:
    """A Gemini-generated predicted question with full traceability."""

    question: str
    marks: Optional[int] = None
    difficulty: Optional[str] = None
    confidence: float = 0.0
    reasoning: str = ""
    source_zone: Dict[str, Any] = field(default_factory=dict)
    based_on_pyqs: List[str] = field(default_factory=list)


@dataclass
class AnalysisMetrics:
    """Metadata about the analysis process itself."""

    zone_radius: int = 2
    scoring_formula: str = "frequency × recency_weight (0.3 per year closer to current)"
    total_raw_mappings: int = 0
    zones_before_merge: int = 0
    zones_after_merge: int = 0
    unique_chapters_hit: int = 0


@dataclass
class AnalysisReport:
    """Complete analysis output — zones + trends + predictions."""

    book_id: uuid.UUID
    chapter_id: Optional[uuid.UUID]
    total_pyqs_analysed: int = 0
    total_zones_found: int = 0
    top_zones: List[TopicZone] = field(default_factory=list)
    trends: List[TrendItem] = field(default_factory=list)
    predictions: List[PredictedQuestion] = field(default_factory=list)
    metrics: AnalysisMetrics = field(default_factory=AnalysisMetrics)


# ─────────────────────────────────────────────────────────────────────
# Analyser
# ─────────────────────────────────────────────────────────────────────

class PYQAnalyzer:
    """End-to-end PYQ analysis: zones → trends → predictions."""

    def __init__(
        self,
        model: str = GEMINI_MODEL,
        api_key: Optional[str] = None,
    ) -> None:
        key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise ValueError("No API key. Set GEMINI_API_KEY or GOOGLE_API_KEY.")
        self._client = genai.Client(api_key=key)
        self._model = model
        logger.info("PYQAnalyzer initialised (model=%s)", model)

    # ─────────────────────────────────────────────────────────────────
    # 1. ZONE ANALYSIS
    # ─────────────────────────────────────────────────────────────────

    async def analyse(
        self,
        pg: PostgresHandler,
        book_id: uuid.UUID,
        chapter_id: Optional[uuid.UUID] = None,
        *,
        zone_radius: int = 2,
    ) -> Tuple[List[TopicZone], AnalysisMetrics]:
        """Build topic zones from PYQ→chunk mappings.

        For each mapped chunk at position_index N, the zone spans
        [N - zone_radius, N + zone_radius].  Overlapping zones within the
        same chapter are merged.  Frequency = distinct PYQ count per zone.
        """
        rows = await pg.get_pyq_chunk_analysis(book_id, chapter_id)

        if not rows:
            metrics = AnalysisMetrics(zone_radius=zone_radius, total_raw_mappings=0)
            return [], metrics

        # ── Group rows by chapter ────────────────────────────────────
        chapter_rows: Dict[uuid.UUID, List[Dict]] = defaultdict(list)
        for r in rows:
            chapter_rows[r["chapter_id"]].append(r)

        # ── Build raw zones per chapter ──────────────────────────────
        raw_zones: List[TopicZone] = []

        for ch_id, ch_rows in chapter_rows.items():
            # Collect unique (position_index → set of pyq data)
            pos_map: Dict[int, List[Dict]] = defaultdict(list)
            for r in ch_rows:
                pos_map[r["position_index"]].append(r)

            # For each hit position, create a raw zone [pos-radius, pos+radius]
            for pos, hit_rows in pos_map.items():
                sample_row = hit_rows[0]
                zone = TopicZone(
                    chapter_id=ch_id,
                    chapter_title=sample_row["chapter_title"],
                    chapter_number=sample_row["chapter_number"],
                    zone_start=pos - zone_radius,
                    zone_end=pos + zone_radius,
                    section_titles=[],
                    representative_content=sample_row["content"][:500],
                )

                for r in hit_rows:
                    zone._pyq_ids.add(r["pyq_id"])
                    zone.total_relevance += float(r["relevance"] or 1.0)
                    if r["year"] and r["year"] not in zone.years_seen:
                        zone.years_seen.append(r["year"])
                    if r["exam"] and r["exam"] not in zone.exams_seen:
                        zone.exams_seen.append(r["exam"])
                    if r["section_title"] and r["section_title"] not in zone.section_titles:
                        zone.section_titles.append(r["section_title"])
                    q = r["question"]
                    if q and q not in zone.sample_questions:
                        zone.sample_questions.append(q)

                zone.frequency = len(zone._pyq_ids)
                raw_zones.append(zone)

        zones_before_merge = len(raw_zones)

        # ── Merge overlapping zones within same chapter ──────────────
        merged = self._merge_zones(raw_zones)

        metrics = AnalysisMetrics(
            zone_radius=zone_radius,
            total_raw_mappings=len(rows),
            zones_before_merge=zones_before_merge,
            zones_after_merge=len(merged),
            unique_chapters_hit=len(chapter_rows),
        )

        # Sort by frequency descending, then by total_relevance
        merged.sort(key=lambda z: (z.frequency, z.total_relevance), reverse=True)

        return merged, metrics

    @staticmethod
    def _merge_zones(zones: List[TopicZone]) -> List[TopicZone]:
        """Merge overlapping zones within the same chapter."""
        # Group by chapter
        by_chapter: Dict[uuid.UUID, List[TopicZone]] = defaultdict(list)
        for z in zones:
            by_chapter[z.chapter_id].append(z)

        merged: List[TopicZone] = []

        for ch_id, ch_zones in by_chapter.items():
            # Sort by zone_start
            ch_zones.sort(key=lambda z: z.zone_start)

            stack: List[TopicZone] = []
            for z in ch_zones:
                if stack and z.zone_start <= stack[-1].zone_end:
                    # Merge into top of stack
                    top = stack[-1]
                    top.zone_end = max(top.zone_end, z.zone_end)
                    top._pyq_ids |= z._pyq_ids
                    top.total_relevance += z.total_relevance
                    for y in z.years_seen:
                        if y not in top.years_seen:
                            top.years_seen.append(y)
                    for e in z.exams_seen:
                        if e not in top.exams_seen:
                            top.exams_seen.append(e)
                    for s in z.section_titles:
                        if s not in top.section_titles:
                            top.section_titles.append(s)
                    for q in z.sample_questions:
                        if q not in top.sample_questions:
                            top.sample_questions.append(q)
                    if not top.representative_content and z.representative_content:
                        top.representative_content = z.representative_content
                    top.frequency = len(top._pyq_ids)
                else:
                    stack.append(z)

            merged.extend(stack)

        return merged

    # ─────────────────────────────────────────────────────────────────
    # 2. TREND DETECTION
    # ─────────────────────────────────────────────────────────────────

    def detect_trends(self, zones: List[TopicZone]) -> List[TrendItem]:
        """Classify each zone's temporal trend.

        Trend labels:
        - ``rising``     — more hits in recent years
        - ``declining``  — more hits in older years, fewer recently
        - ``consistent`` — spread across years fairly evenly
        - ``one-shot``   — appeared in only one year
        """
        trends: List[TrendItem] = []

        for zone in zones:
            sorted_years = sorted(zone.years_seen) if zone.years_seen else []

            if not sorted_years:
                trends.append(TrendItem(
                    zone=zone, trend="unknown",
                    recency_score=0.0, streak_years=0,
                ))
                continue

            # Year distribution: count questions per year
            year_dist: Dict[int, int] = defaultdict(int)
            for q in zone.sample_questions:
                # We need to count per year; use years_seen as proxy
                pass
            # Simpler: count how many times each year appears
            for y in sorted_years:
                year_dist[y] += 1

            # Recency score: higher = more recent emphasis
            recency = 0.0
            for y in sorted_years:
                years_ago = CURRENT_YEAR - y
                recency += max(0.0, 1.0 - 0.15 * years_ago)  # decays 15% per year
            recency_score = recency / max(len(sorted_years), 1)

            # Streak: consecutive years ending at most recent
            streak = 1
            for i in range(len(sorted_years) - 1, 0, -1):
                if sorted_years[i] - sorted_years[i - 1] <= 1:
                    streak += 1
                else:
                    break

            # Classify
            if len(sorted_years) == 1:
                trend = "one-shot"
            elif recency_score >= 0.7 and sorted_years[-1] >= CURRENT_YEAR - 2:
                trend = "rising"
            elif sorted_years[-1] < CURRENT_YEAR - 3:
                trend = "declining"
            else:
                trend = "consistent"

            trends.append(TrendItem(
                zone=zone,
                trend=trend,
                year_distribution=dict(year_dist),
                recency_score=round(recency_score, 3),
                streak_years=streak,
            ))

        # Sort: rising first, then consistent, then declining
        order = {"rising": 0, "consistent": 1, "one-shot": 2, "declining": 3, "unknown": 4}
        trends.sort(key=lambda t: (order.get(t.trend, 5), -t.zone.frequency))

        return trends

    # ─────────────────────────────────────────────────────────────────
    # 3. QUESTION PREDICTION (Gemini)
    # ─────────────────────────────────────────────────────────────────

    async def predict_questions(
        self,
        zones: List[TopicZone],
        trends: List[TrendItem],
        *,
        top_k: int = 5,
    ) -> List[PredictedQuestion]:
        """Use Gemini to predict likely future exam questions.

        The prompt is grounded in:
        - Topic zones with frequency data
        - Trend classifications
        - Real sample PYQs from each zone
        - Chunk content for factual accuracy
        """
        if not zones:
            return []

        # Select top zones by composite score: freq × recency_weight
        trend_map = {id(t.zone): t for t in trends}
        scored = []
        for z in zones:
            t = trend_map.get(id(z))
            recency_w = t.recency_score if t else 0.5
            composite = z.frequency * (0.5 + recency_w)
            scored.append((composite, z, t))
        scored.sort(key=lambda x: x[0], reverse=True)

        # Take top zones for the prompt (capped to keep prompt manageable)
        prompt_zones = scored[:min(top_k * 2, 10)]

        prompt = self._build_prediction_prompt(prompt_zones, top_k)

        # Call Gemini
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=[
                    {"role": "user", "parts": [{"text": prompt}]},
                ],
                config=genai.types.GenerateContentConfig(
                    temperature=GEMINI_TEMPERATURE,
                    max_output_tokens=GEMINI_MAX_TOKENS,
                ),
            )
            raw = response.text or ""
            logger.info("Gemini prediction response: %d chars", len(raw))
        except Exception as e:
            logger.error("Gemini prediction call failed: %s", e)
            return [PredictedQuestion(
                question="[Prediction unavailable — LLM call failed]",
                reasoning=str(e),
            )]

        # Parse the JSON response
        return self._parse_predictions(raw, prompt_zones)

    def _build_prediction_prompt(
        self,
        scored_zones: List[Tuple[float, TopicZone, Optional[TrendItem]]],
        top_k: int,
    ) -> str:
        """Build a detailed prompt for Gemini question prediction."""

        zone_blocks = []
        for i, (score, zone, trend) in enumerate(scored_zones, 1):
            trend_label = trend.trend if trend else "unknown"
            trend_detail = ""
            if trend:
                trend_detail = (
                    f"  Trend: {trend.trend} | "
                    f"Recency score: {trend.recency_score} | "
                    f"Year distribution: {trend.year_distribution} | "
                    f"Consecutive recent years: {trend.streak_years}"
                )

            # Limit sample questions to 5 per zone
            samples = zone.sample_questions[:5]
            samples_text = "\n".join(f"    - {q}" for q in samples) if samples else "    (none)"

            zone_blocks.append(f"""
--- TOPIC ZONE {i} (composite score: {score:.2f}) ---
Chapter: "{zone.chapter_title}" (Chapter {zone.chapter_number})
Sections: {', '.join(zone.section_titles) if zone.section_titles else '(untitled)'}
Chunk range: position {zone.zone_start}–{zone.zone_end}
PYQ frequency: {zone.frequency} questions
Years asked: {sorted(zone.years_seen) if zone.years_seen else 'unknown'}
Exams: {', '.join(zone.exams_seen) if zone.exams_seen else 'various'}
{trend_detail}

Content excerpt:
  {zone.representative_content[:400]}

Sample PYQs from this zone:
{samples_text}
""")

        zones_text = "\n".join(zone_blocks)

        return f"""You are an expert exam question predictor for Indian competitive exams (CBSE, NEET, JEE).

I will give you data about topic zones from a textbook. Each zone represents a contiguous section of the textbook that has been frequently asked in previous year questions (PYQs). I include:
- The frequency of PYQs hitting each zone
- The trend (rising = asked more recently, declining = asked less, consistent = steady)
- Sample real PYQs from each zone
- A content excerpt from the textbook for factual grounding

Based on this data, predict {top_k} NEW exam questions that are most likely to appear in upcoming exams.

IMPORTANT RULES:
1. Each predicted question must be DIFFERENT from the sample PYQs (don't just rephrase them).
2. Each prediction must include detailed REASONING explaining WHY you chose this topic.
3. The reasoning must reference specific data: frequency, trend, years, and which real PYQs inspired it.
4. Assign realistic marks (1, 2, 3, or 5) and difficulty (easy/medium/hard).
5. Assign a confidence score (0.0 to 1.0) based on how strongly the data supports the prediction.
6. Focus more on RISING and CONSISTENT trends — these are most likely to be asked again.

Here are the topic zones:

{zones_text}

Respond ONLY with valid JSON in this exact format (no markdown fencing, no extra text):
{{
  "predictions": [
    {{
      "question": "Full question text here",
      "marks": 3,
      "difficulty": "medium",
      "confidence": 0.85,
      "reasoning": "Detailed explanation of why this question is predicted, referencing zone frequency, trend, years, and which sample PYQs inspired this prediction.",
      "source_zone_index": 1,
      "based_on_sample_pyqs": ["Sample PYQ 1 text", "Sample PYQ 2 text"]
    }}
  ]
}}"""

    def _parse_predictions(
        self,
        raw: str,
        scored_zones: List[Tuple[float, TopicZone, Optional[TrendItem]]],
    ) -> List[PredictedQuestion]:
        """Parse Gemini JSON response into PredictedQuestion objects."""

        # Strip markdown code fences if present
        text = raw.strip()
        if text.startswith("```"):
            # Remove opening ```json or ``` line
            lines = text.split("\n", 1)
            text = lines[1] if len(lines) > 1 else ""
        if text.endswith("```"):
            text = text[:-3].strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse Gemini prediction JSON: %s\nRaw: %s", e, raw[:500])
            return [PredictedQuestion(
                question="[Prediction parse error — invalid JSON from LLM]",
                reasoning=f"Raw response: {raw[:300]}",
            )]

        predictions: List[PredictedQuestion] = []
        for item in data.get("predictions", []):
            # Resolve source zone
            zone_idx = item.get("source_zone_index", 1) - 1  # 1-indexed → 0-indexed
            source_zone_info: Dict[str, Any] = {}
            if 0 <= zone_idx < len(scored_zones):
                _, zone, _ = scored_zones[zone_idx]
                source_zone_info = {
                    "chapter_title": zone.chapter_title,
                    "chapter_number": zone.chapter_number,
                    "section_titles": zone.section_titles,
                    "zone_range": f"{zone.zone_start}–{zone.zone_end}",
                    "frequency": zone.frequency,
                    "years_seen": sorted(zone.years_seen),
                }

            predictions.append(PredictedQuestion(
                question=item.get("question", ""),
                marks=item.get("marks"),
                difficulty=item.get("difficulty"),
                confidence=float(item.get("confidence", 0.0)),
                reasoning=item.get("reasoning", ""),
                source_zone=source_zone_info,
                based_on_pyqs=item.get("based_on_sample_pyqs", []),
            ))

        return predictions

    # ─────────────────────────────────────────────────────────────────
    # 4. FULL REPORT
    # ─────────────────────────────────────────────────────────────────

    async def full_report(
        self,
        pg: PostgresHandler,
        book_id: uuid.UUID,
        chapter_id: Optional[uuid.UUID] = None,
        *,
        zone_radius: int = 2,
        top_k: int = 5,
    ) -> AnalysisReport:
        """Run the complete pipeline: analyse → trends → predict."""

        logger.info(
            "Running full PYQ analysis for book=%s chapter=%s (radius=%d, top_k=%d)",
            book_id, chapter_id, zone_radius, top_k,
        )

        # Step 1: Zone analysis
        zones, metrics = await self.analyse(
            pg, book_id, chapter_id, zone_radius=zone_radius,
        )

        if not zones:
            logger.warning("No topic zones found — no PYQ→chunk mappings exist.")
            return AnalysisReport(
                book_id=book_id,
                chapter_id=chapter_id,
                metrics=metrics,
            )

        # Step 2: Trend detection
        trends = self.detect_trends(zones)

        # Step 3: Question prediction
        predictions = await self.predict_questions(zones, trends, top_k=top_k)

        # Count unique PYQs
        all_pyq_ids: Set[uuid.UUID] = set()
        for z in zones:
            all_pyq_ids |= z._pyq_ids

        report = AnalysisReport(
            book_id=book_id,
            chapter_id=chapter_id,
            total_pyqs_analysed=len(all_pyq_ids),
            total_zones_found=len(zones),
            top_zones=zones,
            trends=trends,
            predictions=predictions,
            metrics=metrics,
        )

        logger.info(
            "Analysis complete: %d PYQs → %d zones → %d trends → %d predictions",
            report.total_pyqs_analysed,
            report.total_zones_found,
            len(trends),
            len(predictions),
        )

        return report

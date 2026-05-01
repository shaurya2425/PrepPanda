"""Pattern Analyzer — generates chart-ready data for PYQ trend visualisation.

Produces structured JSON outputs that the frontend renders as graphs:
  • Year-wise question frequency (line/bar chart)
  • Chapter-wise question heatmap
  • Marks distribution (pie/donut chart)
  • Exam board breakdown (stacked bar)
  • Year × Chapter heatmap matrix
  • Topic hotspot ranking (horizontal bar)
  • Difficulty curve over years (area chart)
  • Repetition analysis — topics that repeat across years

All heavy lifting is done in SQL; this module just reshapes the results.
"""

from __future__ import annotations

import logging
import uuid
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from Core.Storage.PostgresHandler import PostgresHandler

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Output dataclasses (JSON-serialisable via asdict)
# ─────────────────────────────────────────────────────────────────────

@dataclass
class ChartPoint:
    label: str
    value: float

@dataclass
class HeatmapCell:
    x: str          # e.g. year
    y: str          # e.g. chapter title
    value: float

@dataclass
class StackedBarGroup:
    label: str
    segments: Dict[str, float]

@dataclass
class TopicHotspot:
    chapter_title: str
    chapter_number: int
    section_title: str
    frequency: int
    years: List[int]
    avg_marks: float
    trend: str          # "rising" | "declining" | "steady"

@dataclass
class RepetitionCluster:
    topic: str
    chapter_title: str
    year_count: int
    years: List[int]
    question_count: int
    sample_questions: List[str]

@dataclass
class DifficultyPoint:
    year: int
    avg_marks: float
    max_marks: int
    question_count: int

@dataclass
class PatternReport:
    """Complete pattern analysis — every field is a chart-ready dataset."""

    book_id: str
    book_title: str
    total_pyqs: int

    # 1. Year-wise frequency
    year_frequency: List[ChartPoint]

    # 2. Chapter-wise frequency
    chapter_frequency: List[ChartPoint]

    # 3. Marks distribution
    marks_distribution: List[ChartPoint]

    # 4. Exam breakdown
    exam_breakdown: List[ChartPoint]

    # 5. Year × Chapter heatmap
    year_chapter_heatmap: List[HeatmapCell]

    # 6. Exam × Year stacked bar
    exam_year_stacked: List[StackedBarGroup]

    # 7. Topic hotspots (top sections by PYQ frequency)
    topic_hotspots: List[dict]

    # 8. Repetition clusters — sections asked in 3+ different years
    repetition_clusters: List[dict]

    # 9. Difficulty curve — avg marks per year
    difficulty_curve: List[dict]

    # 10. Chapter coverage — % of chapters with at least 1 PYQ
    chapter_coverage: Dict[str, Any]

    # 11. Summary stats
    summary: Dict[str, Any]


# ─────────────────────────────────────────────────────────────────────
# Analyzer
# ─────────────────────────────────────────────────────────────────────

class PatternAnalyzer:
    """Stateless analyzer — pass a PostgresHandler per call."""

    async def generate_report(
        self,
        pg: PostgresHandler,
        book_id: uuid.UUID,
        chapter_id: Optional[uuid.UUID] = None,
    ) -> PatternReport:
        """Run all analyses and return a single PatternReport."""

        pool = pg._pool_guard()

        # ── Fetch book metadata ──────────────────────────────────────
        book = await pg.get_book(book_id)
        if not book:
            raise ValueError(f"Book {book_id} not found")

        # ── Fetch all PYQs (with chapter info) ───────────────────────
        chapter_filter = ""
        params: list = [book_id]
        if chapter_id:
            chapter_filter = "AND p.chapter_id = $2"
            params.append(chapter_id)

        pyq_rows = await pool.fetch(
            f"""
            SELECT p.pyq_id, p.question, p.year, p.exam, p.marks,
                   ch.chapter_id, ch.title AS chapter_title,
                   ch.chapter_number
            FROM core.pyqs p
            LEFT JOIN core.chapters ch ON ch.chapter_id = p.chapter_id
            WHERE p.book_id = $1
              {chapter_filter}
            ORDER BY p.year NULLS LAST, ch.chapter_number
            """,
            *params,
        )

        pyqs = [dict(r) for r in pyq_rows]
        total_pyqs = len(pyqs)

        # ── Fetch section-level data from chunk mappings ─────────────
        section_rows = await pool.fetch(
            f"""
            SELECT DISTINCT ON (p.pyq_id, c.section_title)
                   p.pyq_id, p.year, p.marks, p.question,
                   c.section_title,
                   ch.title AS chapter_title,
                   ch.chapter_number
            FROM core.pyqs p
            JOIN core.pyq_chunk_map pcm ON pcm.pyq_id = p.pyq_id
            JOIN core.chunks c          ON c.chunk_id  = pcm.chunk_id
            JOIN core.chapters ch       ON ch.chapter_id = c.chapter_id
            WHERE p.book_id = $1
              {chapter_filter}
            ORDER BY p.pyq_id, c.section_title, pcm.relevance DESC
            """,
            *params,
        )
        sections = [dict(r) for r in section_rows]

        # ── Fetch all chapters for coverage calc ─────────────────────
        all_chapters = await pg.list_chapters(book_id)

        # ── Build each chart dataset ─────────────────────────────────
        year_freq     = self._year_frequency(pyqs)
        ch_freq       = self._chapter_frequency(pyqs)
        marks_dist    = self._marks_distribution(pyqs)
        exam_bd       = self._exam_breakdown(pyqs)
        heatmap       = self._year_chapter_heatmap(pyqs)
        exam_stacked  = self._exam_year_stacked(pyqs)
        hotspots      = self._topic_hotspots(sections)
        repetitions   = self._repetition_clusters(sections)
        diff_curve    = self._difficulty_curve(pyqs)
        coverage      = self._chapter_coverage(pyqs, all_chapters)
        summary       = self._summary_stats(pyqs, all_chapters, sections)

        return PatternReport(
            book_id=str(book_id),
            book_title=book["title"],
            total_pyqs=total_pyqs,
            year_frequency=year_freq,
            chapter_frequency=ch_freq,
            marks_distribution=marks_dist,
            exam_breakdown=exam_bd,
            year_chapter_heatmap=heatmap,
            exam_year_stacked=exam_stacked,
            topic_hotspots=hotspots,
            repetition_clusters=repetitions,
            difficulty_curve=diff_curve,
            chapter_coverage=coverage,
            summary=summary,
        )

    # ─────────────────────────────────────────────────────────────────
    # Individual chart builders
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _year_frequency(pyqs: List[dict]) -> List[ChartPoint]:
        """Line/bar chart: questions per year."""
        ctr = Counter(p["year"] for p in pyqs if p.get("year"))
        return [
            ChartPoint(label=str(y), value=c)
            for y, c in sorted(ctr.items())
        ]

    @staticmethod
    def _chapter_frequency(pyqs: List[dict]) -> List[ChartPoint]:
        """Horizontal bar: questions per chapter."""
        ctr: Dict[str, int] = defaultdict(int)
        for p in pyqs:
            title = p.get("chapter_title") or "Unmapped"
            ctr[title] += 1
        items = sorted(ctr.items(), key=lambda x: x[1], reverse=True)
        return [ChartPoint(label=t, value=c) for t, c in items]

    @staticmethod
    def _marks_distribution(pyqs: List[dict]) -> List[ChartPoint]:
        """Pie/donut: distribution of marks values."""
        ctr = Counter(p["marks"] for p in pyqs if p.get("marks"))
        return [
            ChartPoint(label=f"{m} marks", value=c)
            for m, c in sorted(ctr.items())
        ]

    @staticmethod
    def _exam_breakdown(pyqs: List[dict]) -> List[ChartPoint]:
        """Bar chart: questions per exam board."""
        ctr = Counter((p.get("exam") or "Unknown").upper() for p in pyqs)
        return [
            ChartPoint(label=e, value=c)
            for e, c in sorted(ctr.items(), key=lambda x: x[1], reverse=True)
        ]

    @staticmethod
    def _year_chapter_heatmap(pyqs: List[dict]) -> List[HeatmapCell]:
        """2D heatmap: Year (x) × Chapter (y) → question count."""
        grid: Dict[tuple, int] = defaultdict(int)
        for p in pyqs:
            y = p.get("year")
            ch = p.get("chapter_title") or "Unmapped"
            if y:
                grid[(str(y), ch)] += 1
        return [
            HeatmapCell(x=k[0], y=k[1], value=v)
            for k, v in sorted(grid.items())
        ]

    @staticmethod
    def _exam_year_stacked(pyqs: List[dict]) -> List[StackedBarGroup]:
        """Stacked bar: each year has segments for each exam board."""
        buckets: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for p in pyqs:
            y = p.get("year")
            e = (p.get("exam") or "Unknown").upper()
            if y:
                buckets[y][e] += 1
        return [
            StackedBarGroup(label=str(y), segments=dict(segs))
            for y, segs in sorted(buckets.items())
        ]

    @staticmethod
    def _topic_hotspots(sections: List[dict]) -> List[dict]:
        """Top textbook sections by PYQ frequency."""
        topics: Dict[str, dict] = {}
        for s in sections:
            sec = s.get("section_title") or "(untitled)"
            ch = s.get("chapter_title") or "?"
            ch_num = s.get("chapter_number", 0)
            key = f"{ch_num}::{sec}"

            if key not in topics:
                topics[key] = {
                    "chapter_title": ch,
                    "chapter_number": ch_num,
                    "section_title": sec,
                    "frequency": 0,
                    "years": set(),
                    "marks_sum": 0,
                    "marks_count": 0,
                }
            t = topics[key]
            t["frequency"] += 1
            if s.get("year"):
                t["years"].add(s["year"])
            if s.get("marks"):
                t["marks_sum"] += s["marks"]
                t["marks_count"] += 1

        results = []
        from datetime import datetime
        current_year = datetime.now().year

        for t in sorted(topics.values(), key=lambda x: x["frequency"], reverse=True):
            years_list = sorted(t["years"])
            avg_marks = round(t["marks_sum"] / t["marks_count"], 1) if t["marks_count"] else 0

            # Simple trend: compare recent-half frequency to older-half
            trend = "steady"
            if len(years_list) >= 2:
                mid = years_list[len(years_list) // 2]
                recent = sum(1 for y in years_list if y >= mid)
                older  = sum(1 for y in years_list if y < mid)
                if recent > older * 1.5:
                    trend = "rising"
                elif older > recent * 1.5:
                    trend = "declining"

            results.append(asdict(TopicHotspot(
                chapter_title=t["chapter_title"],
                chapter_number=t["chapter_number"],
                section_title=t["section_title"],
                frequency=t["frequency"],
                years=years_list,
                avg_marks=avg_marks,
                trend=trend,
            )))

        return results[:30]  # top 30

    @staticmethod
    def _repetition_clusters(sections: List[dict]) -> List[dict]:
        """Sections asked across 2+ different years."""
        by_section: Dict[str, dict] = defaultdict(
            lambda: {"years": set(), "questions": [], "ch": "", "count": 0}
        )
        for s in sections:
            sec = s.get("section_title") or "(untitled)"
            ch = s.get("chapter_title") or "?"
            key = f"{ch}::{sec}"
            b = by_section[key]
            b["ch"] = ch
            b["count"] += 1
            if s.get("year"):
                b["years"].add(s["year"])
            q = s.get("question", "")
            if q and q not in b["questions"]:
                b["questions"].append(q)

        results = []
        for key, b in by_section.items():
            yrs = sorted(b["years"])
            if len(yrs) < 2:
                continue
            sec = key.split("::", 1)[1] if "::" in key else key
            results.append(asdict(RepetitionCluster(
                topic=sec,
                chapter_title=b["ch"],
                year_count=len(yrs),
                years=yrs,
                question_count=b["count"],
                sample_questions=b["questions"][:5],
            )))

        results.sort(key=lambda x: x["year_count"], reverse=True)
        return results[:20]

    @staticmethod
    def _difficulty_curve(pyqs: List[dict]) -> List[dict]:
        """Average marks per year — proxy for difficulty trend."""
        buckets: Dict[int, list] = defaultdict(list)
        for p in pyqs:
            y = p.get("year")
            m = p.get("marks")
            if y and m:
                buckets[y].append(m)

        return [
            asdict(DifficultyPoint(
                year=y,
                avg_marks=round(sum(ms) / len(ms), 2),
                max_marks=max(ms),
                question_count=len(ms),
            ))
            for y, ms in sorted(buckets.items())
        ]

    @staticmethod
    def _chapter_coverage(pyqs: List[dict], all_chapters: List[dict]) -> Dict[str, Any]:
        """How many chapters have at least one PYQ."""
        total = len(all_chapters)
        covered_ids = {p["chapter_id"] for p in pyqs if p.get("chapter_id")}
        covered = len(covered_ids)
        uncovered = []
        for ch in all_chapters:
            if ch["chapter_id"] not in covered_ids:
                uncovered.append({
                    "chapter_number": ch["chapter_number"],
                    "title": ch["title"],
                })
        return {
            "total_chapters": total,
            "covered": covered,
            "uncovered": total - covered,
            "coverage_pct": round(covered / total * 100, 1) if total else 0,
            "uncovered_chapters": uncovered,
        }

    @staticmethod
    def _summary_stats(
        pyqs: List[dict],
        all_chapters: List[dict],
        sections: List[dict],
    ) -> Dict[str, Any]:
        """High-level summary numbers for dashboard cards."""
        years = sorted({p["year"] for p in pyqs if p.get("year")})
        exams = sorted({(p.get("exam") or "").upper() for p in pyqs if p.get("exam")})
        marks_vals = [p["marks"] for p in pyqs if p.get("marks")]

        unique_sections = len({
            s.get("section_title") for s in sections if s.get("section_title")
        })

        return {
            "total_questions": len(pyqs),
            "year_span": f"{years[0]}–{years[-1]}" if years else "N/A",
            "unique_years": len(years),
            "exam_boards": exams,
            "avg_marks": round(sum(marks_vals) / len(marks_vals), 2) if marks_vals else 0,
            "total_marks_pool": sum(marks_vals),
            "unique_topics_hit": unique_sections,
            "total_chapters": len(all_chapters),
            "most_asked_chapter": max(
                ((p.get("chapter_title") or "?") for p in pyqs),
                key=lambda t: sum(1 for p in pyqs if p.get("chapter_title") == t),
                default="N/A",
            ),
        }

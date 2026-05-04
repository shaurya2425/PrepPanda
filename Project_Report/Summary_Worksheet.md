# MINOR PROJECT WORK SUMMARY SHEET

**Project Title:** PrepPanda — AI-Powered NCERT Study Assistant with RAG-Based Smart Retrieval, Mind-Map Generation, PYQ Analysis, and Adaptive Quiz Engine

**Department:** Computer Science & Engineering | **Program:** B.Tech
**Supervisor:** [Supervisor Name] | **Date:** May 5, 2026

| **Team Member** | **Roll No.** |
|-----------------|-------------|
| Student A | [Roll No.] |
| Student B | [Roll No.] |
| Student C | [Roll No.] |

---

## 1. Motivation Behind the Project

Over 250 million Indian students rely on NCERT textbooks for board (CBSE) and competitive exams (NEET/JEE). Existing study platforms deliver static, pre-curated content without intelligent retrieval from the actual textbook. Students waste significant time manually searching for concepts, creating notes, analysing PYQ trends, and building concept maps. General-purpose AI chatbots (ChatGPT, Bard) hallucinate and are not aligned with NCERT syllabus. PrepPanda was motivated by the need for a **curriculum-grounded, AI-powered study assistant** that combines RAG-based Q&A, automated mind maps, PYQ analytics with question prediction, and adaptive quizzes — all derived directly from ingested NCERT PDF content.

---

## 2. Type of Project

**(c) Research cum Development Project**

The project involves both novel research contributions (hybrid semantic+keyword retrieval for educational content, spatial image-caption association, zone-based PYQ trend analysis with LLM-powered question prediction) and significant software development (full-stack web application with FastAPI backend, React frontend, Docker-based infrastructure).

---

## 3. Critical Analysis of Research Papers & Gaps

| # | Paper (Year) | One-Line Summary | Gap Identified |
|---|-------------|------------------|----------------|
| 1 | Lewis et al. — RAG for NLP Tasks (2020) | Combines retrieval with generation for grounded answers | Applied to Wikipedia, not domain-specific educational content |
| 2 | Reimers & Gurevych — Sentence-BERT (2019) | Siamese BERT networks for semantically meaningful sentence embeddings | No application to NCERT-style structured textbook chunking |
| 3 | Robertson & Zaragoza — BM25 (2009) | Probabilistic term-frequency ranking for keyword search | Used alone; no hybrid combination with dense retrieval for education |
| 4 | Malkov & Yashunin — HNSW Graphs (2020) | Sub-linear approximate nearest neighbour search for vectors | Not integrated with educational full-text search pipelines |
| 5 | Gao et al. — RAG Survey (2024) | Taxonomy: Naive, Advanced, Modular RAG architectures | No implementation targeting Indian curriculum content |
| 6 | Kasneci et al. — ChatGPT for Education (2023) | Opportunities and risks of LLMs in education (hallucination, bias) | No RAG-based mitigation system for NCERT-specific grounding |
| 7 | Google — Gemini Models (2024) | Highly capable multimodal generation models | Not applied to structured textbook RAG with figure embedding |
| 8 | Touvron et al. — LLaMA (2023) | Open-source efficient foundation models | Not used for educational concept graph extraction |

**Key Gap:** No existing system combines dual-parser PDF ingestion, hybrid retrieval, PYQ-to-textbook semantic mapping with zone-based trend analysis, and LLM-powered question prediction — all grounded in actual NCERT content.

---

## 4. Overall Design of Project

```
┌────────────────────────────────────────────────────────────────┐
│              FRONTEND (React + Vite + Tailwind CSS)            │
│   Landing │ Library │ Study Workspace (8 Tabs) │ Admin Panel   │
│   [Notes] [MindMap] [PYQ Analytics] [Patterns] [Quiz] [PDF]   │
└──────────────────────────┬─────────────────────────────────────┘
                           │ REST API (HTTP/JSON)
┌──────────────────────────┴─────────────────────────────────────┐
│                 BACKEND (FastAPI + Python)                      │
│                                                                 │
│  ┌─────────────┐ ┌───────────┐ ┌──────────┐ ┌───────────────┐ │
│  │ SRS Pipeline │ │ MindMap   │ │ PYQ      │ │ Quiz          │ │
│  │ (Retriever + │ │ Generator │ │ Analyzer │ │ Generator     │ │
│  │  Generator)  │ │ (Groq)   │ │ +Pattern │ │ (Gemini)      │ │
│  └──────┬───────┘ └─────┬────┘ └────┬─────┘ └──────┬────────┘ │
│         │               │           │               │          │
│  ┌──────┴───────────────┴───────────┴───────────────┘          │
│  │  ChapterPipeline ← NodeParser + VisualParser + Embedder     │
│  └─────────────────────────────────────────┬───────────────────┘│
└────────────────────────────────────────────┼────────────────────┘
                                             │
┌────────────────────────────────────────────┼────────────────────┐
│                    DATA LAYER (Docker)      │                    │
│   PostgreSQL + pgvector          MinIO (S3-compatible)          │
│   (chunks, embeddings,           (PDFs, chapter images)         │
│    PYQs, concept graphs)                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Features Built & Languages Used

**Features Built:**

| # | Feature | Description |
|---|---------|-------------|
| 1 | PDF Ingestion Pipeline | Dual-parser (text + visual) with structure-aware chunking & spatial image association |
| 2 | Hybrid RAG Q&A (SRS) | 70% semantic + 30% keyword search with neighbour expansion → Gemini answer generation |
| 3 | Mind Map Generator | LLM-powered hierarchical concept graphs with semantic tags, cached in DB |
| 4 | PYQ Analysis Engine | Zone-based frequency analysis, trend detection (rising/declining/consistent), question prediction |
| 5 | Pattern Visualiser | 11 chart-ready datasets (heatmaps, trends, difficulty curves, repetition clusters) |
| 6 | Adaptive Quiz Engine | 5 MCQs per request: 60% PYQ-weighted, 40% random, with explanations |
| 7 | Admin Panel | Book/chapter/PYQ CRUD with batch ingestion and Basic HTTP Auth |
| 8 | Interactive Study Workspace | 8-tab interface: Notes, MindMap, PYQ, Patterns, Quiz, PDF, Analytics, Settings |

**Languages & Technologies:**

| Layer | Technologies |
|-------|-------------|
| Backend | Python 3.12, FastAPI, asyncpg, PyMuPDF, spaCy, Sentence Transformers |
| Frontend | JavaScript (React 18), Vite 6, Tailwind CSS 4, Radix UI, React Flow, Recharts |
| Database | PostgreSQL + pgvector (vector search), MinIO (object storage) |
| Infrastructure | Docker Compose |
| AI/ML | Google Gemini API, Groq API (LLaMA 3.1-8B), all-mpnet-base-v2 (768-dim embeddings) |

---

## 6. Proposed Methodology

1. **Ingest** NCERT PDFs through dual-parser pipeline: NodeParser (structure-aware text chunking via heading detection + spaCy sentence splitting) and VisualParser (spatial caption→image association using bounding box proximity)
2. **Embed** text chunks using all-mpnet-base-v2 sentence transformer (768-dim vectors) stored in pgvector with HNSW index
3. **Retrieve** using weighted hybrid search: 70% cosine-similarity semantic search + 30% BM25 keyword search, with ±1 neighbour expansion for context continuity
4. **Generate** answers by building structured prompts with retrieved chunks and figure placeholders, calling Gemini, and replacing image tags with real URLs
5. **Analyse** PYQs by semantically mapping questions to textbook chunks, building frequency zones, detecting temporal trends, and predicting future questions via Gemini
6. **Visualise** via interactive React frontend with React Flow (mind maps), Recharts (pattern charts), and react-markdown (AI answers)

---

## 7. Algorithm / Description of Work

**Core Algorithm — Hybrid Retrieval with Neighbour Expansion:**

```
INPUT: query (string), chapter_id (UUID)

1. normalised_query ← remove_stopwords(lowercase(query))
2. query_vector ← encode(normalised_query)  // all-mpnet-base-v2 → 768-dim

3. sem_hits ← HNSW_search(query_vector, chapter_id, pool=30)
4. kw_hits  ← BM25_search(normalised_query, chapter_id, pool=30)

5. sem_scores ← min_max_normalise(sem_hits.scores)
6. kw_scores  ← min_max_normalise(kw_hits.scores)

7. FOR each chunk_id in UNION(sem_hits, kw_hits):
     hybrid_score[chunk_id] = 0.7 × sem_scores[chunk_id]
                             + 0.3 × kw_scores[chunk_id]

8. top_K ← top 10 chunks by hybrid_score
9. expanded ← top_K ∪ neighbours(±1 position_index)
10. final_chunks ← sort(expanded, by=position_index)  // reading order
11. images ← fetch_linked_images(final_chunks)

OUTPUT: RetrievalResult{chunks, images, query_normalised}
```

**PYQ Zone Analysis Algorithm:**
1. Group all PYQ→chunk mappings by chapter
2. For each hit position, create zone [pos−2, pos+2]
3. Merge overlapping zones using stack-based interval merge
4. Count distinct PYQ frequency per merged zone
5. Classify trend: rising/declining/consistent/one-shot based on year distribution
6. Rank zones by composite_score = frequency × (0.5 + recency_weight)
7. Feed top zones to Gemini for question prediction with confidence scores

---

## 8. Division of Work Among Students

| Student | Role | Specific Contributions |
|---------|------|----------------------|
| **Student A** | Backend & AI Engineer | NodeParser, VisualParser, ChapterPipeline, ChunkEmbedder, SRS pipeline (Retriever + Context Builder + Generator), Gemini & Groq API integration, PostgreSQL schema design with pgvector |
| **Student B** | Full-Stack & Data Engineer | All 6 FastAPI routers (admin, catalog, srs, mindmap, analysis, quiz), PYQAnalyzer, PatternAnalyzer, Docker Compose setup, PYQ ingestion & semantic mapping, test cases |
| **Student C** | Frontend & UI/UX Designer | React app: Landing Page, Library Flow, Study Workspace (8 tabs), Admin Panel. API client module, React Flow mind-map integration, Recharts pattern charts, Tailwind CSS responsive design |

---

## 9. Results

| Metric | Value |
|--------|-------|
| Avg chunks per chapter | 40–60 with section breadcrumbing |
| Avg figures extracted per chapter | 8–15 with >85% caption accuracy |
| Embedding speed (CPU) | ~47 chunks in <3 seconds |
| Hybrid search relevance (manual 1–5 rating) | **4.8 avg** vs 4.4 semantic-only vs 3.8 keyword-only |
| PYQ zones detected per book | 25–35 after merging |
| Prediction confidence range | 0.6–0.95 with source traceability |
| Quiz generation | 5 MCQs with 60/40 PYQ-weighted distribution |
| Mind-map nodes per chapter | 80–150 (rule-based), coherent hierarchies (LLM) |
| Frontend pages | 7 pages, 8 study workspace tabs |
| API endpoints | 20+ across 6 routers |

PrepPanda's hybrid retrieval consistently outperforms single-method approaches. The PYQ analysis module provides unique capabilities not available in any existing educational platform (Toppr, Embibe, Byju's).

---

## 10. Conclusion

PrepPanda successfully demonstrates the application of RAG architecture, hybrid vector-keyword search, multi-LLM orchestration, and zone-based PYQ analytics to build an intelligent NCERT study assistant. The system ingests textbook PDFs through a novel dual-parser pipeline, creates rich knowledge representations (embedded chunks + spatially linked figures), and provides an integrated study workspace combining AI notes, interactive mind maps, PYQ trend analysis with question prediction, adaptive quizzes, and PDF reading — all grounded in verified textbook content.

**Key contributions:** (1) First RAG system specifically designed for NCERT content with figure-aware retrieval, (2) Novel zone-based PYQ analysis with temporal trend detection and traceable question prediction, (3) Hybrid 70/30 semantic-keyword search with neighbour expansion outperforming single-method approaches.

**Limitations:** Single language (English), no student auth/progress tracking, external LLM API dependency.

**Future scope:** Spaced repetition, Hindi support, mobile app, fine-tuned domain embeddings, offline inference.

---

*Submitted to Panel Members — May 5, 2026*

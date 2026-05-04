# CHAPTER 3: SYSTEM DESIGN & METHODOLOGY

## 3.1 Proposed Methodology

PrepPanda employs a modular, pipeline-oriented architecture comprising seven interconnected subsystems. Each subsystem is described below with its internal flow.

### 3.1.1 High-Level System Architecture

**Figure 3.1: High-Level System Architecture of PrepPanda**

```
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND (React + Vite)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────┐ ┌──────────┐ │
│  │ AI Notes │ │ Mind Map │ │ PYQ Anal.│ │ Quiz │ │ PDF Read │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──┬───┘ └────┬─────┘ │
│       │            │            │           │          │        │
│       └────────────┴────────────┴───────────┴──────────┘        │
│                          API Client (api.js)                    │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP/REST
┌──────────────────────────────┴──────────────────────────────────┐
│                   BACKEND (FastAPI + Python)                     │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────┐ ┌────────┐ │
│  │ SRS      │  │ MindMap  │  │ Analysis │  │ Quiz │ │ Admin  │ │
│  │ Router   │  │ Router   │  │ Router   │  │Router│ │ Router │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──┬───┘ └───┬────┘ │
│       │             │             │            │         │       │
│  ┌────┴─────┐  ┌────┴─────┐  ┌───┴────┐   ┌──┴───┐ ┌───┴────┐ │
│  │Retriever │  │MindMap   │  │PYQ     │   │Gemini│ │Chapter │ │
│  │Context   │  │Builder   │  │Analyzer│   │ API  │ │Pipeline│ │
│  │Generator │  │(Groq)    │  │Pattern │   └──────┘ └───┬────┘ │
│  └────┬─────┘  └──────────┘  │Analyzer│             ┌──┴────┐  │
│       │                      └────────┘             │Node   │  │
│  ┌────┴─────┐                                       │Parser │  │
│  │ Gemini   │                                       │Visual │  │
│  │ API      │                                       │Parser │  │
│  └──────────┘                                       │Embedder│ │
│                                                     └───┬────┘  │
└──────────────────────────────────────────────────────────┼──────┘
                                                           │
┌──────────────────────────────────────────────────────────┼──────┐
│                    DATA LAYER (Docker)                    │      │
│  ┌───────────────────────┐  ┌───────────────────────┐   │      │
│  │ PostgreSQL + pgvector │  │ MinIO (S3-compatible) │   │      │
│  │ ┌───────┐ ┌────────┐ │  │ ┌─────────────────┐   │   │      │
│  │ │ Books │ │ Chunks │ │  │ │ PDF Files       │   │   │      │
│  │ │Chapter│ │Embedding│ │  │ │ Chapter Images  │   │   │      │
│  │ │ PYQs  │ │ Images │ │  │ └─────────────────┘   │   │      │
│  │ └───────┘ └────────┘ │  └───────────────────────┘   │      │
│  └───────────────────────┘                              │      │
└─────────────────────────────────────────────────────────────────┘
```

### 3.1.2 PDF Ingestion Pipeline

**Figure 3.2: PDF Ingestion Pipeline — NodeParser and VisualParser Flow**

The ingestion pipeline consists of two parallel parsers orchestrated by the `ChapterPipeline`:

```
                         PDF File (Input)
                              │
                    ┌─────────┴──────────┐
                    ▼                    ▼
            ┌──────────────┐    ┌───────────────┐
            │  NodeParser  │    │ VisualParser   │
            │  (Text Side) │    │ (Layout Side)  │
            └──────┬───────┘    └───────┬────────┘
                   │                    │
        ┌──────────┤                    ├──────────┐
        ▼          ▼                    ▼          ▼
   ┌─────────┐ ┌──────────┐    ┌──────────┐ ┌──────────┐
   │ Text    │ │ Figure   │    │ Image    │ │ Spatial  │
   │ Chunks  │ │ Refs     │    │ Blocks   │ │ Assoc.   │
   │(spaCy)  │ │(regex)   │    │(PyMuPDF) │ │(bbox)    │
   └────┬────┘ └────┬─────┘    └────┬─────┘ └────┬─────┘
        │           │               │             │
        ▼           ▼               ▼             ▼
   ┌─────────────────────────────────────────────────┐
   │           ChapterPipeline (Orchestrator)         │
   │                                                   │
   │  1. Create chapter row in PostgreSQL              │
   │  2. Upload raw PDF to MinIO bucket                │
   │  3. Store text chunks → core.chunks               │
   │  4. Upload images → MinIO, store → core.images    │
   │  5. Link chunks ↔ images → chunk_image_links      │
   │  6. Embed chunks → update embedding vectors       │
   └───────────────────────────────────────────────────┘
```

**NodeParser Process:**
1. **PDF Text Extraction:** Uses PyMuPDF (`fitz`) in layout-aware text mode to extract full text from the PDF while preserving structural information.
2. **Heading Detection:** Employs regex patterns to detect NCERT-style numbered headings (e.g., "1.1", "1.2.3"), ALL-CAPS headings, and title-case short headings.
3. **Section Stack Maintenance:** Maintains a section hierarchy stack, tracking nesting depth from numbered heading prefixes. When a new heading is encountered, the stack is trimmed to the appropriate depth and the heading is pushed.
4. **Semantic Chunking:** Body text is buffered line-by-line and flushed at heading boundaries. Oversized buffers (>550 words) are split at sentence boundaries using spaCy's `en_core_web_sm` model. Minimum chunk size is enforced at 20 characters.
5. **Figure Reference Extraction:** Regex patterns match inline figure references (e.g., "Fig 1.1", "Figure 2") within each chunk, storing deduplicated reference IDs for downstream linking.
6. **Structural Breadcrumbing:** Each `TextChunk` carries a `section_path` (list of ancestor headings) and generates a `full_content()` method that prefixes the content with a structural breadcrumb (e.g., "[1.2 Motion > Definition]\\nContent...") for higher-quality embeddings.

**VisualParser Process:**
1. **Page Element Extraction:** Iterates over every page using PyMuPDF's dictionary mode (`get_text("dict")`), extracting both text blocks (with bounding boxes) and image references (with xref IDs and rects).
2. **Text Block Classification:** Each text block is classified into one of five roles using heuristic rules: `HEADING`, `CAPTION`, `CONTEXT`, `QUESTION`, or `BODY`.
3. **Caption-Driven Image Association:** Instead of searching image→caption (which lets decorative banners steal real captions), the system flips the direction: for each caption, it finds the nearest image ABOVE it on the same page. This is reliable because NCERT textbooks consistently place figures above their captions.
4. **Image Rendering:** Matched images are rendered via `page.get_pixmap()` at 2× upscale with alpha compositing, producing high-quality PNG bytes. Blank/solid-fill pixmaps are filtered out.
5. **Multi-Image Grouping:** Side-by-side images (common in NCERT comparison diagrams) are grouped when their Y-range overlap exceeds 50%, forming a single semantic unit with a combined bounding box.
6. **Content Deduplication:** Images are deduplicated by both xref (PDF-level) and content hash (MD5 of rendered PNG bytes).

### 3.1.3 Hybrid Retrieval Pipeline

**Figure 3.3: Hybrid Retrieval Pipeline (Semantic + Keyword Search)**

```
        User Query: "What is double fertilisation?"
                           │
                           ▼
                 ┌─────────────────┐
                 │  Normalise Query │
                 │  (Remove stops,  │
                 │   lowercase)     │
                 └────────┬────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
     ┌────────────────┐      ┌────────────────┐
     │ Embed Query     │      │ Keyword Search │
     │ (all-mpnet-     │      │ (BM25 via      │
     │  base-v2)       │      │  tsvector)     │
     └───────┬────────┘      └───────┬────────┘
             │                       │
             ▼                       ▼
     ┌────────────────┐      ┌────────────────┐
     │ Vector Search  │      │ ts_rank_cd     │
     │ (cosine sim    │      │ scoring        │
     │  via HNSW)     │      │                │
     │ Pool: 30 hits  │      │ Pool: 30 hits  │
     └───────┬────────┘      └───────┬────────┘
             │                       │
             └───────────┬───────────┘
                         ▼
              ┌──────────────────────┐
              │  Min-Max Normalise   │
              │  Each Score Set      │
              └─────────┬────────────┘
                        ▼
              ┌──────────────────────┐
              │  Hybrid Score =      │
              │  0.7×Semantic +      │
              │  0.3×Keyword         │
              └─────────┬────────────┘
                        ▼
              ┌──────────────────────┐
              │  Take Top-K (10)     │
              │  by Hybrid Score     │
              └─────────┬────────────┘
                        ▼
              ┌──────────────────────┐
              │  Neighbour Expansion │
              │  ±1 position_index   │
              └─────────┬────────────┘
                        ▼
              ┌──────────────────────┐
              │  Sort by             │
              │  position_index      │
              │  (reading order)     │
              └─────────┬────────────┘
                        ▼
              ┌──────────────────────┐
              │  Fetch Linked Images │
              │  (chunk_image_links) │
              └──────────────────────┘
```

### 3.1.4 SRS (Smart Retrieval System) End-to-End Flow

**Figure 3.4: SRS End-to-End Flow**

```
  Student Question ──► Retriever ──► Context Builder ──► Generator
                        │                │                  │
                        │                │                  ▼
                    Hybrid Search    Build Prompt       Call Gemini
                    + Neighbours     (System +          (gemini-3-
                    + Images          User prompt)       flash-preview)
                                     with {{IMG:X.X}}       │
                                     placeholders           ▼
                                                      Replace {{IMG}}
                                                      with real URLs
                                                           │
                                                           ▼
                                                    Markdown Answer
                                                    with embedded
                                                    figure images
```

### 3.1.5 Mind-Map Generation Pipeline

**Figure 3.5: Mind-Map Generation Pipeline**

The mind-map generation employs two complementary strategies:

**Strategy A — Rule-Based Semantic Extraction (MindMapBuilder):**
- Pattern-match common textbook constructs using registered regex rules:
  - "X is defined as Y" → `DEFINITION` node
  - "types of X" → `CLASSIFICATION` node
  - "process of X" → `STEPS` node
  - "X differs from Y" → `COMPARISON` node
  - "for example" → `EXAMPLE` node
  - Bulleted/numbered lists → `ENUMERATION` nodes
- Build a hierarchical tree by walking chunks in order, reconstructing heading hierarchy via a stack-based depth tracker.

**Strategy B — LLM-Powered Concept Graph (Groq LLaMA 3.1-8B):**
- Concatenate all chunk content for the chapter.
- Send a structured prompt to Groq requesting a JSON concept graph with semantic tags (`core_concept`, `definition`, `classification`, `steps`, `comparison`, `example`, `enumeration`, `body`).
- Cache the generated concept graph in `core.chapters.concept_graph` (JSONB column) to avoid regeneration.
- The cached graph is reused for mind-map display, quiz context, and PYQ prediction context.

### 3.1.6 PYQ Analysis and Question Prediction Pipeline

**Figure 3.6: PYQ Analysis and Question Prediction Pipeline**

```
  PYQ Questions ──► Semantic Mapping ──► Zone Analysis ──► Trend Detection
   (Ingested)       to Textbook Chunks    (±2 radius,       (rising/declining/
                    via cosine sim.       merge overlaps)    consistent/one-shot)
                                              │                    │
                                              ▼                    ▼
                                         ┌─────────────────────────────┐
                                         │  Question Prediction        │
                                         │  (Gemini-3-Flash-Preview)   │
                                         │                             │
                                         │  Input: Top zones by        │
                                         │  composite score =          │
                                         │  freq × (0.5 + recency)    │
                                         │                             │
                                         │  Output: New questions      │
                                         │  with marks, difficulty,    │
                                         │  confidence, reasoning,     │
                                         │  source traceability        │
                                         └─────────────────────────────┘
```

### 3.1.7 Database Schema Design

**Figure 3.7: Database Entity-Relationship Diagram**

```
  ┌──────────┐     1:N     ┌───────────┐     1:N     ┌──────────┐
  │  Books   │────────────►│ Chapters  │────────────►│  Chunks  │
  │          │             │           │             │          │
  │ book_id  │             │chapter_id │             │ chunk_id │
  │ title    │             │ title     │             │ content  │
  │ grade    │             │ pdf_url   │             │embedding │
  │ subject  │             │concept_   │             │ tsv      │
  └────┬─────┘             │ graph     │             │section_  │
       │                   └─────┬─────┘             │ title    │
       │                         │                   └────┬─────┘
       │                         │ 1:N                    │
       │                   ┌─────┴─────┐                  │ M:N
       │                   │  Images   │          ┌───────┴───────┐
       │                   │ image_id  │          │chunk_image_   │
       │                   │image_path │          │   links       │
       │                   │ caption   │          │(chunk_id,     │
       │                   └───────────┘          │ image_id)     │
       │                                          └───────────────┘
       │ 1:N
  ┌────┴─────┐            ┌──────────────┐
  │   PYQs   │            │pyq_chunk_map │
  │ pyq_id   │────M:N────►│(pyq_id,      │
  │ question │            │ chunk_id,    │
  │ year     │            │ relevance)   │
  │ exam     │            └──────────────┘
  │ marks    │
  └──────────┘
```

## 3.2 Tool and Technique Selection

**Table 3.1: Tool and Technology Selection with Justification**

| Component | Tool/Technology | Version | Justification |
|-----------|----------------|---------|---------------|
| **Backend Framework** | FastAPI (Python) | 0.135+ | Async-native, auto-generated OpenAPI docs, built-in validation via Pydantic. Superior performance over Flask/Django for I/O-bound LLM and DB operations. |
| **Frontend Framework** | React + Vite | React 18.3, Vite 6.3 | Component-based architecture for complex interactive UI. Vite provides near-instant HMR for development. |
| **CSS Framework** | Tailwind CSS | 4.1 | Utility-first approach enables rapid UI development with consistent design tokens. |
| **UI Components** | Radix UI + shadcn/ui | Various | Headless, accessible, composable primitives (Accordion, Dialog, Tabs, Select). Production-ready with ARIA compliance. |
| **Graph Visualisation** | React Flow (@xyflow/react) | 12.10+ | Purpose-built for interactive node-edge graph rendering. Supports custom nodes, automatic layout (dagre), zoom/pan, and minimap — ideal for mind-map display. |
| **Charts** | Recharts | 2.15+ | Declarative, composable chart library built on D3 with React components. Used for PYQ trend charts, heatmaps, pie charts. |
| **Database** | PostgreSQL + pgvector | PG 16, pgvector latest | pgvector adds native vector column type and HNSW indexing. PostgreSQL's tsvector provides built-in BM25-style full-text search, eliminating need for a separate search engine (Elasticsearch). |
| **Object Storage** | MinIO | Latest | S3-compatible self-hosted object storage. Avoids AWS dependency. Used to store chapter PDFs and extracted figure images. |
| **Containerisation** | Docker Compose | 3.9 | Reproducible infrastructure for PostgreSQL and MinIO. Single `docker compose up` command for setup. |
| **PDF Parsing** | PyMuPDF (fitz) | 1.27+ | Fastest pure-Python PDF library with layout-aware text extraction and image rendering via pixmap. Supports dict mode for bounding box access. |
| **NLP** | spaCy (en_core_web_sm) | 3.8+ | Lightweight, fast sentence segmentation model. Used for splitting oversized chunks at sentence boundaries. |
| **Embedding Model** | all-mpnet-base-v2 (Sentence Transformers) | 3.4+ | 768-dimensional embeddings with best quality among small open models. Normalised embeddings enable cosine similarity via L2 distance. Runs on CPU without GPU requirement. |
| **Generation LLM** | Google Gemini (gemini-3-flash-preview) | Latest | Large context window, structured JSON output, multimodal capability. Used for answer generation, question prediction, quiz creation. |
| **Concept Graph LLM** | Groq (LLaMA 3.1-8B-Instant) | Latest | Ultra-fast inference for structured JSON extraction tasks. Significantly cheaper than Gemini for concept graph generation. |
| **Python Package Manager** | uv | Latest | Ultra-fast dependency resolution and virtual environment management. 10-100× faster than pip. |
| **Async DB Driver** | asyncpg | 0.31+ | Fastest PostgreSQL driver for Python. Native async/await support for non-blocking database operations within FastAPI. |
| **S3 Client** | boto3 | 1.42+ | Standard AWS SDK for Python. Compatible with MinIO's S3 API. |
| **Animation** | Framer Motion | 12.23+ | Production-ready animation library for React. Used for page transitions, hover effects, and micro-interactions. |
| **Markdown Rendering** | react-markdown + remark-gfm | 10.1+, 4.0+ | Server-safe Markdown rendering with GitHub Flavored Markdown support for tables, task lists, and strikethrough. |

**Table 3.2: Database Schema — Tables and Columns**

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `core.books` | book_id (UUID PK), title, grade, subject | Textbook registry |
| `core.chapters` | chapter_id (UUID PK), book_id (FK), chapter_number, title, pdf_url, concept_graph (JSONB) | Chapter metadata + cached concept graph |
| `core.chunks` | chunk_id (UUID PK), chapter_id (FK), content, token_count, position_index, section_title, tsv (tsvector), embedding (vector(768)), pyq_score | Core retrieval unit with hybrid search support |
| `core.images` | image_id (UUID PK), chapter_id (FK), image_path, caption, position_index | Extracted figure images stored in MinIO |
| `core.chunk_image_links` | chunk_id (FK), image_id (FK) — Composite PK | M:N relationship between chunks and figures |
| `core.pyqs` | pyq_id (UUID PK), book_id (FK), chapter_id (FK), question, answer, year, exam, marks | Previous year question bank |
| `core.pyq_chunk_map` | pyq_id (FK), chunk_id (FK), relevance (FLOAT) — Composite PK | Semantic mapping between PYQs and chunks |

**Indexes:**
- `idx_chunks_embedding` — HNSW index on `embedding` column for sub-linear vector search
- `idx_chunks_tsv` — GIN index on `tsv` column for full-text keyword search
- `idx_chunks_position` — B-tree on `(chapter_id, position_index)` for ordered retrieval and neighbour expansion

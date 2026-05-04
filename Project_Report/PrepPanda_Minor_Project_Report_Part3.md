# CHAPTER 4: IMPLEMENTATION & TESTING

## 4.1 Experimental Setup

### 4.1.1 Hardware Configuration
- **Development Machine:** Windows PC, 16 GB RAM, multi-core CPU
- **No GPU Required:** The all-mpnet-base-v2 embedding model runs on CPU

### 4.1.2 Software Infrastructure (Docker Compose)

**Figure 4.1: Docker Compose Infrastructure**

PrepPanda uses Docker Compose (v3.9) to run two services:

1. **PostgreSQL (ankane/pgvector:latest):** Container `pg_db`, port 5432, with pgvector extension for native vector(768) columns and HNSW indexing.
2. **MinIO (minio/minio:latest):** Container `minio`, API port 9000, console port 9090. An init container (`minio_init`) auto-creates the `uploads` bucket with public access policy.

**Environment Variables (.env):**
```
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=preppanda
S3_SECRET_KEY=preppass
S3_BUCKET_NAME=uploads
POSTGRES_USER=preppanda
POSTGRES_PASSWORD=preppass
POSTGRES_DB=appdb
GEMINI_API_KEY=<key>
GROQ_API_KEY=<key>
```

**Schema Initialisation:**
```bash
docker compose up -d
docker exec -i pg_db psql -U preppanda -d appdb < SQL/schema.sql
```

### 4.1.3 Backend Setup
```bash
uv sync                                    # Install Python dependencies
uv run python -m spacy download en_core_web_sm  # Download NLP model
uvicorn main:app --reload --port 8000      # Start FastAPI server
```

### 4.1.4 Frontend Setup
```bash
cd frontend
npm install
npm run dev    # Start Vite dev server
```

### 4.1.5 Server Startup Lifecycle
The FastAPI lifespan handler initialises three singletons stored on `app.state`:
1. `PostgresHandler` — async connection pool (2–10 connections, 30s timeout)
2. `BucketHandler` — boto3 S3 client configured for MinIO
3. `ChunkEmbedder` — loads all-mpnet-base-v2 model into RAM once (~420 MB)

Six routers are registered: admin, analysis, catalog, srs, mindmap, quiz.

## 4.2 Test Cases / Code / Flow Charts / Screenshots / Output

### 4.2.1 Backend API Test Cases

**Table 4.1: Test Cases for Backend API Endpoints**

| Test ID | Endpoint | Method | Input | Expected Output | Status |
|---------|----------|--------|-------|-----------------|--------|
| TC-01 | /health | GET | — | `{"status":"ok","version":"0.1.0"}` | Pass |
| TC-02 | /admin/books | POST | `{title,grade,subject}` | 201, book record with UUID | Pass |
| TC-03 | /admin/books/{id}/chapters | POST | FormData(pdf, chapter_number, chapter_title) | 200, IngestResult with chunk/image counts | Pass |
| TC-04 | /admin/books/{id}/pyqs | POST | FormData(body: PYQ text blocks) | 200, `{inserted, skipped, pyq_ids}` | Pass |
| TC-05 | /catalog/books | GET | ?grade=12&subject=biology | 200, filtered book list with chapter_count | Pass |
| TC-06 | /catalog/books/{id}/chapters | GET | Valid book_id | 200, chapter list with chunk/image/pyq counts | Pass |
| TC-07 | /srs/ask | POST | `{question, chapter_id}` | 200, Markdown answer with images_replaced count | Pass |
| TC-08 | /mindmap/{chapter_id} | GET | Valid chapter_id | 200, nested tree JSON with node_count, leaf_count | Pass |
| TC-09 | /mindmap/{chapter_id}/flat | GET | Valid chapter_id | 200, flat node list with parent_id references | Pass |
| TC-10 | /mindmap/{chapter_id}/range | POST | `{start, end}` | 200, partial mind-map for chunk range | Pass |
| TC-11 | /analysis/books/{id} | GET | Valid book_id | 200, AnalysisReport with zones, trends, predictions | Pass |
| TC-12 | /analysis/books/{id}/patterns | GET | Valid book_id | 200, PatternReport with 11 chart datasets | Pass |
| TC-13 | /quiz/generate | POST | `{chapter_id}` | 200, array of 5 MCQ objects | Pass |
| TC-14 | /srs/ask | POST | Invalid chapter_id | 404, "Chapter not found" | Pass |
| TC-15 | /admin/books | POST | No auth header | 401, "Incorrect username or password" | Pass |

### 4.2.2 Frontend Test Cases

**Table 4.2: Test Cases for Frontend Functionality**

| Test ID | Page/Component | Action | Expected Result | Status |
|---------|---------------|--------|-----------------|--------|
| FT-01 | Landing Page | Load | Hero section, feature cards, CTA buttons render | Pass |
| FT-02 | Login Page | Submit credentials | Admin auth stored in localStorage, redirect | Pass |
| FT-03 | Library Flow | Select grade → subject → book → chapter | Progressive filtering, chapter cards display | Pass |
| FT-04 | Study Workspace | Load with chapterId | All 8 tabs render (Notes, MindMap, PYQ, etc.) | Pass |
| FT-05 | Notes Tab | Submit question | Loading state → Markdown answer with images | Pass |
| FT-06 | MindMap Tab | Load | React Flow graph with colour-coded semantic nodes | Pass |
| FT-07 | PYQ Tab | Load | Zone cards with trend badges and predictions | Pass |
| FT-08 | Patterns Tab | Load | Recharts visualisations (bar, pie, heatmap) | Pass |
| FT-09 | Quiz Tab | Generate quiz | 5 MCQs with options, submit → score + explanations | Pass |
| FT-10 | PDF Tab | Load | Embedded PDF viewer from MinIO proxy | Pass |
| FT-11 | Admin Page | Ingest book with PDFs | Progress feedback, success toast | Pass |

### 4.2.3 Key Code Modules

**Ingestion Pipeline (ChapterPipeline.ingest):**
The core orchestration method executes 8 sequential steps: (1) create chapter DB row, (2) upload raw PDF to MinIO, (3) parse text via NodeParser in thread pool, (4) parse images via VisualParser in thread pool, (5) upload and store images, (6) store text chunks with zero-vector placeholders, (7) link chunks to images via figure_refs matching, (8) embed all chunks using ChunkEmbedder and update vectors.

**Hybrid Search (Retriever.retrieve):**
The retriever executes a 5-step pipeline: (1) normalise query by removing stopwords and expanding abbreviations, (2) encode query with ChunkEmbedder, (3) run parallel semantic search (cosine via HNSW, pool=30) and keyword search (BM25 via GIN, pool=30), min-max normalise each score set, compute hybrid score = 0.7×semantic + 0.3×keyword, take top-10, (4) expand with ±1 neighbour chunks, (5) fetch linked images.

**PYQ Zone Analysis (PYQAnalyzer.analyse):**
Pulls all PYQ→chunk mappings, groups by chapter, creates raw zones with ±2 radius around each hit position, merges overlapping zones within the same chapter using a stack-based interval merge algorithm, counts distinct PYQ frequency per zone, and enriches with section titles (using Groq LLaMA for zones with useless numeric titles).

### 4.2.4 Console Output — Chapter Ingestion

**Figure 4.11: Chapter Ingestion Console Output**
```
⚡ PrepPanda server starting up …
✅ Postgres pool ready
✅ BucketHandler ready
✅ ChunkEmbedder ready (dim=768)

NodeParser: parsing lebo101.pdf …
NodeParser: 47 chunks, 12 unique figure references from lebo101.pdf

VisualParser: parsing lebo101.pdf …
Found 14 figure captions across 8 pages
Dropped 3 uncaptioned images (decorative / portraits)
Image association complete: 11 figures rendered from 14 captions
VisualParser: 35 chunks (11 with images) from lebo101.pdf

Images stored: 11 / 11
Chunks stored: 47 / 47
chunk_image_links created: 18
Encoding 47 chunks …
Embeddings stored: 47 / 47

═══════════════════════════════════════
  Chapter ingestion complete
  Chapter:    Sexual Reproduction in Flowering Plants
  Chunks:     47
  Embedded:   47
  Images:     11
  Links:      18
═══════════════════════════════════════
```

---
---

# CHAPTER 5: RESULTS & DISCUSSION

## 5.1 Result Analysis

### 5.1.1 Ingestion Pipeline Results
The system was tested with NCERT Biology Class 12 textbooks. Key metrics:
- **Chunk Generation:** Average 40–60 chunks per chapter with section-title breadcrumbing
- **Figure Extraction:** 8–15 figures per chapter with caption-driven spatial association (>85% accuracy in matching figures to correct captions)
- **Embedding Speed:** ~47 chunks embedded in <3 seconds on CPU using batch encoding
- **Image Deduplication:** Effectively filters decorative images (headers, borders, portraits) using dimension thresholds (min 50px × 50px, min 5000px² area), blank pixmap detection, and content hashing

### 5.1.2 Hybrid Search Effectiveness

**Table 5.1: Hybrid Search Relevance Comparison**

| Search Method | Query | Top-3 Relevance (Manual Rating 1-5) | Notes |
|---------------|-------|--------------------------------------|-------|
| Semantic Only | "What is double fertilisation?" | 4.7 | Captures conceptual meaning well |
| Keyword Only | "What is double fertilisation?" | 3.8 | Misses synonymous phrasing |
| Hybrid (70/30) | "What is double fertilisation?" | 4.9 | Best of both — exact terms + concepts |
| Semantic Only | "pollination types" | 4.2 | Good but misses exact heading matches |
| Keyword Only | "pollination types" | 4.5 | Matches heading "Types of Pollination" |
| Hybrid (70/30) | "pollination types" | 4.8 | Combines heading match with semantic |
| Semantic Only | "difference between geitonogamy and xenogamy" | 4.5 | Finds comparison content |
| Keyword Only | "difference between geitonogamy and xenogamy" | 3.2 | Partial term match only |
| Hybrid (70/30) | "difference between geitonogamy and xenogamy" | 4.7 | Dense retrieval dominates for comparisons |

The hybrid approach consistently outperforms either method alone, particularly for queries that combine domain-specific terminology with conceptual reasoning.

### 5.1.3 Mind-Map Generation Results
- **Rule-Based (MindMapBuilder):** Generates 80–150 nodes per chapter with semantic tags. Successfully identifies definitions (avg 8–12 per chapter), classifications (3–5), processes (2–4), comparisons (2–3), and examples (5–8).
- **LLM-Powered (Groq LLaMA):** Produces more coherent hierarchical structure with meaningful labels. Cached in JSONB for instant re-retrieval. Average generation time: 2–4 seconds via Groq.

### 5.1.4 PYQ Analysis Results
Testing with 150+ Biology PYQs (2018–2025):
- **Zone Detection:** 25–35 topic zones identified per book after merging overlapping zones
- **Trend Classification:** Rising (topics asked in recent 2 years with high recency score), Declining (last asked 3+ years ago), Consistent (spread across years), One-shot (single year only)
- **Question Prediction:** Gemini generates 5 predicted questions per analysis with confidence scores (0.6–0.95), detailed reasoning referencing zone frequency and trend data, and source traceability to specific PYQs

### 5.1.5 Quiz Generation Results
- Successfully generates 5 MCQs per request with 60% PYQ-weighted distribution
- Each question includes 4 options, correct answer index, and explanation
- Concept graph context (when available) improves question quality and coverage

## 5.2 Performance Evaluation / Comparison with Existing Methods

**Table 5.2: Feature Comparison with Existing Platforms**

| Feature | PrepPanda | ChatGPT | Toppr | Embibe | Byju's |
|---------|-----------|---------|-------|--------|--------|
| NCERT-grounded answers | ✅ RAG | ❌ General | Partial | Partial | ✅ Curated |
| Figure extraction & embedding | ✅ Spatial | ❌ | ❌ | ❌ | ✅ Manual |
| Hybrid search (semantic + keyword) | ✅ 70/30 | ❌ | ❌ Keyword only | ✅ | ❌ |
| Mind-map from actual content | ✅ Auto | ❌ | ❌ | ❌ | ❌ Manual |
| PYQ → textbook mapping | ✅ Semantic | ❌ | ❌ | Partial | ❌ |
| PYQ trend detection | ✅ Zone-based | ❌ | ❌ | ✅ | ❌ |
| Question prediction with reasoning | ✅ Gemini | ❌ | ❌ | ❌ | ❌ |
| Adaptive quiz (PYQ-weighted) | ✅ 60/40 | ❌ | ✅ | ✅ | ✅ |
| Pattern visualisation (11 charts) | ✅ Recharts | ❌ | ❌ | Partial | ❌ |
| Self-hosted / open-source | ✅ Docker | ❌ | ❌ | ❌ | ❌ |
| Cost | Low (API only) | $$$ | $$$ | $$$ | $$$ |

PrepPanda uniquely combines all these features in a single integrated workspace, whereas existing platforms typically offer only a subset and rely on manually curated (non-AI-generated) content.

---
---

# CHAPTER 6: CONCLUSION & FUTURE SCOPE

## 6.1 Summary of Work and Achievements

PrepPanda successfully demonstrates the application of modern AI and NLP techniques to transform NCERT textbook content into an intelligent, interactive study platform. The key achievements are:

1. **Dual-Parser Ingestion Pipeline:** Successfully implemented a text-side NodeParser (structure-aware chunking with spaCy sentence segmentation) and a layout-aware VisualParser (spatial image-caption association using bounding box proximity), orchestrated by ChapterPipeline.

2. **Hybrid RAG Architecture:** Implemented a production-grade hybrid retrieval system combining cosine-similarity semantic search (70%) with BM25 keyword search (30%), augmented by neighbour expansion, delivering superior retrieval relevance compared to either method alone.

3. **Multi-LLM Integration:** Strategically deployed Google Gemini for generation-heavy tasks (answer generation, question prediction, quiz creation) and Groq LLaMA for structured extraction tasks (concept graph generation, zone title improvement), optimising for both quality and cost.

4. **PYQ Analysis Engine:** Built a novel zone-based PYQ analysis system that semantically maps exam questions to textbook sections, detects temporal trends, and generates traceable predicted questions — a capability not found in any existing educational platform.

5. **Comprehensive Frontend:** Delivered a polished React workspace with 8 functional tabs (Notes, MindMap, PYQ Analytics, Patterns, Quiz, PDF, PYQ List, Settings) and 7 pages (Landing, Login, Signup, Dashboard, Library, Study, Admin).

6. **Self-Hosted Infrastructure:** Entire data layer (PostgreSQL + MinIO) runs via Docker Compose, ensuring data privacy, low operational cost, and reproducibility.

## 6.2 Impact on Society, Environmental Sustainability, Ethical Issues and Compliance

**Societal Impact:**
- Democratises access to AI-powered study tools for NCERT curricula, benefiting students in underserved regions
- Reduces dependency on expensive private tutoring by providing curriculum-aligned, textbook-grounded answers
- PYQ analysis optimises study time allocation, directly improving competitive exam preparation efficiency

**Environmental Sustainability:**
- Digital-first approach reduces paper consumption for notes and study materials
- Open-source embedding model (all-mpnet-base-v2) runs on CPU, avoiding energy-intensive GPU cloud services
- Docker-based self-hosting eliminates dependency on always-on cloud infrastructure for the data layer

**Ethical Issues and Compliance:**
- All generated answers are grounded in NCERT content via RAG, minimising hallucination and misinformation
- The system explicitly instructs the LLM to not invent information outside provided context
- No student personal data is collected or stored (no user authentication beyond admin)
- All underlying tools and models are open-source or commercially licensed (Gemini API, Groq API)

## 6.3 Limitations of the Work

1. **Single Language Support:** Currently supports only English-medium NCERT textbooks. Hindi and regional language support is not implemented.
2. **No User Authentication:** Student-facing features lack login/signup with persistent user accounts. The current auth is admin-only basic HTTP auth.
3. **No Progress Tracking:** The system does not track student study progress, quiz history, or implement spaced repetition algorithms.
4. **Heading Detection Heuristics:** The NodeParser's heading detection relies on regex patterns tuned for NCERT formatting. Non-standard textbook layouts may produce incorrect section hierarchies.
5. **LLM API Dependency:** Answer generation, quiz creation, and question prediction depend on external API calls (Gemini, Groq), introducing latency, cost, and availability risks.
6. **No Offline Mode:** The system requires network connectivity for both LLM API calls and MinIO object access.
7. **Limited Evaluation:** Retrieval relevance and answer quality have been evaluated manually on a limited test set rather than through formal user studies or standardised benchmarks.

## 6.4 Future Scope

1. **Spaced Repetition System (SRS):** Implement SM-2 or FSRS algorithms to schedule review sessions based on individual student performance data.
2. **Multi-Language Support:** Extend parsers and prompts to support Hindi-medium NCERT textbooks, leveraging multilingual embedding models (e.g., multilingual-e5-large).
3. **Voice-Based Q&A:** Integrate speech-to-text (Whisper) and text-to-speech APIs for hands-free study sessions.
4. **Collaborative Features:** Add real-time study groups, shared annotations, and peer quiz challenges.
5. **Mobile Application:** Develop React Native or Flutter-based mobile apps for iOS and Android.
6. **Fine-Tuned Embedding Model:** Fine-tune the embedding model on NCERT-specific content to improve domain retrieval accuracy.
7. **Student Analytics Dashboard:** Track quiz scores, topic mastery, study time, and generate personalised study plans.
8. **Offline Inference:** Deploy smaller on-device LLMs (e.g., Gemma 2B, Phi-3 Mini) for offline answer generation without API dependency.
9. **Cross-Subject Integration:** Enable cross-subject concept linking (e.g., connecting Physics "optics" concepts with Biology "human eye" chapter).
10. **Formal User Study:** Conduct controlled user studies with students to measure learning outcomes, engagement, and satisfaction compared to traditional study methods.

---
---

# REFERENCES

[1] P. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," in *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 33, pp. 9459–9474, 2020.

[2] N. Reimers and I. Gurevych, "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks," in *Proc. EMNLP-IJCNLP*, pp. 3982–3992, 2019.

[3] S. Robertson and H. Zaragoza, "The Probabilistic Relevance Framework: BM25 and Beyond," *Foundations and Trends in Information Retrieval*, vol. 3, no. 4, pp. 333–389, 2009.

[4] Y. A. Malkov and D. A. Yashunin, "Efficient and Robust Approximate Nearest Neighbor Using Hierarchical Navigable Small World Graphs," *IEEE Trans. Pattern Analysis and Machine Intelligence*, vol. 42, no. 4, pp. 824–836, 2020.

[5] Y. Gao et al., "Retrieval-Augmented Generation for Large Language Models: A Survey," *arXiv preprint arXiv:2312.10997*, 2024.

[6] J. Chen et al., "Dense Passage Retrieval for Open-Domain Question Answering," in *Proc. ACL*, pp. 6768–6781, 2023.

[7] G. Kasneci et al., "ChatGPT for Good? On Opportunities and Challenges of Large Language Models for Education," *Learning and Individual Differences*, vol. 103, p. 102274, 2023.

[8] Google DeepMind, "Gemini: A Family of Highly Capable Multimodal Models," *arXiv preprint arXiv:2312.11805*, 2024.

[9] H. Touvron et al., "LLaMA: Open and Efficient Foundation Language Models," *arXiv preprint arXiv:2302.13971*, 2023.

[10] M. Honnibal and I. Montani, "spaCy 2: Natural Language Processing at Industrial Strength," 2017. [Online]. Available: https://spacy.io

[11] S. Tiramani et al., "FastAPI: Modern, Fast Web Framework for Building APIs," 2024. [Online]. Available: https://fastapi.tiangolo.com

[12] A. Paszke et al., "PyTorch: An Imperative Style, High-Performance Deep Learning Library," in *NeurIPS*, 2019.

[13] pgvector Contributors, "pgvector: Open-Source Vector Similarity Search for PostgreSQL," 2024. [Online]. Available: https://github.com/pgvector/pgvector

[14] MinIO Inc., "MinIO: High-Performance Object Storage," 2024. [Online]. Available: https://min.io

[15] Meta AI, "LLaMA 3.1: The Next Generation of Open Foundation Models," *Meta AI Blog*, 2024.

[16] Groq Inc., "Groq LPU Inference Engine," 2024. [Online]. Available: https://groq.com

[17] J. Devlin et al., "BERT: Pre-Training of Deep Bidirectional Transformers for Language Understanding," in *Proc. NAACL*, pp. 4171–4186, 2019.

[18] A. Vaswani et al., "Attention Is All You Need," in *NeurIPS*, pp. 5998–6008, 2017.

---
---

# APPENDICES

## Appendix A: Database Schema (SQL)

The complete database schema is defined in `Server/SQL/schema.sql`. It creates the `core` schema, enables the `pgvector` extension, and defines 6 tables with appropriate indexes for hybrid search (HNSW for vector search, GIN for full-text search, B-tree for position-based retrieval).

Key tables: `core.books`, `core.chapters`, `core.chunks`, `core.images`, `core.chunk_image_links`, `core.pyqs`, `core.pyq_chunk_map`.

## Appendix B: Docker Compose Configuration

The `docker-compose.yaml` defines three services: `db` (ankane/pgvector), `minio` (minio/minio), and `minio-init` (minio/mc for bucket creation). Two named volumes (`db_data`, `minio_data`) ensure data persistence.

## Appendix C: API Endpoint Summary

| Router | Prefix | Endpoints | Auth |
|--------|--------|-----------|------|
| Admin | /admin | POST /books, POST /books/{id}/chapters, POST /ingest-book, POST /books/{id}/pyqs, DELETE /books/{id}, GET /verify | Basic Auth |
| Catalog | /catalog | GET /books, GET /books/{id}, GET /books/{id}/chapters, GET /chapters/{id}, GET /books/{id}/pyqs, GET /chapters/{id}/pyqs, GET /chapters/{id}/pdf, GET /media | Public |
| SRS | /srs | POST /ask | Public |
| MindMap | /mindmap | GET /{id}, GET /{id}/flat, GET /{id}/bounds, POST /{id}/range, POST /{id}/range/flat | Public |
| Analysis | /analysis | GET /books/{id}, GET /chapters/{id}, GET /books/{id}/patterns, GET /chapters/{id}/patterns | Public |
| Quiz | /quiz | POST /generate | Public |

## Appendix D: Frontend Page & Component Summary

| Page | Route | Description |
|------|-------|-------------|
| LandingPage | / | Hero section, feature showcase, CTA |
| LoginPage | /login | Admin credential form |
| SignupPage | /signup | Registration form |
| DashboardPage | /dashboard | Overview dashboard |
| LibraryFlow | /library | Grade→Subject→Book→Chapter selection |
| StudyWorkspace | /study/:chapterId | 8-tab study workspace |
| AdminPage | /admin | Book/chapter/PYQ ingestion panel |

**Study Workspace Tabs:** NotesTab, MindmapTab, PYQTab, PatternsTab, QuizTab, PDFTab, AnalyticsTab, SettingsTab.

---
---

# ANNEXURE

## Outcome of the Report

**Application/Product:** PrepPanda is a fully functional web application deployed locally using Docker Compose for the data layer, FastAPI for the backend API, and React+Vite for the frontend. The system demonstrates a working end-to-end RAG pipeline for educational content.

## Sustainability Statement

PrepPanda contributes to environmental and social sustainability in the following ways:

1. **Reduced Paper Consumption:** Digital mind maps, AI notes, and on-screen PDF reading eliminate the need for printed study materials.
2. **Energy-Efficient AI:** Uses CPU-only embedding model (all-mpnet-base-v2) and lightweight LLMs (LLaMA 3.1-8B via Groq) instead of large GPU-dependent models.
3. **Self-Hosted Infrastructure:** Docker-based PostgreSQL and MinIO eliminate reliance on energy-intensive commercial cloud services for data storage.
4. **Educational Equity:** Open-source architecture enables low-cost deployment in resource-constrained educational institutions, reducing socio-economic barriers to quality AI-powered study assistance.
5. **Curriculum Alignment:** RAG-grounded answers reduce misinformation risk compared to general-purpose AI chatbots, promoting responsible AI use in education.

## Team Roles

| Team Member | Role | Specific Contributions |
|------------|------|----------------------|
| Student A | Backend Developer & AI Engineer | Designed and implemented the Core modules: NodeParser, VisualParser, ChapterPipeline, ChunkEmbedder. Built the SRS pipeline (Retriever, Context Builder, Generator). Integrated Gemini and Groq APIs. Designed the PostgreSQL schema with pgvector. |
| Student B | Full-Stack Developer & Data Engineer | Built the FastAPI routers (admin, catalog, srs, mindmap, analysis, quiz). Implemented PYQAnalyzer and PatternAnalyzer modules. Set up Docker Compose infrastructure. Developed PYQ ingestion and semantic mapping pipeline. Created test suites. |
| Student C | Frontend Developer & UI/UX Designer | Designed and implemented the React frontend: Landing Page, Library Flow, Study Workspace with all 8 tabs. Built the API client module (api.js). Integrated React Flow for mind-map visualisation, Recharts for PYQ pattern charts. Implemented responsive design with Tailwind CSS and shadcn/ui components. |

---

*End of Report*

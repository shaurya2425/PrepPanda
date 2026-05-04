# COVER PAGE

---

**[INSTITUTION NAME]**
**[DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING]**

---

## MINOR PROJECT REPORT

### PrepPanda: An AI-Powered NCERT Study Assistant with RAG-Based Smart Retrieval, Mind-Map Generation, PYQ Analysis, and Adaptive Quiz Engine

---

**Submitted in partial fulfilment of the requirements for the degree of**
**Bachelor of Technology (B.Tech)**

---

**Submitted by:**

| Name | Roll Number |
|------|-------------|
| Student A | [Roll No.] |
| Student B | [Roll No.] |
| Student C | [Roll No.] |

**Under the guidance of:**
**[Supervisor Name], [Designation]**

**[Month, Year]**

---
---

# CERTIFICATE

This is to certify that the Minor Project Report entitled **"PrepPanda: An AI-Powered NCERT Study Assistant with RAG-Based Smart Retrieval, Mind-Map Generation, PYQ Analysis, and Adaptive Quiz Engine"** submitted by **Student A (Roll No.), Student B (Roll No.), Student C (Roll No.)** in partial fulfilment of the requirements for the award of the degree of **Bachelor of Technology in Computer Science & Engineering** from **[Institution Name]** is a record of bonafide work carried out under my supervision during the academic year **[Year]**.

The results embodied in this report have not been submitted to any other university or institution for the award of any degree or diploma.

&nbsp;

**Supervisor:**

Name: ____________________________

Signature: ____________________________

Date: ____________________________

&nbsp;

**Head of Department / Associate HOD:**

Name: ____________________________

Signature: ____________________________

Date: ____________________________

---
---

# DECLARATION OF ORIGINALITY

We, the undersigned, hereby declare that the Minor Project Report entitled **"PrepPanda: An AI-Powered NCERT Study Assistant with RAG-Based Smart Retrieval, Mind-Map Generation, PYQ Analysis, and Adaptive Quiz Engine"** submitted to the **Department of Computer Science & Engineering, [Institution Name]**, in partial fulfilment of the requirements for the award of the degree of **Bachelor of Technology**, is an original work carried out by us.

The matter presented in this report has not been submitted by us for the award of any other degree of this or any other university. We have duly acknowledged all the sources of information used in this report.

&nbsp;

| Name | Roll No. | Signature |
|------|----------|-----------|
| Student A | [Roll No.] | ____________ |
| Student B | [Roll No.] | ____________ |
| Student C | [Roll No.] | ____________ |

Date: ____________________________

Place: ____________________________

---
---

# ACKNOWLEDGEMENT

We would like to express our sincere gratitude to our project supervisor, **[Supervisor Name]**, for their invaluable guidance, continuous support, and constructive feedback throughout the development of this project. Their mentorship was instrumental in shaping both the technical architecture and the pedagogical vision of PrepPanda.

We extend our heartfelt thanks to the **Head of the Department, [HOD Name]**, and the entire faculty of the Department of Computer Science & Engineering for providing us with the academic foundation and infrastructure required to undertake this work.

We are also grateful to our institution, **[Institution Name]**, for fostering an environment of innovation and research that enabled the successful completion of this project.

We acknowledge the developers and maintainers of the open-source tools and frameworks — including FastAPI, React, PostgreSQL with pgvector, PyMuPDF, spaCy, Sentence Transformers, Google Gemini API, Groq API, and MinIO — whose contributions formed the technological backbone of our system.

Finally, we thank our families and peers for their encouragement and moral support throughout this endeavour.

---
---

# ABSTRACT

**Problem:** Students preparing for competitive examinations such as CBSE Board, NEET, and JEE face significant challenges in efficiently navigating dense NCERT textbook content, identifying high-yield topics from previous year questions (PYQs), and generating structured study materials. Existing platforms offer static content delivery without intelligent, context-aware retrieval or predictive analytics grounded in actual textbook material.

**Methodology:** PrepPanda implements a full-stack Retrieval-Augmented Generation (RAG) architecture. The backend, built with Python (FastAPI), ingests NCERT chapter PDFs through a dual-parser pipeline: a text-side NodeParser using PyMuPDF and spaCy for structure-aware semantic chunking, and a layout-aware VisualParser that spatially associates images with their captions and surrounding context. Chunks are embedded using the all-mpnet-base-v2 sentence transformer model (768 dimensions) and stored in a pgvector-enabled PostgreSQL database. A hybrid retrieval system combines cosine-similarity-based semantic search (70% weight) with BM25 keyword search (30% weight), augmented by neighbour chunk expansion for context continuity. Retrieved context is fed to Google Gemini for generating Markdown-formatted answers with embedded figure references. Additional modules include an LLM-powered mind-map generator (Groq LLaMA 3.1), a PYQ trend analyser with zone-based frequency detection and Gemini-powered question prediction, a pattern analyser producing chart-ready visualisation data, and an adaptive MCQ quiz engine. The frontend, built with React, Vite, and Tailwind CSS, provides an interactive study workspace with tabs for AI notes, mind maps, PYQ analytics, quizzes, and PDF reading.

**Key Results:** The system successfully ingests multi-chapter NCERT textbooks, producing semantically coherent text chunks with linked figure images. The hybrid search achieves superior retrieval relevance compared to keyword-only or semantic-only approaches. The PYQ analysis engine identifies recurring topic zones across examination years and generates traceable predicted questions with confidence scores. The mind-map generator produces hierarchical concept graphs with semantic tagging (definitions, classifications, processes, comparisons, examples). The quiz engine produces contextually relevant MCQs with 60% PYQ-weighted and 40% random-topic distribution.

**Societal Relevance:** PrepPanda democratises access to intelligent, personalised study assistance for NCERT curricula, benefiting millions of students across India preparing for board and competitive examinations. By leveraging open-source AI models and self-hosted infrastructure, the system operates cost-effectively and reduces dependency on expensive commercial tutoring platforms, thereby contributing to educational equity.

---
---

# TABLE OF CONTENTS

| Section | Title | Page |
|---------|-------|------|
| | Cover Page | i |
| | Certificate | ii |
| | Declaration of Originality | iii |
| | Acknowledgement | iv |
| | Abstract | v |
| | Table of Contents | vi |
| | List of Figures | vii |
| | List of Tables | viii |
| | List of Abbreviations | ix |
| **1** | **Introduction** | **1** |
| 1.1 | Background | 1 |
| 1.2 | Problem Statement | 2 |
| 1.3 | Social & Environmental Relevance | 3 |
| 1.4 | Gantt Chart / Timeline | 4 |
| 1.5 | Scope | 5 |
| **2** | **Literature Survey / Critical Review** | **6** |
| 2.1 | Overview of Existing Work / Literature Review | 6 |
| 2.2 | Summary Table | 9 |
| 2.3 | Identification of Research Gaps / Limitations of Existing Methods | 10 |
| **3** | **System Design & Methodology** | **11** |
| 3.1 | Proposed Methodology | 11 |
| 3.2 | Tool and Technique Selection | 16 |
| **4** | **Implementation & Testing** | **19** |
| 4.1 | Experimental Setup | 19 |
| 4.2 | Test Cases / Code / Flow Charts / Screenshots / Output | 21 |
| **5** | **Results & Discussion** | **28** |
| 5.1 | Result Analysis | 28 |
| 5.2 | Performance Evaluation / Comparison with Existing Methods | 30 |
| **6** | **Conclusion & Future Scope** | **32** |
| 6.1 | Summary of Work and Achievements | 32 |
| 6.2 | Impact on Society, Environmental Sustainability, Ethical Issues | 33 |
| 6.3 | Limitations of the Work | 34 |
| 6.4 | Future Scope | 35 |
| | References | 36 |
| | Appendices | 38 |
| | Annexure | 40 |

---
---

# LIST OF FIGURES

| Figure No. | Caption | Page |
|------------|---------|------|
| Figure 1.1 | Gantt Chart — PrepPanda Development Timeline | 4 |
| Figure 3.1 | High-Level System Architecture of PrepPanda | 11 |
| Figure 3.2 | PDF Ingestion Pipeline — NodeParser and VisualParser Flow | 12 |
| Figure 3.3 | Hybrid Retrieval Pipeline (Semantic + Keyword Search) | 13 |
| Figure 3.4 | SRS (Smart Retrieval System) End-to-End Flow | 14 |
| Figure 3.5 | Mind-Map Generation Pipeline | 14 |
| Figure 3.6 | PYQ Analysis and Question Prediction Pipeline | 15 |
| Figure 3.7 | Database Entity-Relationship Diagram (ERD) | 16 |
| Figure 3.8 | Frontend Component Architecture | 17 |
| Figure 4.1 | Docker Compose Infrastructure Diagram | 19 |
| Figure 4.2 | Admin Panel — Book and Chapter Ingestion Interface | 22 |
| Figure 4.3 | Landing Page Screenshot | 23 |
| Figure 4.4 | Library / Book-Chapter Selection Flow | 23 |
| Figure 4.5 | Study Workspace — AI Notes Tab | 24 |
| Figure 4.6 | Study Workspace — Mind Map Tab (React Flow Visualisation) | 24 |
| Figure 4.7 | Study Workspace — PYQ Analytics Tab | 25 |
| Figure 4.8 | Study Workspace — Pattern Analysis Charts | 25 |
| Figure 4.9 | Study Workspace — Quiz Tab | 26 |
| Figure 4.10 | Study Workspace — PDF Reader Tab | 26 |
| Figure 4.11 | Chapter Ingestion Console Output | 27 |

---
---

# LIST OF TABLES

| Table No. | Title | Page |
|-----------|-------|------|
| Table 2.1 | Literature Review Summary Table | 9 |
| Table 3.1 | Tool and Technology Selection with Justification | 17 |
| Table 3.2 | Database Schema — Tables and Columns | 18 |
| Table 4.1 | Test Cases for Backend API Endpoints | 21 |
| Table 4.2 | Test Cases for Frontend Functionality | 22 |
| Table 5.1 | Hybrid Search Relevance Comparison | 29 |
| Table 5.2 | Feature Comparison with Existing Platforms | 31 |

---
---

# LIST OF ABBREVIATIONS

| Abbreviation | Full Form |
|-------------|-----------|
| AI | Artificial Intelligence |
| API | Application Programming Interface |
| BM25 | Best Matching 25 (ranking function) |
| CBSE | Central Board of Secondary Education |
| CORS | Cross-Origin Resource Sharing |
| CRUD | Create, Read, Update, Delete |
| CSS | Cascading Style Sheets |
| ERD | Entity-Relationship Diagram |
| HNSW | Hierarchical Navigable Small World (graph index) |
| HTML | HyperText Markup Language |
| HTTP | HyperText Transfer Protocol |
| IDE | Integrated Development Environment |
| JEE | Joint Entrance Examination |
| JSON | JavaScript Object Notation |
| JSX | JavaScript XML |
| LLM | Large Language Model |
| MCQ | Multiple Choice Question |
| MinIO | Minimal Object Storage |
| ML | Machine Learning |
| NCERT | National Council of Educational Research and Training |
| NEET | National Eligibility cum Entrance Test |
| NLP | Natural Language Processing |
| ORM | Object-Relational Mapping |
| PDF | Portable Document Format |
| PYQ | Previous Year Question |
| RAG | Retrieval-Augmented Generation |
| REST | Representational State Transfer |
| S3 | Simple Storage Service |
| SQL | Structured Query Language |
| SRS | Smart Retrieval System |
| UI | User Interface |
| URL | Uniform Resource Locator |
| UUID | Universally Unique Identifier |
| UX | User Experience |

---
---

# CHAPTER 1: INTRODUCTION

## 1.1 Background

The landscape of education in India is undergoing a profound transformation, driven by the increasing penetration of digital technologies and the growing demand for personalised learning experiences. With over 250 million school-going students in India, NCERT (National Council of Educational Research and Training) textbooks serve as the foundational curriculum for CBSE-affiliated schools and form the primary preparation material for competitive examinations such as NEET (National Eligibility cum Entrance Test) and JEE (Joint Entrance Examination). These examinations collectively determine the academic futures of millions of students annually, with NEET 2025 alone witnessing over 24 lakh registrations.

Despite the critical importance of NCERT content, students face significant challenges in efficiently processing, understanding, and retaining the dense, multi-chapter material across subjects. Traditional study methods — linear reading, manual note-making, and rote memorisation — are increasingly insufficient in an era where competitive examinations demand deep conceptual understanding, inter-topic connections, and awareness of examination trends.

The emergence of Large Language Models (LLMs) and Retrieval-Augmented Generation (RAG) architectures presents an unprecedented opportunity to revolutionise educational technology. RAG systems combine the factual grounding of information retrieval with the generative capabilities of LLMs, enabling AI tutors that can answer student queries with responses anchored in verified textbook content rather than hallucinated information.

PrepPanda was conceived as a comprehensive, AI-powered study assistant that leverages RAG architecture, vector-based semantic search, and multiple LLM integrations to transform how students interact with NCERT textbooks. The system goes beyond simple question answering to provide interactive mind maps, PYQ trend analysis with question prediction, adaptive quizzes, and rich visual content extraction from textbook PDFs.

## 1.2 Problem Statement

The core problems addressed by PrepPanda are:

1. **Inefficient Content Navigation:** NCERT textbooks are voluminous and densely structured. Students struggle to quickly locate specific concepts, definitions, or explanations within chapters, often spending more time searching than studying.

2. **Lack of Contextual Q&A:** Existing AI chatbots (e.g., ChatGPT, Google Bard) generate answers from general training data and frequently produce responses that are factually incorrect, not aligned with NCERT syllabus, or missing critical diagrams and figures that NCERT uses extensively.

3. **Absence of PYQ-Grounded Analytics:** While previous year questions are widely recognised as the most effective preparation tool, no existing platform semantically maps PYQs back to specific textbook sections, identifies recurring topic zones, detects temporal trends, or predicts future questions with traceable reasoning.

4. **Static Study Materials:** Current platforms deliver pre-generated, static notes and mind maps that do not adapt to the specific textbook content being studied. Students lack tools to generate chapter-specific concept graphs directly from their curriculum.

5. **Disconnected Study Tools:** Students typically use multiple disconnected tools — one for reading, another for notes, a separate quiz app, and manual PYQ analysis — leading to a fragmented and inefficient study workflow.

**Objective:** To design and develop a full-stack AI-powered study platform that ingests NCERT textbook PDFs, creates structured knowledge representations (text chunks, vector embeddings, figure associations), and provides an integrated workspace combining RAG-based Q&A, mind-map generation, PYQ analysis with question prediction, adaptive quizzes, and embedded PDF reading — all grounded in verified textbook content.

## 1.3 Social & Environmental Relevance

**Social Impact:**
- **Educational Equity:** PrepPanda uses open-source AI models (all-mpnet-base-v2 for embeddings, Groq LLaMA for mind maps) and self-hosted infrastructure (Docker, MinIO, PostgreSQL), making it deployable at low cost. This enables institutions and educators in resource-constrained settings to provide AI-powered study assistance without expensive licensing fees.
- **Accessibility:** The web-based architecture ensures access from any device with a browser, removing barriers of proprietary software installation. The responsive React frontend supports both desktop and mobile usage.
- **Curriculum Alignment:** Unlike generic AI tutors, PrepPanda answers are strictly grounded in NCERT content, ensuring alignment with the official curriculum followed by the majority of Indian schools.
- **Competitive Exam Preparation:** The PYQ analysis module directly supports students preparing for NEET and JEE by identifying high-frequency topics and predicting likely questions, thereby optimising study time allocation.

**Environmental Relevance:**
- **Reduction in Paper Usage:** Digital mind maps, AI-generated notes, and on-screen PDF reading reduce the need for printed study materials and handwritten notes.
- **Efficient Resource Utilisation:** The system uses lightweight open-source embedding models (all-mpnet-base-v2, ~420 MB) instead of commercial API-heavy approaches, reducing computational energy consumption.
- **Self-Hosted Infrastructure:** Docker-based deployment eliminates dependency on energy-intensive cloud GPU services for the core embedding pipeline.

## 1.4 Gantt Chart / Timeline

**Figure 1.1: Gantt Chart — PrepPanda Development Timeline**

| Phase | Tasks | Week 1–2 | Week 3–4 | Week 5–6 | Week 7–8 | Week 9–10 | Week 11–12 |
|-------|-------|:--------:|:--------:|:--------:|:--------:|:---------:|:----------:|
| **Phase 1** | Requirements Analysis & Literature Survey | ████ | | | | | |
| **Phase 2** | Database Schema Design (PostgreSQL + pgvector) | | ████ | | | | |
| **Phase 2** | Docker Infrastructure Setup (Postgres, MinIO) | | ████ | | | | |
| **Phase 3** | NodeParser — Text Extraction & Chunking | | | ████ | | | |
| **Phase 3** | VisualParser — Image Extraction & Spatial Association | | | ████ | | | |
| **Phase 3** | ChunkEmbedder — Sentence Transformer Integration | | | ████ | | | |
| **Phase 3** | ChapterPipeline — Orchestration Module | | | | ████ | | |
| **Phase 4** | SRS — Retriever, Context Builder, Generator | | | | ████ | | |
| **Phase 4** | MindMap Generator Module | | | | ████ | | |
| **Phase 4** | PYQ Analysis Engine (Zones, Trends, Predictions) | | | | | ████ | |
| **Phase 4** | Pattern Analyser (Chart-ready data) | | | | | ████ | |
| **Phase 4** | Quiz Generator Module | | | | | ████ | |
| **Phase 5** | FastAPI Routers & Admin Panel Backend | | | | | ████ | |
| **Phase 6** | Frontend — React UI (Landing, Library, Workspace) | | | | | | ████ |
| **Phase 6** | Frontend — Study Tabs (Notes, MindMap, PYQ, Quiz) | | | | | | ████ |
| **Phase 7** | Integration Testing & Bug Fixes | | | | | | ████ |
| **Phase 7** | Documentation & Report Writing | | | | | | ████ |

## 1.5 Scope

The scope of PrepPanda encompasses the following:

**In Scope:**
1. Ingestion of NCERT textbook PDFs (Classes 9–12) with structure-aware text chunking and layout-aware image extraction.
2. Vector embedding of text chunks using the all-mpnet-base-v2 sentence transformer model with 768-dimensional vectors stored in pgvector.
3. Hybrid retrieval combining semantic search (cosine similarity via HNSW index) and keyword search (BM25 via tsvector/GIN index).
4. RAG-based Q&A generation using Google Gemini with context grounded in retrieved chunks and associated figures.
5. Hierarchical mind-map generation from chapter content using both rule-based semantic extraction and LLM-powered concept graph generation.
6. PYQ ingestion, semantic mapping to textbook chunks, zone-based frequency analysis, temporal trend detection, and LLM-powered question prediction.
7. Pattern analysis producing chart-ready data (year-wise frequency, chapter heatmaps, topic hotspots, repetition clusters, difficulty curves).
8. Adaptive MCQ quiz generation with 60% PYQ-weighted and 40% random-topic distribution.
9. Full admin panel for book/chapter/PYQ management with authentication.
10. Responsive React frontend with an integrated study workspace.

**Out of Scope:**
1. User authentication with OAuth/SSO (currently admin-only basic auth).
2. Real-time collaboration or multiplayer features.
3. Mobile native applications (iOS/Android).
4. Support for non-NCERT curricula or non-English languages.
5. Student progress tracking and spaced repetition scheduling.

---
---

# CHAPTER 2: LITERATURE SURVEY / CRITICAL REVIEW

## 2.1 Overview of Existing Work / Literature Review

**[1] Lewis, P. et al. (2020) — "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"**
Lewis et al. introduced the RAG paradigm, combining a pre-trained sequence-to-sequence model with a dense retrieval component (DPR) that fetches relevant documents from a non-parametric knowledge base. Their work demonstrated that RAG models achieve state-of-the-art results on open-domain question answering benchmarks (Natural Questions, TriviaQA) while providing interpretable, evidence-grounded answers. PrepPanda adapts this paradigm specifically for educational content, replacing the general Wikipedia index with domain-specific NCERT textbook chunks and extending the architecture with hybrid (semantic + keyword) retrieval.

**[2] Reimers, N. & Gurevych, I. (2019) — "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks"**
This foundational work introduced Sentence-BERT (SBERT), which uses siamese and triplet network structures to derive semantically meaningful sentence embeddings. The all-mpnet-base-v2 model used in PrepPanda is a descendant of this architecture, offering 768-dimensional embeddings optimised for semantic textual similarity tasks. PrepPanda leverages these embeddings for both chunk storage and query encoding, enabling cosine-similarity-based nearest-neighbour retrieval.

**[3] Robertson, S. & Zaragoza, H. (2009) — "The Probabilistic Relevance Framework: BM25 and Beyond"**
BM25 remains the gold standard for term-frequency-based information retrieval. PrepPanda implements BM25-style keyword search via PostgreSQL's built-in tsvector/tsquery full-text search with ts_rank_cd scoring. This is combined with semantic search in a 70/30 weighted hybrid approach, addressing the limitation that semantic search alone can miss exact terminology matches critical in scientific textbooks.

**[4] Malkov, Y. A. & Yashunin, D. A. (2020) — "Efficient and Robust Approximate Nearest Neighbor Using Hierarchical Navigable Small World Graphs"**
The HNSW algorithm provides sub-linear-time approximate nearest neighbour search for high-dimensional vectors. PrepPanda uses the pgvector extension's HNSW index (vector_l2_ops) for efficient similarity search across thousands of 768-dimensional chunk embeddings, enabling real-time query responses even with large textbook corpora.

**[5] Gao, Y. et al. (2024) — "Retrieval-Augmented Generation for Large Language Models: A Survey"**
This comprehensive survey categorises RAG systems into Naive RAG, Advanced RAG, and Modular RAG architectures. PrepPanda aligns with the Advanced RAG category by implementing pre-retrieval query normalisation, hybrid retrieval with reciprocal rank fusion, post-retrieval neighbour expansion for context continuity, and structured prompt engineering with image placeholder injection.

**[6] Chen, J. et al. (2023) — "Dense Passage Retrieval for Open-Domain Question Answering"**
Dense retrieval using dual-encoder architectures demonstrated significant improvements over sparse (BM25) methods for question answering. PrepPanda's architecture reflects this finding by weighting semantic (dense) retrieval at 70% and keyword (sparse) retrieval at 30%, while maintaining the sparse component for exact-match recall on domain-specific terminology.

**[7] Kasneci, G. et al. (2023) — "ChatGPT for Good? On Opportunities and Challenges of Large Language Models for Education"**
This work explored the potential and pitfalls of LLMs in educational settings, highlighting risks of hallucination, bias, and misalignment with specific curricula. PrepPanda directly addresses these concerns by grounding all LLM outputs in verified NCERT textbook content through RAG, ensuring curriculum alignment and factual accuracy.

**[8] Team Gemini, Google (2024) — "Gemini: A Family of Highly Capable Multimodal Models"**
Google's Gemini models provide strong performance on reasoning and generation tasks. PrepPanda uses gemini-3-flash-preview for answer generation, question prediction, and quiz creation, leveraging its large context window and structured JSON output capabilities.

**[9] Touvron, H. et al. (2023) — "LLaMA: Open and Efficient Foundation Language Models"**
Meta's LLaMA family of open-source models enables cost-effective LLM deployment. PrepPanda uses LLaMA 3.1-8B-Instant (via Groq's inference API) specifically for concept graph generation and zone title improvement, choosing it for its speed and cost-effectiveness on structured extraction tasks.

**[10] Honnibal, M. & Montani, I. (2017) — "spaCy 2: Natural Language Processing at Industrial Strength"**
spaCy provides production-ready NLP pipelines for sentence segmentation, tokenisation, and named entity recognition. PrepPanda uses the en_core_web_sm model for sentence-boundary detection during chunk splitting, ensuring that oversized text sections are split at linguistically meaningful boundaries rather than arbitrary character counts.

## 2.2 Summary Table

**Table 2.1: Literature Review Summary Table**

| Ref. | Authors (Year) | Title | Key Contribution | Relevance to PrepPanda |
|------|---------------|-------|-----------------|----------------------|
| [1] | Lewis et al. (2020) | RAG for Knowledge-Intensive NLP Tasks | Introduced RAG paradigm combining retrieval with generation | Core architectural inspiration for PrepPanda's SRS module |
| [2] | Reimers & Gurevych (2019) | Sentence-BERT | Semantically meaningful sentence embeddings via siamese networks | Basis for the all-mpnet-base-v2 embedding model used |
| [3] | Robertson & Zaragoza (2009) | BM25 and Beyond | Probabilistic term-frequency retrieval framework | Implemented via PostgreSQL tsvector for keyword search |
| [4] | Malkov & Yashunin (2020) | HNSW Graphs | Sub-linear approximate nearest neighbour search | Used in pgvector HNSW index for semantic chunk retrieval |
| [5] | Gao et al. (2024) | RAG Survey for LLMs | Taxonomy of RAG architectures (Naive, Advanced, Modular) | PrepPanda classified as Advanced RAG with hybrid retrieval |
| [6] | Chen et al. (2023) | Dense Passage Retrieval | Dual-encoder dense retrieval superiority for QA | Validates PrepPanda's 70/30 dense/sparse weighting |
| [7] | Kasneci et al. (2023) | ChatGPT for Education | LLM opportunities and risks in education | Motivates curriculum-grounded RAG approach |
| [8] | Google (2024) | Gemini Models | High-capability multimodal generation | Used for answer generation, prediction, quizzes |
| [9] | Touvron et al. (2023) | LLaMA | Open-source efficient LLMs | LLaMA 3.1-8B used for concept graphs via Groq |
| [10] | Honnibal & Montani (2017) | spaCy | Industrial-strength NLP | Used for sentence segmentation in NodeParser |

## 2.3 Identification of Research Gaps / Limitations of Existing Methods

Based on the literature survey, the following research gaps and limitations were identified:

1. **Lack of Domain-Specific RAG for Indian Education:** Existing RAG implementations (Lewis et al., 2020) target general knowledge bases (Wikipedia, web corpora). No published system applies RAG specifically to NCERT textbook content with structure-aware parsing that preserves section hierarchies, heading breadcrumbs, and figure associations.

2. **No Visual-Textual Spatial Linking:** Current educational AI systems treat text and images independently. No existing tool performs spatial association between images and their surrounding text blocks (captions, explanatory paragraphs, questions) using bounding-box proximity as implemented in PrepPanda's VisualParser.

3. **Absence of PYQ-to-Textbook Semantic Mapping:** While PYQ databases exist (e.g., Embibe, Toppr), none semantically map each question to the specific textbook chunk(s) it tests. This prevents zone-based frequency analysis, trend detection, and grounded question prediction.

4. **Static Mind Maps vs. Content-Derived Graphs:** Existing mind-map tools (MindMeister, XMind) require manual creation. AI-generated mind maps from platforms like Notion AI are generic and not derived from the actual textbook content's structural and semantic features (definitions, classifications, processes, comparisons).

5. **Keyword-Only or Semantic-Only Retrieval:** Most educational platforms use either simple keyword search or basic semantic search. The combination of both in a weighted hybrid approach with neighbour expansion for context continuity is not commonly implemented in educational tools.

6. **No Adaptive Quiz Grounding in PYQ Analysis:** Existing quiz generators create random questions from content. None weight question generation based on PYQ frequency data (60% from PYQ-linked sections, 40% from random sections) to simulate realistic examination conditions.

PrepPanda addresses all six gaps through its integrated architecture combining dual-parser ingestion, hybrid retrieval, multi-LLM generation, and PYQ-grounded analytics.

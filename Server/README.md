# PrepPanda Server

PrepPanda Server is the Python-based backend that handles ingesting raw PDFs, extracting structural knowledge nodes (specifically tuned for NCERT-style structure), generating embeddings, and storing them in a pgvector-enabled PostgreSQL database for fast retrieval.

## 🚀 Prerequisites

1. **Python 3.11+**
2. **[uv](https://github.com/astral-sh/uv)** (for ultra-fast dependency management)
3. **Docker & Docker Compose** (for running the database and object storage)

---

## 🛠️ Setup Instructions

### 1. Install Dependencies
Make sure you have `uv` installed, then run:

```bash
# This will create a `.venv` and install all dependencies defined in pyproject.toml
uv sync

# You also need to download the spaCy NLP model used for semantic chunking
uv run python -m spacy download en_core_web_sm
```

### 2. Environment Variables
Create a `.env` file in the root directory (alongside `main.py`). The file must include your database credentials, S3 bucket credentials, and your LLM API key:

```env
# S3 / Minio
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=preppanda
S3_SECRET_KEY=preppass
S3_BUCKET_NAME=uploads

# PostgreSQL
POSTGRES_USER=preppanda
POSTGRES_PASSWORD=preppass
POSTGRES_DB=appdb
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Language Model
GEMINI_API_KEY=YOUR_API_KEY_HERE
```

### 3. Start Background Services
This project uses Docker to run PostgreSQL (with the `pgvector` extension) and MinIO (for S3-compatible file storage).

```bash
docker compose up -d
```
*Note: A setup script automatically runs inside Docker to create the MinIO bucket and make it public.*

### 4. Initialize Database Schema
Once the Postgres container (`pg_db`) is running, you need to apply the database schema. This creates the required `core` and `vector` schemas, the `node_type` enumerator, and all tables.

```bash
docker exec -i pg_db psql -U preppanda -d appdb < schema.sql
```

---

## 🧪 Testing the Pipeline

A full end-to-end integration test is provided in `test.py`. It tests the entire pipeline: 
1. Reads a test PDF
2. Extracts its text & images structurally
3. Uses NLP to split chunks
4. Classifies chunks using Gemini
5. Embeds them and stores everything in Postgres.

Before running, make sure a `lebo101.pdf` file exists in the root directory.

```bash
uv run test.py
```

## 🏗️ Architecture Architecture

* **`Core/Embedder/`**: High-level semantic pipeline orchestrator.
  * **`parser.py`**: Structure-aware parser using `fitz` (PyMuPDF) and `spaCy`. Maintains a section hierarchy stack to produce context-aware chunks (e.g. `[1.2 Motion > Definition]`).
  * **`classifier.py`**: Asynchronously hits the LLM (with batched concurrency via `asyncio.gather`) to classify nodes into definitions, processes, concepts, etc.
  * **`embedder.py`**: Orchestrates parsing + classifying + generating vectors + mapping to Vector/Bucket/Postgres handlers.
* **`Core/Storage/`**: Connectors that execute data mutations.
  * **`PostgresHandler.py`**: Relational store for files, chapters, and raw nodes.
  * **`VectorHandler.py`**: pgvector store exclusively handling similarity search filtering algorithms.
  * **`BucketHandler.py`**: MinIO bridge used to host and cache image diagrams extracted from PDFs.

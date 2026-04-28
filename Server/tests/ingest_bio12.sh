#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# ingest_bio12.sh — Upload all 13 NCERT Biology Class 12 chapters
#                   to the PrepPanda server in one shot.
#
# Usage:
#   cd tests/
#   bash ingest_bio12.sh
#
# Requirements:
#   - Server running at localhost:8000
#   - PDFs in tests/Material/lebo101.pdf … lebo113.pdf
# ─────────────────────────────────────────────────────────────────────

set -euo pipefail

BASE="${PREPPANDA_BASE:-http://localhost:8000}"
KEY="${PREPPANDA_ADMIN_KEY:-preppanda-admin-secret}"
DIR="$(cd "$(dirname "$0")" && pwd)/Material"

echo "▶ Ingesting NCERT Biology Class 12 to $BASE ..."
echo "  PDF directory: $DIR"
echo ""

curl -X POST "$BASE/admin/ingest-book" \
  -H "X-Admin-Key: $KEY" \
  -F "title=Biology – Class XII" \
  -F "grade=12" \
  -F "subject=biology" \
  -F 'chapters=[
    {"number":1,  "title":"Reproduction in Organisms"},
    {"number":2,  "title":"Sexual Reproduction in Flowering Plants"},
    {"number":3,  "title":"Human Reproduction"},
    {"number":4,  "title":"Reproductive Health"},
    {"number":5,  "title":"Principles of Inheritance and Variation"},
    {"number":6,  "title":"Molecular Basis of Inheritance"},
    {"number":7,  "title":"Evolution"},
    {"number":8,  "title":"Human Health and Disease"},
    {"number":9,  "title":"Strategies for Enhancement in Food Production"},
    {"number":10, "title":"Microbes in Human Welfare"},
    {"number":11, "title":"Biotechnology: Principles and Processes"},
    {"number":12, "title":"Biotechnology and Its Applications"},
    {"number":13, "title":"Organisms and Populations"}
  ]' \
  -F "pdfs=@$DIR/lebo101.pdf;type=application/pdf" \
  -F "pdfs=@$DIR/lebo102.pdf;type=application/pdf" \
  -F "pdfs=@$DIR/lebo103.pdf;type=application/pdf" \
  -F "pdfs=@$DIR/lebo104.pdf;type=application/pdf" \
  -F "pdfs=@$DIR/lebo105.pdf;type=application/pdf" \
  -F "pdfs=@$DIR/lebo106.pdf;type=application/pdf" \
  -F "pdfs=@$DIR/lebo107.pdf;type=application/pdf" \
  -F "pdfs=@$DIR/lebo108.pdf;type=application/pdf" \
  -F "pdfs=@$DIR/lebo109.pdf;type=application/pdf" \
  -F "pdfs=@$DIR/lebo110.pdf;type=application/pdf" \
  -F "pdfs=@$DIR/lebo111.pdf;type=application/pdf" \
  -F "pdfs=@$DIR/lebo112.pdf;type=application/pdf" \
  -F "pdfs=@$DIR/lebo113.pdf;type=application/pdf" \
  | tee /tmp/preppanda_ingest.json | python3 -m json.tool

BOOK_ID=$(python3 -c "import json; print(json.load(open('/tmp/preppanda_ingest.json'))['book_id'])")

echo ""
echo "✅ Book ingested.  book_id = $BOOK_ID"
echo ""

# ── Phase 2: Ingest PYQs (auto-mapped to chapters) ──────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYQ_FILE="$SCRIPT_DIR/pyqs_2026.txt"

if [ -f "$PYQ_FILE" ]; then
    echo "▶ Ingesting PYQs from $PYQ_FILE …"
    curl -s -X POST "$BASE/admin/books/$BOOK_ID/pyqs/file" \
      -H "X-Admin-Key: $KEY" \
      -F "file=@$PYQ_FILE;type=text/plain" \
      | python3 -m json.tool
    echo ""
    echo "✅ PYQs ingested and auto-mapped to chapters."
else
    echo "⚠  $PYQ_FILE not found — skipping PYQ ingestion."
fi

echo ""
echo "✅ All done.  book_id = $BOOK_ID"

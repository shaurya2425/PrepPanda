# ─────────────────────────────────────────────
# ingest_bio12.ps1 — Stable Windows Version
# ─────────────────────────────────────────────

$ErrorActionPreference = "Stop"

# Base config
$BASE = $env:PREPPANDA_BASE
if (-not $BASE) { $BASE = "http://localhost:8000" }

$KEY = $env:PREPPANDA_ADMIN_KEY
if (-not $KEY) { $KEY = "preppanda-admin-secret" }

$DIR = Join-Path $PSScriptRoot "Material"

Write-Host "Ingesting NCERT Biology Class 12 to $BASE"
Write-Host "PDF directory: $DIR"
Write-Host ""

# Chapters JSON
$chapters = @"
[
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
]
"@

# Upload request
$response = curl.exe -X POST "$BASE/admin/ingest-book" `
  -H "X-Admin-Key: $KEY" `
  -F "title=Biology Class XII" `
  -F "grade=12" `
  -F "subject=biology" `
  -F "chapters=$chapters" `
  -F "pdfs=@$DIR/lebo101.pdf;type=application/pdf" `
  -F "pdfs=@$DIR/lebo102.pdf;type=application/pdf" `
  -F "pdfs=@$DIR/lebo103.pdf;type=application/pdf" `
  -F "pdfs=@$DIR/lebo104.pdf;type=application/pdf" `
  -F "pdfs=@$DIR/lebo105.pdf;type=application/pdf" `
  -F "pdfs=@$DIR/lebo106.pdf;type=application/pdf" `
  -F "pdfs=@$DIR/lebo107.pdf;type=application/pdf" `
  -F "pdfs=@$DIR/lebo108.pdf;type=application/pdf" `
  -F "pdfs=@$DIR/lebo109.pdf;type=application/pdf" `
  -F "pdfs=@$DIR/lebo110.pdf;type=application/pdf" `
  -F "pdfs=@$DIR/lebo111.pdf;type=application/pdf" `
  -F "pdfs=@$DIR/lebo112.pdf;type=application/pdf" `
  -F "pdfs=@$DIR/lebo113.pdf;type=application/pdf"

# Save response
$tempFile = Join-Path $env:TEMP "preppanda_ingest.json"
$response | Out-File -Encoding utf8 $tempFile

# Parse JSON
$json = Get-Content $tempFile | ConvertFrom-Json
$BOOK_ID = $json.book_id

Write-Host ""
Write-Host "Book ingested successfully. book_id = $BOOK_ID"
Write-Host ""

# ── Phase 2: PYQs ──
$PYQ_FILE = Join-Path $PSScriptRoot "pyqs_2026.txt"

if (Test-Path $PYQ_FILE) {
    Write-Host "Ingesting PYQs..."

    curl.exe -X POST "$BASE/admin/books/$BOOK_ID/pyqs/file" `
      -H "X-Admin-Key: $KEY" `
      -F "file=@$PYQ_FILE;type=text/plain"

    Write-Host "PYQs ingested successfully."
}
else {
    Write-Host "PYQ file not found. Skipping."
}

Write-Host ""
Write-Host "All done. book_id = $BOOK_ID"
#!/usr/bin/env python3
"""
ingest.py — Upload all 13 NCERT Biology Class 12 chapters
            to the PrepPanda server in one shot.

Usage:
    cd tests/
    python ingest.py

Requirements:
    - Server running at localhost:8000
    - PDFs in tests/Material/lebo101.pdf … lebo113.pdf
"""

import requests
import json
import os
import sys

BASE = os.getenv("PREPPANDA_BASE", "http://localhost:8000")
KEY  = os.getenv("PREPPANDA_ADMIN_KEY", "preppass")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DIR        = os.path.join(SCRIPT_DIR, "Material")
TEMP_FILE  = os.path.join(SCRIPT_DIR, "preppanda_ingest.json")

print(f"▶ Ingesting NCERT Biology Class 12 to {BASE}")
print(f"  PDF directory: {DIR}\n")

chapters = [
    {"number": 1,  "title": "Reproduction in Organisms"},
    {"number": 2,  "title": "Sexual Reproduction in Flowering Plants"},
    {"number": 3,  "title": "Human Reproduction"},
    {"number": 4,  "title": "Reproductive Health"},
    {"number": 5,  "title": "Principles of Inheritance and Variation"},
    {"number": 6,  "title": "Molecular Basis of Inheritance"},
    {"number": 7,  "title": "Evolution"},
    {"number": 8,  "title": "Human Health and Disease"},
    {"number": 9,  "title": "Strategies for Enhancement in Food Production"},
    {"number": 10, "title": "Microbes in Human Welfare"},
    {"number": 11, "title": "Biotechnology: Principles and Processes"},
    {"number": 12, "title": "Biotechnology and Its Applications"},
    {"number": 13, "title": "Organisms and Populations"},
]

# ── Phase 1: Ingest book ─────────────────────────────────────────────

file_handles = []
files = []
try:
    for i in range(101, 114):
        path = os.path.join(DIR, f"lebo{i}.pdf")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing PDF: {path}")
        fh = open(path, "rb")
        file_handles.append(fh)
        files.append(("pdfs", (f"lebo{i}.pdf", fh, "application/pdf")))

    response = requests.post(
        f"{BASE}/admin/ingest-book",
        # ↓ Fix: pass header as a keyword arg so requests sends it correctly
        headers={"X-Admin-Key": KEY},
        data={
            "title":    "Biology \u2013 Class XII",
            "grade":    "12",
            "subject":  "biology",
            "chapters": json.dumps(chapters),   # matches curl -F behaviour
        },
        files=files,
    )
finally:
    for fh in file_handles:
        fh.close()

# Save raw response (mirrors bash `tee`)
with open(TEMP_FILE, "w", encoding="utf-8") as f:
    f.write(response.text)

print(f"Response status: {response.status_code}")

# ── Friendlier auth error message ───────────────────────────────────
if response.status_code == 401:
    print("\n❌  401 Not Authenticated.")
    print("    Check that PREPPANDA_ADMIN_KEY matches the server's expected key.")
    print(f"    Current key used: {KEY!r}")
    print("    Set the correct key with:  set PREPPANDA_ADMIN_KEY=<your-key>  (Windows)")
    print("                          or:  export PREPPANDA_ADMIN_KEY=<your-key>  (Unix)")
    sys.exit(1)

try:
    parsed = response.json()
    print(json.dumps(parsed, indent=2))
except ValueError:
    print("Non-JSON response body:")
    print(response.text)
    sys.exit(1)

if "book_id" not in parsed:
    print(f"\n❌  Server responded but 'book_id' missing. Full response:\n{json.dumps(parsed, indent=2)}")
    sys.exit(1)

BOOK_ID = parsed["book_id"]
print(f"\n✅ Book ingested.  book_id = {BOOK_ID}\n")

# ── Phase 2: Ingest PYQs ────────────────────────────────────────────

PYQ_FILE = os.path.join(SCRIPT_DIR, "pyqs_2026.txt")

if os.path.exists(PYQ_FILE):
    print(f"▶ Ingesting PYQs from {PYQ_FILE} …")
    with open(PYQ_FILE, "rb") as f:
        pyq_res = requests.post(
            f"{BASE}/admin/books/{BOOK_ID}/pyqs/file",
            headers={"X-Admin-Key": KEY},
            files={"file": ("pyqs_2026.txt", f, "text/plain")},
        )

    print(f"Response status: {pyq_res.status_code}")
    try:
        print(json.dumps(pyq_res.json(), indent=2))
    except ValueError:
        print(pyq_res.text)

    if pyq_res.ok:
        print("\n✅ PYQs ingested and auto-mapped to chapters.")
    else:
        print(f"\n⚠  PYQ ingestion returned status {pyq_res.status_code}.")
else:
    print(f"⚠  {PYQ_FILE} not found — skipping PYQ ingestion.")

print(f"\n✅ All done.  book_id = {BOOK_ID}")
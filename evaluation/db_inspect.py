import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = ROOT / "Server"
sys.path.insert(0, str(SERVER_ROOT))

from Core.Storage.PostgresHandler import PostgresHandler

async def main() -> None:
    os.environ["POSTGRES_USER"] = "preppanda"
    os.environ["POSTGRES_PASSWORD"] = "preppass"
    os.environ["POSTGRES_DB"] = "appdb"
    os.environ["POSTGRES_HOST"] = "localhost"
    os.environ["POSTGRES_PORT"] = "5432"

    pg = PostgresHandler()
    await pg.connect()
    try:
        pool = pg._pool_guard()
        rows = await pool.fetch(
            """
            SELECT c.chapter_id, c.title, b.title AS book_title
            FROM core.chapters c
            JOIN core.books b ON c.book_id = b.book_id
            WHERE lower(b.subject) LIKE $1
              AND b.grade = 12
            ORDER BY c.title
            """,
            "%biology%",
        )
        print("count", len(rows))
        for r in rows:
            print(r["chapter_id"], "--", r["title"], "--", r["book_title"])
    finally:
        await pg.disconnect()

if __name__ == "__main__":
    asyncio.run(main())

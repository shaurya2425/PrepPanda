import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = ROOT / 'Server'
sys.path.insert(0, str(SERVER_ROOT))

from Core.Storage.PostgresHandler import PostgresHandler

async def main():
    os.environ.setdefault('POSTGRES_USER', 'preppanda')
    os.environ.setdefault('POSTGRES_PASSWORD', 'preppass')
    os.environ.setdefault('POSTGRES_DB', 'appdb')
    os.environ.setdefault('POSTGRES_HOST', 'localhost')
    os.environ.setdefault('POSTGRES_PORT', '5432')

    pg = PostgresHandler()
    await pg.connect()
    try:
        pool = pg._pool_guard()
        rows = await pool.fetch(
            """
            SELECT c.chapter_id, b.title AS book_title, c.title AS chapter_title
            FROM core.chapters c
            JOIN core.books b ON c.book_id = b.book_id
            WHERE lower(b.subject) LIKE $1 AND b.grade = 12
            ORDER BY c.chapter_number
            """,
            '%biology%',
        )
        print('chapters:', len(rows))
        for r in rows:
            print(r['chapter_id'], '|', r['book_title'], '|', r['chapter_title'])

        print('\nSample chunks for human reproduction chapter(s):')
        rows = await pool.fetch(
            """
            SELECT chapter_id, content, position_index
            FROM core.chunks
            WHERE chapter_id = $1
            ORDER BY position_index
            LIMIT 10
            """,
            rows[0]['chapter_id'] if rows else None,
        )
        for c in rows:
            print('pos', c['position_index'], c['content'][:200].replace('\n',' '))
    finally:
        await pg.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = ROOT / 'Server'
sys.path.insert(0, str(SERVER_ROOT))

from Core.Storage.PostgresHandler import PostgresHandler

CHAPTERS = {
    'Human Reproduction': 'e9b3f002-f293-40fe-8591-87f6dc44da5d',
    'Reproductive Health': '7ba50bb0-0e79-43dd-9525-b5fae00149d9',
    'Sexual Reproduction in Flowering Plants': '4450becc-0d5f-4587-9a16-7a17e1b111d8',
    'Molecular Basis of Inheritance': '1e04530f-c596-49a3-85e3-b44bc655daed',
}

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
        for name, chapter_id in CHAPTERS.items():
            rows = await pool.fetch(
                '''
                SELECT chunk_id, position_index, content
                FROM core.chunks
                WHERE chapter_id = $1
                ORDER BY position_index
                LIMIT 15
                ''',
                chapter_id,
            )
            print(f'--- {name} ({chapter_id}) ---')
            for r in rows:
                content = r['content'].replace('\n', ' ')
                print(r['position_index'], content[:200])
            print()
    finally:
        await pg.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

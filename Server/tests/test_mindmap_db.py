import asyncio
import logging
import os
import sys

# Add the parent directory to sys.path to allow importing from Core
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv

from Core.Features.MindMap import MindMapBuilder, MindMapNode
from Core.Storage.PostgresHandler import PostgresHandler

def _print_tree(node: MindMapNode, indent: int = 0) -> None:
    prefix = "  " * indent
    tag = node.tag.name[:4]
    figs = f" 📊{node.figure_ids}" if node.figure_ids else ""
    print(f"{prefix}{'├─' if indent else '●'} [{tag}] {node.label}{figs}")
    for child in node.children:
        _print_tree(child, indent + 1)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

async def main() -> None:
    load_dotenv()
    
    pg = PostgresHandler()
    try:
        await pg.connect()
        logger.info("PostgreSQL connected.")
    except Exception as e:
        logger.error("PostgreSQL connection failed: %s", e)
        return

    try:
        pool = pg._pool_guard()
        
        # 1. Get a chapter ID
        row = await pool.fetchrow("SELECT chapter_id, title FROM core.chapters LIMIT 1")
        if not row:
            logger.error("No chapters found in the database. Run test_parser.py first to populate it.")
            return
            
        chapter_id = row["chapter_id"]
        chapter_title = row["title"]
        logger.info("Found chapter: %s (ID: %s)", chapter_title, chapter_id)
        
        # 2. Get all chunks for this chapter
        chunk_rows = await pool.fetch(
            "SELECT * FROM core.chunks WHERE chapter_id = $1 ORDER BY position_index",
            chapter_id
        )
        
        if not chunk_rows:
            logger.warning("No chunks found for this chapter.")
            return
            
        logger.info("Fetched %d chunks from the database.", len(chunk_rows))
        
        # Convert asyncpg.Record to dict
        chunk_dicts = [pg._record_to_dict(r) for r in chunk_rows]
        
        # 3. Build MindMap
        logger.info("Building MindMap from DB chunks...")
        tree = MindMapBuilder.from_db_chunks(chunk_dicts, root_label=chapter_title)
        
        # 4. Print Tree
        print("\n  ── Generated Mind-Map Tree (Real Data) ──")
        _print_tree(tree, indent=2)
        
        print(f"\nStats: {tree.node_count()} nodes, {tree.leaf_count()} leaves")

    except Exception as e:
        logger.exception("MindMap DB test failed: %s", e)
    finally:
        await pg.disconnect()
        logger.info("Disconnected from PostgreSQL.")

if __name__ == "__main__":
    asyncio.run(main())

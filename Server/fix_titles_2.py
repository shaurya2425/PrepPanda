import asyncio
import os
import re
import asyncpg

async def main():
    conn = await asyncpg.connect(
        user=os.environ.get("POSTGRES_USER", "preppanda"),
        password=os.environ.get("POSTGRES_PASSWORD", "preppass"),
        database=os.environ.get("POSTGRES_DB", "appdb"),
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
    )
    
    rows = await conn.fetch("SELECT chunk_id, section_title FROM core.chunks;")
    
    updates = 0
    for r in rows:
        title = r["section_title"]
        if not title:
            continue
        original = title
        title = title.strip()
        
        # 1. Check if it's just a number like "10."
        if re.match(r"^\d+(\.\d+)*\.?$", title):
            # We will print these to see why they didn't get fixed
            print(f"Still completely numeric: '{title}' (chunk: {r['chunk_id']})")
            continue
            
        # 2. Check if it has a prefix like "4.8.2 " or "4.6 " or "10. "
        # We want to strip the prefix
        m = re.match(r"^(\d+(\.\d+)*\.?\s+)(.*)$", title)
        if m:
            new_title = m.group(3).strip()
            # if new_title is empty or just numbers, ignore for now
            if new_title and not re.match(r"^\d+(\.\d+)*\.?$", new_title):
                await conn.execute("UPDATE core.chunks SET section_title = $1 WHERE chunk_id = $2", new_title, r["chunk_id"])
                print(f"Stripped prefix: '{original}' -> '{new_title}'")
                updates += 1

    print(f"Total stripped: {updates}")

asyncio.run(main())

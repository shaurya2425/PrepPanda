import asyncio
import os
import re
import json
import asyncpg
from groq import AsyncGroq

async def main():
    conn = await asyncpg.connect(
        user=os.environ.get("POSTGRES_USER", "preppanda"),
        password=os.environ.get("POSTGRES_PASSWORD", "preppass"),
        database=os.environ.get("POSTGRES_DB", "appdb"),
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
    )
    
    rows = await conn.fetch("SELECT chunk_id, section_title, content FROM core.chunks;")
    to_fix = []
    
    for r in rows:
        title = r["section_title"]
        if not title: continue
        title = title.strip()
        if re.match(r"^\d+(\.\d+)*\.?$", title):
            to_fix.append(r)
            
    print(f"Found {len(to_fix)} completely numeric chunks to fix.")
    if not to_fix: return
    
    key = os.environ.get("GROQ_API_KEY")
    client = AsyncGroq(api_key=key)
    
    batch_size = 10
    for i in range(0, len(to_fix), batch_size):
        batch = to_fix[i:i+batch_size]
        prompt_lines = [
            "You are an expert textbook editor. Below are excerpts from different textbook sections that currently have useless numeric titles (like '10.').",
            "Please provide a concise, descriptive 2-5 word topic title for each excerpt based on its content.",
            "Return ONLY a JSON object with the format: {\"titles\": [\"Title 1\", \"Title 2\", ...]} maintaining the exact order.",
            ""
        ]
        for idx, z in enumerate(batch):
            prompt_lines.append(f"Excerpt {idx+1}:\n{z['content'][:300]}\n")
            
        prompt = "\n".join(prompt_lines)
        
        try:
            resp = await client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            data = json.loads(resp.choices[0].message.content)
            titles = data.get("titles", [])
            for j, title in enumerate(titles):
                if j < len(batch) and title and not re.match(r"^\d+(\.\d+)*\.?$", title.strip()):
                    await conn.execute("UPDATE core.chunks SET section_title = $1 WHERE chunk_id = $2", title, batch[j]["chunk_id"])
                    print(f"Updated {batch[j]['chunk_id']} -> {title}")
                else:
                    print(f"Groq returned invalid title for {batch[j]['chunk_id']}: {title}")
        except Exception as e:
            print(f"Error parsing groq: {e}")

asyncio.run(main())

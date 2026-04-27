import asyncio
import logging
import os
import uuid

from dotenv import load_dotenv

from Core.Parser.VisualParser import parse_pdf_visual
from Core.Storage.BucketHandler import BucketHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    # Load env vars from .env
    load_dotenv()
    
    # ── 1. Instantiate Handlers ─────────────────────────────────────
    try:
        bucket = BucketHandler()
        logger.info("BucketHandler instantiated successfully.")
    except Exception as e:
        logger.error(f"Failed to instantiate BucketHandler. Are env vars set? Error: {e}")
        return

    # ── 2. Run the Visual Parser ────────────────────────────────────
    pdf_path = "lebo101.pdf"
    if not os.path.exists(pdf_path):
        logger.error(f"PDF not found at {pdf_path}")
        return

    logger.info(f"Starting VisualParser for: {pdf_path}")
    try:
        # VisualParser is synchronous, we don't need to await it
        chunks = parse_pdf_visual(pdf_path)
        logger.info(f"VisualParser finished! Extracted {len(chunks)} chunks.")
    except Exception as e:
        logger.exception(f"VisualParser failed: {e}")
        return

    # ── 3. Upload Images ────────────────────────────────────────────
    logger.info("Uploading extracted images to Bucket...")
    chapter_id = str(uuid.uuid4())
    upload_count = 0
    
    for i, chunk in enumerate(chunks):
        if not chunk.images:
            continue
            
        for j, img in enumerate(chunk.images):
            # Generate a filename
            fig_id = img.figure_id or f"unlabeled_{i}_{j}"
            
            # Clean up the caption for the filename
            safe_caption = ""
            if img.caption:
                # Remove non-alphanumeric characters and replace spaces with underscores
                safe_caption = "".join([c if c.isalnum() else "_" for c in img.caption])
                # Remove consecutive underscores
                while "__" in safe_caption:
                    safe_caption = safe_caption.replace("__", "_")
                safe_caption = safe_caption.strip("_")[:30]
            
            if not safe_caption:
                safe_caption = "no_caption"
                
            filename = f"test_visual/{chapter_id}/fig_{fig_id}_{safe_caption}.png"
            
            try:
                # bucket.upload_bytes is synchronous
                url = bucket.upload_bytes(img.image_bytes, filename, "image/png")
                logger.info(f"Uploaded Image (Chunk {i}, Fig {img.figure_id}): {url}")
                upload_count += 1
            except Exception as e:
                logger.error(f"Failed to upload image {filename}: {e}")

    logger.info(f"Finished uploading {upload_count} images.")

if __name__ == "__main__":
    asyncio.run(main())

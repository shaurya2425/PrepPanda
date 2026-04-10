"""Shared constants for the Embedder pipeline."""

# Chunking thresholds
MIN_CHUNK_CHARS = 20
MAX_CHUNK_WORDS = 500
MIN_CHUNK_SENTENCES = 1

# spaCy model to load for sentence segmentation
SPACY_MODEL = "en_core_web_sm"

# Image extraction thresholds
MIN_IMAGE_DIMENSION = 50   # px – skip images narrower/shorter than this
MIN_IMAGE_AREA = 5000      # px² – skip tiny decorative images

"""Shared constants for the Embedder pipeline."""

VALID_NODE_TYPES = {"definition", "concept", "process", "example", "diagram"}
DEFAULT_NODE_TYPE = "concept"

# Chunking thresholds
MIN_CHUNK_CHARS = 20
MAX_CHUNK_WORDS = 500
MIN_CHUNK_SENTENCES = 1

# spaCy model to load for sentence segmentation
SPACY_MODEL = "en_core_web_sm"

# LLM classification prompt
CLASSIFICATION_PROMPT = (
    "Classify the following text into exactly one of these categories: "
    "definition, concept, process, example.\n"
    "Respond with ONLY the category name in lowercase.\n\n"
    "Text:\n{text}"
)

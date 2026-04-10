"""Embedder – PDF → node → embedding → retrieval pipeline.

Public API::

    from Core.Embedder import Embedder, EmbedderError, StructuralNode
"""

from Core.Embedder.embedder import Embedder, EmbedderError
from Core.Embedder.parser import StructuralNode

__all__ = ["Embedder", "EmbedderError", "StructuralNode"]

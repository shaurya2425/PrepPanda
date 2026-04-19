"""Embedder – PDF → node → embedding → retrieval pipeline.

Public API::

    from Core.Embedder import Embedder, EmbedderError, FigureCaption, StructuralNode
"""

from Core.Embedder.embedder import Embedder, EmbedderError
from Core.Embedder.parser import FigureCaption, StructuralNode

__all__ = ["Embedder", "EmbedderError", "FigureCaption", "StructuralNode"]

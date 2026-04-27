"""
Second Brain — persistent knowledge and memory system for agency agents.

Provides storage, retrieval, and CLI access to a JSON-backed knowledge base
that persists across agent sessions.

Quick start:
    from second_brain import MemoryStore, KnowledgeItem, KnowledgeRetriever

    store = MemoryStore()
    item = KnowledgeItem(title="My note", content="...", category="engineering")
    store.add(item)

    retriever = KnowledgeRetriever(store)
    results = retriever.search("my note")
"""

from .knowledge import KnowledgeItem
from .memory import MemoryStore, DEFAULT_STORE_PATH
from .retrieval import KnowledgeRetriever

__all__ = ["KnowledgeItem", "MemoryStore", "KnowledgeRetriever", "DEFAULT_STORE_PATH"]
__version__ = "0.1.0"

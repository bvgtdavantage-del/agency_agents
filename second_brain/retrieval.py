"""
Context-aware knowledge retrieval for the Second Brain system.

Provides keyword search, tag filtering, category filtering, and
relevance scoring without any external ML dependencies.
"""

import re
from typing import Dict, List, Optional

from .knowledge import KnowledgeItem
from .memory import MemoryStore


def _tokenize(text: str) -> List[str]:
    """Split text into lowercase tokens, stripping punctuation."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _score(item: KnowledgeItem, query_tokens: List[str]) -> float:
    """
    Score an item against query tokens.

    Title matches are weighted 3×, tag matches 2×, content matches 1×.
    Returns 0.0 if no tokens match.
    """
    if not query_tokens:
        return 0.0

    title_tokens = set(_tokenize(item.title))
    tag_tokens = set(_tokenize(" ".join(item.tags)))
    content_tokens = set(_tokenize(item.content))

    score = 0.0
    for token in query_tokens:
        if token in title_tokens:
            score += 3.0
        if token in tag_tokens:
            score += 2.0
        if token in content_tokens:
            score += 1.0

    # Normalise so longer queries don't always win
    return score / len(query_tokens)


class KnowledgeRetriever:
    """Query interface over a MemoryStore."""

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def search(
        self,
        query: str = "",
        *,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> List[Dict]:
        """
        Return knowledge items ranked by relevance.

        Args:
            query:    Free-text search string.
            category: Exact category filter (case-insensitive).
            tags:     All provided tags must be present on an item.
            limit:    Maximum number of results.
            min_score: Exclude items scoring below this threshold when a
                       query is provided.

        Returns:
            List of dicts: {"item": KnowledgeItem, "score": float}
        """
        query_tokens = _tokenize(query) if query else []
        items = self.store.all()

        results = []
        for item in items:
            # Category filter
            if category and item.category.lower() != category.lower():
                continue

            # Tag filter
            if tags and not item.matches_tags(tags):
                continue

            score = _score(item, query_tokens) if query_tokens else 1.0

            if score < min_score:
                continue

            results.append({"item": item, "score": score})

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:limit]

    def get_by_category(self, category: str) -> List[KnowledgeItem]:
        return [
            item for item in self.store.all()
            if item.category.lower() == category.lower()
        ]

    def get_by_tag(self, tag: str) -> List[KnowledgeItem]:
        tag_lower = tag.lower()
        return [
            item for item in self.store.all()
            if any(t.lower() == tag_lower for t in item.tags)
        ]

    def list_categories(self) -> List[str]:
        return sorted({item.category for item in self.store.all()})

    def list_tags(self) -> List[str]:
        tags: set = set()
        for item in self.store.all():
            tags.update(t.lower() for t in item.tags)
        return sorted(tags)

    def related(self, item_id: str, limit: int = 5) -> List[Dict]:
        """
        Find items related to a given item using its title and tags as query.
        """
        source = self.store.get(item_id)
        if source is None:
            return []

        query = " ".join([source.title] + source.tags)
        results = self.search(query, limit=limit + 1)
        # Exclude the source item itself
        return [r for r in results if r["item"].id != item_id][:limit]

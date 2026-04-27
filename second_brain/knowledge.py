"""
Knowledge item data structures for the Second Brain system.
"""

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class KnowledgeItem:
    """A single unit of knowledge stored in the second brain."""

    title: str
    content: str
    category: str
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=_utcnow)
    updated_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeItem":
        return cls(
            id=data["id"],
            title=data["title"],
            content=data["content"],
            category=data["category"],
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", _utcnow()),
            updated_at=data.get("updated_at", _utcnow()),
        )

    def update(self, **kwargs: Any) -> None:
        """Update fields and refresh updated_at."""
        allowed = {"title", "content", "category", "tags", "metadata"}
        for key, value in kwargs.items():
            if key in allowed:
                setattr(self, key, value)
        self.updated_at = _utcnow()

    def matches_tags(self, tags: List[str]) -> bool:
        """Return True if the item has ALL of the given tags."""
        item_tags_lower = {t.lower() for t in self.tags}
        return all(t.lower() in item_tags_lower for t in tags)

    def text_for_search(self) -> str:
        """Combined searchable text (lowercased)."""
        parts = [self.title, self.content, self.category] + self.tags
        return " ".join(parts).lower()

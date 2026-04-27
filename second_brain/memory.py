"""
Persistent memory store for the Second Brain system.

Stores knowledge items as JSON with atomic writes to prevent corruption.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from .knowledge import KnowledgeItem


DEFAULT_STORE_PATH = Path.home() / ".agency_second_brain" / "memories.json"


class MemoryStore:
    """
    JSON-backed persistent store for KnowledgeItems.

    All writes are atomic (write-to-tmp then rename) so the store
    is never left in a partially-written state.
    """

    def __init__(self, store_path: Optional[Path] = None) -> None:
        self.store_path = Path(store_path) if store_path else DEFAULT_STORE_PATH
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._items: Dict[str, KnowledgeItem] = {}
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self.store_path.exists():
            return
        try:
            with open(self.store_path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            for entry in raw.get("items", []):
                item = KnowledgeItem.from_dict(entry)
                self._items[item.id] = item
        except (json.JSONDecodeError, KeyError, TypeError):
            self._items = {}

    def _save(self) -> None:
        payload = {"items": [item.to_dict() for item in self._items.values()]}
        dir_ = self.store_path.parent
        # Atomic write: write to a temp file then rename
        with tempfile.NamedTemporaryFile(
            "w", dir=dir_, delete=False, suffix=".tmp", encoding="utf-8"
        ) as tmp:
            json.dump(payload, tmp, ensure_ascii=False, indent=2)
            tmp_path = tmp.name
        os.replace(tmp_path, self.store_path)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(self, item: KnowledgeItem) -> KnowledgeItem:
        """Persist a new knowledge item; raises ValueError if ID already exists."""
        if item.id in self._items:
            raise ValueError(f"Item with id '{item.id}' already exists.")
        self._items[item.id] = item
        self._save()
        return item

    def get(self, item_id: str) -> Optional[KnowledgeItem]:
        return self._items.get(item_id)

    def update(self, item_id: str, **kwargs) -> KnowledgeItem:
        """Update fields of an existing item; raises KeyError if not found."""
        item = self._items.get(item_id)
        if item is None:
            raise KeyError(f"Item '{item_id}' not found.")
        item.update(**kwargs)
        self._save()
        return item

    def delete(self, item_id: str) -> bool:
        """Remove an item; returns True if it existed."""
        if item_id not in self._items:
            return False
        del self._items[item_id]
        self._save()
        return True

    def all(self) -> List[KnowledgeItem]:
        return list(self._items.values())

    def count(self) -> int:
        return len(self._items)

    def clear(self) -> None:
        """Remove all items (useful for testing)."""
        self._items = {}
        self._save()

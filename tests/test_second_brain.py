"""
Tests for the Second Brain system: memory, knowledge, retrieval, and CLI.
"""

import json
import sys
import pytest
from pathlib import Path

from second_brain.knowledge import KnowledgeItem
from second_brain.memory import MemoryStore
from second_brain.retrieval import KnowledgeRetriever
from second_brain.cli import main as cli_main


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_store(tmp_path):
    """Return a MemoryStore backed by a temp file."""
    return MemoryStore(tmp_path / "test_memories.json")


@pytest.fixture
def populated_store(tmp_store):
    """MemoryStore with three pre-loaded items."""
    tmp_store.add(KnowledgeItem(
        title="React useEffect cleanup",
        content="Return a cleanup function to avoid memory leaks on unmount.",
        category="engineering",
        tags=["react", "hooks", "memory-leak"],
    ))
    tmp_store.add(KnowledgeItem(
        title="Postgres index on FK columns",
        content="Always add an index on foreign key columns for query performance.",
        category="engineering",
        tags=["postgres", "database", "performance"],
    ))
    tmp_store.add(KnowledgeItem(
        title="Brand colour palette",
        content="Primary: #3B82F6  Secondary: #10B981  Danger: #EF4444",
        category="design",
        tags=["brand", "colour", "design-system"],
    ))
    return tmp_store


# ---------------------------------------------------------------------------
# KnowledgeItem tests
# ---------------------------------------------------------------------------

class TestKnowledgeItem:
    def test_creates_with_required_fields(self):
        item = KnowledgeItem(title="T", content="C", category="engineering")
        assert item.title == "T"
        assert item.content == "C"
        assert item.category == "engineering"
        assert item.id  # auto-generated UUID

    def test_default_tags_is_empty_list(self):
        item = KnowledgeItem(title="T", content="C", category="engineering")
        assert item.tags == []

    def test_to_dict_and_from_dict_roundtrip(self):
        item = KnowledgeItem(title="T", content="C", category="eng", tags=["x", "y"])
        restored = KnowledgeItem.from_dict(item.to_dict())
        assert restored.id == item.id
        assert restored.title == item.title
        assert restored.tags == item.tags

    def test_update_refreshes_updated_at(self):
        item = KnowledgeItem(title="T", content="C", category="engineering")
        original_ts = item.updated_at
        item.update(title="T2")
        assert item.title == "T2"
        assert item.updated_at >= original_ts

    def test_matches_tags_all_required(self):
        item = KnowledgeItem(title="T", content="C", category="e", tags=["a", "b", "c"])
        assert item.matches_tags(["a", "b"])
        assert not item.matches_tags(["a", "z"])

    def test_matches_tags_case_insensitive(self):
        item = KnowledgeItem(title="T", content="C", category="e", tags=["React"])
        assert item.matches_tags(["react"])

    def test_text_for_search_includes_all_fields(self):
        item = KnowledgeItem(title="Hooks", content="cleanup", category="eng", tags=["react"])
        text = item.text_for_search()
        assert "hooks" in text
        assert "cleanup" in text
        assert "react" in text


# ---------------------------------------------------------------------------
# MemoryStore tests
# ---------------------------------------------------------------------------

class TestMemoryStore:
    def test_add_and_get(self, tmp_store):
        item = KnowledgeItem(title="T", content="C", category="engineering")
        tmp_store.add(item)
        fetched = tmp_store.get(item.id)
        assert fetched is not None
        assert fetched.title == "T"

    def test_add_duplicate_raises(self, tmp_store):
        item = KnowledgeItem(title="T", content="C", category="engineering")
        tmp_store.add(item)
        with pytest.raises(ValueError, match="already exists"):
            tmp_store.add(item)

    def test_get_missing_returns_none(self, tmp_store):
        assert tmp_store.get("nonexistent") is None

    def test_update_fields(self, tmp_store):
        item = KnowledgeItem(title="Old", content="Old content", category="engineering")
        tmp_store.add(item)
        updated = tmp_store.update(item.id, title="New", content="New content")
        assert updated.title == "New"
        assert updated.content == "New content"

    def test_update_missing_raises(self, tmp_store):
        with pytest.raises(KeyError):
            tmp_store.update("bad-id", title="X")

    def test_delete_existing(self, tmp_store):
        item = KnowledgeItem(title="T", content="C", category="engineering")
        tmp_store.add(item)
        assert tmp_store.delete(item.id) is True
        assert tmp_store.get(item.id) is None

    def test_delete_missing_returns_false(self, tmp_store):
        assert tmp_store.delete("nonexistent") is False

    def test_count(self, populated_store):
        assert populated_store.count() == 3

    def test_all_returns_list(self, populated_store):
        items = populated_store.all()
        assert len(items) == 3

    def test_clear(self, populated_store):
        populated_store.clear()
        assert populated_store.count() == 0

    def test_persistence_across_instances(self, tmp_path):
        path = tmp_path / "persist.json"
        s1 = MemoryStore(path)
        item = KnowledgeItem(title="Persist", content="C", category="engineering")
        s1.add(item)

        s2 = MemoryStore(path)
        assert s2.get(item.id) is not None
        assert s2.get(item.id).title == "Persist"

    def test_atomic_write_produces_valid_json(self, tmp_path):
        path = tmp_path / "atomic.json"
        store = MemoryStore(path)
        store.add(KnowledgeItem(title="T", content="C", category="engineering"))
        data = json.loads(path.read_text())
        assert "items" in data
        assert len(data["items"]) == 1

    def test_corrupt_file_recovers_to_empty(self, tmp_path):
        path = tmp_path / "corrupt.json"
        path.write_text("NOT JSON {{{{")
        store = MemoryStore(path)
        assert store.count() == 0


# ---------------------------------------------------------------------------
# KnowledgeRetriever tests
# ---------------------------------------------------------------------------

class TestKnowledgeRetriever:
    def test_search_returns_ranked_results(self, populated_store):
        retriever = KnowledgeRetriever(populated_store)
        results = retriever.search("react hooks")
        assert len(results) > 0
        assert results[0]["item"].title == "React useEffect cleanup"

    def test_search_no_query_returns_all(self, populated_store):
        retriever = KnowledgeRetriever(populated_store)
        results = retriever.search()
        assert len(results) == 3

    def test_search_with_category_filter(self, populated_store):
        retriever = KnowledgeRetriever(populated_store)
        results = retriever.search(category="design")
        assert all(r["item"].category == "design" for r in results)
        assert len(results) == 1

    def test_search_with_tag_filter(self, populated_store):
        retriever = KnowledgeRetriever(populated_store)
        results = retriever.search(tags=["postgres"])
        assert len(results) == 1
        assert "postgres" in results[0]["item"].tags

    def test_search_limit_respected(self, populated_store):
        retriever = KnowledgeRetriever(populated_store)
        results = retriever.search(limit=1)
        assert len(results) == 1

    def test_get_by_category(self, populated_store):
        retriever = KnowledgeRetriever(populated_store)
        items = retriever.get_by_category("engineering")
        assert len(items) == 2

    def test_get_by_category_case_insensitive(self, populated_store):
        retriever = KnowledgeRetriever(populated_store)
        assert retriever.get_by_category("ENGINEERING") == retriever.get_by_category("engineering")

    def test_get_by_tag(self, populated_store):
        retriever = KnowledgeRetriever(populated_store)
        items = retriever.get_by_tag("react")
        assert len(items) == 1

    def test_list_categories(self, populated_store):
        retriever = KnowledgeRetriever(populated_store)
        cats = retriever.list_categories()
        assert "engineering" in cats
        assert "design" in cats

    def test_list_tags(self, populated_store):
        retriever = KnowledgeRetriever(populated_store)
        tags = retriever.list_tags()
        assert "react" in tags
        assert "postgres" in tags

    def test_related_excludes_self(self, populated_store):
        retriever = KnowledgeRetriever(populated_store)
        item_id = populated_store.all()[0].id
        related = retriever.related(item_id)
        assert all(r["item"].id != item_id for r in related)

    def test_related_missing_item_returns_empty(self, populated_store):
        retriever = KnowledgeRetriever(populated_store)
        assert retriever.related("no-such-id") == []

    def test_empty_store_search_returns_empty(self, tmp_store):
        retriever = KnowledgeRetriever(tmp_store)
        assert retriever.search("anything") == []


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

class TestCLI:
    def _run(self, args, store_path):
        return cli_main(["--store", str(store_path)] + args)

    def test_add_and_stats(self, tmp_path, capsys):
        path = tmp_path / "cli.json"
        rc = self._run(
            ["add", "--title", "CLI Test", "--content", "Some content",
             "--category", "engineering", "--tags", "cli", "test"],
            path,
        )
        assert rc == 0
        rc2 = self._run(["stats"], path)
        assert rc2 == 0
        out = capsys.readouterr().out
        assert "1" in out

    def test_search_finds_item(self, tmp_path, capsys):
        path = tmp_path / "cli.json"
        self._run(
            ["add", "--title", "Search Me", "--content", "findable content",
             "--category", "engineering"],
            path,
        )
        rc = self._run(["search", "findable"], path)
        assert rc == 0
        out = capsys.readouterr().out
        assert "Search Me" in out

    def test_get_existing_item(self, tmp_path, capsys):
        path = tmp_path / "cli.json"
        store = MemoryStore(path)
        item = KnowledgeItem(title="Get Me", content="content", category="engineering")
        store.add(item)

        rc = self._run(["get", item.id], path)
        assert rc == 0
        out = capsys.readouterr().out
        assert "Get Me" in out

    def test_get_missing_returns_nonzero(self, tmp_path):
        path = tmp_path / "cli.json"
        MemoryStore(path)  # create file
        rc = self._run(["get", "00000000-0000-0000-0000-000000000000"], path)
        assert rc != 0

    def test_delete_item(self, tmp_path, capsys):
        path = tmp_path / "cli.json"
        store = MemoryStore(path)
        item = KnowledgeItem(title="Delete Me", content="bye", category="engineering")
        store.add(item)

        rc = self._run(["delete", item.id], path)
        assert rc == 0
        assert MemoryStore(path).count() == 0

    def test_list_all(self, tmp_path, capsys):
        path = tmp_path / "cli.json"
        store = MemoryStore(path)
        store.add(KnowledgeItem(title="A", content="c", category="engineering"))
        store.add(KnowledgeItem(title="B", content="c", category="design"))

        rc = self._run(["list"], path)
        assert rc == 0
        out = capsys.readouterr().out
        assert "A" in out
        assert "B" in out

    def test_list_filtered_by_category(self, tmp_path, capsys):
        path = tmp_path / "cli.json"
        store = MemoryStore(path)
        store.add(KnowledgeItem(title="Eng Item", content="c", category="engineering"))
        store.add(KnowledgeItem(title="Design Item", content="c", category="design"))

        self._run(["list", "--category", "engineering"], path)
        out = capsys.readouterr().out
        assert "Eng Item" in out
        assert "Design Item" not in out

    def test_tags_command(self, tmp_path, capsys):
        path = tmp_path / "cli.json"
        store = MemoryStore(path)
        store.add(KnowledgeItem(title="T", content="c", category="e", tags=["alpha", "beta"]))

        rc = self._run(["tags"], path)
        assert rc == 0
        out = capsys.readouterr().out
        assert "alpha" in out
        assert "beta" in out

    def test_categories_command(self, tmp_path, capsys):
        path = tmp_path / "cli.json"
        store = MemoryStore(path)
        store.add(KnowledgeItem(title="T", content="c", category="protocols"))

        rc = self._run(["categories"], path)
        assert rc == 0
        assert "protocols" in capsys.readouterr().out

    def test_update_command(self, tmp_path, capsys):
        path = tmp_path / "cli.json"
        store = MemoryStore(path)
        item = KnowledgeItem(title="Old Title", content="c", category="engineering")
        store.add(item)

        rc = self._run(["update", item.id, "--title", "New Title"], path)
        assert rc == 0
        assert MemoryStore(path).get(item.id).title == "New Title"

"""
Command-line interface for the Second Brain system.

Usage examples:
    python -m second_brain add --title "React hooks" --content "..." --category engineering --tags react hooks
    python -m second_brain search "react performance"
    python -m second_brain list --category engineering
    python -m second_brain get <id>
    python -m second_brain delete <id>
    python -m second_brain related <id>
    python -m second_brain tags
    python -m second_brain categories
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from .knowledge import KnowledgeItem
from .memory import MemoryStore, DEFAULT_STORE_PATH
from .retrieval import KnowledgeRetriever


def _make_store(store_path: Optional[str]) -> MemoryStore:
    path = Path(store_path) if store_path else DEFAULT_STORE_PATH
    return MemoryStore(path)


def _print_item(item: KnowledgeItem, verbose: bool = False) -> None:
    print(f"[{item.id[:8]}] {item.title}  ({item.category})")
    if item.tags:
        print(f"  tags: {', '.join(item.tags)}")
    if verbose:
        print(f"  {item.content}")
        print(f"  created: {item.created_at}  updated: {item.updated_at}")


# ------------------------------------------------------------------
# Sub-command handlers
# ------------------------------------------------------------------

def cmd_add(args, store: MemoryStore) -> int:
    item = KnowledgeItem(
        title=args.title,
        content=args.content,
        category=args.category,
        tags=args.tags or [],
        metadata=json.loads(args.metadata) if args.metadata else {},
    )
    store.add(item)
    print(f"Added: [{item.id}] {item.title}")
    return 0


def cmd_get(args, store: MemoryStore) -> int:
    item = store.get(args.id)
    if item is None:
        print(f"Not found: {args.id}", file=sys.stderr)
        return 1
    _print_item(item, verbose=True)
    return 0


def cmd_update(args, store: MemoryStore) -> int:
    kwargs = {}
    if args.title:
        kwargs["title"] = args.title
    if args.content:
        kwargs["content"] = args.content
    if args.category:
        kwargs["category"] = args.category
    if args.tags is not None:
        kwargs["tags"] = args.tags
    try:
        item = store.update(args.id, **kwargs)
        print(f"Updated: [{item.id}] {item.title}")
        return 0
    except KeyError as exc:
        print(str(exc), file=sys.stderr)
        return 1


def cmd_delete(args, store: MemoryStore) -> int:
    removed = store.delete(args.id)
    if removed:
        print(f"Deleted: {args.id}")
        return 0
    print(f"Not found: {args.id}", file=sys.stderr)
    return 1


def cmd_search(args, store: MemoryStore) -> int:
    retriever = KnowledgeRetriever(store)
    results = retriever.search(
        query=args.query,
        category=args.category,
        tags=args.tags,
        limit=args.limit,
    )
    if not results:
        print("No results found.")
        return 0
    for r in results:
        print(f"[score={r['score']:.2f}] ", end="")
        _print_item(r["item"])
    return 0


def cmd_list(args, store: MemoryStore) -> int:
    retriever = KnowledgeRetriever(store)
    items = retriever.get_by_category(args.category) if args.category else store.all()
    if not items:
        print("No items found.")
        return 0
    for item in items:
        _print_item(item)
    print(f"\nTotal: {len(items)}")
    return 0


def cmd_related(args, store: MemoryStore) -> int:
    retriever = KnowledgeRetriever(store)
    results = retriever.related(args.id, limit=args.limit)
    if not results:
        print("No related items found.")
        return 0
    for r in results:
        print(f"[score={r['score']:.2f}] ", end="")
        _print_item(r["item"])
    return 0


def cmd_tags(args, store: MemoryStore) -> int:
    retriever = KnowledgeRetriever(store)
    tags = retriever.list_tags()
    print("\n".join(tags) if tags else "No tags found.")
    return 0


def cmd_categories(args, store: MemoryStore) -> int:
    retriever = KnowledgeRetriever(store)
    cats = retriever.list_categories()
    print("\n".join(cats) if cats else "No categories found.")
    return 0


def cmd_stats(args, store: MemoryStore) -> int:
    retriever = KnowledgeRetriever(store)
    print(f"Total items : {store.count()}")
    print(f"Categories  : {', '.join(retriever.list_categories()) or 'none'}")
    print(f"Unique tags : {len(retriever.list_tags())}")
    print(f"Store path  : {store.store_path}")
    return 0


# ------------------------------------------------------------------
# Argument parser
# ------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="second_brain",
        description="Second Brain — persistent knowledge store for agency agents",
    )
    parser.add_argument(
        "--store", metavar="PATH", help="Path to the JSON store file (overrides default)"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = sub.add_parser("add", help="Add a knowledge item")
    p_add.add_argument("--title", required=True)
    p_add.add_argument("--content", required=True)
    p_add.add_argument("--category", required=True)
    p_add.add_argument("--tags", nargs="*", default=[])
    p_add.add_argument("--metadata", help="JSON string of extra metadata")

    # get
    p_get = sub.add_parser("get", help="Get a knowledge item by ID")
    p_get.add_argument("id")

    # update
    p_upd = sub.add_parser("update", help="Update a knowledge item")
    p_upd.add_argument("id")
    p_upd.add_argument("--title")
    p_upd.add_argument("--content")
    p_upd.add_argument("--category")
    p_upd.add_argument("--tags", nargs="*")

    # delete
    p_del = sub.add_parser("delete", help="Delete a knowledge item by ID")
    p_del.add_argument("id")

    # search
    p_search = sub.add_parser("search", help="Search knowledge items")
    p_search.add_argument("query", nargs="?", default="")
    p_search.add_argument("--category")
    p_search.add_argument("--tags", nargs="*")
    p_search.add_argument("--limit", type=int, default=10)

    # list
    p_list = sub.add_parser("list", help="List all knowledge items")
    p_list.add_argument("--category", help="Filter by category")

    # related
    p_rel = sub.add_parser("related", help="Find related items")
    p_rel.add_argument("id")
    p_rel.add_argument("--limit", type=int, default=5)

    # tags
    sub.add_parser("tags", help="List all tags")

    # categories
    sub.add_parser("categories", help="List all categories")

    # stats
    sub.add_parser("stats", help="Show store statistics")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    store = _make_store(getattr(args, "store", None))

    handlers = {
        "add": cmd_add,
        "get": cmd_get,
        "update": cmd_update,
        "delete": cmd_delete,
        "search": cmd_search,
        "list": cmd_list,
        "related": cmd_related,
        "tags": cmd_tags,
        "categories": cmd_categories,
        "stats": cmd_stats,
    }
    return handlers[args.command](args, store)


if __name__ == "__main__":
    sys.exit(main())

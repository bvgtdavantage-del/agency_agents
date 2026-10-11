"""
Tests for .claude-plugin/marketplace.json: every agent file is published once and loads in Claude Code.
"""

import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


@pytest.fixture(scope="module")
def marketplace():
    return json.loads(MARKETPLACE.read_text())


def published_files(marketplace):
    files = []
    for plugin in marketplace["plugins"]:
        source = (ROOT / plugin["source"]).resolve()
        files.extend((source / path).resolve() for path in plugin["agents"])
    return files


def frontmatter(path):
    match = re.match(r"^---\n(.*?)\n---\n", path.read_text(), re.S)
    assert match, f"{path.relative_to(ROOT)} has no YAML frontmatter"
    return yaml.safe_load(match.group(1))


def test_marketplace_identity(marketplace):
    assert KEBAB.match(marketplace["name"])
    assert marketplace["owner"]["name"]


def test_plugin_names_are_unique_kebab_case(marketplace):
    names = [plugin["name"] for plugin in marketplace["plugins"]]
    assert len(names) == len(set(names))
    assert all(KEBAB.match(name) for name in names)


def test_plugin_sources_exist(marketplace):
    for plugin in marketplace["plugins"]:
        assert plugin["source"].startswith("./")
        assert (ROOT / plugin["source"]).is_dir(), plugin["source"]


def test_agent_paths_are_relative_md_files_that_exist(marketplace):
    for plugin in marketplace["plugins"]:
        for path in plugin["agents"]:
            assert path.startswith("./") and path.endswith(".md"), path
        for path in published_files({"plugins": [plugin]}):
            assert path.is_file(), path


def test_every_agent_file_is_published_exactly_once(marketplace):
    published = published_files(marketplace)
    on_disk = sorted(p.resolve() for p in (ROOT / "agents").glob("*/*.md"))
    assert len(published) == len(set(published))
    assert sorted(published) == on_disk


def test_published_agents_have_name_and_description(marketplace):
    for path in published_files(marketplace):
        meta = frontmatter(path)
        assert meta.get("name"), path
        assert meta.get("description"), path

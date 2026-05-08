#!/usr/bin/env python3
"""
install.py — One-shot installer for agency_agents.

What it does:
  1. Verifies Python >= 3.8
  2. Installs the Python packages (agency_agents, second_brain, hackingtool)
  3. Copies all agent .md files from agents/ → ~/.claude/agents/
  4. Copies protocol .md files from protocols/ → ~/.claude/protocols/

Usage:
    python install.py [--dry-run] [--no-packages] [--no-agents] [--no-protocols]
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


# ── Colour helpers (no external deps) ─────────────────────────────────────────

BOLD  = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED   = "\033[31m"
CYAN  = "\033[36m"
DIM   = "\033[2m"
RESET = "\033[0m"


def _supports_color() -> bool:
    import os
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def ok(msg: str) -> None:
    prefix = f"{GREEN}✔{RESET} " if _supports_color() else "[ok] "
    print(prefix + msg)


def info(msg: str) -> None:
    prefix = f"{CYAN}→{RESET} " if _supports_color() else "[..] "
    print(prefix + msg)


def warn(msg: str) -> None:
    prefix = f"{YELLOW}!{RESET} " if _supports_color() else "[!!] "
    print(prefix + msg)


def err(msg: str) -> None:
    prefix = f"{RED}✖{RESET} " if _supports_color() else "[ERR] "
    print(prefix + msg, file=sys.stderr)


def header(msg: str) -> None:
    if _supports_color():
        print(f"\n{BOLD}{CYAN}{msg}{RESET}")
    else:
        print(f"\n=== {msg} ===")


# ── Steps ─────────────────────────────────────────────────────────────────────

def check_python() -> None:
    header("Checking Python version")
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 8):
        err(f"Python 3.8+ is required (found {major}.{minor})")
        sys.exit(1)
    ok(f"Python {major}.{minor} — OK")


def install_packages(repo_root: Path, dry_run: bool) -> None:
    header("Installing Python packages")
    cmd = [sys.executable, "-m", "pip", "install", "-e", str(repo_root), "--quiet"]
    info("Running: " + " ".join(cmd))
    if dry_run:
        warn("(dry-run) skipping pip install")
        return
    result = subprocess.run(cmd)
    if result.returncode != 0:
        err("pip install failed — see output above")
        sys.exit(result.returncode)
    ok("Packages installed (agency_agents, second_brain, hackingtool)")


def _copy_tree(src_dir: Path, dst_dir: Path, pattern: str, dry_run: bool) -> int:
    """Copy matching files from src_dir into dst_dir, preserving subdirectory structure."""
    files = list(src_dir.rglob(pattern))
    if not files:
        warn(f"No {pattern!r} files found in {src_dir}")
        return 0

    copied = 0
    for src in files:
        rel = src.relative_to(src_dir)
        dst = dst_dir / rel
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        info(f"  {'(dry-run) ' if dry_run else ''}{'~/' + str(dst.relative_to(Path.home()))}")
        copied += 1
    return copied


def install_agents(repo_root: Path, dry_run: bool) -> None:
    header("Installing Claude agent definitions")
    src = repo_root / "agents"
    dst = Path.home() / ".claude" / "agents"
    if not src.exists():
        warn(f"agents/ directory not found at {src} — skipping")
        return

    info(f"Source : {src}")
    info(f"Target : {dst}")

    if not dry_run:
        dst.mkdir(parents=True, exist_ok=True)

    count = _copy_tree(src, dst, "*.md", dry_run)
    ok(f"Installed {count} agent file(s) → {dst}")


def install_protocols(repo_root: Path, dry_run: bool) -> None:
    header("Installing protocol documentation")
    src = repo_root / "protocols"
    dst = Path.home() / ".claude" / "protocols"
    if not src.exists():
        warn(f"protocols/ directory not found at {src} — skipping")
        return

    info(f"Source : {src}")
    info(f"Target : {dst}")

    if not dry_run:
        dst.mkdir(parents=True, exist_ok=True)

    count = _copy_tree(src, dst, "*.md", dry_run)
    ok(f"Installed {count} protocol file(s) → {dst}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Install agency_agents, agents, and protocols.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would happen without making any changes")
    parser.add_argument("--no-packages", action="store_true",
                        help="Skip pip install step")
    parser.add_argument("--no-agents", action="store_true",
                        help="Skip copying agent .md files to ~/.claude/agents/")
    parser.add_argument("--no-protocols", action="store_true",
                        help="Skip copying protocol .md files to ~/.claude/protocols/")
    args = parser.parse_args()

    repo_root = Path(__file__).parent.resolve()

    if args.dry_run:
        warn("DRY-RUN mode — no files will be written")

    check_python()

    if not args.no_packages:
        install_packages(repo_root, args.dry_run)

    if not args.no_agents:
        install_agents(repo_root, args.dry_run)

    if not args.no_protocols:
        install_protocols(repo_root, args.dry_run)

    header("Done")
    ok("Installation complete.")
    if not args.no_packages:
        print(f"\n{DIM}CLI commands now available:{RESET}")
        print("  second-brain --help")
        print("  hackingtool  --help")
    return 0


if __name__ == "__main__":
    sys.exit(main())

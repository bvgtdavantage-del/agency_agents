#!/usr/bin/env python3
"""
install.py — One-shot installer for agency_agents.

What it does:
  1. Verifies Python >= 3.8
  2. Installs the Python packages (agency_agents, second_brain, hackingtool)
  3. Copies all agent .md files from agents/ → ~/.claude/agents/
  4. Copies protocol .md files from protocols/ → ~/.claude/protocols/
  5. Clones Z4nzu/hackingtool → ~/.claude/tools/hackingtool/
     and creates a launcher at ~/.local/bin/hackingtool-menu

Usage:
    python install.py [--dry-run] [--no-packages] [--no-agents]
                      [--no-protocols] [--no-z4nzu]
"""

import argparse
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path


# ── Colour helpers (no external deps) ─────────────────────────────────────────

BOLD   = "\033[1m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
CYAN   = "\033[36m"
DIM    = "\033[2m"
RESET  = "\033[0m"

Z4NZU_REPO = "https://github.com/Z4nzu/hackingtool.git"
Z4NZU_DIR  = Path.home() / ".claude" / "tools" / "hackingtool"
LAUNCHER   = Path.home() / ".local" / "bin" / "hackingtool-menu"


def _supports_color() -> bool:
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


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, **kwargs)


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
        info(f"  {'(dry-run) ' if dry_run else ''}~/{dst.relative_to(Path.home())}")
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


def _check_git() -> bool:
    return shutil.which("git") is not None


def _clone_or_update(dry_run: bool) -> bool:
    """Clone Z4nzu/hackingtool or pull latest if already present. Returns True on success."""
    if Z4NZU_DIR.exists():
        info(f"Found existing clone at {Z4NZU_DIR} — pulling latest")
        if not dry_run:
            try:
                _run(["git", "-C", str(Z4NZU_DIR), "pull", "--quiet"])
            except subprocess.CalledProcessError:
                warn("git pull failed — using existing clone")
        else:
            warn("(dry-run) skipping git pull")
    else:
        info(f"Cloning {Z4NZU_REPO}")
        info(f"  → {Z4NZU_DIR}")
        if not dry_run:
            Z4NZU_DIR.parent.mkdir(parents=True, exist_ok=True)
            try:
                _run(["git", "clone", "--depth=1", "--quiet", Z4NZU_REPO, str(Z4NZU_DIR)])
            except subprocess.CalledProcessError:
                err("git clone failed")
                return False
        else:
            warn("(dry-run) skipping git clone")
    return True


def _setup_venv(dry_run: bool) -> Path:
    """Create venv inside the Z4nzu clone and install its dependencies."""
    venv_dir = Z4NZU_DIR / ".venv"
    python_bin = venv_dir / "bin" / "python"
    pip_bin    = venv_dir / "bin" / "pip"

    if not dry_run:
        if not venv_dir.exists():
            info("Creating virtual environment")
            _run([sys.executable, "-m", "venv", str(venv_dir)])

        req = Z4NZU_DIR / "requirements.txt"
        if req.exists():
            info("Installing dependencies (rich)")
            _run([str(pip_bin), "install", "-q", "-r", str(req)])
        else:
            info("Installing rich directly")
            _run([str(pip_bin), "install", "-q", "rich>=13.0.0"])
    else:
        warn("(dry-run) skipping venv creation and pip install")

    return python_bin


def _write_launcher(python_bin: Path, dry_run: bool) -> None:
    """Write a shell launcher at ~/.local/bin/hackingtool-menu."""
    entry = Z4NZU_DIR / "hackingtool.py"
    script = f"""#!/usr/bin/env bash
# Launcher for Z4nzu/hackingtool (interactive menu)
exec "{python_bin}" "{entry}" "$@"
"""
    info(f"Writing launcher → {LAUNCHER}")
    if dry_run:
        warn("(dry-run) skipping launcher write")
        return

    LAUNCHER.parent.mkdir(parents=True, exist_ok=True)
    LAUNCHER.write_text(script)
    LAUNCHER.chmod(LAUNCHER.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def install_z4nzu(dry_run: bool) -> None:
    header("Installing Z4nzu/hackingtool (interactive menu)")

    if not _check_git():
        err("git is not installed — cannot clone Z4nzu/hackingtool")
        warn("Install git and re-run, or pass --no-z4nzu to skip")
        return

    if not _clone_or_update(dry_run):
        return

    python_bin = _setup_venv(dry_run)
    _write_launcher(python_bin, dry_run)

    ok(f"Z4nzu/hackingtool installed → {Z4NZU_DIR}")
    ok(f"Launcher  → {LAUNCHER}")

    # Remind user to add ~/.local/bin to PATH if needed
    path_dirs = os.environ.get("PATH", "").split(":")
    if str(LAUNCHER.parent) not in path_dirs and not dry_run:
        warn(f"{LAUNCHER.parent} is not in $PATH")
        warn("Add this to your shell rc file:")
        warn(f'  export PATH="$HOME/.local/bin:$PATH"')


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Install agency_agents, agents, protocols, and Z4nzu/hackingtool.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would happen without making any changes")
    parser.add_argument("--no-packages", action="store_true",
                        help="Skip pip install step")
    parser.add_argument("--no-agents", action="store_true",
                        help="Skip copying agent .md files to ~/.claude/agents/")
    parser.add_argument("--no-protocols", action="store_true",
                        help="Skip copying protocol .md files to ~/.claude/protocols/")
    parser.add_argument("--no-z4nzu", action="store_true",
                        help="Skip cloning Z4nzu/hackingtool")
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

    if not args.no_z4nzu:
        install_z4nzu(args.dry_run)

    header("Done")
    ok("Installation complete.")

    print(f"\n{DIM}CLI commands available:{RESET}")
    if not args.no_packages:
        print("  second-brain       --help   # persistent knowledge base")
        print("  hackingtool        --help   # recon / web / crypto / CTF")
    if not args.no_z4nzu:
        print("  hackingtool-menu           # Z4nzu interactive menu (185+ tools)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

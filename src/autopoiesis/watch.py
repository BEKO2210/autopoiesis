"""Poll a project tree and install the post-commit heartbeat hook."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from pathlib import Path

from autopoiesis.model import ApoError

DEFAULT_IGNORE: frozenset[str] = frozenset(
    {".git", ".apo", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
)

_HOOK = """#!/bin/sh
# autopoiesis-hook
apo tick --quiet || true
"""
_MARKER = "# autopoiesis-hook"


def snapshot(root: Path, ignore: frozenset[str] = DEFAULT_IGNORE) -> dict[str, tuple[float, int]]:
    """Map each file to ``(mtime, size)``.

    Ignored directory names are not walked. A resolved git HEAD, when present, is stored
    under ``.git/HEAD`` as ``(0.0, int(sha, 16))`` so a new commit changes the snapshot.
    """
    found: dict[str, tuple[float, int]] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in ignore]
        for filename in filenames:
            path = Path(dirpath) / filename
            try:
                stat = path.stat()
            except OSError:
                continue
            found[path.relative_to(root).as_posix()] = (stat.st_mtime, stat.st_size)
    sha = _head_commit(root)
    if sha is not None:
        found[".git/HEAD"] = (0.0, int(sha, 16))
    return found


def watch(
    root: Path,
    on_change: Callable[[], None],
    interval: float = 2.0,
    stop: Callable[[], bool] = lambda: False,
) -> None:
    """Poll ``root`` and call ``on_change`` when the snapshot differs.

    The first snapshot is only a baseline, so it never calls ``on_change``.
    """
    previous = snapshot(root)
    while not stop():
        time.sleep(interval)
        if stop():
            return
        current = snapshot(root)
        if current != previous:
            previous = current
            on_change()


def install_hook(root: Path) -> Path:
    """Create an executable ``.git/hooks/post-commit`` that runs ``apo tick --quiet``.

    A hook that already contains ``# autopoiesis-hook`` is left in place. Any other
    existing hook raises ``ApoError`` instead of being overwritten.
    """
    git_dir = _git_dir(Path(root))
    if git_dir is None:
        raise ApoError("not a git repository")
    hook = git_dir / "hooks" / "post-commit"
    try:
        hook.parent.mkdir(parents=True, exist_ok=True)
        if hook.exists():
            if not hook.is_file():
                raise ApoError(f"refusing to overwrite {hook}")
            current = hook.read_text(encoding="utf-8", errors="replace")
            if _MARKER not in current:
                raise ApoError(f"refusing to overwrite {hook}")
        else:
            hook.write_text(_HOOK, encoding="utf-8")
        hook.chmod(hook.stat().st_mode | 0o111)
    except ApoError:
        raise
    except OSError as exc:
        raise ApoError(f"cannot install hook: {exc}") from exc
    return hook


def _git_dir(root: Path) -> Path | None:
    git = root / ".git"
    if git.is_dir():
        return git
    if not git.is_file():
        return None
    try:
        text = git.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not text.startswith("gitdir:"):
        return None
    target = Path(text.split(":", 1)[1].strip())
    if not target.is_absolute():
        target = root / target
    target = target.resolve()
    return target if target.is_dir() else None


def _head_commit(root: Path) -> str | None:
    git_dir = _git_dir(root)
    if git_dir is None:
        return None
    try:
        text = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if text.startswith("ref:"):
        return _resolve_ref(git_dir, text.split(":", 1)[1].strip())
    if _is_sha(text):
        return text.lower()
    return None


def _resolve_ref(git_dir: Path, ref: str) -> str | None:
    loose = git_dir / ref
    try:
        text = loose.read_text(encoding="utf-8").strip()
    except OSError:
        text = ""
    if _is_sha(text):
        return text.lower()
    try:
        lines = (git_dir / "packed-refs").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        if not line or line[0] in "#^":
            continue
        sha, _, name = line.partition(" ")
        if name == ref and _is_sha(sha):
            return sha.lower()
    return None


def _is_sha(text: str) -> bool:
    return len(text) == 40 and all(char in "0123456789abcdefABCDEF" for char in text)

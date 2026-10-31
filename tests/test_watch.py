"""Watcher tests using a temporary directory and a stop callback."""

import os

import pytest

from autopoiesis.model import ApoError
from autopoiesis.watch import DEFAULT_IGNORE, install_hook, snapshot, watch


def test_default_ignore_names():
    assert DEFAULT_IGNORE == frozenset(
        {".git", ".apo", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
    )


def test_snapshot_skips_ignored_dirs_and_records_size(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("hello")
    nested = tmp_path / "pkg" / "node_modules"
    nested.mkdir(parents=True)
    (nested / "junk.js").write_text("nope")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "a.pyc").write_bytes(b"xyz")
    found = snapshot(tmp_path)
    assert found["src/a.py"][1] == len("hello")
    assert all("node_modules" not in key and "__pycache__" not in key for key in found)
    assert ".git/HEAD" not in found


def test_snapshot_tracks_resolved_head(tmp_path):
    git = tmp_path / ".git"
    (git / "refs" / "heads").mkdir(parents=True)
    (git / "HEAD").write_text("ref: refs/heads/main\n")
    first = "a" * 40
    (git / "refs" / "heads" / "main").write_text(first + "\n")
    (git / "objects").mkdir()
    (git / "objects" / "pack").write_text("hidden")
    before = snapshot(tmp_path)
    assert before[".git/HEAD"] == (0.0, int(first, 16))
    assert "objects/pack" not in before
    second = "b" * 40
    (git / "refs" / "heads" / "main").unlink()
    (git / "packed-refs").write_text(f"# pack\n{second} refs/heads/main\n")
    after = snapshot(tmp_path)
    assert after[".git/HEAD"] == (0.0, int(second, 16))
    assert before != after


def test_snapshot_detached_and_gitfile(tmp_path):
    real = tmp_path / "real.git"
    real.mkdir()
    sha = "c" * 40
    (real / "HEAD").write_text(sha + "\n")
    work = tmp_path / "work"
    work.mkdir()
    (work / ".git").write_text(f"gitdir: {real}\n")
    (work / "note.txt").write_text("n")
    found = snapshot(work)
    assert found[".git/HEAD"][1] == int(sha, 16)
    assert found["note.txt"][1] == 1


def test_watch_does_not_fire_on_baseline_or_ignored_noise(tmp_path, monkeypatch):
    (tmp_path / "a.txt").write_text("one")
    calls: list[int] = []
    sleeps = {"n": 0}

    def fake_sleep(_interval: float) -> None:
        sleeps["n"] += 1
        if sleeps["n"] == 1:
            noise = tmp_path / "node_modules"
            noise.mkdir()
            (noise / "x.js").write_text("ignored")

    monkeypatch.setattr("autopoiesis.watch.time.sleep", fake_sleep)

    def stop() -> bool:
        return sleeps["n"] >= 2

    watch(tmp_path, lambda: calls.append(1), interval=9, stop=stop)
    assert calls == []


def test_watch_fires_once_on_change_then_stops(tmp_path, monkeypatch):
    (tmp_path / "a.txt").write_text("one")
    calls: list[int] = []
    sleeps = {"n": 0}

    def fake_sleep(_interval: float) -> None:
        sleeps["n"] += 1
        if sleeps["n"] == 1:
            (tmp_path / "a.txt").write_text("two!!")

    monkeypatch.setattr("autopoiesis.watch.time.sleep", fake_sleep)

    def stop() -> bool:
        return bool(calls) or sleeps["n"] >= 3

    watch(tmp_path, lambda: calls.append(1), interval=9, stop=stop)
    assert calls == [1]


def test_watch_stop_before_sleep(tmp_path):
    calls: list[int] = []
    watch(tmp_path, lambda: calls.append(1), stop=lambda: True)
    assert calls == []


def test_install_hook_is_idempotent_and_refuses_foreign_hooks(tmp_path):
    with pytest.raises(ApoError):
        install_hook(tmp_path)
    git = tmp_path / ".git"
    git.mkdir()
    hook = install_hook(tmp_path)
    assert hook == git / "hooks" / "post-commit"
    text = hook.read_text()
    assert "# autopoiesis-hook" in text
    assert "apo tick --quiet || true" in text
    assert os.access(hook, os.X_OK)
    hook.chmod(0o644)
    again = install_hook(tmp_path)
    assert again.read_text() == text
    assert os.access(again, os.X_OK)
    hook.write_text("#!/bin/sh\necho other\n")
    with pytest.raises(ApoError):
        install_hook(tmp_path)
    assert hook.read_text() == "#!/bin/sh\necho other\n"


def test_install_hook_follows_gitdir_file(tmp_path):
    real = tmp_path / "real.git"
    (real / "hooks").mkdir(parents=True)
    work = tmp_path / "work"
    work.mkdir()
    (work / ".git").write_text("gitdir: ../real.git\n")
    hook = install_hook(work)
    assert hook == (real / "hooks" / "post-commit").resolve()
    assert hook.stat().st_mode & 0o111

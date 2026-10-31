"""CLI tests. Skipped until the kernel (and mutator) modules exist."""

import sys

import pytest

pytest.importorskip("autopoiesis.kernel")
pytest.importorskip("autopoiesis.mutator")

from autopoiesis.cli import main


def test_command_flow(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["status"]) == 1
    assert capsys.readouterr().err.strip()

    assert main(["init", "--goal", "Ship the thing"]) == 0
    assert (tmp_path / ".apo").is_dir()
    assert (tmp_path / "constitution.toml").is_file()
    capsys.readouterr()

    assert (
        main(
            [
                "add",
                "Check",
                "--verify",
                "true",
                "--run",
                "true",
                "--instruction",
                "do it",
                "--obsolete",
                "false",
            ]
        )
        == 0
    )
    cid = capsys.readouterr().out.strip()
    assert cid.startswith("c-")
    assert main(["add", "After", "--verify", "true", "--dep", cid]) == 0
    capsys.readouterr()

    assert main(["status"]) == 0
    status = capsys.readouterr().out
    assert "goal: Ship the thing" in status
    assert "energy:" in status
    assert "tick:" in status
    assert "Check" in status
    assert cid in status

    assert main(["next"]) == 0
    assert cid in capsys.readouterr().out

    assert main(["show", cid]) == 0
    shown = capsys.readouterr().out
    assert "do it" in shown
    assert "true" in shown

    assert main(["run", cid]) == 0
    assert capsys.readouterr().out.splitlines()[0] == "ok"

    assert main(["tick"]) == 0
    capsys.readouterr()
    assert main(["tick", "--quiet"]) == 0
    assert capsys.readouterr().out == ""

    assert main(["graph"]) == 0
    assert "flowchart TD" in capsys.readouterr().out
    assert main(["graph", "--format", "dot"]) == 0
    dot = capsys.readouterr().out
    assert "digraph cells" in dot
    assert "->" in dot

    assert main(["log", "-n", "10"]) == 0
    assert "born" in capsys.readouterr().out

    assert main(["fitness"]) == 0
    assert main(["ratify"]) == 0
    capsys.readouterr()

    assert main(["approve", "c-missing"]) == 1
    assert capsys.readouterr().err.strip()
    assert main(["hook", "install"]) == 1
    assert capsys.readouterr().err.strip()


def test_commands_use_parent_apo_directory(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--goal", "Nested"]) == 0
    sub = tmp_path / "sub"
    sub.mkdir()
    monkeypatch.chdir(sub)
    capsys.readouterr()
    assert main(["status"]) == 0
    assert "goal: Nested" in capsys.readouterr().out
    assert not (sub / ".apo").exists()


def test_color_respects_tty_and_no_color(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--goal", "g"]) == 0
    assert main(["add", "Paint", "--verify", "true"]) == 0
    capsys.readouterr()
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert main(["status"]) == 0
    assert "\033[32m" in capsys.readouterr().out
    monkeypatch.setenv("NO_COLOR", "1")
    assert main(["status"]) == 0
    assert "\033[" not in capsys.readouterr().out


def test_ctrl_c_exits_zero(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["init"]) == 0

    def _raise(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr("autopoiesis.cli.watch", _raise)
    assert main(["watch"]) == 0

"""Command-line interface for the autopoiesis kernel."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from autopoiesis.kernel import Kernel
from autopoiesis.model import ApoError, NotInitialized, UnknownCell
from autopoiesis.mutator import from_env
from autopoiesis.render import render_dot, render_events, render_mermaid, render_tree
from autopoiesis.watch import install_hook, watch


def main(argv: list[str] | None = None) -> int:
    """Run one ``apo`` command. ``ApoError`` prints one line and returns 1."""
    parser = _parser()
    try:
        args = parser.parse_args(argv)
        return int(args.func(args))
    except ApoError as exc:
        message = str(exc).strip() or exc.__class__.__name__
        print(message.splitlines()[0], file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    except SystemExit as exc:
        code = exc.code
        if code is None or code == 0:
            return 0
        if isinstance(code, int):
            return code
        return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="apo")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create constitution.toml and .apo/")
    init.add_argument("--goal", default="")
    init.set_defaults(func=_cmd_init)

    add = sub.add_parser("add", help="add a cell")
    add.add_argument("title")
    add.add_argument("--verify", required=True, metavar="CMD")
    add.add_argument("--run", metavar="CMD")
    add.add_argument("--instruction", default="")
    add.add_argument("--dep", action="append", default=[], metavar="ID")
    add.add_argument("--obsolete", metavar="CMD")
    add.set_defaults(func=_cmd_add)

    status = sub.add_parser("status", help="show goal, energy, tick, and the tree")
    status.set_defaults(func=_cmd_status)

    nxt = sub.add_parser("next", help="show the next ready cell")
    nxt.set_defaults(func=_cmd_next)

    show = sub.add_parser("show", help="show one cell")
    show.add_argument("id")
    show.set_defaults(func=_cmd_show)

    run = sub.add_parser("run", help="run one cell")
    run.add_argument("id")
    run.set_defaults(func=_cmd_run)

    tick = sub.add_parser("tick", help="run one heartbeat")
    tick.add_argument("--quiet", action="store_true")
    tick.set_defaults(func=_cmd_tick)

    watching = sub.add_parser("watch", help="tick whenever the tree changes")
    watching.add_argument("--interval", type=float, default=2.0)
    watching.set_defaults(func=_cmd_watch)

    approve = sub.add_parser("approve", help="release a quarantined cell")
    approve.add_argument("id")
    approve.set_defaults(func=_cmd_approve)

    ratify = sub.add_parser("ratify", help="accept the current constitution")
    ratify.set_defaults(func=_cmd_ratify)

    fitness = sub.add_parser("fitness", help="run fitness checks")
    fitness.set_defaults(func=_cmd_fitness)

    graph = sub.add_parser("graph", help="print the cell graph")
    graph.add_argument("--format", choices=("mermaid", "dot"), default="mermaid")
    graph.set_defaults(func=_cmd_graph)

    log = sub.add_parser("log", help="print recent events")
    log.add_argument("-n", type=int, default=50)
    log.set_defaults(func=_cmd_log)

    hook = sub.add_parser("hook", help="git hook helpers")
    hook_sub = hook.add_subparsers(dest="hook_command", required=True)
    install = hook_sub.add_parser("install", help="install the post-commit hook")
    install.set_defaults(func=_cmd_hook_install)
    return parser


def _cmd_init(args: argparse.Namespace) -> int:
    start = Path.cwd().resolve()
    root = start
    for candidate in (start, *start.parents):
        if (candidate / ".apo").is_dir():
            root = candidate
            break
    kernel = Kernel.init(root, goal=args.goal)
    print(kernel.root)
    return 0


def _cmd_add(args: argparse.Namespace) -> int:
    cell = _open().add(
        args.title,
        args.verify,
        instruction=args.instruction,
        run_cmd=args.run,
        obsolete_cmd=args.obsolete,
        deps=args.dep,
    )
    print(cell.id)
    return 0


def _cmd_status(_args: argparse.Namespace) -> int:
    kernel = _open()
    cells = kernel.store.cells()
    pressure = {cell.id: kernel.pressure(cell.id) for cell in cells}
    print(f"goal: {kernel.constitution.goal}")
    print(f"energy: {_energy(kernel.store.energy())}")
    print(f"tick: {kernel.store.tick_no()}")
    _emit(render_tree(cells, pressure, color=_use_color()))
    return 0


def _cmd_next(_args: argparse.Namespace) -> int:
    ready = _open().ready()
    if not ready:
        print("none")
        return 0
    cell = ready[0]
    print(f"{cell.id} {cell.title}")
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    kernel = _open()
    cell = kernel.store.get(args.id)
    if cell is None:
        raise UnknownCell(args.id)
    print(f"id: {cell.id}")
    print(f"title: {cell.title}")
    print(f"state: {cell.state}")
    print(f"pressure: {kernel.pressure(cell.id)}")
    print(f"verify: {cell.verify_cmd}")
    if cell.run_cmd:
        print(f"run: {cell.run_cmd}")
    if cell.instruction:
        print(f"instruction: {cell.instruction}")
    if cell.obsolete_cmd:
        print(f"obsolete: {cell.obsolete_cmd}")
    if cell.parent_id:
        print(f"parent: {cell.parent_id}")
    if cell.deps:
        print("deps: " + ", ".join(cell.deps))
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    result = _open().run(args.id)
    print("ok" if result.ok else "fail")
    tail = result.output.strip()
    if tail:
        print(tail)
    return 0


def _cmd_tick(args: argparse.Namespace) -> int:
    events = _open().tick()
    if not args.quiet:
        _emit(render_events(events))
    return 0


def _cmd_watch(args: argparse.Namespace) -> int:
    kernel = _open()

    def on_change() -> None:
        _emit(render_events(kernel.tick()))

    watch(kernel.root, on_change, interval=args.interval)
    return 0


def _cmd_approve(args: argparse.Namespace) -> int:
    _open().approve(args.id)
    print(f"approved {args.id}")
    return 0


def _cmd_ratify(_args: argparse.Namespace) -> int:
    _open().ratify()
    print("ratified")
    return 0


def _cmd_fitness(_args: argparse.Namespace) -> int:
    for name, passed in _open().fitness().items():
        print(f"{'pass' if passed else 'fail'} {name}")
    return 0


def _cmd_graph(args: argparse.Namespace) -> int:
    cells = _open().store.cells()
    if args.format == "dot":
        _emit(render_dot(cells))
    else:
        _emit(render_mermaid(cells))
    return 0


def _cmd_log(args: argparse.Namespace) -> int:
    _emit(render_events(_open().store.events(limit=args.n)))
    return 0


def _cmd_hook_install(_args: argparse.Namespace) -> int:
    print(install_hook(_find_root(Path.cwd())))
    return 0


def _open() -> Kernel:
    return Kernel(_find_root(Path.cwd()), mutator=from_env())


def _find_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".apo").is_dir():
            return candidate
    raise NotInitialized("no .apo/ directory; run `apo init`")


def _use_color() -> bool:
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


def _energy(value: float) -> str:
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:g}"


def _emit(text: str) -> None:
    if not text:
        return
    print(text, end="" if text.endswith("\n") else "\n", flush=True)

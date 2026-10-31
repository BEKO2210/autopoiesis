"""Text, Mermaid, and Graphviz views of the cell graph."""

from __future__ import annotations

import json
import time

from autopoiesis.model import Cell, Event

_HIDDEN = frozenset({"dead", "fused"})
_BADGE = {"active": "32", "done": "36", "quarantined": "33"}


def render_tree(cells: list[Cell], pressure: dict[str, int], color: bool = False) -> str:
    """Parent/child tree. Dead and fused cells are omitted."""
    visible = [cell for cell in cells if cell.state not in _HIDDEN]
    known = {cell.id for cell in visible}
    kids: dict[str, list[Cell]] = {}
    roots: list[Cell] = []
    for cell in visible:
        if cell.parent_id in known:
            kids.setdefault(cell.parent_id, []).append(cell)
        else:
            roots.append(cell)
    roots.sort(key=_order)
    for group in kids.values():
        group.sort(key=_order)
    lines: list[str] = []

    def walk(cell: Cell, prefix: str, last: bool | None) -> None:
        connector = "" if last is None else ("└── " if last else "├── ")
        lines.append(f"{prefix}{connector}{_body(cell, pressure, color)}")
        child_prefix = prefix
        if last is True:
            child_prefix = f"{prefix}    "
        elif last is False:
            child_prefix = f"{prefix}│   "
        children = kids.get(cell.id, [])
        for index, child in enumerate(children):
            walk(child, child_prefix, index == len(children) - 1)

    for root in roots:
        walk(root, "", None)
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def render_mermaid(cells: list[Cell]) -> str:
    """Flowchart of visible cells. An edge means the source is a dependency."""
    visible = sorted((cell for cell in cells if cell.state not in _HIDDEN), key=_order)
    known = {cell.id for cell in visible}
    lines = ["flowchart TD"]
    for cell in visible:
        label = _quote(f"{cell.title} [{cell.state}]")
        lines.append(f'  {_node(cell.id)}["{label}"]')
    for cell in visible:
        for dep in cell.deps:
            if dep in known:
                lines.append(f"  {_node(dep)} --> {_node(cell.id)}")
    return "\n".join(lines) + "\n"


def render_dot(cells: list[Cell]) -> str:
    """Graphviz digraph. An edge means the source is a dependency."""
    visible = sorted((cell for cell in cells if cell.state not in _HIDDEN), key=_order)
    known = {cell.id for cell in visible}
    lines = ["digraph cells {"]
    for cell in visible:
        label = _quote(f"{cell.title}\\n{cell.state}")
        lines.append(f'  "{cell.id}" [label="{label}"];')
    for cell in visible:
        for dep in cell.deps:
            if dep in known:
                lines.append(f'  "{dep}" -> "{cell.id}";')
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_events(events: list[Event]) -> str:
    """One line per event: local time, kind, cell id, compact detail."""
    if not events:
        return ""
    return "\n".join(_event_line(event) for event in events) + "\n"


def _order(cell: Cell) -> tuple[float, str]:
    return (cell.created_at, cell.id)


def _body(cell: Cell, pressure: dict[str, int], color: bool) -> str:
    deps = ", ".join(cell.deps)
    badge = _badge(cell.state, color)
    text = f"{badge} {cell.id} {cell.title}  p={pressure.get(cell.id, 0)}  deps: {deps}"
    return text.rstrip()


def _badge(state: str, color: bool) -> str:
    label = f"[{state}]"
    code = _BADGE.get(state)
    if not color or code is None:
        return label
    return f"\033[{code}m{label}\033[0m"


def _node(cell_id: str) -> str:
    return "n" + "".join(ch if ch.isalnum() else "_" for ch in cell_id)


def _quote(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def _event_line(event: Event) -> str:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(event.at))
    cell_id = event.cell_id or "-"
    detail = _compact(event.detail)
    if detail:
        return f"{stamp} {event.kind} {cell_id} {detail}"
    return f"{stamp} {event.kind} {cell_id}"


def _compact(detail: dict) -> str:
    return " ".join(f"{key}={_value(detail[key])}" for key in sorted(detail))


def _value(value: object) -> str:
    if isinstance(value, str):
        return value.replace("\n", " ").replace("\r", " ")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)

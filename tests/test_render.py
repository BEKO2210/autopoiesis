"""Pure renderer tests."""

import time

from autopoiesis.model import Cell, Event
from autopoiesis.render import render_dot, render_events, render_mermaid, render_tree


def _cell(**kwargs) -> Cell:
    data = {"id": "c-000001", "title": "T", "verify_cmd": "true", "state": "active"}
    data.update(kwargs)
    return Cell(**data)


def test_tree_hides_dead_and_fused_and_draws_children():
    cells = [
        _cell(id="c-000001", title="Root", created_at=1),
        _cell(id="c-000002", title="Left", parent_id="c-000001", created_at=2),
        _cell(
            id="c-000003",
            title="Deep",
            parent_id="c-000002",
            created_at=3,
            deps=["c-000002"],
        ),
        _cell(id="c-000004", title="Right", state="done", parent_id="c-000001", created_at=4),
        _cell(id="c-000005", title="Gone", state="dead", parent_id="c-000001", created_at=5),
        _cell(id="c-000006", title="Absorbed", state="fused", created_at=6),
    ]
    pressure = {cell.id: 1 for cell in cells}
    pressure["c-000001"] = 4
    text = render_tree(cells, pressure)
    assert (
        text
        == """\
[active] c-000001 Root  p=4  deps:
├── [active] c-000002 Left  p=1  deps:
│   └── [active] c-000003 Deep  p=1  deps: c-000002
└── [done] c-000004 Right  p=1  deps:
"""
    )
    assert "\033[" not in text
    assert "Gone" not in text
    assert "Absorbed" not in text


def test_tree_color_and_orphan_of_dead_parent():
    live = _cell(id="c-live00", title="Live", parent_id="c-dead00")
    dead = _cell(id="c-dead00", title="Gone", state="dead")
    text = render_tree([dead, live], {"c-live00": 2}, color=True)
    assert text == "\033[32m[active]\033[0m c-live00 Live  p=2  deps:\n"
    quarantine = render_tree(
        [_cell(id="c-qqqqqq", title="Hold", state="quarantined")], {}, color=True
    )
    assert quarantine.startswith("\033[33m[quarantined]\033[0m")
    assert "p=0" in quarantine


def test_tree_orders_siblings_by_creation():
    later = _cell(id="c-aaaaaa", title="Later", created_at=2)
    earlier = _cell(id="c-bbbbbb", title="Earlier", created_at=1)
    text = render_tree([later, earlier], {})
    assert text.index("Earlier") < text.index("Later")


def test_mermaid_and_dot_skip_hidden_cells():
    cells = [
        _cell(id="c-aaaaaa", title='A "x"', created_at=1),
        _cell(id="c-bbbbbb", title="B", state="done", created_at=2, deps=["c-aaaaaa"]),
        _cell(id="c-cccccc", title="Dead", state="dead", created_at=3, deps=["c-aaaaaa"]),
    ]
    mermaid = render_mermaid(cells)
    assert mermaid.startswith("flowchart TD\n")
    assert 'nc_aaaaaa["A \\"x\\" [active]"]' in mermaid
    assert "nc_aaaaaa --> nc_bbbbbb" in mermaid
    assert "Dead" not in mermaid
    dot = render_dot(cells)
    assert dot.startswith("digraph cells {\n")
    assert '"c-aaaaaa" -> "c-bbbbbb";' in dot
    assert "Dead" not in dot
    assert dot.endswith("}\n")


def test_events_are_one_local_line():
    when = 1_700_000_000.0
    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(when))
    events = [
        Event(at=when, kind="born", cell_id="c-000001", detail={"title": "Parent\nline"}),
        Event(at=when, kind="ratified", cell_id=None, detail={}),
        Event(at=when, kind="fitness_pass", cell_id=None, detail={"ok": True, "n": 2}),
    ]
    text = render_events(events)
    assert text == (
        f"{stamp} born c-000001 title=Parent line\n"
        f"{stamp} ratified -\n"
        f"{stamp} fitness_pass - n=2 ok=true\n"
    )
    assert render_events([]) == ""

from __future__ import annotations

from autopoiesis.kernel import Kernel


def test_store_read_api_and_ordering(tmp_path):
    kernel = Kernel.init(tmp_path, goal="Ship it")
    first = kernel.add("first", "true", instruction="one")
    second = kernel.add("second", "true", deps=[first.id], parent_id=first.id)

    assert kernel.constitution.goal == "Ship it"
    assert kernel.store.get(first.id).verify_cmd == "true"
    assert [cell.id for cell in kernel.store.cells(["active"])] == [first.id, second.id]
    assert [cell.id for cell in kernel.store.children(first.id)] == [second.id]
    assert [cell.id for cell in kernel.store.dependents(first.id)] == [second.id]
    assert kernel.store.versions(first.id)[0].origin == "birth"
    assert kernel.store.energy() == 100
    assert kernel.store.tick_no() == 0
    assert [event.kind for event in kernel.store.events()] == ["born", "born"]


def test_store_wal_foreign_keys_and_output_tail(tmp_path):
    kernel = Kernel.init(tmp_path)
    cell = kernel.add("tail", "verify")
    kernel.runner = lambda cmd, cwd, timeout: (1, "x" * 5000)
    kernel.run(cell.id)

    assert kernel.store.conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert kernel.store.conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    run = kernel.store.runs(cell.id)[0]
    assert len(run.output) == 4000
    assert not run.ok

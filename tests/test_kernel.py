from __future__ import annotations

import re
from dataclasses import dataclass, field

import pytest

import autopoiesis.kernel as kernel_module
from autopoiesis.kernel import Kernel
from autopoiesis.model import ChildSpec, ConstitutionTampered, Gradient, Quarantined


@dataclass
class FakeRunner:
    codes: dict[str, int] = field(default_factory=dict)
    default: int = 1
    calls: list[str] = field(default_factory=list)

    def __call__(self, cmd, cwd, timeout):
        self.calls.append(cmd)
        return self.codes.get(cmd, self.default), f"output:{cmd}"


@dataclass
class FakeMutator:
    children: list[ChildSpec] = field(default_factory=list)
    gradients: list[Gradient | None] = field(default_factory=list)

    def split(self, cell, failure_log, max_children):
        return self.children[:max_children]

    def critique(self, cell, failure_log, upstream):
        return self.gradients.pop(0) if self.gradients else None


def configure(kernel: Kernel, **values) -> None:
    path = kernel.root / "constitution.toml"
    text = path.read_text()
    for key, value in values.items():
        encoded = str(value).lower() if isinstance(value, bool) else str(value)
        text, count = re.subn(rf"^{key} = .*$", f"{key} = {encoded}", text, flags=re.MULTILINE)
        assert count == 1
    path.write_text(text)
    kernel.ratify()


def test_sense_marks_done_and_rewards(tmp_path):
    kernel = Kernel.init(tmp_path)
    runner = FakeRunner({"verify": 0})
    kernel.runner = runner
    cell = kernel.add("cell", "verify")

    events = kernel.tick()

    assert kernel.store.get(cell.id).state == "done"
    assert kernel.store.energy() == 120
    assert {event.kind for event in events} >= {"run_ok", "completed"}


def test_mitosis_children_quarantined_and_parent_requires_own_verify(tmp_path):
    kernel = Kernel.init(tmp_path)
    configure(kernel, fail_streak_for_mitosis=2)
    runner = FakeRunner({"parent": 1, "child-a": 0, "child-b": 0})
    kernel.runner = runner
    kernel.mutator = FakeMutator(
        children=[
            ChildSpec("a", "child-a", run_cmd="do-a"),
            ChildSpec("b", "child-b", run_cmd="do-b"),
        ]
    )
    parent = kernel.add("parent", "parent")

    kernel.run(parent.id)
    kernel.run(parent.id)
    children = kernel.store.children(parent.id)
    assert len(children) == 2
    assert {child.state for child in children} == {"quarantined"}
    assert set(kernel.store.get(parent.id).deps) == {child.id for child in children}
    assert kernel.store.get(parent.id).state == "active"

    for child in children:
        with pytest.raises(Quarantined):
            kernel.run(child.id)
        kernel.approve(child.id)
        runner.codes[child.run_cmd] = 0
        kernel.run(child.id)
    assert kernel.store.get(parent.id).state == "active"
    runner.codes["parent"] = 0
    kernel.run(parent.id)
    assert kernel.store.get(parent.id).state == "done"


def test_recombination_can_mutate_direct_dependency_and_verify_is_immutable(tmp_path):
    kernel = Kernel.init(tmp_path)
    configure(kernel, fail_streak_for_mitosis=99)
    dependency = kernel.add("dep", "dep-contract", instruction="old")
    cell = kernel.add("cell", "fail", deps=[dependency.id])
    kernel.runner = FakeRunner({"fail": 1})
    kernel.mutator = FakeMutator(
        gradients=[Gradient(dependency.id, "improved", "upstream caused failure")]
    )

    kernel.run(cell.id)

    changed = kernel.store.get(dependency.id)
    assert changed.instruction == "improved"
    assert changed.verify_cmd == "dep-contract"
    assert [version.origin for version in kernel.store.versions(dependency.id)] == [
        "birth",
        "mutation",
    ]


def test_oscillation_and_cooldown_are_rejected(tmp_path):
    kernel = Kernel.init(tmp_path)
    configure(kernel, fail_streak_for_mitosis=99, mutation_cooldown_ticks=2)
    cell = kernel.add("cell", "fail", instruction="original")
    kernel.runner = FakeRunner({"fail": 1})
    kernel.mutator = FakeMutator(
        gradients=[
            Gradient(cell.id, "changed", "first"),
            Gradient(cell.id, "another", "too soon"),
            Gradient(cell.id, "original", "go back"),
        ]
    )

    kernel.run(cell.id)
    kernel.run(cell.id)
    assert kernel.store.events()[0].detail["reason"] == "cooldown"
    kernel.tick()
    kernel.tick()
    kernel.run(cell.id)
    assert kernel.store.events()[0].detail["reason"] == "oscillation"
    assert kernel.store.get(cell.id).instruction == "changed"


def test_energy_denied_and_process_caps(tmp_path):
    empty = Kernel.init(tmp_path / "empty")
    configure(empty, fail_streak_for_mitosis=99)
    cell = empty.add("cell", "fail")
    empty.runner = FakeRunner()
    empty.mutator = FakeMutator(gradients=[Gradient(cell.id, "new", "costly")])
    with empty.store.conn:
        empty.store.set_meta("energy", 0)
    empty.run(cell.id)
    assert empty.store.get(cell.id).instruction == ""
    assert empty.store.events()[0].kind == "energy_denied"

    capped = Kernel.init(tmp_path / "capped")
    configure(capped, fail_streak_for_mitosis=1, max_cells=1)
    parent = capped.add("parent", "fail")
    capped.runner = FakeRunner()
    capped.mutator = FakeMutator(children=[ChildSpec("child", "child")])
    capped.run(parent.id)
    assert capped.store.children(parent.id) == []
    assert any(event.detail.get("limit") == "max_cells" for event in capped.store.events())

    depth = Kernel.init(tmp_path / "depth")
    configure(depth, fail_streak_for_mitosis=1, max_depth=0)
    parent = depth.add("parent", "fail")
    depth.runner = FakeRunner()
    depth.mutator = FakeMutator(children=[ChildSpec("child", "child")])
    depth.run(parent.id)
    assert depth.store.children(parent.id) == []
    assert any(event.detail.get("limit") == "max_depth" for event in depth.store.events())

    children = Kernel.init(tmp_path / "children")
    configure(children, fail_streak_for_mitosis=1, max_children=1)
    parent = children.add("parent", "fail")
    children.runner = FakeRunner()
    children.mutator = FakeMutator(
        children=[ChildSpec("one", "one"), ChildSpec("two", "two")]
    )
    children.run(parent.id)
    assert len(children.store.children(parent.id)) == 1


def test_rollback_restores_previous_dna_and_makes_bad_dna_taboo(tmp_path):
    kernel = Kernel.init(tmp_path)
    configure(kernel, fail_streak_for_mitosis=99, rollback_window=1, mutation_cooldown_ticks=0)
    cell = kernel.add("cell", "fail", instruction="good")
    kernel.runner = FakeRunner({"fail": 1})
    kernel.mutator = FakeMutator(gradients=[Gradient(cell.id, "bad", "try")])
    kernel.run(cell.id)
    with kernel.store.conn:
        kernel.store.conn.execute(
            """INSERT INTO runs(cell_id, version, ok, exit_code, duration_s, output, at)
               VALUES (?, 1, 1, 0, 0, '', ?)""",
            (cell.id, kernel_module.time.time() + 1),
        )
    kernel.mutator = FakeMutator()
    kernel.run(cell.id)
    kernel.tick()

    restored = kernel.store.get(cell.id)
    assert restored.instruction == "good"
    assert kernel.store.versions(cell.id)[-1].origin == "rollback"
    assert any(event.kind == "rollback" for event in kernel.store.events())

    kernel.mutator = FakeMutator(gradients=[Gradient(cell.id, "bad", "retry")])
    kernel.run(cell.id)
    assert kernel.store.events()[0].detail["reason"] == "taboo"


def test_apoptosis_obsolete_parent_done_and_idle(tmp_path, monkeypatch):
    clock = [1_000_000.0]
    monkeypatch.setattr(kernel_module.time, "time", lambda: clock[0])
    kernel = Kernel.init(tmp_path)
    configure(kernel, idle_ttl_days=1)
    runner = FakeRunner({"obsolete": 0, "parent": 0, "child": 1, "block": 1, "idle": 1})
    kernel.runner = runner
    obsolete = kernel.add("obsolete", "never", obsolete_cmd="obsolete")
    parent = kernel.add("parent", "parent")
    child = kernel.add("child", "child", parent_id=parent.id)
    blocker = kernel.add("blocker", "block")
    idle = kernel.add("idle", "idle", deps=[blocker.id])
    clock[0] += 2 * 86400

    kernel.tick()

    assert kernel.store.get(obsolete.id).state == "dead"
    assert kernel.store.get(parent.id).state == "done"
    assert kernel.store.get(child.id).state == "dead"
    assert kernel.store.get(idle.id).state == "dead"
    reasons = {
        event.cell_id: event.detail["reason"]
        for event in kernel.store.events()
        if event.kind == "apoptosis"
    }
    assert reasons[obsolete.id] == "obsolete_cmd"
    assert reasons[child.id] == "parent_done"
    assert reasons[idle.id] == "idle"


def test_fusion_of_successful_two_cell_chain(tmp_path):
    kernel = Kernel.init(tmp_path)
    configure(kernel, fusion_after=2, idle_ttl_days=0)
    first = kernel.add("first", "verify-a", run_cmd="run-a")
    second = kernel.add("second", "verify-b", run_cmd="run-b", deps=[first.id])
    kernel.runner = FakeRunner(
        {"run-a": 0, "verify-a": 0, "run-b": 0, "verify-b": 0}
    )
    for _ in range(2):
        kernel.run(first.id)
        kernel.run(second.id)

    kernel.tick()

    assert kernel.store.get(first.id).state == "fused"
    assert kernel.store.get(second.id).state == "fused"
    fused = kernel.store.cells(["active"])[0]
    assert fused.run_cmd == "(run-a) && (run-b)"
    assert fused.verify_cmd == "(verify-a) && (verify-b)"


def test_constitution_tamper_requires_ratification(tmp_path):
    kernel = Kernel.init(tmp_path)
    cell = kernel.add("cell", "verify")
    path = tmp_path / "constitution.toml"
    path.write_text(path.read_text().replace("initial_energy = 100", "initial_energy = 101"))

    with pytest.raises(ConstitutionTampered):
        kernel.tick()
    with pytest.raises(ConstitutionTampered):
        kernel.run(cell.id)
    kernel.ratify()
    kernel.runner = FakeRunner({"verify": 0})
    kernel.run(cell.id)
    assert kernel.store.get(cell.id).state == "done"


def test_fitness_refuses_tampered_constitution(tmp_path):
    from autopoiesis.kernel import Kernel
    from autopoiesis.model import ConstitutionTampered

    kernel = Kernel.init(tmp_path)
    with (tmp_path / "constitution.toml").open("a") as fh:
        fh.write('\n[[fitness]]\nname = "x"\ncmd = "true"\n')
    with pytest.raises(ConstitutionTampered):
        Kernel(tmp_path).fitness()
    assert kernel.store.energy() == 100


def test_empty_split_falls_back_to_recombination(tmp_path):
    from autopoiesis.kernel import Kernel
    from autopoiesis.model import Gradient

    class NoSplit:
        def split(self, cell, failure_log, max_children):
            return []

        def critique(self, cell, failure_log, upstream):
            return Gradient(cell.id, "try harder", "split gave nothing")

    Kernel.init(tmp_path)
    kernel = Kernel(tmp_path, mutator=NoSplit(), runner=lambda cmd, cwd, timeout: (1, "no"))
    cell = kernel.add("t", "false")
    kernel.run(cell.id)
    kernel.run(cell.id)
    assert kernel.store.get(cell.id).instruction == "try harder"
    assert kernel.store.children(cell.id) == []

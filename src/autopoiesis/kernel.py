"""Transactional graph processes and the three hard kernel laws."""

from __future__ import annotations

import hashlib
import json
import secrets
import subprocess
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from .constitution import TEMPLATE, Constitution, load
from .model import (
    ApoError,
    Cell,
    ConstitutionTampered,
    Event,
    Gradient,
    Mutator,
    NotInitialized,
    NullMutator,
    Quarantined,
    RunResult,
    UnknownCell,
)
from .store import Store

Runner = Callable[[str, Path, float], tuple[int, str]]


def run_shell(cmd: str, cwd: Path, timeout: float) -> tuple[int, str]:
    """Run a shell command, returning its exit status and combined output tail."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result.returncode, result.stdout[-4000:]
    except subprocess.TimeoutExpired as error:
        output = error.stdout or ""
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        return 124, output[-4000:]


def _dna_hash(instruction: str, run_cmd: str | None) -> str:
    raw = json.dumps([instruction, run_cmd], separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


class Kernel:
    """The deterministic autopoiesis kernel."""

    @classmethod
    def init(cls, root: Path, goal: str = "") -> Kernel:
        root = root.resolve()
        root.mkdir(parents=True, exist_ok=True)
        constitution_path = root / "constitution.toml"
        if not constitution_path.exists():
            content = TEMPLATE
            if goal:
                encoded = json.dumps(goal, ensure_ascii=False)
                content = content.replace('"Describe the real project goal here."', encoded, 1)
            constitution_path.write_text(content)
        (root / ".apo").mkdir(exist_ok=True)
        database_path = root / ".apo" / "cells.db"
        if not database_path.exists():
            Store(database_path).close()
        kernel = cls(root)
        with kernel.store.conn:
            if kernel.store.meta("constitution_sha") is None:
                kernel.store.set_meta("constitution_sha", kernel.constitution.sha256)
            if kernel.store.meta("energy") is None:
                kernel.store.set_meta("energy", kernel.constitution.budget["initial_energy"])
            if kernel.store.meta("tick_no") is None:
                kernel.store.set_meta("tick_no", 0)
        return kernel

    def __init__(
        self,
        root: Path,
        mutator: Mutator | None = None,
        runner: Runner | None = None,
    ):
        self.root = root.resolve()
        constitution_path = self.root / "constitution.toml"
        database_path = self.root / ".apo" / "cells.db"
        if not constitution_path.exists() or not database_path.exists():
            raise NotInitialized(f"not initialized: {self.root}")
        self.constitution: Constitution = load(constitution_path)
        self.store = Store(database_path)
        self.mutator = mutator or NullMutator()
        self.runner = runner or run_shell

    def _check_constitution(self) -> None:
        current = load(self.root / "constitution.toml")
        expected = self.store.meta("constitution_sha")
        if expected != current.sha256:
            raise ConstitutionTampered("constitution.toml changed; run `apo ratify`")
        self.constitution = current

    def _new_id(self) -> str:
        while True:
            cell_id = f"c-{secrets.token_hex(3)}"
            if self.store.get(cell_id) is None:
                return cell_id

    def _insert_cell(self, cell: Cell, origin: str = "birth", reason: str = "") -> None:
        self.store.conn.execute(
            """INSERT INTO cells(
                   id, title, verify_cmd, instruction, run_cmd, obsolete_cmd, parent_id,
                   state, depth, version, fail_streak, created_at, updated_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                cell.id,
                cell.title,
                cell.verify_cmd,
                cell.instruction,
                cell.run_cmd,
                cell.obsolete_cmd,
                cell.parent_id,
                cell.state,
                cell.depth,
                cell.version,
                cell.fail_streak,
                cell.created_at,
                cell.updated_at,
            ),
        )
        self.store.conn.executemany(
            "INSERT INTO deps(cell_id, dep_id) VALUES (?, ?)",
            [(cell.id, dep_id) for dep_id in cell.deps],
        )
        self.store.conn.execute(
            """INSERT INTO versions(
                   cell_id, version, instruction, run_cmd, origin, reason, dna_hash, at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                cell.id,
                cell.version,
                cell.instruction,
                cell.run_cmd,
                origin,
                reason,
                _dna_hash(cell.instruction, cell.run_cmd),
                cell.created_at,
            ),
        )
        self.store.event(cell.created_at, "born", cell.id, {"title": cell.title})

    def add(
        self,
        title: str,
        verify_cmd: str,
        *,
        instruction: str = "",
        run_cmd: str | None = None,
        obsolete_cmd: str | None = None,
        deps: Sequence[str] = (),
        parent_id: str | None = None,
    ) -> Cell:
        dep_ids = list(dict.fromkeys(deps))
        for dep_id in dep_ids:
            if self.store.get(dep_id) is None:
                raise UnknownCell(dep_id)
        parent = None
        if parent_id is not None:
            parent = self.store.get(parent_id)
            if parent is None:
                raise UnknownCell(parent_id)
        now = time.time()
        limit = None
        if len(self.store.cells(["active", "quarantined"])) >= int(
            self.constitution.limits["max_cells"]
        ):
            limit = "max_cells"
        elif parent and parent.depth + 1 > int(self.constitution.limits["max_depth"]):
            limit = "max_depth"
        elif parent and len(self.store.children(parent.id)) >= int(
            self.constitution.limits["max_children"]
        ):
            limit = "max_children"
        if limit:
            with self.store.conn:
                self.store.event(now, "limit_reached", parent_id, {"limit": limit})
            raise ApoError(f"limit reached: {limit}")
        cell = Cell(
            id=self._new_id(),
            title=title,
            verify_cmd=verify_cmd,
            instruction=instruction,
            run_cmd=run_cmd,
            obsolete_cmd=obsolete_cmd,
            parent_id=parent_id,
            depth=parent.depth + 1 if parent else 0,
            deps=dep_ids,
            created_at=now,
            updated_at=now,
        )
        with self.store.conn:
            self._insert_cell(cell)
        return cell

    def ready(self) -> list[Cell]:
        ready = []
        for cell in self.store.cells(["active"]):
            deps = [self.store.get(dep_id) for dep_id in cell.deps]
            if all(dep is not None and dep.state == "done" for dep in deps):
                ready.append(cell)
        return sorted(ready, key=lambda item: (-self.pressure(item.id), item.created_at, item.id))

    def pressure(self, cell_id: str) -> int:
        if self.store.get(cell_id) is None:
            raise UnknownCell(cell_id)
        seen: set[str] = set()
        pending = [cell_id]
        active = 0
        while pending:
            current = pending.pop()
            for dependent in self.store.dependents(current):
                if dependent.id in seen:
                    continue
                seen.add(dependent.id)
                pending.append(dependent.id)
                if dependent.state == "active":
                    active += 1
        return 1 + active

    def _command(self, cmd: str) -> tuple[int, str, float]:
        started = time.monotonic()
        code, output = self.runner(
            cmd, self.root, float(self.constitution.trust["command_timeout_s"])
        )
        return code, output[-4000:], time.monotonic() - started

    def _record_run(
        self,
        cell: Cell,
        ok: bool,
        exit_code: int,
        duration: float,
        output: str,
        now: float,
    ) -> RunResult:
        result = RunResult(cell.id, cell.version, ok, exit_code, duration, output[-4000:], now)
        self.store.conn.execute(
            """INSERT INTO runs(cell_id, version, ok, exit_code, duration_s, output, at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                result.cell_id,
                result.version,
                int(result.ok),
                result.exit_code,
                result.duration_s,
                result.output,
                result.at,
            ),
        )
        self.store.event(now, "run_ok" if ok else "run_failed", cell.id, {"exit_code": exit_code})
        return result

    def _complete(self, cell: Cell, now: float) -> None:
        if cell.state != "done":
            self.store.conn.execute(
                "UPDATE cells SET state='done', fail_streak=0, updated_at=? WHERE id=?",
                (now, cell.id),
            )
            self._change_energy(float(self.constitution.budget["reward_per_done"]))
            self.store.event(now, "completed", cell.id)

    def _change_energy(self, amount: float) -> None:
        self.store.set_meta("energy", self.store.energy() + amount)

    def _spend(self, amount: float, cell_id: str, process: str, now: float) -> bool:
        if self.store.energy() < amount:
            self.store.event(now, "energy_denied", cell_id, {"process": process, "cost": amount})
            return False
        self._change_energy(-amount)
        return True

    def run(self, cell_id: str) -> RunResult:
        self._check_constitution()
        cell = self.store.get(cell_id)
        if cell is None:
            raise UnknownCell(cell_id)
        if cell.state == "quarantined":
            raise Quarantined(cell_id)
        if cell.state not in {"active", "done"}:
            raise ApoError(f"cell cannot run in state {cell.state}: {cell_id}")
        with self.store.conn:
            output_parts: list[str] = []
            duration = 0.0
            run_code = 0
            if cell.run_cmd:
                run_code, output, elapsed = self._command(cell.run_cmd)
                output_parts.append(output)
                duration += elapsed
            verify_code, output, elapsed = self._command(cell.verify_cmd)
            output_parts.append(output)
            duration += elapsed
            ok = run_code == 0 and verify_code == 0
            exit_code = verify_code if run_code == 0 else run_code
            now = time.time()
            result = self._record_run(cell, ok, exit_code, duration, "\n".join(output_parts), now)
            if ok:
                self._complete(cell, now)
            else:
                streak = cell.fail_streak + 1
                self.store.conn.execute(
                    "UPDATE cells SET fail_streak=?, updated_at=? WHERE id=?",
                    (streak, now, cell.id),
                )
                cell.fail_streak = streak
                if streak >= int(self.constitution.limits["fail_streak_for_mitosis"]):
                    if not self._mitosis(cell, result.output, now):
                        self._recombine(cell, result.output, now)
                else:
                    self._recombine(cell, result.output, now)
        return result

    def _mitosis(self, parent: Cell, failure_log: str, now: float) -> bool:
        limits = self.constitution.limits
        if parent.depth >= int(limits["max_depth"]):
            self.store.event(now, "limit_reached", parent.id, {"limit": "max_depth"})
            return False
        existing = self.store.children(parent.id)
        remaining_children = int(limits["max_children"]) - len(existing)
        live_count = len(self.store.cells(["active", "quarantined"]))
        remaining_cells = int(limits["max_cells"]) - live_count
        allowed = min(remaining_children, remaining_cells)
        if allowed <= 0:
            limit = "max_children" if remaining_children <= 0 else "max_cells"
            self.store.event(now, "limit_reached", parent.id, {"limit": limit})
            return False
        cost = float(self.constitution.budget["mitosis_cost"])
        if not self._spend(cost, parent.id, "mitosis", now):
            return False
        specs = self.mutator.split(parent, failure_log, allowed)[:allowed]
        if not specs:
            self._change_energy(cost)
            return True
        auto_approve = bool(self.constitution.trust["auto_approve_llm_commands"])
        child_ids = []
        for spec in specs:
            child = Cell(
                id=self._new_id(),
                title=spec.title,
                verify_cmd=spec.verify_cmd,
                instruction=spec.instruction,
                run_cmd=spec.run_cmd,
                parent_id=parent.id,
                state="active" if auto_approve else "quarantined",
                depth=parent.depth + 1,
                deps=list(parent.deps),
                created_at=now,
                updated_at=now,
            )
            self._insert_cell(child, reason=f"mitosis from {parent.id}")
            child_ids.append(child.id)
            self.store.conn.execute(
                "INSERT OR IGNORE INTO deps(cell_id, dep_id) VALUES (?, ?)",
                (parent.id, child.id),
            )
            if child.state == "quarantined":
                self.store.event(now, "quarantined", child.id, {"reason": "llm_command"})
        self.store.conn.execute(
            "UPDATE cells SET fail_streak=0, updated_at=? WHERE id=?", (now, parent.id)
        )
        self.store.event(now, "mitosis", parent.id, {"children": child_ids})
        return True

    def _recombine(self, cell: Cell, failure_log: str, now: float) -> None:
        upstream = [dep for dep_id in cell.deps if (dep := self.store.get(dep_id)) is not None]
        gradient = self.mutator.critique(cell, failure_log, upstream)
        if gradient is None:
            return
        allowed = {cell.id, *cell.deps}
        if gradient.target_id not in allowed:
            self.store.event(now, "rejected", cell.id, {"reason": "invalid_target"})
            return
        target = self.store.get(gradient.target_id)
        if target is None:
            self.store.event(now, "rejected", cell.id, {"reason": "invalid_target"})
            return
        self._mutate(target, gradient, now)

    def _mutate(self, target: Cell, gradient: Gradient, now: float) -> None:
        new_run_cmd = target.run_cmd if gradient.new_run_cmd is None else gradient.new_run_cmd
        new_hash = _dna_hash(gradient.new_instruction, new_run_cmd)
        current_hash = _dna_hash(target.instruction, target.run_cmd)
        if new_hash == current_hash:
            self.store.event(now, "rejected", target.id, {"reason": "unchanged"})
            return
        previous_hashes = {version.dna_hash for version in self.store.versions(target.id)}
        if new_hash in previous_hashes:
            reason = "taboo" if self.store.meta(f"taboo:{target.id}:{new_hash}") else "oscillation"
            self.store.event(now, "rejected", target.id, {"reason": reason})
            return
        cooldown = int(self.constitution.limits["mutation_cooldown_ticks"])
        last_tick = self.store.meta(f"last_mutation_tick:{target.id}")
        if last_tick is not None and self.store.tick_no() - int(last_tick) < cooldown:
            self.store.event(now, "rejected", target.id, {"reason": "cooldown"})
            return
        cost = float(self.constitution.budget["mutation_cost"])
        if not self._spend(cost, target.id, "mutation", now):
            return
        version = target.version + 1
        state = target.state
        if gradient.new_run_cmd is not None and gradient.new_run_cmd != target.run_cmd:
            if not self.constitution.trust["auto_approve_llm_commands"]:
                state = "quarantined"
        self.store.conn.execute(
            """UPDATE cells SET instruction=?, run_cmd=?, version=?, state=?, updated_at=?
               WHERE id=?""",
            (gradient.new_instruction, new_run_cmd, version, state, now, target.id),
        )
        self.store.conn.execute(
            """INSERT INTO versions(
                   cell_id, version, instruction, run_cmd, origin, reason, dna_hash, at
               ) VALUES (?, ?, ?, ?, 'mutation', ?, ?, ?)""",
            (
                target.id,
                version,
                gradient.new_instruction,
                new_run_cmd,
                gradient.rationale,
                new_hash,
                now,
            ),
        )
        self.store.set_meta(f"last_mutation_tick:{target.id}", self.store.tick_no())
        self.store.event(now, "mutation", target.id, {"version": version})
        if state == "quarantined" and target.state != "quarantined":
            self.store.event(now, "quarantined", target.id, {"reason": "new_run_cmd"})

    def tick(self) -> list[Event]:
        self._check_constitution()
        first_event = self.store.last_event_id()
        with self.store.conn:
            self.store.set_meta("tick_no", self.store.tick_no() + 1)
            self._sense()
            self._apoptosis()
            self._fusion()
            self._rollback()
        return self.store.events_after(first_event)

    def _sense(self) -> None:
        for cell in self.ready():
            code, output, duration = self._command(cell.verify_cmd)
            now = time.time()
            ok = code == 0
            self._record_run(cell, ok, code, duration, output, now)
            if ok:
                self._complete(cell, now)

    def _kill(self, cell: Cell, reason: str, now: float) -> None:
        self.store.conn.execute(
            "UPDATE cells SET state='dead', updated_at=? WHERE id=?", (now, cell.id)
        )
        self.store.conn.execute("DELETE FROM deps WHERE cell_id=? OR dep_id=?", (cell.id, cell.id))
        self.store.event(now, "apoptosis", cell.id, {"reason": reason})

    def _has_done_ancestor(self, cell: Cell) -> bool:
        parent_id = cell.parent_id
        seen: set[str] = set()
        while parent_id and parent_id not in seen:
            seen.add(parent_id)
            parent = self.store.get(parent_id)
            if parent is None:
                return False
            if parent.state == "done":
                return True
            parent_id = parent.parent_id
        return False

    def _apoptosis(self) -> None:
        ttl = float(self.constitution.limits["idle_ttl_days"])
        for cell in list(self.store.cells(["active"])):
            current = self.store.get(cell.id)
            if current is None or current.state != "active":
                continue
            now = time.time()
            if current.obsolete_cmd:
                code, _, _ = self._command(current.obsolete_cmd)
                if code == 0:
                    self._kill(current, "obsolete_cmd", now)
                    continue
            if self._has_done_ancestor(current):
                self._kill(current, "parent_done", now)
                continue
            active_dependents = [
                item
                for item in self.store.dependents(current.id)
                if item.state == "active"
            ]
            if ttl > 0 and not active_dependents:
                row = self.store.conn.execute(
                    """SELECT MAX(at) FROM (
                           SELECT created_at AS at FROM cells WHERE id=?
                           UNION ALL SELECT at FROM runs WHERE cell_id=?
                           UNION ALL SELECT at FROM events WHERE cell_id=?
                       )""",
                    (current.id, current.id, current.id),
                ).fetchone()
                if row[0] is not None and now - float(row[0]) >= ttl * 86400:
                    self._kill(current, "idle", now)

    def _fusion(self) -> None:
        window = int(self.constitution.limits["fusion_after"])
        if window <= 0:
            return
        for second in list(self.store.cells(["active", "done"])):
            if len(second.deps) != 1 or not second.run_cmd:
                continue
            first = self.store.get(second.deps[0])
            if first is None or first.state not in {"active", "done"} or not first.run_cmd:
                continue
            dependents = self.store.dependents(first.id)
            if len(dependents) != 1 or dependents[0].id != second.id:
                continue
            first_runs = list(reversed(self.store.runs(first.id, window)))
            second_runs = list(reversed(self.store.runs(second.id, window)))
            if len(first_runs) < window or len(second_runs) < window:
                continue
            if not all(item.ok for item in first_runs + second_runs):
                continue
            if not all(a.at < b.at for a, b in zip(first_runs, second_runs, strict=True)):
                continue
            now = time.time()
            fused = Cell(
                id=self._new_id(),
                title=f"{first.title} + {second.title}",
                verify_cmd=f"({first.verify_cmd}) && ({second.verify_cmd})",
                instruction="\n\n".join(filter(None, [first.instruction, second.instruction])),
                run_cmd=f"({first.run_cmd}) && ({second.run_cmd})",
                depth=min(first.depth, second.depth),
                deps=list(first.deps),
                created_at=now,
                updated_at=now,
            )
            self._insert_cell(fused, reason=f"fusion of {first.id} and {second.id}")
            for dependent in self.store.dependents(second.id):
                if dependent.id != fused.id:
                    self.store.conn.execute(
                        "UPDATE deps SET dep_id=? WHERE cell_id=? AND dep_id=?",
                        (fused.id, dependent.id, second.id),
                    )
            self.store.conn.execute(
                "UPDATE cells SET state='fused', updated_at=? WHERE id IN (?, ?)",
                (now, first.id, second.id),
            )
            self.store.conn.execute(
                "DELETE FROM deps WHERE cell_id IN (?, ?) OR dep_id IN (?, ?)",
                (first.id, second.id, first.id, second.id),
            )
            self.store.event(now, "fusion", fused.id, {"cells": [first.id, second.id]})
            break

    def _rollback(self) -> None:
        window = int(self.constitution.limits["rollback_window"])
        if window <= 0:
            return
        for cell in self.store.cells(["active", "quarantined"]):
            versions = self.store.versions(cell.id)
            if len(versions) < 2 or versions[-1].origin != "mutation":
                continue
            current_runs = self.store.conn.execute(
                """SELECT ok FROM runs WHERE cell_id=? AND version=?
                   ORDER BY id DESC LIMIT ?""",
                (cell.id, cell.version, window),
            ).fetchall()
            previous = versions[-2]
            previous_runs = self.store.conn.execute(
                """SELECT ok FROM runs WHERE cell_id=? AND version=?
                   ORDER BY id DESC LIMIT ?""",
                (cell.id, previous.version, window),
            ).fetchall()
            if len(current_runs) < window or not previous_runs:
                continue
            current_fail = 1 - sum(row[0] for row in current_runs) / len(current_runs)
            previous_fail = 1 - sum(row[0] for row in previous_runs) / len(previous_runs)
            if current_fail <= previous_fail:
                continue
            now = time.time()
            bad_hash = versions[-1].dna_hash
            new_version = cell.version + 1
            self.store.conn.execute(
                """UPDATE cells
                   SET instruction=?, run_cmd=?, version=?, state='active', updated_at=?
                   WHERE id=?""",
                (previous.instruction, previous.run_cmd, new_version, now, cell.id),
            )
            self.store.conn.execute(
                """INSERT INTO versions(
                       cell_id, version, instruction, run_cmd, origin, reason, dna_hash, at
                   ) VALUES (?, ?, ?, ?, 'rollback', ?, ?, ?)""",
                (
                    cell.id,
                    new_version,
                    previous.instruction,
                    previous.run_cmd,
                    f"version {cell.version} performed worse than {previous.version}",
                    previous.dna_hash,
                    now,
                ),
            )
            self.store.set_meta(f"taboo:{cell.id}:{bad_hash}", 1)
            self.store.event(now, "rollback", cell.id, {"bad_hash": bad_hash})

    def fitness(self) -> dict[str, bool]:
        results: dict[str, bool] = {}
        with self.store.conn:
            for index, check in enumerate(self.constitution.fitness):
                name = str(check.get("name", f"fitness-{index + 1}"))
                code, output, _ = self._command(str(check["cmd"]))
                passed = code == 0
                key = f"fitness:{name}"
                previous = self.store.meta(key)
                self.store.set_meta(key, "1" if passed else "0")
                if passed and previous == "0":
                    self._change_energy(float(self.constitution.budget["reward_per_fitness"]))
                self.store.event(
                    time.time(),
                    "fitness_pass" if passed else "fitness_fail",
                    None,
                    {"name": name, "output": output[-4000:]},
                )
                results[name] = passed
        return results

    def approve(self, cell_id: str) -> None:
        cell = self.store.get(cell_id)
        if cell is None:
            raise UnknownCell(cell_id)
        if cell.state != "quarantined":
            return
        now = time.time()
        with self.store.conn:
            self.store.conn.execute(
                "UPDATE cells SET state='active', updated_at=? WHERE id=?", (now, cell_id)
            )
            self.store.event(now, "approved", cell_id)

    def ratify(self) -> None:
        current = load(self.root / "constitution.toml")
        now = time.time()
        with self.store.conn:
            self.store.set_meta("constitution_sha", current.sha256)
            self.store.event(now, "ratified", None, {"sha256": current.sha256})
        self.constitution = current

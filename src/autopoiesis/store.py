"""SQLite persistence for the autopoiesis graph."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from .model import Cell, Event, RunResult, Version


class Store:
    """A small SQLite store whose writes are transaction-controlled by the kernel."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA foreign_keys = ON")
        with self.conn:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS cells (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    verify_cmd TEXT NOT NULL,
                    instruction TEXT NOT NULL DEFAULT '',
                    run_cmd TEXT,
                    obsolete_cmd TEXT,
                    parent_id TEXT REFERENCES cells(id),
                    state TEXT NOT NULL,
                    depth INTEGER NOT NULL,
                    version INTEGER NOT NULL,
                    fail_streak INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS deps (
                    cell_id TEXT NOT NULL REFERENCES cells(id) ON DELETE CASCADE,
                    dep_id TEXT NOT NULL REFERENCES cells(id) ON DELETE CASCADE,
                    PRIMARY KEY (cell_id, dep_id)
                );
                CREATE TABLE IF NOT EXISTS versions (
                    cell_id TEXT NOT NULL REFERENCES cells(id) ON DELETE CASCADE,
                    version INTEGER NOT NULL,
                    instruction TEXT NOT NULL,
                    run_cmd TEXT,
                    origin TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    dna_hash TEXT NOT NULL,
                    at REAL NOT NULL,
                    PRIMARY KEY (cell_id, version)
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cell_id TEXT NOT NULL REFERENCES cells(id) ON DELETE CASCADE,
                    version INTEGER NOT NULL,
                    ok INTEGER NOT NULL,
                    exit_code INTEGER NOT NULL,
                    duration_s REAL NOT NULL,
                    output TEXT NOT NULL,
                    at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    at REAL NOT NULL,
                    kind TEXT NOT NULL,
                    cell_id TEXT REFERENCES cells(id),
                    detail_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )

    def close(self) -> None:
        self.conn.close()

    def _cell(self, row: sqlite3.Row) -> Cell:
        deps = [
            item[0]
            for item in self.conn.execute(
                "SELECT dep_id FROM deps WHERE cell_id = ? ORDER BY dep_id", (row["id"],)
            )
        ]
        return Cell(
            id=row["id"],
            title=row["title"],
            verify_cmd=row["verify_cmd"],
            instruction=row["instruction"],
            run_cmd=row["run_cmd"],
            obsolete_cmd=row["obsolete_cmd"],
            parent_id=row["parent_id"],
            state=row["state"],
            depth=row["depth"],
            version=row["version"],
            fail_streak=row["fail_streak"],
            deps=deps,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get(self, cell_id: str) -> Cell | None:
        row = self.conn.execute("SELECT * FROM cells WHERE id = ?", (cell_id,)).fetchone()
        return self._cell(row) if row else None

    def cells(self, states: Iterable[str] | None = None) -> list[Cell]:
        if states is None:
            rows = self.conn.execute("SELECT * FROM cells ORDER BY created_at, id").fetchall()
        else:
            selected = tuple(states)
            if not selected:
                return []
            marks = ",".join("?" for _ in selected)
            rows = self.conn.execute(
                f"SELECT * FROM cells WHERE state IN ({marks}) ORDER BY created_at, id", selected
            ).fetchall()
        return [self._cell(row) for row in rows]

    def children(self, cell_id: str) -> list[Cell]:
        rows = self.conn.execute(
            "SELECT * FROM cells WHERE parent_id = ? ORDER BY created_at, id", (cell_id,)
        ).fetchall()
        return [self._cell(row) for row in rows]

    def dependents(self, cell_id: str) -> list[Cell]:
        rows = self.conn.execute(
            """SELECT cells.* FROM cells JOIN deps ON cells.id = deps.cell_id
               WHERE deps.dep_id = ? ORDER BY cells.created_at, cells.id""",
            (cell_id,),
        ).fetchall()
        return [self._cell(row) for row in rows]

    def versions(self, cell_id: str) -> list[Version]:
        rows = self.conn.execute(
            "SELECT * FROM versions WHERE cell_id = ? ORDER BY version", (cell_id,)
        ).fetchall()
        return [Version(**dict(row)) for row in rows]

    def runs(self, cell_id: str | None = None, limit: int = 20) -> list[RunResult]:
        if cell_id is None:
            rows = self.conn.execute(
                "SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM runs WHERE cell_id = ? ORDER BY id DESC LIMIT ?",
                (cell_id, limit),
            ).fetchall()
        return [
            RunResult(
                cell_id=row["cell_id"],
                version=row["version"],
                ok=bool(row["ok"]),
                exit_code=row["exit_code"],
                duration_s=row["duration_s"],
                output=row["output"],
                at=row["at"],
            )
            for row in rows
        ]

    def events(self, limit: int = 50) -> list[Event]:
        rows = self.conn.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [
            Event(row["at"], row["kind"], row["cell_id"], json.loads(row["detail_json"]))
            for row in rows
        ]

    def events_after(self, event_id: int) -> list[Event]:
        rows = self.conn.execute(
            "SELECT * FROM events WHERE id > ? ORDER BY id", (event_id,)
        ).fetchall()
        return [
            Event(row["at"], row["kind"], row["cell_id"], json.loads(row["detail_json"]))
            for row in rows
        ]

    def last_event_id(self) -> int:
        row = self.conn.execute("SELECT COALESCE(MAX(id), 0) FROM events").fetchone()
        return int(row[0])

    def meta(self, key: str, default: str | None = None) -> str | None:
        row = self.conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default

    def set_meta(self, key: str, value: object) -> None:
        self.conn.execute(
            """INSERT INTO meta(key, value) VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
            (key, str(value)),
        )

    def energy(self) -> float:
        return float(self.meta("energy", "0"))

    def tick_no(self) -> int:
        return int(self.meta("tick_no", "0"))

    def event(self, at: float, kind: str, cell_id: str | None, detail: dict | None = None) -> None:
        self.conn.execute(
            "INSERT INTO events(at, kind, cell_id, detail_json) VALUES (?, ?, ?, ?)",
            (at, kind, cell_id, json.dumps(detail or {}, sort_keys=True)),
        )

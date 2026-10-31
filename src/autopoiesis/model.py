"""Shared data contracts between store, kernel, mutator, renderer and CLI. See docs/SPEC.md §6."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

STATES = ("active", "done", "dead", "fused", "quarantined")


@dataclass
class Cell:
    id: str
    title: str
    verify_cmd: str  # membrane contract: immutable after birth
    instruction: str = ""  # DNA: prompt for whoever does the work
    run_cmd: str | None = None  # DNA: optional executable step
    obsolete_cmd: str | None = None  # apoptosis sensor: exit 0 means "no longer needed"
    parent_id: str | None = None
    state: str = "active"
    depth: int = 0
    version: int = 1
    fail_streak: int = 0
    deps: list[str] = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0


@dataclass
class Version:
    cell_id: str
    version: int
    instruction: str
    run_cmd: str | None
    origin: str  # birth | mutation | rollback
    reason: str
    dna_hash: str
    at: float


@dataclass
class RunResult:
    cell_id: str
    version: int
    ok: bool
    exit_code: int
    duration_s: float
    output: str
    at: float


@dataclass
class Event:
    at: float
    kind: str
    cell_id: str | None
    detail: dict = field(default_factory=dict)


@dataclass
class ChildSpec:
    title: str
    verify_cmd: str
    instruction: str = ""
    run_cmd: str | None = None


@dataclass
class Gradient:
    target_id: str
    new_instruction: str
    rationale: str
    new_run_cmd: str | None = None


class Mutator(Protocol):
    def split(self, cell: Cell, failure_log: str, max_children: int) -> list[ChildSpec]: ...

    def critique(self, cell: Cell, failure_log: str, upstream: list[Cell]) -> Gradient | None: ...


class NullMutator:
    """No LLM: the graph still senses, dies, fuses and rolls back; it just never rewrites DNA."""

    def split(self, cell: Cell, failure_log: str, max_children: int) -> list[ChildSpec]:
        return []

    def critique(self, cell: Cell, failure_log: str, upstream: list[Cell]) -> Gradient | None:
        return None


class ApoError(Exception):
    """Base error; the CLI prints it as one line and exits 1."""


class NotInitialized(ApoError):
    pass


class ConstitutionTampered(ApoError):
    pass


class Quarantined(ApoError):
    pass


class UnknownCell(ApoError):
    pass

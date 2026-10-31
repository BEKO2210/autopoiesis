"""Project constitution loading and defaults."""

from __future__ import annotations

import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path

TEMPLATE = '''goal = "Describe the real project goal here."

[budget]
initial_energy = 100
mutation_cost = 5
mitosis_cost = 10
reward_per_done = 20
reward_per_fitness = 30

[limits]
max_cells = 64
max_depth = 3
max_children = 3
fail_streak_for_mitosis = 2
mutation_cooldown_ticks = 3
rollback_window = 3
fusion_after = 3
idle_ttl_days = 30

[trust]
auto_approve_llm_commands = false
command_timeout_s = 120

# [[fitness]]
# name = "tests"
# cmd = "python -m pytest -q"
'''

_DEFAULTS = tomllib.loads(TEMPLATE)


@dataclass(frozen=True)
class Constitution:
    """The immutable, merged view of a project's constitution."""

    goal: str
    budget: dict
    limits: dict
    trust: dict
    fitness: list[dict]
    sha256: str


def load(path: Path) -> Constitution:
    """Load a constitution, merging missing sections and keys with defaults."""
    raw = path.read_bytes()
    data = tomllib.loads(raw.decode())
    budget = {**_DEFAULTS["budget"], **data.get("budget", {})}
    limits = {**_DEFAULTS["limits"], **data.get("limits", {})}
    trust = {**_DEFAULTS["trust"], **data.get("trust", {})}
    return Constitution(
        goal=data.get("goal", _DEFAULTS["goal"]),
        budget=budget,
        limits=limits,
        trust=trust,
        fitness=list(data.get("fitness", [])),
        sha256=hashlib.sha256(raw).hexdigest(),
    )

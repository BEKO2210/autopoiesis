# autopoiesis — Specification v0.1

A roadmap that is not a document but a living graph. Every task is a **cell** in a SQLite graph.
A heartbeat reacts to project events and runs four processes — **mitosis, apoptosis, fusion,
recombination** — under three hard laws. Python ≥ 3.11, **standard library only** at runtime.

## 1. Cell anatomy

| Part | Field(s) | Mutable? |
|---|---|---|
| Membrane (contract) | `verify_cmd` (shell, exit 0 = goal reached), `deps` | `verify_cmd` **never** after birth |
| DNA | `instruction` (prompt for the human/agent), `run_cmd` (optional shell step) | yes, only via versioned mutation |
| Metabolism | global `energy` pool + per-cell `pressure` (computed) | kernel only |
| Epigenetics | `versions` + `runs` tables (what changed, what worked) | append-only |

States: `active` · `done` · `dead` (apoptosis, kept for audit, hidden from active graph) ·
`fused` (absorbed into a fused cell) · `quarantined` (holds LLM-written shell, waits for `approve`).
A cell is **ready** when `active` and every dep is `done`.
`pressure(c) = 1 + number of active cells that transitively depend on c`.

## 2. The three laws (enforced in code, never by an LLM)

1. **Soma vs. germline.** `constitution.toml` (project root) holds goal, budget, limits, trust and
   fitness checks. The kernel never writes it. `init` stores its SHA-256; every `tick`/`run` raises
   `ConstitutionTampered` if the hash differs, until a human runs `apo ratify`. The kernel source is
   germline too: cells mutate, the kernel does not (no Gödel-style self-patching — deliberate).
   A cell's `verify_cmd` is immutable, and a parent is only done when **its own** `verify_cmd`
   passes — children created by mitosis cannot fake their parent's success.
2. **Metabolic cost.** One global energy pool (`budget.initial_energy`). Mutation costs
   `budget.mutation_cost`, mitosis `budget.mitosis_cost`. Energy is only earned by verified progress:
   `reward_per_done` when a cell becomes `done` via its `verify_cmd`, `reward_per_fitness` when a
   fitness check flips fail→pass. Not enough energy → process skipped, event `energy_denied`.
   Hard caps: `limits.max_cells` (active), `limits.max_depth`, `limits.max_children`.
3. **Transactions + rollback reflex.** Every process is one SQLite transaction. Every DNA change
   writes a new row in `versions` (`origin` = birth | mutation | rollback). After a mutation has
   `limits.rollback_window` runs, if its failure rate is higher than the previous version's, the
   kernel restores the previous DNA (`origin=rollback`) and adds the bad DNA's hash to a taboo set.
   Oscillation guard: a mutation is rejected if its DNA hash was ever used by that cell before, or
   if the cell mutated less than `limits.mutation_cooldown_ticks` ticks ago.

## 3. Processes

**On `run(cell)`** — execute `run_cmd` (if any), then `verify_cmd`, each with
`trust.command_timeout_s`. Record a run. `ok = run exit 0 and verify exit 0`.
- ok → `done` (+reward if newly done), `fail_streak = 0`.
- fail → `fail_streak += 1`, then exactly one of:
  - **Mitosis** if `fail_streak >= limits.fail_streak_for_mitosis`, depth < max_depth, caps and
    energy allow: `mutator.split()` → up to `max_children` children (`depth+1`, `parent_id`,
    deps = parent's deps). Parent gains a dep on every child (it waits, then re-checks its own
    contract). Children are `quarantined` unless `trust.auto_approve_llm_commands`. Reset streak.
  - **Recombination** (TextGrad-style) otherwise: `mutator.critique(cell, log, upstream=direct deps)`
    → a `Gradient` naming the cell itself or one direct dep as the cause. Apply as a mutation of
    the target's `instruction` (and `run_cmd` if given; a new `run_cmd` quarantines the target unless
    auto-approve). Rejected if target not allowed, DNA unchanged, taboo, cooldown or energy.

**On `tick()`** (heartbeat; deterministic, no LLM) in this order:
1. constitution hash check; `tick_no += 1`
2. **sense**: every ready, non-quarantined cell runs its `verify_cmd` → pass = `done` (+reward)
3. **apoptosis**: active cell whose `obsolete_cmd` exits 0 → `dead`; active descendants of a `done`
   cell → `dead` (`reason=parent_done`); cell with no active dependents and no run/event for
   `limits.idle_ttl_days` (0 = off) → `dead` (`reason=idle`). Edges to dead cells are dropped.
4. **fusion**: linear chain A→B (B's only dep is A, A's only dependent is B, both have `run_cmd`, both
   not quarantined) whose last `limits.fusion_after` runs each succeeded with every B run following
   an A run → new cell F: `run_cmd = "(A.run) && (B.run)"`, `verify_cmd = "(A.verify) && (B.verify)"`,
   deps = A's deps, B's dependents rewired to F; A and B → `fused`. No LLM needed for F.
5. **rollback** check (Law 3).

`fitness()` runs every `[[fitness]]` check, rewards fail→pass flips, logs `fitness_pass/fail`.

## 4. Storage (`.apo/cells.db`)

Tables: `cells`, `deps(cell_id, dep_id)`, `versions(cell_id, version, instruction, run_cmd, origin,
reason, dna_hash, at)`, `runs(id, cell_id, version, ok, exit_code, duration_s, output, at)`,
`events(id, at, kind, cell_id, detail_json)`, `meta(key, value)` (energy, tick_no, constitution_sha,
fitness state). WAL mode. `output` keeps the last 4000 chars. Cell ids: `c-` + 6 hex chars.

Event kinds: born, completed, run_ok, run_failed, mitosis, apoptosis, fusion, mutation, rollback,
quarantined, approved, fitness_pass, fitness_fail, energy_denied, limit_reached, rejected, ratified.

## 5. Constitution template (written by `apo init` if missing)

```toml
goal = "Describe the real project goal here."

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
```

## 6. Python API (shared contract — names are fixed)

Types and exceptions live in `autopoiesis/model.py` (already written, do not rename fields).

```python
# autopoiesis/store.py
class Store:
    def __init__(self, path: Path): ...
    def get(self, cell_id: str) -> Cell | None
    def cells(self, states: Iterable[str] | None = None) -> list[Cell]   # deps filled
    def children(self, cell_id: str) -> list[Cell]
    def dependents(self, cell_id: str) -> list[Cell]
    def versions(self, cell_id: str) -> list[Version]                    # oldest first
    def runs(self, cell_id: str | None = None, limit: int = 20) -> list[RunResult]  # newest first
    def events(self, limit: int = 50) -> list[Event]                     # newest first
    def energy(self) -> float
    def tick_no(self) -> int

# autopoiesis/constitution.py
@dataclass(frozen=True)
class Constitution: goal, budget: dict, limits: dict, trust: dict, fitness: list[dict], sha256: str
def load(path: Path) -> Constitution        # defaults merged for missing keys
TEMPLATE: str

# autopoiesis/kernel.py
Runner = Callable[[str, Path, float], tuple[int, str]]   # (cmd, cwd, timeout) -> (exit_code, output)
def run_shell(cmd: str, cwd: Path, timeout: float) -> tuple[int, str]   # timeout -> exit 124
class Kernel:
    @classmethod
    def init(cls, root: Path, goal: str = "") -> "Kernel"
    def __init__(self, root: Path, mutator: Mutator | None = None, runner: Runner | None = None)
    store: Store; constitution: Constitution; root: Path
    def add(self, title: str, verify_cmd: str, *, instruction: str = "", run_cmd: str | None = None,
            obsolete_cmd: str | None = None, deps: Sequence[str] = (), parent_id: str | None = None) -> Cell
    def tick(self) -> list[Event]
    def run(self, cell_id: str) -> RunResult
    def ready(self) -> list[Cell]          # pressure desc, then created_at
    def pressure(self, cell_id: str) -> int
    def fitness(self) -> dict[str, bool]
    def approve(self, cell_id: str) -> None
    def ratify(self) -> None

# autopoiesis/mutator.py
class OpenAIMutator:   # any OpenAI-compatible /v1 endpoint (Ollama, llama.cpp, vLLM, OpenAI)
    def __init__(self, base_url: str, model: str, api_key: str | None = None, timeout: float = 120)
def from_env() -> Mutator    # APO_LLM_BASE_URL + APO_LLM_MODEL (+ APO_LLM_API_KEY) else NullMutator()

# autopoiesis/render.py
def render_tree(cells: list[Cell], pressure: dict[str, int], color: bool = False) -> str
def render_mermaid(cells: list[Cell]) -> str
def render_dot(cells: list[Cell]) -> str
def render_events(events: list[Event]) -> str

# autopoiesis/watch.py
DEFAULT_IGNORE: frozenset[str]   # .git .apo node_modules __pycache__ .venv venv dist build
def snapshot(root: Path, ignore: frozenset[str] = DEFAULT_IGNORE) -> dict[str, tuple[float, int]]
def watch(root: Path, on_change: Callable[[], None], interval: float = 2.0,
          stop: Callable[[], bool] = lambda: False) -> None
def install_hook(root: Path) -> Path     # .git/hooks/post-commit running `apo tick --quiet || true`
```

## 7. CLI `apo` (argparse, `autopoiesis/cli.py`, entry `main(argv=None) -> int`)

`init [--goal]` · `add TITLE --verify CMD [--run CMD] [--instruction TEXT] [--dep ID]... [--obsolete CMD]`
· `status` · `next` · `show ID` · `run ID` · `tick [--quiet]` · `watch [--interval S]` · `approve ID`
· `ratify` · `fitness` · `graph [--format mermaid|dot]` · `log [-n N]` · `hook install`.
Project root = nearest parent containing `.apo/` (else cwd for `init`). Exit 1 + one-line message on
`ApoError`. Color only when stdout is a TTY and `NO_COLOR` is unset.

## 8. Non-goals (v0.1)

No kernel self-modification, no network service, no web UI, no inotify dependency (polling),
no git shadow branches (SQLite versions instead).

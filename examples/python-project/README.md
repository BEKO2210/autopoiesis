# Example: Python project walkthrough

Walkthrough of `apo` commands from [docs/SPEC.md](../../docs/SPEC.md) §7
against a small library whose goal is encoded in
[`constitution.toml`](constitution.toml) (schema from SPEC §5 /
`Constitution` in `model.py`).

Commands below are the only CLI surface this example uses. Replace
paths with your checkout. Requires Python ≥ 3.11 and an installed
`apo` entry point (`pip install -e .` from the repo root).

## 1. Initialize

From an empty or existing project directory that should own the graph:

```bash
apo init --goal "Ship a small Python library with passing unit tests and a clean ruff check."
```

If `constitution.toml` is missing, `init` writes the SPEC §5 template.
This example already provides one: copy it to the project root (or point
`init` at a directory that contains it), then continue.

Confirm the store:

```bash
apo status
```

## 2. Add cells

Membrane contracts are fixed at birth. Prefer precise `verify_cmd` values.

```bash
apo add "unit tests pass" \
  --verify "python -m pytest -q" \
  --instruction "Add tests under tests/ for the public API; keep them deterministic."

apo add "ruff clean" \
  --verify "python -m ruff check ." \
  --instruction "Fix ruff findings without disabling rules globally." \
  --dep c-XXXXXX
```

Use the id printed by the first `add` as `--dep` for the second (ids look
like `c-` + 6 hex digits). Optional flags from SPEC §7: `--run`,
`--obsolete`.

Inspect:

```bash
apo show c-XXXXXX
apo next
apo graph --format mermaid
```

## 3. Work a ready cell

```bash
apo run c-XXXXXX
```

`run` executes optional `run_cmd`, then `verify_cmd`. On repeated failure
the kernel may attempt mitosis or recombination (SPEC §3), subject to
energy and limits in `constitution.toml`. If mitosis is attempted and
`Mutator.split()` returns no children, the failure falls back to recombination.

If a cell is `quarantined` (LLM-written shell, default trust settings):

```bash
apo show c-YYYYYY
# review run_cmd / instruction
apo approve c-YYYYYY
```

`apo approve` only sets the cell state to `active`; it does not execute
any command. Commands run later via `apo run` or sense during `apo tick`.

## 4. Heartbeat and fitness

```bash
apo tick
apo fitness
apo log -n 20
```

`tick` is deterministic (no LLM): after the hash check, sense, apoptosis,
fusion, and rollback run in **one** SQLite transaction. After you edit
`constitution.toml` by hand:

```bash
apo ratify
```

until then, `tick` / `run` / `fitness` raise `ConstitutionTampered`.

## 5. Watch and git hook

```bash
apo watch --interval 2
apo hook install
```

`hook install` writes `.git/hooks/post-commit` that runs
`apo tick --quiet || true` (SPEC §6 `install_hook`).

## 6. Graph and status

```bash
apo status
apo graph --format mermaid
apo graph --format dot
apo log -n 50
```

## Trust notes

This example keeps `auto_approve_llm_commands = false`. Approve
quarantined cells only after reading their commands (approval does not
sandbox or isolate the filesystem). See
[docs/safety.md](../../docs/safety.md).

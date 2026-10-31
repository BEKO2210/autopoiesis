# autopoiesis

[![ci](https://github.com/BEKO2210/autopoiesis/actions/workflows/ci.yml/badge.svg)](https://github.com/BEKO2210/autopoiesis/actions/workflows/ci.yml) [![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

[![ci](https://github.com/BEKO2210/autopoiesis/actions/workflows/ci.yml/badge.svg)](https://github.com/BEKO2210/autopoiesis/actions/workflows/ci.yml)

Autopoiesis is a roadmap kept as a graph of cells in `.apo/cells.db`, not as a document. A cell is a task with a shell contract (`verify_cmd`, exit 0 means done), an instruction, an optional `run_cmd`, and dependencies. `apo tick` is the heartbeat. `apo run` executes one cell. Four processes — mitosis, apoptosis, fusion, recombination — run under three laws enforced in code. Python ≥ 3.11, standard library only. An optional local LLM may propose new instructions and shell; it does not edit `constitution.toml` or the kernel.

## Why

A static to-do list rots: finished work stays open, blocked work stays urgent, and two steps that have become one stay two. Here each cell is checked by a command you wrote. A passing check marks it done and pays energy. Repeated failure can split the cell or rewrite its instruction. Cells that are idle, obsolete, or left behind by a finished parent leave the active graph and stay in the database for audit.

## Install

Python ≥ 3.11. No runtime dependencies.

```bash
pip install "git+https://github.com/BEKO2210/autopoiesis.git"
```

That installs the `apo` command (`autopoiesis.cli:main`).

## Quickstart

From an empty directory. Cell ids are `c-` plus six hex digits; the ids and timestamps below are from one run.

```text
$ apo init --goal "Ship the marker."
/tmp/apo-qs-l51_cgmx

$ apo add "create base.txt" --verify "test -f base.txt"
c-b4129d

$ apo add "create extra.txt" --verify "test -f extra.txt" --dep c-b4129d
c-d2ac8a

$ apo status
goal: Ship the marker.
energy: 100
tick: 0
[active] c-b4129d create base.txt  p=2  deps:
[active] c-d2ac8a create extra.txt  p=1  deps: c-b4129d

$ apo tick
2026-10-31 22:49:15 run_failed c-b4129d exit_code=1

$ : > base.txt
$ apo tick
2026-10-31 22:49:16 run_ok c-b4129d exit_code=0
2026-10-31 22:49:16 completed c-b4129d

$ apo run c-d2ac8a
fail

$ : > extra.txt
$ apo run c-d2ac8a
ok

$ apo status
goal: Ship the marker.
energy: 140
tick: 2
[done] c-b4129d create base.txt  p=1  deps:
[done] c-d2ac8a create extra.txt  p=1  deps: c-b4129d

$ apo graph
flowchart TD
  nc_b4129d["create base.txt [done]"]
  nc_d2ac8a["create extra.txt [done]"]
  nc_b4129d --> nc_d2ac8a
```

`apo tick` runs `verify_cmd` only for ready cells (state `active`, every dep `done`). `apo run ID` runs that cell's `run_cmd` (if any) and then `verify_cmd`. Energy starts at `budget.initial_energy` (100). Each cell that becomes `done` adds `budget.reward_per_done` (20), so two completions reach 140. `p` is pressure: 1 plus the number of active cells that depend on it. `apo graph` defaults to `--format mermaid` (also `dot`). An edge means the source is a dependency.

## Processes and laws

| Process | When |
|---|---|
| Mitosis | `apo run` after `limits.fail_streak_for_mitosis` failed runs (default 2), if depth, cell count, and energy allow. Up to `limits.max_children` (3) children. They start `quarantined` unless `trust.auto_approve_llm_commands`. |
| Apoptosis | `apo tick`. An active cell dies if `obsolete_cmd` exits 0, if an ancestor is `done`, or if it has no active dependents and no run or event for `limits.idle_ttl_days` (default 30; 0 turns this off). |
| Fusion | `apo tick`. A chain of two cells that both have `run_cmd`, where the last `limits.fusion_after` runs (default 3) each succeeded and each second run followed a first run, becomes one cell. |
| Recombination | `apo run` on a failure that does not split. The LLM may replace `instruction` and, if it sends one, `run_cmd`. No LLM means the DNA stays as it is. |

| Law | Rule |
|---|---|
| Soma vs germline | The kernel never writes `constitution.toml`. `apo init` stores its SHA-256. If the file differs, `apo tick` and `apo run` exit 1 and print `` constitution.toml changed; run `apo ratify` `` until you run `apo ratify`. `verify_cmd` is fixed at birth. A cell is done only when its own `verify_cmd` exits 0. |
| Metabolic cost | One energy pool. Mitosis costs `budget.mitosis_cost` (10), a mutation costs `budget.mutation_cost` (5). A new `done` pays 20. A fitness check that flips from fail to pass pays `budget.reward_per_fitness` (30). Not enough energy skips that process (`energy_denied`). Caps: `limits.max_cells` 64, `limits.max_depth` 3, `limits.max_children` 3. |
| Transactions and rollback | Each process is one SQLite transaction. Every DNA change appends a `versions` row. After `limits.rollback_window` runs (default 3), a mutation that fails more often than the previous version is restored and its DNA hash is taboo. The same hash again, or a mutation sooner than `limits.mutation_cooldown_ticks` (default 3), is rejected. |

`constitution.toml` is written by `apo init` when missing. Missing keys load the defaults above. `trust.command_timeout_s` defaults to 120. `trust.auto_approve_llm_commands` defaults to false.

## Local LLM

Set both environment variables or the kernel uses no model (`NullMutator`): no mitosis children and no instruction rewrites. Sensing, apoptosis, fusion, and rollback still run.

```bash
export APO_LLM_BASE_URL="http://127.0.0.1:11434/v1"   # Ollama's OpenAI-compatible API
export APO_LLM_MODEL="llama3.2"
# export APO_LLM_API_KEY="..."   # optional; sent as Bearer
```

The client POSTs `{APO_LLM_BASE_URL}/chat/completions`. Any OpenAI-compatible server (Ollama, llama.cpp, vLLM, OpenAI) works the same way.

## Safety

LLM-written shell is not executed immediately. Mitosis children are `quarantined`. A recombination that supplies a new `run_cmd` quarantines that cell. `apo tick` does not verify quarantined cells. `apo run` on one prints the id to stderr and exits 1. `apo approve ID` sets the cell back to `active`. This holds while `trust.auto_approve_llm_commands` is false (the default). Shell you pass yourself with `--verify` and `--run` is not quarantined.

## Docs

- [docs/SPEC.md](docs/SPEC.md) — specification v0.1
- [docs/concepts.md](docs/concepts.md) — cell, energy, the four processes
- [docs/research.md](docs/research.md) — background
- [docs/safety.md](docs/safety.md) — quarantine and the constitution

## License

Apache License 2.0. Copyright 2026 Belkis Aslani. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

# Graph Report - autopoiesis  (2026-10-31)

## Corpus Check
- 18 files · ~10,982 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 3)

## Summary
- 291 nodes · 832 edges · 11 communities (9 shown, 2 thin omitted)
- Extraction: 80% EXTRACTED · 20% INFERRED · 0% AMBIGUOUS · INFERRED: 166 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3ddbf133`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Kernel
- cli.py
- mutator.py
- test_mutator.py
- ApoError
- render.py
- kernel.py
- .init
- autopoiesis — Specification v0.1
- autopoiesis-kernel

## God Nodes (most connected - your core abstractions)
1. `Kernel` - 57 edges
2. `Cell` - 40 edges
3. `Store` - 26 edges
4. `ApoError` - 19 edges
5. `_parser()` - 18 edges
6. `Gradient` - 17 edges
7. `_open()` - 16 edges
8. `FakeLLM` - 16 edges
9. `OpenAIMutator` - 14 edges
10. `ChildSpec` - 13 edges

## Surprising Connections (you probably didn't know these)
- `Local LLM` --references--> `NullMutator`  [INFERRED]
  README.md → src/autopoiesis/model.py
- `7. CLI `apo` (argparse, `autopoiesis/cli.py`, entry `main(argv=None) -> int`)` --references--> `ApoError`  [INFERRED]
  docs/SPEC.md → src/autopoiesis/model.py
- `3. Processes` --references--> `Gradient`  [INFERRED]
  docs/SPEC.md → src/autopoiesis/model.py
- `2. The three laws (enforced in code, never by an LLM)` --references--> `ConstitutionTampered`  [INFERRED]
  docs/SPEC.md → src/autopoiesis/model.py
- `configure()` --uses--> `Kernel`  [INFERRED]
  tests/test_kernel.py → src/autopoiesis/kernel.py

## Import Cycles
- None detected.

## Communities (11 total, 2 thin omitted)

### Community 0 - "Kernel"
Cohesion: 0.13
Nodes (6): 1. Cell anatomy, Kernel, Cell, RunResult, UnknownCell, Store

### Community 1 - "cli.py"
Cohesion: 0.13
Nodes (27): _cmd_add(), _cmd_approve(), _cmd_fitness(), _cmd_graph(), _cmd_hook_install(), _cmd_init(), _cmd_log(), _cmd_next() (+19 more)

### Community 2 - "mutator.py"
Cohesion: 0.11
Nodes (15): 3. Processes, ChildSpec, Gradient, Mutator, NullMutator, _child(), from_env(), _gradient() (+7 more)

### Community 3 - "test_mutator.py"
Cohesion: 0.15
Nodes (18): _cell(), _child(), fake(), FakeLLM, _Handler, _mutator(), _Server, test_critique_valid_and_upstream_in_prompt() (+10 more)

### Community 4 - "ApoError"
Cohesion: 0.11
Nodes (18): ApoError, _git_dir(), _head_commit(), install_hook(), _is_sha(), _resolve_ref(), snapshot(), watch() (+10 more)

### Community 5 - "render.py"
Cohesion: 0.14
Nodes (20): Event, _badge(), _body(), _compact(), _event_line(), _node(), _order(), _quote() (+12 more)

### Community 6 - "kernel.py"
Cohesion: 0.11
Nodes (6): Constitution, load(), _dna_hash(), run_shell(), Quarantined, Version

### Community 7 - ".init"
Cohesion: 0.19
Nodes (17): 2. The three laws (enforced in code, never by an LLM), ConstitutionTampered, configure(), FakeMutator, FakeRunner, test_apoptosis_obsolete_parent_done_and_idle(), test_constitution_tamper_requires_ratification(), test_energy_denied_and_process_caps() (+9 more)

### Community 8 - "autopoiesis — Specification v0.1"
Cohesion: 0.12
Nodes (15): 4. Storage (`.apo/cells.db`), 5. Constitution template (written by `apo init` if missing), 6. Python API (shared contract — names are fixed), 7. CLI `apo` (argparse, `autopoiesis/cli.py`, entry `main(argv=None) -> int`), 8. Non-goals (v0.1), autopoiesis — Specification v0.1, autopoiesis, Docs (+7 more)

## Knowledge Gaps
- **10 isolated node(s):** `autopoiesis-kernel`, `Why`, `Install`, `Quickstart`, `Safety` (+5 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 72 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Kernel` connect `Kernel` to `cli.py`, `mutator.py`, `ApoError`, `render.py`, `kernel.py`, `.init`?**
  _High betweenness centrality (0.185) - this node is a cross-community bridge._
- **Are the 27 inferred relationships involving `Kernel` (e.g. with `_cmd_init()` and `Constitution`) actually correct?**
  _`Kernel` has 27 INFERRED edges - model-reasoned connections that need verification._
- **What connects `autopoiesis-kernel`, `Why`, `Install` to the rest of the system?**
  _10 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Kernel` be split into smaller, more focused modules?**
  _Cohesion score 0.1349019607843137 - nodes in this community are weakly interconnected._
- **Why does `Cell` connect `Kernel` to `mutator.py`, `test_mutator.py`, `render.py`, `kernel.py`?**
  _High betweenness centrality (0.150) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `Cell` (e.g. with `Kernel` and `OpenAIMutator`) actually correct?**
  _`Cell` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Should `cli.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12685560053981107 - nodes in this community are weakly interconnected._
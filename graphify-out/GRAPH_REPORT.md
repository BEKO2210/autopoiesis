# Graph Report - autopoiesis  (2026-10-31)

## Corpus Check
- 25 files · ~15,993 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: (none) 3, .toml 1)

## Summary
- 353 nodes · 961 edges · 14 communities (12 shown, 2 thin omitted)
- Extraction: 76% EXTRACTED · 24% INFERRED · 0% AMBIGUOUS · INFERRED: 227 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `64788332`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Kernel
- cli.py
- mutator.py
- test_mutator.py
- watch.py
- render.py
- kernel.py
- .init
- autopoiesis
- autopoiesis-kernel
- autopoiesis — Specification v0.1
- main
- [Unreleased]

## God Nodes (most connected - your core abstractions)
1. `Kernel` - 58 edges
2. `Cell` - 40 edges
3. `Store` - 26 edges
4. `Gradient` - 20 edges
5. `ApoError` - 19 edges
6. `_parser()` - 18 edges
7. `_open()` - 16 edges
8. `FakeLLM` - 16 edges
9. `OpenAIMutator` - 15 edges
10. `ChildSpec` - 13 edges

## Surprising Connections (you probably didn't know these)
- `Local LLM` --references--> `NullMutator`  [INFERRED]
  README.md → src/autopoiesis/model.py
- `Workflow` --references--> `main()`  [INFERRED]
  CONTRIBUTING.md → src/autopoiesis/cli.py
- `Example: Python project walkthrough` --references--> `Constitution`  [INFERRED]
  examples/python-project/README.md → src/autopoiesis/constitution.py
- `4. LLM-written shell commands` --references--> `run_shell()`  [INFERRED]
  docs/safety.md → src/autopoiesis/kernel.py
- `2. Oscillation` --references--> `NullMutator`  [INFERRED]
  docs/safety.md → src/autopoiesis/model.py

## Import Cycles
- None detected.

## Communities (14 total, 2 thin omitted)

### Community 0 - "Kernel"
Cohesion: 0.10
Nodes (22): Changed, Cell anatomy, CLI surface, On `tick()` — the heartbeat, The three laws, 1. Reward hacking, 2. Oscillation, 3. Runaway mitosis (+14 more)

### Community 1 - "cli.py"
Cohesion: 0.19
Nodes (23): _cmd_add(), _cmd_approve(), _cmd_fitness(), _cmd_graph(), _cmd_hook_install(), _cmd_init(), _cmd_log(), _cmd_next() (+15 more)

### Community 2 - "mutator.py"
Cohesion: 0.09
Nodes (20): Concepts for developers, Heartbeat diagram, Mutator contract, On `run(cell)` ([SPEC.md](SPEC.md) §3), The four processes, 3. Processes, ChildSpec, Gradient (+12 more)

### Community 3 - "test_mutator.py"
Cohesion: 0.16
Nodes (18): _cell(), _child(), fake(), FakeLLM, _Handler, _mutator(), _Server, test_critique_valid_and_upstream_in_prompt() (+10 more)

### Community 4 - "watch.py"
Cohesion: 0.12
Nodes (18): 5. Watch and git hook, _git_dir(), _head_commit(), install_hook(), _is_sha(), _resolve_ref(), snapshot(), watch() (+10 more)

### Community 5 - "render.py"
Cohesion: 0.14
Nodes (19): Event, _badge(), _body(), _compact(), _event_line(), _node(), _order(), _quote() (+11 more)

### Community 6 - "kernel.py"
Cohesion: 0.12
Nodes (5): Constitution, load(), _dna_hash(), run_shell(), Version

### Community 7 - ".init"
Cohesion: 0.18
Nodes (17): configure(), FakeMutator, FakeRunner, test_apoptosis_obsolete_parent_done_and_idle(), test_constitution_tamper_requires_ratification(), test_empty_split_falls_back_to_recombination(), critique(), test_energy_denied_and_process_caps() (+9 more)

### Community 8 - "autopoiesis"
Cohesion: 0.22
Nodes (9): autopoiesis, Docs, Install, License, Local LLM, Processes and laws, Quickstart, Safety (+1 more)

### Community 11 - "autopoiesis — Specification v0.1"
Cohesion: 0.06
Nodes (30): 1. Correction, 2. Warning, 3. Temporary Ban, 4. Permanent Ban, Attribution, Contributor Covenant Code of Conduct, Enforcement, Enforcement Guidelines (+22 more)

### Community 12 - "main"
Cohesion: 0.13
Nodes (12): Code of conduct, Contributing, Documentation, Scope, Security, Setup, Workflow, main() (+4 more)

### Community 13 - "[Unreleased]"
Cohesion: 0.50
Nodes (3): Added, Changelog, [Unreleased]

## Knowledge Gaps
- **33 isolated node(s):** `autopoiesis-kernel`, `Added`, `Our Pledge`, `Our Standards`, `Enforcement Responsibilities` (+28 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 97 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Kernel` connect `Kernel` to `cli.py`, `mutator.py`, `render.py`, `kernel.py`, `.init`?**
  _High betweenness centrality (0.168) - this node is a cross-community bridge._
- **Are the 28 inferred relationships involving `Kernel` (e.g. with `_cmd_init()` and `Constitution`) actually correct?**
  _`Kernel` has 28 INFERRED edges - model-reasoned connections that need verification._
- **What connects `autopoiesis-kernel`, `Added`, `Our Pledge` to the rest of the system?**
  _33 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Kernel` be split into smaller, more focused modules?**
  _Cohesion score 0.10017050298380221 - nodes in this community are weakly interconnected._
- **Why does `Cell` connect `Kernel` to `mutator.py`, `test_mutator.py`, `render.py`, `kernel.py`?**
  _High betweenness centrality (0.117) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `Cell` (e.g. with `Kernel` and `OpenAIMutator`) actually correct?**
  _`Cell` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Should `mutator.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09487179487179487 - nodes in this community are weakly interconnected._
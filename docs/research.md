# Research background

This document records the sources that shaped autopoiesis v0.1.
For each source: what the paper (or body of work) actually claims, what
autopoiesis takes from it, and what it deliberately does **not** do.
Citations were opened and checked against title, authors, year, and claim.
Anything that could not be verified is marked **unverified**.

The fixed product contract is [SPEC.md](SPEC.md). Nothing here overrides it.

---

## 1. Maturana & Varela — autopoiesis

**Source (verified).** F. G. Varela, H. R. Maturana, and R. Uribe,
["Autopoiesis: The organization of living systems, its characterization and a model"](https://monoskop.org/images/d/dd/Varela_Maturana_Uribe_1974_Autopoiesis.pdf),
*Biosystems*, 1974. Collected with Maturana's 1970 essay in
H. R. Maturana and F. J. Varela,
[*Autopoiesis and Cognition: The Realization of the Living*](https://link.springer.com/book/10.1007/978-94-009-8947-4)
(D. Reidel / Springer, 1980).

**What it really does.** Defines living systems as *autopoietic*: a network of
component productions that (i) recursively produce the same network and
(ii) realize that network as a material unity. Autonomy and organizational
closure are primary; the product of the system's operation is the system
itself (as opposed to allopoietic machines whose product is something else).

**What autopoiesis takes.** The metaphor that a task graph should maintain
itself: cells (tasks) are produced, checked, fused, and removed under fixed
laws so the graph remains a working unity. Names (`mitosis`, `apoptosis`,
`fusion`, `recombination`) and the idea of a protected "germline"
(constitution + kernel, guarded by hash checks rather than filesystem
read-only mounts) vs mutable "soma" (cell DNA) borrow this language.

**What it deliberately does NOT do.** It does not claim biological
equivalence, does not model metabolism chemically, and does not treat
cognition as circular closure in Maturana's sense. The constitution is an
external, human-edited file with a hash check ([SPEC.md](SPEC.md) §2 Law 1),
not an emergent organizational invariant.

---

## 2. Michael Levin — morphogenesis / bioelectric homeostasis

**Source (verified).** Representative reviews of the research programme:
M. Levin, ["Endogenous bioelectrical networks store non-genetic patterning
information during development and regeneration"](https://doi.org/10.1113/jphysiol.2014.271940),
*Journal of Physiology*, 2014; M. Levin,
["Bioelectric signaling: Reprogrammable circuits underlying embryogenesis,
regeneration, and cancer"](https://www.cell.com/cell/fulltext/S0092-8674(21)00223-3),
*Cell*, 2021. Related: M. Levin, A. M. Pietak, and J. Bischof,
["Planarian regeneration as a model of anatomical homeostasis: Recent
progress in biophysical and computational approaches"](https://pubmed.ncbi.nlm.nih.gov/29635019/),
*Seminars in Cell & Developmental Biology* 87:125–144 (2019; online 2018;
[doi:10.1016/j.semcdb.2018.04.003](https://doi.org/10.1016/j.semcdb.2018.04.003)).

**What it really does.** Argues that non-neural cells use bioelectric
networks (membrane potentials, ion channels, gap junctions) as a control
layer for growth and form. Multicellular collectives exhibit *anatomical
homeostasis*: they reduce the error between current morphology and a
species-typical target morphology, then stop.

**What autopoiesis takes.** Goal-directed error reduction against an external
target. Fitness checks and `verify_cmd` act as target-morphology sensors
([SPEC.md](SPEC.md) §§1–3). Apoptosis of obsolete / idle / parent-done cells
and fusion of stable chains are homeostasis moves, not open-ended growth.

**What it deliberately does NOT do.** No bioelectric simulation, no
anatomical encoding, no planarian or regeneration experiments. Pressure is a
simple transitive-dependency count, not a voltage field.

---

## 3. TextGrad (Yuksekgonul et al., Nature 2025)

**Source (verified).** M. Yuksekgonul, F. Bianchi, J. Boen, S. Liu, P. Lu,
Z. Huang, C. Guestrin, and J. Zou,
["Optimizing generative AI by backpropagating language model feedback"](https://www.nature.com/articles/s41586-025-08661-4),
*Nature* 639, 609–616 (2025). Published 19 March 2025.
Code: [github.com/zou-group/textgrad](https://github.com/zou-group/textgrad).

**What it really does.** Treats LLM-generated natural-language critiques as
"textual gradients" and backpropagates them through a computation graph to
improve prompts, code, molecules, treatment plans, and agent systems — an
analogue of autodiff for text.

**What autopoiesis takes.** Recombination on failed `run` is TextGrad-style:
`mutator.critique(cell, log, upstream=direct deps)` returns a `Gradient`
naming the cell or one direct dependency; that target's `instruction`
(and optional `run_cmd`) is mutated ([SPEC.md](SPEC.md) §3;
`Gradient` in `model.py`).

**What it deliberately does NOT do.** No general autodiff engine, no molecule
or radiotherapy domains, no PyTorch-like Variable graph over the whole
project. Gradients only travel to the cell itself or a *direct* dependency,
and only after a failed run (not a continuous optimizer loop).

---

## 4. Gödel Agent (arXiv:2410.04444)

**Source (verified).** X. Yin, X. Wang, L. Pan, L. Lin, X. Wan, and W. Y. Wang,
["Gödel Agent: A Self-Referential Agent Framework for Recursively
Self-Improvement"](https://arxiv.org/abs/2410.04444), arXiv:2410.04444
(2024). Code: [github.com/Arvid-pku/Godel_Agent](https://github.com/Arvid-pku/Godel_Agent).

**What it really does.** A self-referential LLM agent inspired by
Schmidhuber's Gödel machine. It inspects and rewrites its own runtime code
(including the improvement loop) via monkey patching, aiming to search the
full agent design space without a fixed meta-algorithm.

**What autopoiesis takes.** The contrast: SPEC Law 1 states that the kernel
is germline and cells mutate, *not* the kernel — "no Gödel-style
self-patching — deliberate" ([SPEC.md](SPEC.md) §2). Cell DNA versioning and
taboo hashes are the limited, audited form of self-change allowed.

**What it deliberately does NOT do.** No monkey patching of the kernel, no
recursive rewrite of `tick`/`run`, no self-modification of the mutator
protocol. Non-goal in SPEC §8: "No kernel self-modification".

---

## 5. ADAS — Meta Agent Search (arXiv:2408.08435)

**Source (verified).** S. Hu, C. Lu, and J. Clune,
["Automated Design of Agentic Systems"](https://arxiv.org/abs/2408.08435),
arXiv:2408.08435 (2024). Code: [github.com/ShengranHu/ADAS](https://github.com/ShengranHu/ADAS).
Algorithm name: **Meta Agent Search** (archive-conditioned iterative
programming of new agents). This is **not** MCTS.

**What it really does.** Frames Automated Design of Agentic Systems (ADAS):
search space, search algorithm, evaluation. Meta Agent Search has a meta
agent iteratively program new agents in code from an ever-growing archive,
evaluate on validation data, repair errors, and store successful designs.

**What autopoiesis takes.** Archive / history of what worked: append-only
`versions` and `runs` tables ([SPEC.md](SPEC.md) §4). Mitosis asks the
mutator to invent child cells (new "designs") under hard caps. Evaluation is
always the cell's own immutable `verify_cmd`.

**What it deliberately does NOT do.** No outer meta agent that rewrites the
kernel or invents new process types. No archive of entire agentic systems in
Python. Search is local to one project's SQLite graph, not a multi-benchmark
agent zoo.

---

## 6. AFlow (arXiv:2410.10762)

**Source (verified).** J. Zhang, J. Xiang, Z. Yu, F. Teng, X.-H. Chen,
J. Chen, M. Zhuge, X. Cheng, S. Hong, J. Wang, B. Zheng, B. Liu, Y. Luo,
and C. Wu,
["AFlow: Automating Agentic Workflow Generation"](https://arxiv.org/abs/2410.10762),
arXiv:2410.10762 (2024). Uses **Monte Carlo Tree Search (MCTS)** over
code-represented workflows.

**What it really does.** Casts agentic workflow optimization as search over
code graphs. Each MCTS tree node is a complete workflow; selection, LLM
expansion, execution evaluation, and experience backpropagation discover
workflows without hand-building them.

**What autopoiesis takes.** Almost nothing algorithmic. AFlow is cited as a
*related* automated-workflow line that autopoiesis deliberately diverges
from: the heartbeat is a fixed, deterministic order (sense → apoptosis →
fusion → rollback), not MCTS.

**What it deliberately does NOT do.** No MCTS, no soft mixed-probability
selection over workflow variants, no tree of candidate graphs. Fusion is a
rule on linear successful chains, not a search expansion.

**Discrepancy note.** ADAS (Hu et al.) is Meta Agent Search; AFlow (Zhang et
al.) is MCTS. Do not conflate the two.

---

## 7. SEPM (arXiv:2610.14515)

**Source (verified).** Y. Liu, J. Zhao, L. Sun, J. Zhang, and S. Su,
["SEPM: Self-Evolving Procedural Memory Grounded in Task Graphs for
Multi-Agent Collaboration"](https://arxiv.org/abs/2610.14515),
arXiv:2610.14515 (2026).

**What it really does.** Couples multi-agent procedural memory with
coordination via shared task dependency graphs and a blackboard.
Procedures are created, refined, specialized, and retired from verified
execution evidence; divergence-aware alignment fixes goal / plan / state
drift.

**What autopoiesis takes.** Task dependency graphs as the unit of work;
verified outcomes gate promotion (here: `verify_cmd` must pass; parent
success cannot be faked by children — Law 1). Experience is stored
(versions/runs/events), not only the latest instruction.

**What it deliberately does NOT do.** No multi-agent team, no shared
blackboard across agents, no procedure pool across projects, no BM25 /
embedding retrieval of procedures. One kernel, one SQLite DB, one human /
agent operator via `apo`.

---

## 8. STRATA (arXiv:2610.19386)

**Source (verified).** G. Zhu, H. Li, Z. Wei, M. Du, and C. Yuan,
["STRATA: Self-Maintaining Structured Experience Graphs for Self-Evolving
Language Agents"](https://arxiv.org/abs/2610.19386), arXiv:2610.19386
(2026).

**What it really does.** A three-layer experience graph (atomic skills,
workflows, meta-frameworks) with typed edges, multi-dimensional similarity,
typed reflection, community detection for metas, pressure-triggered
forgetting with articulation-point protection, and contrast edges against
negative transfer.

**What autopoiesis takes.** Self-maintenance under pressure: hard caps
(`max_cells`, `max_depth`, `max_children`), energy costs, idle apoptosis,
and taboo / cooldown guards against oscillating mutations
([SPEC.md](SPEC.md) §§2–3). Structured history instead of a flat prompt dump.

**What it deliberately does NOT do.** No embedding similarity retrieval, no
Louvain communities, no contrast-edge lexicon, no three-layer memory graph.
Cell graph edges are dependency edges only (`deps`), not experience-type
edges.

---

## 9. Voyager skill library (arXiv:2305.16291)

**Source (verified).** G. Wang, Y. Xie, Y. Jiang, A. Mandlekar, C. Xiao,
Y. Zhu, L. Fan, and A. Anandkumar,
["Voyager: An Open-Ended Embodied Agent with Large Language Models"](https://arxiv.org/abs/2305.16291),
arXiv:2305.16291 (2023). Project: [voyager.minedojo.org](https://voyager.minedojo.org).

**What it really does.** An LLM-powered lifelong learning agent in Minecraft
with (1) an automatic curriculum, (2) an ever-growing skill library of
executable code indexed by description embeddings, and (3) iterative
prompting with environment feedback, execution errors, and self-verification.

**What autopoiesis takes.** Executable skills as first-class objects:
optional `run_cmd` plus mandatory `verify_cmd`; composition via mitosis /
fusion. DNA history is append-only in `versions`; successful versions are
recorded and are restored only by rollback, not reused as a skill library.
Curriculum-like pressure from ready cells ordered by dependency pressure.

**What it deliberately does NOT do.** No Minecraft / Mineflayer stack, no
automatic open-ended curriculum proposing novel goals, no vector DB of
skills across worlds. The project goal lives in `constitution.toml` and is
human-ratified, not curiosity-driven discovery.

---

## Summary table

| Source | Verified? | Taken | Explicitly rejected |
|---|---|---|---|
| Maturana & Varela | yes | self-maintaining unity; germline/soma | biological claim |
| Levin | yes | target morphology / homeostasis | bioelectric model |
| TextGrad | yes | textual gradient on deps | full autodiff framework |
| Gödel Agent | yes | (as negative example) | kernel self-patching |
| ADAS / Meta Agent Search | yes | archive of evaluated designs | outer meta-agent search |
| AFlow (MCTS) | yes | (related work only) | MCTS workflow search |
| SEPM | yes | graph + verified promotion | multi-agent blackboard |
| STRATA | yes | pressure, forgetting, structure | embedding memory graph |
| Voyager | yes | skill as code + verify; version history | open-ended curriculum / skill reuse |

No sources in this list were left unverified after opening the linked
abstract / article pages. If a future citation fails to resolve, mark it
**unverified** rather than inventing bibliographic detail.

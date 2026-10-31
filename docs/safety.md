# Safety

How [SPEC.md](SPEC.md) constrains failure modes that appear when an LLM
rewrites task DNA. This is honest about residual risk: the kernel laws are
necessary, not sufficient.

## Failure modes and SPEC countermeasures

### 1. Reward hacking

**Risk.** A mutator (or a human) writes a `verify_cmd` / fitness command that
always exits 0, or a child that "passes" so the parent looks done without
real progress.

**How SPEC stops it.**

- `verify_cmd` is immutable after birth ([SPEC.md](SPEC.md) §1 membrane;
  Law 1). The LLM cannot soften the contract of an existing cell.
- A parent is `done` only when **its own** `verify_cmd` passes — children
  created by mitosis cannot fake parent success (Law 1).
- Energy is earned only on verified progress: `reward_per_done` when a cell
  becomes `done` via `verify_cmd`, `reward_per_fitness` on fail→pass fitness
  flips (Law 2). There is no reward for mutation volume or for LLM
  confidence.
- Fitness checks live in the read-only constitution; changing them requires
  a human edit plus `apo ratify` (Law 1, §5).

**Limits.** A badly chosen initial `verify_cmd` (e.g. `true`) is still a
valid contract. SPEC does not judge semantic adequacy of shell commands.
Review `verify_cmd` at `add` time. Fitness cmds are equally trusted once
ratified.

### 2. Oscillation

**Risk.** A cell flips between two DNA variants forever, burning energy and
never converging.

**How SPEC stops it.**

- Law 3 oscillation guard: a mutation is rejected if its DNA hash was ever
  used by that cell before, or if the cell mutated less than
  `limits.mutation_cooldown_ticks` ticks ago ([SPEC.md](SPEC.md) §2).
- After `limits.rollback_window` runs, a version with a higher failure rate
  than the previous version is rolled back and its hash is added to a taboo
  set (Law 3).
- Every DNA change is append-only in `versions` with `origin` in
  `{birth, mutation, rollback}` (§4).

**Limits.** Taboo is per-cell hash equality, not semantic similarity. Two
paraphrases with different hashes can still thrash until cooldown / energy /
fail_streak push mitosis or denial. `NullMutator` avoids the issue by never
mutating.

### 3. Runaway mitosis

**Risk.** Repeated failures cause unbounded splitting into a huge task graph.

**How SPEC stops it.**

- Mitosis only when `fail_streak >= limits.fail_streak_for_mitosis`,
  `depth < max_depth`, and energy / caps allow (§3).
- Hard caps: `limits.max_cells` (active), `max_depth`, `max_children` (Law 2).
- Mitosis costs `budget.mitosis_cost`; insufficient energy → skip +
  `energy_denied` event.
- Parent gains a dependency on every child and must still pass its own
  `verify_cmd` (Law 1).
- Apoptosis removes obsolete, parent-done, and idle cells on `tick` (§3).

**Limits.** Caps are configuration. A constitution with huge `max_cells` /
tiny costs weakens the brake. `auto_approve_llm_commands = true` lets
children run without human review of LLM-written shells (see next section).

### 4. LLM-written shell commands

**Risk.** Mitosis or recombination invents a `run_cmd` (or child
`verify_cmd` at birth) that is destructive, exfiltrating, or unbounded
(`rm -rf`, network abuse, fork bombs).

**How SPEC stops it.**

- Default `trust.auto_approve_llm_commands = false` (§5). New LLM-written
  shell steps put the target cell in `quarantined` until `apo approve ID`
  (§3, §7).
- `Quarantined` cells are not ready; sense on `tick` skips them (§3).
- `trust.command_timeout_s` bounds wall time (timeout → exit 124 per §6
  `run_shell`).
- Constitution and kernel remain read-only to the LLM (Law 1).
- Events include `quarantined` and `approved` for audit (§4).

**Limits.**

- Quarantine is a human gate, not a sandbox. `approve` runs the command with
  the same privileges as the `apo` process (local user, cwd = project root).
- There is no network policy, syscall filter, or container in SPEC v0.1.
- `auto_approve_llm_commands = true` disables the gate; do not enable it on
  untrusted mutators.
- Birth-time `verify_cmd` chosen by mitosis is set once and then immutable;
  review quarantined children before approve.
- Non-goals (§8): no network service, no extra isolation layer.

## Operational recommendations

1. Keep `auto_approve_llm_commands = false` unless you accept full shell risk.
2. Write strict `verify_cmd` and `[[fitness]]` commands yourself; never let an
   LLM propose the constitution without review + `ratify`.
3. Use low `max_cells` / `max_depth` while testing mutators.
4. Read `apo log` and `apo graph` after ticks that trigger mitosis or
   mutation.
5. Report security issues privately — see [SECURITY.md](../SECURITY.md).

## What SPEC does not claim

SPEC v0.1 does not provide formal verification, capability-based sandboxing,
multi-tenant isolation, or guarantees against a malicious human operator with
write access to the repo and shell. The three laws bound *LLM-driven graph
evolution* inside one project directory. Treat `apo` like any other local
dev tool that can execute shell commands you (or an approved cell) supply.

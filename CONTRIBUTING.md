# Contributing

## Scope

[docs/SPEC.md](docs/SPEC.md) and `src/autopoiesis/model.py` are the fixed
contract for v0.1. Do not rename public types or CLI commands without an
explicit SPEC change.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
```

Runtime code must stay on the Python standard library only (SPEC intro).
Dev extras (`pytest`, `ruff`) are for contributors, not runtime.

## Workflow

1. Open an issue or discuss the change before large design shifts.
2. Branch from `main`. Do not push to `main` directly.
3. Prefer small [Conventional Commits](https://www.conventionalcommits.org/):
   `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
4. Include tests for kernel / store behaviour when you change them.
5. Open a pull request against `main`. One logical change per PR when
   practical.
6. Do not put personal email addresses or local absolute home paths into
   the repository.

## Documentation

Developer-facing docs live under `docs/`. Examples under `examples/` must
use only `apo` commands listed in SPEC §7.

## Code of conduct

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Security

See [SECURITY.md](SECURITY.md). Do not file public issues for undisclosed
vulnerabilities.

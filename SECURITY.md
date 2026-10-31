# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x (main) | yes |

## Reporting a vulnerability

Please report security issues **privately** through
[GitHub Security Advisories](https://github.com/BEKO2210/autopoiesis/security/advisories/new)
for this repository.

Do not open a public issue, discussion, or pull request that discloses an
unfixed vulnerability.

Include:

- affected version or commit
- description of the issue and impact
- steps to reproduce (proof of concept if available)
- any known mitigations

Maintainers will acknowledge the report and coordinate a fix and disclosure
timeline through the advisory.

## Trust boundary (v0.1)

`apo` can execute shell commands from cell `run_cmd` / `verify_cmd` /
fitness checks in the project directory. Default configuration quarantines
LLM-written commands until `apo approve`. See [docs/safety.md](docs/safety.md).

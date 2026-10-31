# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Docs aligned with kernel behaviour on main: single-transaction `tick`,
  empty `split()` skips recombination, `max_cells` includes quarantined,
  `fitness()` hash check, `approve` is state-only, version history is not
  skill reuse.

### Added

- Documentation: research background, concepts, and safety notes under `docs/`.
- Example Python project constitution and `apo` walkthrough under
  `examples/python-project/`.
- Contributor, security, code of conduct, and changelog community files.

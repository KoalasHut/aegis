# Changelog

## 0.2.1

Harden artifact validation and scenario specifications before adding behavioral
conformance. Agent protocol version remains 0.1.0.

- Fix decision leakage from examples (R-1) and test fixtures (R-2) into project
  validation, and false ID collisions across project/example scopes (R-3).
- Make structured `decisions.yaml` authoritative and require an approved decision
  in the same scope for approved domain rules (R-4).
- Require enforceable RFC3339 date-time validation instead of silently skipping
  formats (R-5), and check top-level scenario input/output fields against contracts
  (R-6). Nested contract fields remain opaque.
- Count automated scenarios, rather than manual-only scenarios, toward automated
  rule coverage (R-7). Replace ambiguous neutrality words with phrases and add
  per-context allowlists (R-8); scan glossary and contract prose (R-9).
- Standardize shared ID patterns and supersession: the new rule carries
  `supersedes`, while the retained old rule becomes deprecated. Add graph checks
  and `--base` protection for approved rule fields and retained IDs.
- Add push/PR GitHub Actions checks on Python 3.9 and latest stable 3.x, strict
  warning handling, PR base comparison and downloadable JSON findings. Required
  branch checks still need manual owner configuration.
- Define partial object/exact array matching, explicit matchers, captures,
  intentional setup errors, event scope and clock advancement. Use ordered
  `given.steps`; legacy `given.commands` remains accepted during 0.2.x migration.
- Add Tiny TODO as the primary isolated example; retain core-preservation as an
  advanced isolated example. Record OD-1 through OD-13 as structured decisions.

See [migration notes](docs/MIGRATION-0.2.md#from-020-to-021) for breaking artifact
changes and dependency updates. This release validates scenario structure and
references; it does not execute domain scenarios or supply behavioral conformance,
a runner/driver/matrix, workflow lanes, provisional-rule flow or legacy extraction.

## 0.2.0

Core-preservation milestone: keep decisions, domain rules, vocabulary and expected
behavior independent of implementation technology.

- Add identified domain rules, five rule types, context templates, rule registry
  and core-preservation constitution rules CPR-001 through CPR-005.
- Add structured context-owned scenarios, rule/scenario references from packs,
  and owner review of rules, scenarios and glossary.
- Add a Python validator for artifact structure, references, ID integrity and
  coverage, with human and JSON output and development dependencies.
- Make discussion and generated briefs problem-first: people/context, desired
  outcome, success signals and evidence before alternatives, candidate rules,
  scenarios and feature commitment.
- Record owner defaults OD-1 through OD-7 and provide
  [manual migration from 0.1.0](docs/MIGRATION-0.2.md).

This delivers phases 1 and 2 plus task 4.1 of the approved improvement milestone.
Scenario execution, conformance drivers/reports/matrix, workflow lanes,
provisional-rule reverse flow and legacy extraction remain deferred. A passing
validator is not runtime conformance evidence. Agent protocol version remains
0.1.0; initialization remains dependency-free and does not upgrade existing projects.

## 0.1.0

Initial reusable starter: scoped six-stage workflow, role and handoff contracts,
Concept Pack templates, optional uninstalled Codex candidates, and conservative
project initialization with onboarding guides.

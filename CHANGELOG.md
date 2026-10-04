# Changelog

## 0.2.3

Complete the artifact-side type model and define cross-stack value semantics
before executable conformance work. Agent protocol version remains 0.1.0.

- Add context-owned `types.yaml`, structured enums and records, list/map type
  expressions, recursive named references, shared normalized type trees and
  validation at nested record/list/map depth. Existing contract-level unions
  remain valid; qualified imported type resolution is reserved and not delivered.
- Treat prose types as opaque with `OPAQUE_TYPE` during 0.2.x. Add
  `UNKNOWN_TYPE`, `TYPE_SHADOWED`, `UNUSED_TYPE`, `UNKNOWN_FIELD`,
  `INVALID_ENUM_VALUE`, `MATCHER_TYPE_MISMATCH`, `CONTRADICTORY_EXPECTATION`,
  `UNSAFE_INTEGER`, capture-path/type and time-zone diagnostics.
- Make null and absent equivalent for optional expected values, while required
  input fields remain present and non-null. A separate complete actual-output
  conformance gate remains phase-3 work.
- Normalize calendar durations by `(years, months, fixed seconds)`, including
  mixed fixed components and explicit zeros. This intentionally makes
  `P1M1D` equal `P1MT24H`; years still do not collapse into months.
- Supersede OD-17 with exact normalized `number`/`decimal` comparison: exponent,
  trailing-zero and signed-zero representations normalize without tolerance.
  Canonical wire decimals are strings; integers are intrinsically limited to
  the JSON safe range.
- Compare `string` after NFC normalization, keep `id` and enums raw, require
  enum membership, and add explicit time-zone and collation vocabulary. Ordinal
  is the portable automated collation profile; locale ordering stays manual.
- Extend event expectations with `{event, input}` typed payload assertions.
  Capture traversal follows record fields only, rejects list indexing, captures
  maps as whole values and requires equal resolved source/target types.
- Report one visible finding per deterministic cause by default. Add verbose
  suppressed findings and same-scope, warning-only, approved-decision-backed
  allowances that remain visible while no longer failing strict validation.
- Record approved OD-21 through OD-34, with OD-22 superseding OD-19's nested
  opacity and OD-27 superseding OD-17's numeric semantics. Add executable
  matching examples and broaden nested validator/matcher regression coverage.
- Link 48 normative matching examples to stable specification clauses, require
  100% matcher branch coverage, and add seven property families, 22 executable
  historical regressions, and 30 executable validator mutations. Record locally
  reproduced Python, JavaScript, and .NET serializer output with source and
  runtime provenance; Kotlin/JVM and Swift remain explicitly unverified.

The reference matcher and validator specify and check artifact semantics. This
release still has no scenario runner, driver, executable imported-type resolver,
or conformance report/matrix. Kotlin and Swift serializer evidence was unavailable,
so five-stack conformance is not claimed. See
[migration notes](docs/MIGRATION-0.2.md#from-022-to-023).

## 0.2.2

Protect approved decisions and make scenario values portable before behavioral
conformance work begins. Agent protocol version remains 0.1.0.

- Fix in-place edits to approved decisions (F-1) and removal of decision IDs
  (F-2). `--base` now protects governed fields and retained IDs, while current
  validation checks decision supersession graphs. CPR-006 records the rule.
- Reject duplicate captures (F-3), captures on expected-error steps and invalid
  or whole-output capture references (F-4). Captured values retain their types.
- Compare declared `datetime` values as instants with expected precision (F-5),
  declared numbers by numeric value and fixed-unit durations by length. Other
  values stay strict; scenario literals are interpreted only through contract
  declarations.
- Require distinct actual elements for `$contains` and `$unordered` (F-6), using
  one-to-one assignment in the tested reference matcher.
- Reject product rules backed by `D-AEGIS-*` maintenance records and warn when a
  project has not been initialized (F-7). The untouched template is recognized
  only by exact maintenance-log hashes.
- Define the scalar vocabulary, validate top-level typed literals, and warn on
  unknown scalar types during 0.2.x. Nested contract fields remain opaque.
- Record OD-14 through OD-20 and add the phase 3 readiness checklist. The matcher
  is reference code for the specified semantics; this release still does not
  execute scenarios or provide a runner, driver protocol, report, or matrix.

See [migration notes](docs/MIGRATION-0.2.md#from-021-to-022) for capture cleanup,
date-time offsets and precision, scalar declarations, typed literals, matching,
decision history and project initialization.

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

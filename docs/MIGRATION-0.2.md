# Migrate an Aegis project through 0.2.x

For an existing 0.2.1 project, begin with [0.2.1 to 0.2.2](#from-021-to-022).
For 0.2.0, apply [0.2.0 to 0.2.1](#from-020-to-021) first. For 0.1.0, perform
the core-preservation steps below and then apply both later sections. Preserve
historical decisions and project identity throughout.

## From 0.1.0 to 0.2.0

The goal is to preserve the project's core across stack changes. This migration
gives existing business behavior stable rule IDs and structured scenarios; it
does not approve new behavior or prove an implementation conforms.

The initializer is not an upgrade tool. Do not rerun it or delete generated
documents to avoid conflicts. Preserve project identity, approvals, existing
contracts and evidence. Use a reviewed branch or disposable copy with an
explicit migration assignment; governance changes need named authority.

## 1. Review the template changes

Compare your adopted Aegis revision with the 0.2.0 release. Review new language
schemas, context/block templates, CPR constitution rules, registries, architect
and discussion instructions, validator, tests and `requirements-dev.txt`.
Merge reusable changes deliberately. Never replace populated project registries
or decision logs with empty template versions, or copy teaching examples as
approved product rules.

Keep `project.json`'s `aegis.version` as the version that initialized the project.
Record adoption of 0.2.0 and exact old/new template revisions in your project's
own migration decision; do not fabricate initialization history. The template's
VERSION becomes 0.2.0. Agent protocol fields stay 0.1.0 in this milestone.

## 2. Give existing domain behavior a home

Work one context at a time. Start its glossary and themed rule files from
`framework/templates/context/`. Review existing `invariants.md`, `concept.md`,
contract semantics and decision records for business rules. Assign stable
`BR-<CONTEXT>-NNN` IDs, type, owner, rationale, verification method and status.
Retain approving decision provenance for approved rules. Unclear or unsupported
behavior stays proposed and returns for owner review; running code is not approval.

Use `source` evidence for external constraints or extracted statements as
specified by the domain-rule schema. Status `extracted` alone does not install
an extraction workflow. Do not silently change an approved statement: use the
supersession procedure and keep retired IDs in the registry.

Update packs to reference rules they enforce or observe. Replace duplicated
business-rule text with references while preserving contract-specific input,
output, failure and effect semantics. Update the rule registry without reusing IDs.

## 3. Convert expected behavior into structured scenarios

Move behavior ownership to `framework/contexts/<context>/scenarios/`. Convert
existing Given/When/Then narrative into SC-identified YAML scenarios that
exercise BR IDs through public commands/queries. Cover expected output or error,
events and observation queries where applicable. Use command setup where possible;
seed setup requires a declared seed contract. Keep UI selectors, platform APIs
and storage inspection out of the core scenarios.

Preserve `scenarios.md` in a pack as helpful narrative if desired, but reference
the canonical context scenarios instead of maintaining a competing specification.
Have the owner review glossary, rules and scenarios. Architect artifacts must
remain consistent with those reviewed semantics.

## 4. Validate and review the migration

From the project root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
python3 scripts/validate.py
python3 scripts/validate.py --json
python3 -m unittest discover -s tests -v
```

For Windows PowerShell, use `.venv\Scripts\Activate.ps1` to activate. Correct
errors and review warnings, including missing automated scenario coverage and
potential platform language. Inspect every changed file, preserved decision
reference and acceptance mapping before accepting the migration. Structural
checks cannot authenticate approvals or replace semantic review.

## 5. Adopt problem-first discussion

Adapt existing brief templates manually: Problem, Who and when, Desired outcome,
Signals of success and Evidence come first. Compare alternatives, then record
candidate rules (`proposed`) and plain-language scenarios before committing to
features. Preserve previous approvals and open questions. A throwaway mockup is
an explicitly scoped question tool; record its resulting decision, never treat
its behavior as precedent.

## What this migration does not enable

Keep using the current full stage chain. No implementation lane, lane-diff gate,
conformance runner/driver/matrix, provisional-rule continuation or extractor role
is provided in 0.2.0. Existing mandatory unknowns still block dependent work.
Schema support for provisional/extracted statuses is not permission to bypass
that rule. Implementation checks and evidence remain explicitly assigned and
reviewed; a successful validator run does not mean scenarios passed on any stack.

## From 0.2.0 to 0.2.1

This release changes artifact formats and interpretation. Review the diff in a
bounded migration assignment; do not rerun initialization as an upgrade. Keep
`project.json`'s original initialization version and record the adopted release,
source revisions and review evidence in the project's migration decision.

### Make decision logs authoritative

Create or migrate `framework/decisions.yaml` and `agents/decisions.yaml`; examples
each use their own `decisions.yaml`. Entries use D-AREA-NNN IDs and the
[decision schema](../framework/language/schemas/decision.schema.json): title,
question, decision and status, plus approver, date and source for approved entries.
Markdown logs may remain as narrative, but no longer satisfy validator references.
Convert only actual approvals to `approved`; retain proposed/rejected decisions
with their correct status. Cite a same-scope approved decision from each approved
domain rule. Example decisions and test fixtures cannot back project rules.

Retain project decision IDs and sources. Do not replace your populated logs with
the template's maintenance decisions or an empty list. The initializer's special
replacement of recognized bundled maintenance logs is for a fresh project only;
it must not be used to erase migration history.

### Correct supersession and ID references

Put `supersedes: <old-id>` on the **new** rule. Mark the old rule `deprecated`
and otherwise retain it; do not add `supersededBy`. Likewise, a new decision can
supersede an old decision whose status becomes `superseded`. Targets must exist
in the same scope; cycles and multiple active replacements are invalid.
Use the shared ID grammar from
[common definitions](../framework/language/schemas/common.schema.json) and update
malformed references with reviewed migration evidence, never by reusing retired IDs.

Fetch an available baseline and run `python3 scripts/validate.py --base <git-ref>`.
An edited approved statement/type/verification or removed rule ID is an error.
Title/rationale clarifications require review and produce warnings. Deprecate and
supersede instead of editing approved behavior in place. Missing Git or baseline
history is a failed check, not evidence of compatibility.

### Adopt explicit scenario semantics

Use ordered `given.steps` for new scenarios. Move each legacy `given.commands`
entry into a step in the same order; `given.commands` remains accepted during
0.2.x migration, but never combine both forms. `given.clock` precedes setup;
`advanceClock` steps express time passing between commands.

Expected objects match partially, arrays match exactly in length and order, and
scalars match without coercion. Explicit `$contains`, `$unordered`, `$length`,
`$absent` and `$any` matchers are the closed alternative grammar; misspelled
matcher keys fail validation. Review old expected values for these semantics.
Use `as` to capture setup output and `${name.path}` only after that capture;
the first output field must exist in its contract. Mark intentional setup errors
with `expectError`; unexpected setup failure means scenario `error` for the future
runner. Event assertions cover only `when` events and match exactly unless
`eventsMatch: contains` is explicit. See the
[scenario specification](../framework/language/scenario-spec.md) and
[Tiny TODO example](../framework/examples/tiny-todo/).

Input/output checks cover top-level contract fields, not opaque nested types.
Automated rules need automated scenario coverage; manual-only scenarios no longer
satisfy that warning check. Review neutrality phrases across rules, scenarios,
glossary and contract prose. Use a context's `neutrality-allow.txt` only for
intentional legitimate domain language, with review rationale.

### Refresh dependencies and CI

Reinstall `requirements-dev.txt` in the project virtual environment, including
`rfc3339-validator`. Missing format support fails explicitly. Run the tests and
validator, then reproduce CI with `python3 scripts/validate.py --json --strict`
and the same command plus `--base <git-ref>`. Normal validation exits nonzero on
errors; strict mode also fails warnings while retaining JSON findings.

Adopt `.github/workflows/validate.yml` after reviewing existing project workflows.
It runs push/PR tests on Python 3.9 and latest stable 3.x, validates with strict
warnings, compares PRs to their fetched base and uploads JSON reports. Configure
required checks manually using [the CI guide](GETTING_STARTED.md#continuous-validation-on-github).
Neither adopting the file nor running initialization changes branch protection.

These are artifact and traceability checks. No domain scenario execution,
behavioral conformance, runner/driver/matrix, workflow lanes, provisional-rule
continuation or extraction workflow is provided by this migration.

## From 0.2.1 to 0.2.2

This release protects approved decisions, removes ambiguous capture behavior and
defines stack-neutral scalar and array matching. Adopt it in a reviewed migration
assignment. Do not rerun `init.py`: it creates new projects and is not an upgrade
tool. Keep the original `project.json` initialization version and record the
adopted Aegis revision in your own migration evidence.

### Clean up captures

Within each scenario, give every `given.steps` capture a unique name matching
`^[a-z][a-zA-Z0-9_]*$`. Remove `as` from every setup step with `expectError`;
failed steps have no output. Replace a bare `${name}` with a field reference such
as `${name.task.id}` and confirm that the first selected field exists in the
captured command's declared output. Captured values are substituted with their
original type and are never stringified.

Run validation after these edits. Duplicate names produce `DUPLICATE_CAPTURE`;
schema and reference findings identify invalid names, failed-step captures and
bad or forward references.

### Declare and review scalar types

For top-level contract input/output fields, use the recognized scalar vocabulary:
`string`, `boolean`, `integer`, `number`, `decimal`, `date`, `datetime`, `duration`
and `id`. Unknown scalar names warn during 0.2.x and become errors in 0.3.0, so
resolve every warning now. Nested types remain opaque and are not recursively
validated.

Review scenario literals against their contract declarations:

- Add `Z` or a numeric offset to every `datetime` expectation and input. The
  Aegis profile accepts offset-bearing minute, second and fractional-second
  forms. Values compare as timeline instants at the precision stated by the
  expectation: a minute expectation covers that minute, a second expectation
  covers that second, and a fractional expectation covers its stated fraction.
- Keep `date` values as valid `YYYY-MM-DD` calendar dates.
- Use the supported nonnegative ISO 8601 duration subset. Fixed units compare by
  length (`PT120M` equals `PT2H`); calendar-unit durations compare literally.
- Review `integer`, `number` and `decimal` fields as numeric values. Decimal
  comparison is exact; integer and decimal representations such as `1` and `1.0`
  can match. A string such as `"1"` is never coerced.
- Treat `id` as an opaque string and prefer captured IDs over implementation
  specific literals.

The validator checks typed top-level literals but still does not execute a
scenario. `INVALID_TYPED_VALUE` and `DATETIME_WITHOUT_OFFSET` are migration
errors, not runner results.

### Adopt one-to-one array matching

Recheck every `$contains` and `$unordered` expectation. Each expected element
must match a distinct actual element; one actual item cannot satisfy duplicate
expectations. `$unordered` also consumes every actual element, while `$contains`
allows extras. This can change the result of scenarios that relied on greedy
matching of partially matched objects.

`scripts/aegis_match.py` and its tests are the reference implementation for the
specified recursive, typed and one-to-one behavior. They demonstrate the matching
rules but do not call your application, execute scenarios or produce conformance
reports.

### Preserve approved decision history

Fetch the reviewed base and run:

```bash
python3 scripts/validate.py --base <git-ref>
python3 scripts/validate.py --json --strict --base <git-ref>
```

Do not edit an approved decision's question, decision, approver, date or source,
delete its ID, or change its status except through valid supersession. To replace
one, retain the old record with status `superseded`, add a new approved decision
with `supersedes: <old-id>`, and move dependent rules to the new ID. Proposed
decisions remain editable. Title or `affects` changes warn and need review.

### Confirm project initialization and maintenance provenance

An existing initialized project keeps its own decision logs and `project.json`.
Never copy `D-AEGIS-*` maintenance records into a project log or cite them from a
product rule; 0.2.2 rejects such citations. If a template copy was never
initialized, create a disposable backup and follow the new-project initialization
instructions rather than deleting logs manually. Exact bundled logs are replaced;
edited or unrecognized logs block safely for owner review.

Finish by reinstalling `requirements-dev.txt`, running the complete test suite,
normal validation and strict base validation, and reviewing every warning. The
agent protocol remains 0.1.0. Phase 3 runners, drivers, reports and matrices,
workflow lanes, provisional-rule flow and nested contract-field validation remain
outside this release.

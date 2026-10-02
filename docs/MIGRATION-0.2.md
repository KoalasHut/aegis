# Migrate an Aegis 0.1.0 project to 0.2.0

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

# Framework maintenance decisions

This file is narrative. [decisions.yaml](decisions.yaml) is authoritative for
validation. OD-1 through OD-5 map to D-AEGIS-001 through D-AEGIS-005; OD-8 through
OD-12 map to D-AEGIS-008 through D-AEGIS-012. Workflow decisions OD-6, OD-7 and
OD-13 are in [the agents YAML log](../agents/decisions.yaml).

These are Aegis framework decisions, not generated-project product approvals.
Owner/issuer: Diego. Approval source, proposal digest, starting revision and
milestone scope are retained in [the 0.2.0 provenance record](../agents/decisions.md).
OD-1 through OD-5 below use that same approval, transcribed under dispatcher
assignment `aegis-020-workflow`. Their effective release is 0.2.0; the later
hardening defaults have separate 0.2.1 provenance recorded below.

## OD-1 — Domain rule identity (approved)

Decision: call business behavior specifications **domain rules**, identified by
`BR-<CONTEXT>-NNN`; keep existing constitution-rule prefixes. Rationale: stable
business references must be distinguishable from framework governance rules.
Alternative: use the same term/prefix for both. Consequence: domain rules get
their own schema, language specification and registry; blocks reference IDs.

## OD-2 — Themed YAML rule files (approved)

Decision: group related domain rules in themed YAML files, keeping IDs unique
across the project. Rationale: review cohesive decisions without creating one
file per sentence. Alternative: one rule per file. Consequence: file boundaries
do not define rule identity; context templates and validator handle rule lists.

## OD-3 — Structured YAML scenarios (approved)

Decision: use structured YAML scenarios at context level, expressed through
public commands/queries and contract-shaped results. Rationale: avoid matching
free-form step text and retain portable expected behavior. Alternative: Gherkin.
Consequences: owners review scenarios with rules and glossary; packs reference
scenario IDs and may retain human narrative separately. Structure validation is
provided now; scenario execution is deferred.

## OD-4 — Python tooling (approved)

Decision: use Python for validation and the future conformance runner.
Rationale: Python is already required for initialization. Alternatives: introduce
another required language/runtime. Consequences in 0.2.0: a Python artifact
validator and declared development dependencies; the initializer remains
standard-library-only. No conformance runner is delivered by this decision.

## OD-5 — JSON Lines driver transport (approved direction; deferred)

Decision: use JSON Lines over standard input/output as the future reference
driver transport; native test generation may be considered later. Rationale:
keep stack integration small and language-neutral. Alternative: mandate a
language-specific test framework. Consequence: phase 3 can use this default,
but 0.2.0 provides no driver protocol implementation, runner, results or matrix.

OD-6 (lanes) and OD-7 (version) are recorded in
[workflow decisions](../agents/decisions.md). Provisional-rule execution and
legacy extraction remain deferred; a status value does not grant a new role or
relax the existing requirement to resolve mandatory unknowns before dependent work.

For each decision, record its ID, date, question, alternatives, chosen policy, rationale, accountable owner, explicit approval source, affected artifacts and exact revisions. Proposals remain proposals until approved. Do not carry another project's approvals into this log.

## Hardening defaults approved for 0.2.1

Diego approved the following on 2026-10-02 in the current Aegis maintenance
conversation. The [workflow provenance record](../agents/decisions.md) retains
the plan digest, baseline and dispatcher/release assignment references.

- OD-8: structured YAML decisions are authoritative; Markdown remains narrative.
- OD-9: the new rule points to the old through `supersedes`; retain the old rule
  as deprecated. Decisions follow the same direction with status superseded.
- OD-10: project and each example are isolated scopes; test fixtures do not
  satisfy project references.
- OD-11: case-insensitive neutrality phrases and reviewed context allowlists
  replace ambiguous single-word warnings.
- OD-12: arrays match exactly by default, objects partially, scalars without
  coercion; explicit matchers opt out. Ordered `given.steps` is canonical and
  legacy `given.commands` remains accepted during 0.2.x migration.

The owner also selected Tiny TODO as the primary example and retained
core-preservation as an advanced isolated example. Scenario semantics are
specified and validated structurally; no runner executes them in this release.
Historical OD-1 through OD-7 approvals retain the date 2026-10-01 in YAML.

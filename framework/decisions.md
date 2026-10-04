# Framework maintenance decisions

This file is narrative. [decisions.yaml](decisions.yaml) is authoritative for
validation. OD-1 through OD-5 map to D-AEGIS-001 through D-AEGIS-005; OD-8 through
OD-12 map to D-AEGIS-008 through D-AEGIS-012; OD-14 through OD-19 map to
D-AEGIS-014 through D-AEGIS-019; OD-21 through OD-34 map to D-AEGIS-021
through D-AEGIS-034. Workflow decisions OD-6, OD-7, OD-13 and OD-20 are in
[the agents YAML log](../agents/decisions.yaml).

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

## Final phase 3 hardening defaults approved for 0.2.2

Diego approved OD-14 through OD-20 on 2026-10-02 using the defaults in the
reviewed 0.2.2 plan, with an explicit Aegis-profile clarification for
offset-bearing minute-precision date-times. The authoritative records above
retain the approval source and plan digest.

- OD-14 protects approved decision meaning and provenance. Only a valid
  approved-to-superseded transition is allowed; title and `affects` edits warn.
- OD-15 forbids captures on setup steps that expect errors.
- OD-16 compares declared date-times as instants at the precision stated by the
  expectation, including the offset-bearing minute-precision Aegis form.
- OD-17 compares declared numeric types by numeric value, with exact decimals
  and no string coercion.
- OD-18 requires a distinct actual array element for every expected element
  under `$contains` and `$unordered`.
- OD-19 selects typed semantics from contract declarations rather than guessing
  from value shapes; nested fields remain opaque.

OD-20, the maintenance-decision guard, is summarized in the workflow narrative.
The tested matcher is a reference implementation of these semantics, not a
scenario runner or conformance result.

## Type and cross-stack semantics approved for 0.2.3

Diego approved OD-21 through OD-34 on 2026-10-03 using the defaults in the
reviewed 0.2.3 plan plus the orchestrator's conservative resolutions of audit
S-02 through S-24. The authoritative records retain the exact plan and audit
digests and the reviewed Wave 1 revision. OD-27 supersedes OD-17's numeric
policy; OD-22 supersedes OD-19's top-level-only type limit. The old records stay
in the YAML log with `status: superseded`.

- OD-21 puts reusable types in a context `types.yaml`. Qualified imported types
  remain reserved until manifest namespace and version resolution is implemented.
- OD-22 closes the type-expression grammar over scalars, enums, records, lists,
  maps and lazy named references. It excludes inline type unions while preserving
  existing contract-level union kinds. Requiredness remains on record fields and
  equality uses resolved normalized trees.
- OD-23 permits opaque prose types with `OPAQUE_TYPE` during 0.2.x. Validation
  stops below that boundary; reachability begins at contract fields, so a
  recursive self-reference alone does not make a type used.
- OD-24 and OD-25 make absent and null equivalent for optional observable values.
  Required inputs remain present and non-null. Partial expected-object matching
  is separate from the complete actual-output check deferred to phase 3.
- OD-26 normalizes durations to years, months and fixed seconds. Fixed components
  normalize even in mixed values (`P1M1D` equals `P1MT24H`), explicit zero
  components do not change a value, and years never collapse into months.
- OD-27 compares `number` and `decimal` by exact normalized decimal value, with
  no tolerance. Exponents, trailing zeros and signed zero normalize; authors use
  quoted decimals when source-lexeme precision matters.
- OD-28 defines lossless wire forms: decimal strings and safe-range JSON integers,
  plus offset-bearing date-times, dates and durations. A runner/driver protocol
  and actual-output conformance gate are still phase-3 work.
- OD-29 makes the business time zone explicit and uses available `zoneinfo` data
  for artifact validation. Tzdb version/capability and DST execution evidence
  belong to phase 3.
- OD-30 applies NFC to `string`, while `id` and enum members remain raw.
- OD-31 requires semantic review of text-ordering rules. Ordinal NFC code-point
  order is the only portable automated profile in 0.2.3; locale-aware assertions
  remain manual and CPR-008 applicability is not inferred from prose.
- OD-32 makes enums closed, raw and case-sensitive.
- OD-33 lets captures traverse record fields only, forbids list indexing, treats
  maps as whole values and requires equal resolved source and target types,
  including typed event payloads. Event expectations retain string references
  and add `{event, input}` for a typed payload assertion.
- OD-34 reports the highest-priority diagnosis for one deterministic cause by
  default. Verbose mode exposes dependent findings. Same-scope, warning-only,
  decision-backed allowances apply after suppression and stay visible.

These decisions specify artifact and matching behavior. Release 0.2.3 does not
claim a scenario runner, driver, imported-type integration, or five-stack corpus.

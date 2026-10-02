# Domain rule language

Domain rules are the versioned, owner-facing statements of business behavior. A
context owns its glossary and themed YAML rule files under
`framework/contexts/<context>/rules/`. A rule ID is stable and is never reused,
including after deprecation. The file is a YAML list validated as a whole by
`schemas/domain-rule.schema.json`.

Each rule uses `BR-<CONTEXT>-NNN`, where `<CONTEXT>` is one or more uppercase
letter-and-digit segments separated by hyphens. Use plain business language in
`title`, `statement`, and `rationale`.
Do not name a language, framework, storage mechanism, endpoint, UI control, or
other implementation detail. A constraint may name an external authority in
its structured `source`.

## Required fields and lifecycle

Every rule has an ID, title, statement, type, status, owner, rationale, and
verification method. `owner` is the person or role accountable for the rule;
it is not an implementation owner. `verification` is `automated`, `manual`,
or `review`.

`proposed` records a candidate awaiting owner decision. `provisional` is a
temporary, unapproved discovery and must be resolved by the governing workflow.
`extracted` records observed legacy behavior and requires source evidence.
`approved` is authoritative and requires the approving `D-...` decision ID.
`deprecated` preserves a retired ID. Do not change an approved statement in
place: deprecate the old rule unchanged, create the replacement, and put
`supersedes: <old-rule-id>` on the new rule. `supersededBy` is derived from the
catalog and is never stored.

`source` has a source kind and a durable reference. A `constraint` always
requires one. An `extracted` rule also requires a locator, such as a file and
line range or an authoritative section, so that the observation is auditable.

## Decision lifecycle

Structured decisions begin as `proposed`. The domain owner may move a proposal
to `approved` or `rejected`. An approved decision is authoritative and its
`question`, `decision`, `status`, `approver`, `date`, and `source` are governed
history. Do not edit those fields in place. To replace an approved decision,
retain it with status `superseded`, create a new approved decision with
`supersedes: <old-decision-id>`, and move dependent rules to the new decision.
An approved decision may have at most one approved successor. `title` and
`affects` remain editorial, but changing either is reported for review.

Decision IDs are permanent: retain proposed, rejected, approved, and superseded
records. Proposed decisions may be revised while discussion is active.

## Rule types

| Type | Use it for | Example form |
| --- | --- | --- |
| `invariant` | A condition that must always hold. | "An account balance is never negative." |
| `policy` | A business choice that can change over time. | "Orders above the threshold receive free delivery." |
| `calculation` | A derivation or decision from stated inputs. | "The delivery charge is determined by order value." |
| `constraint` | A requirement imposed outside the product. | "Records are retained for the required period." |
| `quality` | A business-level expectation about the experience or result. | "A person receives confirmation before an irreversible action." |

Use `effectiveFrom` for a dated policy when it matters. A calculation may carry
a `decisionTable`; its inputs, outputs, and rows make the decision reviewable
without turning it into executable implementation logic. A decision table can
only appear on a calculation.

## References from Concept Packs

Concept Packs reference domain rules by ID. `manifest.yaml` distinguishes the
rules the block enforces from rules it observes, and lists context-owned
scenario IDs that cover the block. The pack may explain responsibility and
evidence, but it must not copy a rule statement. The canonical rule and
scenario remain in the context.

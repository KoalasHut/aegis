# Scenario language

A context owns scenarios in `framework/contexts/<context>/scenarios/`. A
scenario states observable business behavior independently of a user interface,
process, storage mechanism, or platform API. Its ID is `SC-<CONTEXT>-NNN`; once
issued it remains unique and is never reused.

Each YAML file is a list of scenarios. Every scenario exercises one or more
domain-rule IDs, declares whether it is automated or manual, establishes state
through public commands (or a declared seed contract), performs exactly one
public command or query, and asserts an output or error. `then.observe` checks
state only through public queries.

## Setup and execution

`given.steps` is the canonical ordered setup form. Each step is either a public
command or `advanceClock: <ISO-8601-duration>`. `given.clock` sets the instant
before the first step. A driver without clock capability reports a scenario
using `clock` or `advanceClock` as unsupported.

`given.commands` is the legacy shorthand accepted during the 0.2.x migration.
It has the same command-step shape but cannot express clock advancement. New
scenarios use `given.steps`; migrate a legacy command list by making each
command a step in the same order. A scenario must use one form or the other,
never both.

A command setup step may use `as: <name>` to capture its output. Later setup
steps, `when`, and expected values can reference a captured value as
`${name.path}`, for example `${task1.task.id}`. A reference must name an
earlier capture and its first path segment must be declared in the captured
operation's output contract. Capture names match `^[a-z][a-zA-Z0-9_]*$` and
are unique within a scenario. A reference is a complete scalar value, requires
at least one field after the capture name, and is substituted as-is with its
type preserved. `${task1}` and string interpolation around a reference are not
valid. Any string containing `${` must therefore be exactly one valid capture
reference; malformed tokens such as `${task1.}` are invalid too.

A failed setup step makes the scenario an `error` (invalid setup), never a
pass or fail. Add `expectError: <code>` only when that setup failure is
intentional; the code must be declared by the command's error contract. A step
with `expectError` cannot declare `as`, because a failed operation has no
output to capture.

`given.seed` is permitted only when its `contract` names a declared seed port;
use it for states that cannot be reached through commands.

## Matching

Expected objects match partially: only listed keys are compared, while extra
actual keys are ignored. Arrays match exactly by default: they must have the
same length and order, and each element is matched recursively.

### Value comparison

Scalar comparison is selected from the field's contract-declared type. It is
never inferred from the shape of a scenario or implementation value. Only
top-level contract fields are type-directed in 0.2.x; nested semantic types
remain opaque.

- `datetime` values use an Aegis profile based on RFC 3339. Both values require
  `Z` or a numeric offset and are compared on the timeline. In addition to RFC
  3339 date-times, the profile accepts an offset-bearing minute-precision form
  without seconds, such as `2026-10-02T09:00Z`. This extension preserves the
  F-5 cross-stack serialization case. Thus `2026-10-02T09:00:00Z` matches both
  `2026-10-02T11:00:00+02:00` and `2026-10-02T09:00:00.000Z`; it also matches
  an implementation serialization of `2026-10-02T09:00Z`.
- `date` values compare as calendar dates in `YYYY-MM-DD` form.
- `duration` values use the nonnegative Aegis ISO 8601 subset. Components are
  ordered as years, calendar months, weeks, days, then `T` and hours, minutes,
  seconds. Quantities are integers except that seconds may have a decimal
  fraction. At least one component is required, `T` requires a time component,
  and a week component cannot be combined with another component. Fixed units
  (weeks, days, hours, minutes, and seconds) compare by elapsed length, so
  `PT120M` equals `PT2H` and `P1D` equals `PT24H`. A value containing calendar
  years or months, including a calendar/fixed mixed value, compares as the
  complete literal string because its length depends on context.
- `integer`, `number`, and `decimal` compare by numeric value, so `1` equals
  `1.0`. Decimal comparison uses exact decimal arithmetic, never binary
  floating point. Numeric values must be finite; NaN and positive or negative
  infinity are invalid typed values and never match.
- `string`, `boolean`, and `id`, plus values without a recognized scalar type,
  use strict equality without coercion. IDs are opaque strings. In particular,
  a string field containing `"1"` never equals the number `1`, and a string
  that resembles a date-time remains a string.

The expected date-time defines a half-open interval on the timeline. A
minute-precision expectation covers `[minute, minute + 60 seconds)`, a
whole-second expectation covers `[second, second + 1 second)`, and an
expectation with *n* fractional digits covers
`[expected, expected + 10^-n seconds)`. For example, expected
`2026-10-02T09:00:00Z` matches actual `2026-10-02T09:00:00.999Z` but not
`2026-10-02T09:00:01Z`; expected `2026-10-02T09:00:00.12Z` matches actual
`2026-10-02T09:00:00.129Z` but not `2026-10-02T09:00:00.130Z`. A date-time
without an offset is invalid, not a local-time comparison.

Use one explicit matcher object to opt out of the default behavior:

| Matcher | Meaning |
| --- | --- |
| `{ $contains: [...] }` | Listed array elements are present in any order, each using a distinct actual element. |
| `{ $unordered: [...] }` | Array has exactly these elements in any order, with a one-to-one assignment. |
| `{ $length: n }` | Only the array length is compared. |
| `{ $absent: true }` | The surrounding object key must be absent. |
| `{ $any: true }` | The surrounding object key must be present with any value. |

Matcher keys are closed vocabulary. Any unknown `$...` key is a schema error,
not a literal expected value.

`$contains` and `$unordered` use one-to-one matching: no actual array element
can satisfy two expected elements. `$unordered` also requires every actual
element to be used; `$contains` permits unused actual elements. Runner authors
can implement this as a small bipartite assignment with an augmenting-path
search. Greedy first-match is incorrect because expected objects match
partially.

For example, `$unordered: [{state: open}, {state: open}]` does not match
`[{id: a, state: open}, {id: b, state: complete}]`: only one distinct actual
item is open. Conversely, `$contains: [{state: open}, {id: a}]` does match
`[{id: a, state: open}, {id: b, state: open}]`. A greedy matcher may consume
item `a` for the first expectation and incorrectly fail the second; a valid
assignment uses item `b` first and item `a` second.

## Results, events, and observation

`then.output` and `then.error` are alternatives. `then.events` applies only to
events emitted by the `when` operation: setup events are ignored. Event lists
are exact by default, so unexpected events fail the match. Set
`eventsMatch: contains` only when extra events are explicitly acceptable.

Use neutral names such as `tasks.add` and `tasks.list`. Do not mention screens,
buttons, HTTP, databases, tables, endpoints, caches, frameworks, or programming
languages. A scenario is a contract for the use-case boundary, not an
implementation test.

The validator checks schema shape, ID uniqueness and retirement, references,
automated-rule coverage, capture ordering and output paths, setup error codes,
top-level typed literals, and configured neutrality phrases. Nested
contract-field checks remain outside the 0.2.x validator scope. The normative
text above is authoritative; `scripts/aegis_match.py` is a tested reference
implementation for runner authors.

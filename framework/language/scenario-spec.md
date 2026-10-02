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
operation's output contract.

A failed setup step makes the scenario an `error` (invalid setup), never a
pass or fail. Add `expectError: <code>` only when that setup failure is
intentional; the code must be declared by the command's error contract.

`given.seed` is permitted only when its `contract` names a declared seed port;
use it for states that cannot be reached through commands.

## Matching

Expected objects match partially: only listed keys are compared, while extra
actual keys are ignored. Arrays match exactly by default: they must have the
same length and order, and each element is matched recursively. Scalars match
by strict equality with no type coercion.

Use one explicit matcher object to opt out of the default behavior:

| Matcher | Meaning |
| --- | --- |
| `{ $contains: [...] }` | Listed array elements are present in any order. |
| `{ $unordered: [...] }` | Array has exactly these elements in any order. |
| `{ $length: n }` | Only the array length is compared. |
| `{ $absent: true }` | The surrounding object key must be absent. |
| `{ $any: true }` | The surrounding object key must be present with any value. |

Matcher keys are closed vocabulary. Any unknown `$...` key is a schema error,
not a literal expected value.

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
and configured neutrality phrases. Nested contract-field checks remain outside
the 0.2.1 validator scope.

# Aegis type language

**TS-001.** Type declarations give scenario values stack-neutral meaning. A context owns
one optional `types.yaml` next to its glossary. Contracts refer to those types
by name and may retain contract-local `types` only for operation-specific
shapes. A name declared both locally and in the context is invalid
(`TYPE_SHADOWED`); a local declaration never overrides a context declaration.

## Grammar and resolution

**TS-002.** The closed 0.2.x grammar is:

```text
Type   := Atom | Type "[]" | "map<" Type ">"
Atom   := Scalar | Name
Scalar := string | boolean | integer | number | decimal | date | datetime |
          duration | id
Name   := an unqualified local/context name
```

**TS-003.** Lists preserve order unless an explicit scenario matcher changes comparison.
Maps have string keys and one value type. Records use `fields`; enums use
`enum`. Unions are not part of this grammar. Named references resolve lazily,
so records may be recursive. Resolution checks contract-local and context
names; their names use `^[A-Za-z][A-Za-z0-9_]*$`. An unresolved name is
`UNKNOWN_TYPE`.

**TS-004.** Qualified `context.Type` syntax and manifest-driven import loading
are reserved for a later release. In 0.2.3, the low-level Python registry API
may receive a pre-resolved mapping whose keys are qualified names, but language
artifacts cannot declare or load such a mapping and unresolved qualified names
remain `UNKNOWN_TYPE`.

```yaml
types:
  TaskState:
    description: Whether a task still needs attention.
    enum: [open, complete]
  Task:
    description: A task and its optional due instant.
    fields:
      id: {type: id, required: true}
      state: {type: TaskState, required: true}
      dueAt: {type: datetime}
      tags: {type: "string[]"}
      notes: {type: "map<string>"}
  TaskTree:
    description: A task with recursive children.
    fields:
      task: {type: Task, required: true}
      children: {type: "TaskTree[]"}
```

**TS-005.** A prose string remains a valid local type declaration during 0.2.x. It
produces warning `OPAQUE_TYPE`, and the complete value beneath that type uses
strict equality. Prose-only types become errors in 0.3.0.

## Normalized model

Validators and matchers share the nodes produced by `scripts/aegis_types.py`:

```text
{kind: scalar, name: datetime}
{kind: enum, name: TaskState, values: [open, complete]}
{kind: record, name: Task, fields: {...}, required: [id, state]}
{kind: list, item: <type>}
{kind: map, value: <type>}
{kind: ref, name: TaskTree}
{kind: opaque, name: LegacyRule}
```

**TS-006.** `required: true` means a record field is always present and non-null. A field
whose `required` member is omitted or false is optional and may have no value.
There is no separate nullable flag. An expected null or `$absent` on a
required field is a `CONTRADICTORY_EXPECTATION`.

## Scalar values

**TS-007.** `string` compares after Unicode NFC normalization, code point by code point;
there is no case folding or trimming. `id` compares raw and remains opaque.
Enum members are case-sensitive strings from the declared closed set; a
literal outside it is `INVALID_ENUM_VALUE`.

**TS-008.** `integer` uses a JSON number and is restricted to the inclusive safe range
`-(2^53 - 1)` through `2^53 - 1`; an out-of-range scenario literal is
`UNSAFE_INTEGER`.

**TS-009.** `number` uses exact equality of each parsed decimal value. YAML and
JSON loaders must preserve the source numeric lexeme without first converting
it to binary floating point. Comparison does not use tolerance. Authors use
`decimal` for exact quantities and do not assert rounded binary arithmetic as
`number`.

**TS-010.** `decimal` accepts a JSON number or a decimal string in scenario
YAML and compares by exact decimal value. Decimal strings accept exponent
notation; exponent form, trailing zeros, and signed zero do not change value.
Its canonical driver wire form remains a string.

**TS-011.** `date` uses `YYYY-MM-DD`. `datetime` uses the offset-bearing Aegis RFC 3339
profile in the scenario specification. `duration` uses the nonnegative Aegis
ISO 8601 subset and component normalization described there.

**TS-012.** Map keys are string values and compare after NFC normalization.
Expected and actual maps are each required to have at most one raw key for
each NFC-normalized key. An expected collision is `DUPLICATE_MAP_KEY`; an
actual collision is a contract violation and cannot match. Record field names
are declared identifiers and continue to compare raw. Collision inspection
walks the complete resolved typed value, including nested records, lists, and
maps, and reports the path of each collision. A non-string map key is invalid
and produces a clean non-match rather than being normalized.

**TS-013.** Enum declarations are unique after NFC normalization. NFC-equal
members are `INVALID_TYPE_DEFINITION`, reported at the definition. Valid enum
values still compare raw and case-sensitively at match time; enum matching
does not apply the `string` normalization rule.

The numbered, executable examples M-01 onward live in
`examples/matching.yaml`. They are part of this specification.

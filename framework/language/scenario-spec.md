# Scenario language

A context owns scenarios in `framework/contexts/<context>/scenarios/`. A scenario
states observable business behavior independently of a user interface, process,
storage mechanism, or platform API. Its ID is `SC-<CONTEXT>-NNN`; once issued it
remains unique and is never reused.

Each YAML file is a list of scenarios. Every scenario exercises one or more
domain-rule IDs, declares whether it is automated or manual, establishes state
through public commands (or a declared seed contract), performs exactly one
public command or query, and asserts an output or error. `then.observe` checks
state only by public queries. Partial object matches are intentional: the
scenario names the business-relevant fields without binding an implementation to
incidental output fields.

`given.commands` contains public commands and inputs. `given.seed` is permitted
only when its `contract` names a declared seed port; use it for states that
cannot be reached through commands. `given.clock` and `given.actor` are optional
driver capabilities. `then.events` contains `event-contract-id@major` values.
`then.error` must be a code declared by the command or query exercised by
`when`.

Use neutral names such as `orders.place` and `orders.list`. Do not mention
screens, buttons, HTTP, databases, tables, endpoints, caches, frameworks, or
programming languages. A scenario is a contract for the use-case boundary, not
an implementation test.

```yaml
- id: SC-ORDERS-003
  title: An order with no items is rejected
  exercises: [BR-ORDERS-002]
  verification: automated
  given:
    commands: []
  when:
    command: orders.place
    input: { customerId: customer-1, items: [] }
  then:
    error: ORDER_ITEMS_REQUIRED
    observe:
      - query: orders.list
        input: { customerId: customer-1 }
        expect: { items: [] }
```

The validator checks schema shape, ID uniqueness and retirement, references,
automated-rule coverage, and configured neutrality words. Warnings require
review but do not change the exit status; errors do.

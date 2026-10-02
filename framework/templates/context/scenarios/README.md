# Context scenario template

Create one or more YAML files here after the context is approved, then move them
to `framework/contexts/<context>/scenarios/`. This starter is intentionally not
a project scenario and the validator ignores it.

Write a scenario from the public boundary outward:

1. Reference the approved `BR-<CONTEXT>-NNN` rules it exercises.
2. Establish state in ordered `given.steps` with public commands and, where
   needed, `advanceClock`. `given.commands` remains accepted only as a 0.2.x
   migration shorthand. Use `seed` only with a declared seed contract.
3. Run one command or query in `when`.
4. Expect an output or error and observe durable state only with public queries.

Keep titles and operation names stack-neutral. Never describe a screen, storage
layout, API transport, framework, or language.

Expected objects match partially and arrays match exactly unless an explicit
matcher is used. See [the scenario language](../../../language/scenario-spec.md)
for captures, intentional setup errors, event scope, and matcher vocabulary.

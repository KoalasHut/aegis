# Observer

## Intent
Allows consumers to react to completed facts.

## Triggering Condition
Independent consumers need publication facts.

## When To Use
Declare consumed event versions and repeat handling.

## When Not To Use
Avoid when a synchronous result is required.

## Architectural Consequences
Consumers remain independent of producer internals.

## Related Framework Rules
EVT-003, DEP-001

## Example in capability terms
A catalog observes LessonPublished.

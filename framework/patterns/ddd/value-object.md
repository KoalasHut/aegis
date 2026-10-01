# Value Object

## Intent
Represents a domain value without independent identity.

## Triggering Condition
Equality depends on meaning and values.

## When To Use
Declare constraints and replacement semantics.

## When Not To Use
Do not erase identity when lifecycle matters.

## Architectural Consequences
Values cannot mutate another owner through hidden references.

## Related Framework Rules
DOM-006, CON-002

## Example in capability terms
PublicationEligibility expresses a decision, not an entity.

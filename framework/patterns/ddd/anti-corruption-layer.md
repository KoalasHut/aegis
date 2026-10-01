# Anti Corruption Layer

## Intent
Protects internal language from external semantics.

## Triggering Condition
External meaning differs materially.

## When To Use
Translate concepts and failure meanings at the boundary.

## When Not To Use
Avoid translation where meanings already agree.

## Architectural Consequences
Mapping loss and ambiguity must be explicit.

## Related Framework Rules
DOM-009, DOM-003

## Example in capability terms
Translate an external course approval into training eligibility.

# Aggregate Root

## Intent
Names the entry point controlling aggregate changes.

## Triggering Condition
An aggregate has internal entities.

## When To Use
Expose changes through the root authority.

## When Not To Use
Do not expose internal mutation operations.

## Architectural Consequences
Consumers cannot bypass invariant checks.

## Related Framework Rules
DOM-004, DOM-005

## Example in capability terms
Publication authority creates one logical publication.

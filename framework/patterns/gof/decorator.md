# Decorator

## Intent
Adds behavior around a stable capability.

## Triggering Condition
Cross-cutting behavior wraps an existing contract.

## When To Use
Declare additional observable effects and failures.

## When Not To Use
Do not hide new permissions or semantic changes.

## Architectural Consequences
Wrapped behavior must remain substitutable.

## Related Framework Rules
DES-004, EFF-001

## Example in capability terms
An audit wrapper declares its additional audit effect.

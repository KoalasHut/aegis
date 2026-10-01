# Adapter

## Intent
Translates an external capability to an internal port.

## Triggering Condition
An external technology implements an internal port.

## When To Use
Declare the port and translation obligations.

## When Not To Use
Avoid when no external translation exists.

## Architectural Consequences
Failures and semantics need explicit mapping.

## Related Framework Rules
DES-002, DOM-009

## Example in capability terms
External media readiness could satisfy an internal readiness port.

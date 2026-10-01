# Composite

## Intent
Combines equivalent children through a common contract.

## Triggering Condition
A hierarchy contains equivalent capability types.

## When To Use
Define aggregate outcome and child failure semantics.

## When Not To Use
Use Workflow for distinct coordinated intentions.

## Architectural Consequences
Child dependencies and partial outcomes remain visible.

## Related Framework Rules
DES-005, DEP-004

## Example in capability terms
An eligibility group combines equivalent eligibility predicates.

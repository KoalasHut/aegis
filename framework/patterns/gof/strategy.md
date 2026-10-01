# Strategy

## Intent
Allows behavior variation behind one stable contract.

## Triggering Condition
Multiple policies satisfy the same contract.

## When To Use
Record policy variation and shared invariants.

## When Not To Use
Avoid when there is only one meaningful policy.

## Architectural Consequences
Substitution must preserve consumer expectations.

## Related Framework Rules
DES-001, CORE-006

## Example in capability terms
Different lesson eligibility policies share one query contract.

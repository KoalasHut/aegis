# Aggregate

## Intent
Groups state under one invariant authority.

## Triggering Condition
An invariant requires coordinated changes.

## When To Use
Place invariant enforcement at the aggregate boundary.

## When Not To Use
Do not group unrelated state for convenience.

## Architectural Consequences
Outside capabilities request changes through its boundary.

## Related Framework Rules
DOM-004, DOM-005, STA-002

## Example in capability terms
LessonPublication governs uniqueness per lesson version.

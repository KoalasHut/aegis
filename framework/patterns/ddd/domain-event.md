# Domain Event

## Intent
Declares a business fact that has happened.

## Triggering Condition
Other behavior reacts to a completed domain change.

## When To Use
Publish only necessary fact information.

## When Not To Use
Do not disguise commands as completed facts.

## Architectural Consequences
Version facts and handle repeated observations explicitly.

## Related Framework Rules
DOM-007, EVT-001, EVT-002

## Example in capability terms
LessonPublished records a new publication.

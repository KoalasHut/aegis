# Completion checklist

- One bounded context and one meaningful responsibility.
- Terms, identity, and invariant authority are explicit.
- Inputs, outputs, failures, and direct contracts are complete.
- State ownership, persistent state, observed state, effects, permissions and events agree with impact.
- Repeat behavior and failure atomicity are specified.
- Pattern conditions and every rule ID have evidence.
- Each domain rule and scenario survives a rewrite in a different stack: its
  statement uses business language and no platform, language, framework,
  storage, API, or UI term unless an external constraint source makes it
  intrinsic. Treat configurable validator word-list findings as review
  warnings, then record why any retained term is necessary.
- Owner approval is explicit: every approved domain rule cites its approving
  decision, constraints cite their external source, and extracted rules retain
  file/line or equivalent evidence.
- Context-owned rules and scenarios are referenced by ID from Concept Packs;
  packs do not duplicate their canonical statements or scenarios.
- Decisions and unknowns are recorded; required unknowns block.
- Structure matches schemas; paths and versions resolve.
- Pack stays within context budget or justifies deviation.
- One final status; no implementation choices or code.

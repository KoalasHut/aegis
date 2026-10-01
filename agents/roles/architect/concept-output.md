# Output contract

Deliver concept.md, manifest.yaml, impact.yaml, invariants.md, scenarios.md, decisions.md, open-questions.md, and relevant contracts. concept.md includes responsibility, non-responsibilities, ubiquitous language, aggregate boundary, pattern reasoning, rule assessment, and exactly one final status: VALID, VALID_WITH_WARNINGS, or BLOCKED.

Every input/output uses a defined semantic type. Failures, dependencies, owned/observed/persistent state, permissions, effects, and events are explicit. Scenarios use Given/When/Then and cover success, each failure, repeats, and invariant-sensitive interleavings. Omit irrelevant split contract files only when their dimensions are covered elsewhere.

# Constitution

A block describes one meaningful capability within exactly one bounded context. Its Concept Pack, applicable rules, and direct dependency contracts must be sufficient to understand it independently. Specifications are authoritative over future implementations.

Public contracts describe business meaning. Ownership, dependencies, observable effects, permissions, and failures are explicit. Composition does not bypass ownership or authorization boundaries. Patterns follow architectural conditions.

MUST and MUST NOT violations block validity unless an explicitly waivable rule has an approved waiver. SHOULD and SHOULD NOT deviations require recorded justification and produce warnings. MAY grants an option. Unknown required semantics block a concept; optional questions may remain warnings. No waiver is executed in v0.

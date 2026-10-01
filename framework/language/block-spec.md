# Block language

A Block is a versioned capability concept; an Implementation is a future realization. Foundation v0 defines only Blocks.

Classifications: Resource owns a domain concept and its lifecycle; Command expresses a state-changing intent; Query observes without domain mutation; Workflow coordinates multiple intentions and declares partial outcomes; Subscription reacts to facts; View defines a consumer-facing projection; Adapter translates external semantics through a port; Agent makes bounded decisions; Composite combines equivalent children. Executable blocks use a command, query, workflow, or subscription classification, or declare classification.execution with one of those values.

A Concept Pack contains concept.md, manifest.yaml, impact.yaml, invariants.md, scenarios.md, decisions.md, open-questions.md and relevant contracts. Explicit empty lists mean none, never unknown. Required unknowns must be recorded and status BLOCKED. Templates are incomplete by design and must not be registered as approved blocks.

Manifest contract values are pack-relative paths. Imports identify public contract IDs, version compatibility, interaction mode, and optionality. Exports list owned public contract IDs. This normalizes the handoff's capability/port import examples into one explicit contract reference. State owns lists authoritative semantic state, observes lists foreign read-only state, and persistent lists owned state that survives individual interactions. Effects name semantic targets. Event references use contract-id@major. Patterns use required, expected, and candidates; expected deviations need justification.

State ownership is exclusive. An aggregate's invariant boundary may be divided into capabilities only if no invariant requires bypassing its authority. Concept documents explain aggregate boundaries. Direct dependencies provide their own contracts; packs need not include dependency internals.

The initial review budget is 12 pack files and 20,000 words, excluding direct dependency contracts and framework rules. Exceeding it requires AGT-003 justification; it is a review budget, not a runtime limit.


## Partial concept drafts

Manifest and impact may declare unresolved: a nonempty list of exact dimensions whose semantics are missing. Such a pack MUST have status BLOCKED in its concept and registry. An empty collection for a listed dimension is a placeholder, not a claim of none. Unlisted empty collections retain their original meaning. Schemas allow draft structure; approval still requires semantic completeness. Data-only contracts may own described state without defining mutation commands; they grant no mutation authority.

Manifest imports can reference another contract exported by the same pack when contract-level composition requires it. Dependency review distinguishes the contract-reference graph from synchronous executable capability calls: descriptive type composition does not itself execute a call or imply a runtime dependency cycle.

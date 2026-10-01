# Composition language

Composition connects exported contracts to explicit imports. Synchronous edges form an acyclic graph. A composite declares children as imports and defines its public input, success, failures, ordering requirements, state, permissions, and effects. Child internals remain private.

A workflow describes partial completion and recovery obligations without choosing a transaction or transport mechanism. Composite is appropriate only for equivalent children; workflow coordinates distinct intentions. Event feedback needs explicit termination and duplicate handling even when synchronous cycles are absent. Composition never transfers state ownership or grants additional permissions.

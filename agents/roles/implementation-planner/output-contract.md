# Output contract

Required deliverables:

- Specific task graph with obligation mapping, ownership and verification.

Each task records id, obligationIds, contract references, dependsOn, ownedFiles, implementation notes, verification and doneWhen. Technical-only tasks still explain which obligation they enable. Preserve all generic obligations in a coverage table.

Return a handoff conforming to [handoff schema](../../contracts/handoff.schema.json). The outer workflow outcome is separate from domain artifact status. All limitations remain visible to the recipient.

# Impact language

Impact records identify affected concepts, read and written state, required and optional contracts, emitted and consumed events, permissions, known consumers, breaking change and migration flags, risks, and blast radius. Empty known consumers means none recorded, not proof that no consumers exist.

Manifest and impact declarations must agree. Reads mirror observed state plus owned state inspected; writes are owned mutation targets; dependencies match imports; event and permission declarations match the manifest. Bounded means confined to one context's authority, cross-context means known external consequences, local means only the block, unknown means insufficient evidence.

Future tooling may invert imports to find consumers, traverse dependency and event edges to estimate change impact, and flag migrations. Those analyses and graph validation are not implemented in v0.

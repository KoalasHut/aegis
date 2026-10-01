# Contract language

Every contract defines an ID, semantic version, kind, summary, semantic type dictionary, input and output fields, typed errors, and behavioral semantics. Each field declares type, required, and description. Type names express meaning, not representation. Empty input/output/errors collections are explicit. Error code names are semantic failure variants and meaning defines their interpretation.

Events represent completed facts; output describes their payload and input is empty. Ports describe required behavior independently of providers. Authorization context can be an explicit semantic input. Failure precedence, repeat behavior, and consistency guarantees belong in semantics or linked invariants. Logical event uniqueness does not prescribe physical delivery count.

All nonprimitive field types must be defined in the contract's types dictionary or explicitly referenced from a direct contract. JSON Schema checks structure only; type resolution and behavioral completeness require review. Split input/output/error contracts are supported for templates, but a complete executable contract must bind all three dimensions.


## Data contracts (Foundation v0 additive extension)

Behavioral contracts retain the original input/output/errors shape. Data contracts use lowercase kind resource, value, or union, and share id, version, summary, types, and semantics. Resource declares identity-bearing domain data; value declares a concept without independent identity. Neither implies an executable capability or serialization representation.

Resource and value contracts declare fields using type, required, and description. Optional values restrict the semantic vocabulary; ordered: true marks an ordered collection type. An optional extends references one direct base contract as contract-id@major and includes its common fields. This is semantic record composition, not implementation inheritance. Field redefinition is disallowed by semantic review. Data records are closed: only declared and inherited fields are allowed.

Union contracts declare variants, each referencing a direct contract-id@major. Exactly one variant applies. Optional discriminator.field names the semantic field whose value selects the variant key; every target variant must declare or inherit that field with the matching single value. Undiscriminated unions still require exclusive variant membership and do not prescribe an encoding tag.

Every type is defined locally by meaning; references to other contracts must also appear in manifest imports. Data-contract fields describe semantic data, not runtime JSON payloads. Schema validation checks the specification's structure; it does not validate workflow instances or enforce ranges, union exclusivity, inherited fields, reference resolution, or lifecycle semantics.

A specialization may narrow an inherited field’s values to a subset (for example BlockType to play); its type, requiredness, and meaning must remain unchanged. Other field redefinition remains disallowed.

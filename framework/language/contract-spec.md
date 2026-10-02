# Contract language

Every contract defines an ID, semantic version, kind, summary, semantic type dictionary, input and output fields, typed errors, and behavioral semantics. Each field declares type, required, and description. Type names express meaning, not representation. Empty input/output/errors collections are explicit. Error code names are semantic failure variants and meaning defines their interpretation.

The recognized scalar types are `string`, `boolean`, `integer`, `number`,
`decimal`, `date`, `datetime`, `duration`, and `id`. They are defined once in
`common.schema.json`. `datetime` uses the offset-bearing Aegis date-time
profile defined in `scenario-spec.md`: it is based on RFC 3339 and adds an
offset-bearing minute-precision form for cross-stack serialization matching.
`decimal` has exact decimal semantics; `id` is an opaque string. Contract
authors define other names in the local `types` dictionary for semantic
records and collections. During 0.2.x, an unrecognized scalar-looking field
type remains schema-valid and produces `UNKNOWN_SCALAR_TYPE`; it becomes an
error in 0.3.0. This migration allowance does not add the name to the scalar
vocabulary.

Events represent completed facts; output describes their payload and input is empty. Ports describe required behavior independently of providers. Authorization context can be an explicit semantic input. Failure precedence, repeat behavior, and consistency guarantees belong in semantics or linked invariants. Logical event uniqueness does not prescribe physical delivery count.

All nonprimitive field types must be defined in the contract's types dictionary or explicitly referenced from a direct contract. JSON Schema checks structure only; type resolution and behavioral completeness require review. Split input/output/error contracts are supported for templates, but a complete executable contract must bind all three dimensions.


## Data contracts (Foundation v0 additive extension)

Behavioral contracts retain the original input/output/errors shape. Data contracts use lowercase kind resource, value, or union, and share id, version, summary, types, and semantics. Resource declares identity-bearing domain data; value declares a concept without independent identity. Neither implies an executable capability or serialization representation.

Resource and value contracts declare fields using type, required, and description. Optional values restrict the semantic vocabulary; ordered: true marks an ordered collection type. An optional extends references one direct base contract as contract-id@major and includes its common fields. This is semantic record composition, not implementation inheritance. Field redefinition is disallowed by semantic review. Data records are closed: only declared and inherited fields are allowed.

Union contracts declare variants, each referencing a direct contract-id@major. Exactly one variant applies. Optional discriminator.field names the semantic field whose value selects the variant key; every target variant must declare or inherit that field with the matching single value. Undiscriminated unions still require exclusive variant membership and do not prescribe an encoding tag.

Every type is defined locally by meaning; references to other contracts must also appear in manifest imports. Data-contract fields describe semantic data, not runtime JSON payloads. Schema validation checks the specification's structure; it does not validate workflow instances or enforce ranges, union exclusivity, inherited fields, reference resolution, or lifecycle semantics. Scenario comparison uses a top-level field's declared scalar type; nested semantic types remain opaque in 0.2.x.

A specialization may narrow an inherited field’s values to a subset (for example BlockType to play); its type, requiredness, and meaning must remain unchanged. Other field redefinition remains disallowed.

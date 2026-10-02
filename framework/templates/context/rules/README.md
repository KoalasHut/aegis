# Domain rule template

Create themed YAML files in this directory, for example `membership.yaml` or
`billing.yaml`. Each file is a non-empty YAML list validated by
`framework/language/schemas/domain-rule.schema.json`; the IDs remain unique in
the context even when rules are split across themes.

Use [the domain rule language](../../../language/domain-rule-spec.md) for field
semantics. Rules are owner-facing artifacts: state the business behavior and
why it exists, then assign an accountable owner. A block references IDs only;
it must not copy the rule statement.

`example.yaml` is deliberately an incomplete drafting template. Its `BLOCKED`
label describes the template's readiness, not a domain-rule status and not an
approved rule. `BLOCKED` is intentionally absent from the schema's rule-status
enumeration. Replace every placeholder, choose a real lifecycle status, and
validate the result before adding it to a context or the rule registry.

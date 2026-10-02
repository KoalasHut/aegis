# Output contract

Required deliverables:

- Concept Packs and contract change record.
- Owner-facing context glossary, domain rules, and executable scenarios, with
  approval provenance for every approved rule.
- Validation and impact report.
- Versioned implementation handoff.

Product status remains VALID, VALID_WITH_WARNINGS or BLOCKED under the framework. A produced blocked draft uses workflow BLOCKED and cannot enter dependent planning. Preserve the original Concept Pack requirements in concept-output.md.

The owner approves the context glossary, domain rules, and scenarios as the
core behavior. Manifests, impact, ports, and Concept Packs are architect
artifacts that must be checked against that owner-facing core. Report rule and
scenario IDs, decision references, source evidence, neutrality warnings, and
coverage gaps in the validation evidence.

Return a handoff conforming to [handoff schema](../../contracts/handoff.schema.json). The outer workflow outcome is separate from domain artifact status. All limitations remain visible to the recipient.

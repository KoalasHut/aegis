# Framework validation

The starter contains reusable schemas, rule definitions, templates, empty project registries and teaching examples. It contains no approved product packs or inherited implementation-conformance evidence. No project validation or approval is claimed by this document.

## Run the artifact validator

Install the development dependencies in a virtual environment as described in
[INSTALL.md](../INSTALL.md), then run from the repository root:

```bash
python3 scripts/validate.py
python3 scripts/validate.py --json
```

The [validator](../scripts/validate.py) checks supported artifact schemas, ID
integrity, references and coverage. This includes domain-rule/scenario links,
decision and contract references, and scenario error codes. It warns about
approved automated rules without scenario coverage and potential platform terms
from the configurable neutrality vocabulary. Errors produce a nonzero exit code;
review warnings even when the command succeeds.

Use the [domain-rule specification](language/domain-rule-spec.md),
[scenario specification](language/scenario-spec.md) and
[context templates](templates/context/) to author compatible artifacts.

## Review what the checks cannot establish

Reference resolution and structural consistency do not prove that a cited owner
approval is authentic, a contract is semantically complete, or two implementations
behave identically. Neutrality warnings are review prompts, not a proof of stack
independence. The validator does not execute scenarios or supply runtime
conformance evidence, a conformance runner or workflow lanes.

For each assigned change, record exact artifact revisions, commands and observed
results, semantic review evidence, unresolved issues and limitations. Review the
full changed-file inventory and applicable rules before an integration handoff.
Semantic approval and runtime conformance remain independent of artifact validation.

Templates intentionally contain placeholders and blocked concept status. Empty registries represent no project artifacts, not evidence that an implementation conforms. Host permissions and supervised workflow checks remain separate from framework validation.

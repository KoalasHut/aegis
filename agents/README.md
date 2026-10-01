# Aegis — Scoped Production Chain

Protocol version: 0.1.0. Status: authored pilot; runner enforcement and live model boundary tests are NOT verified.

This is Aegis's model-independent production-line definition. Each assignment belongs to one role and one bounded work window. The dispatcher routes outcomes by responsibility; agents do not need to know which person, model or session will process the next stage.

Read [doctrine](doctrine.md), [stage contracts](stage-contracts.md), and the assigned role only:

| Stage | Role | Role files |
| --- | --- | --- |
| Discuss | discussion | [scope](roles/discussion/agent.md) |
| Consolidate | architect | [scope](roles/architect/agent.md) |
| Plan | planner | [scope](roles/planner/agent.md) |
| Plan specific | implementation-planner | [scope](roles/implementation-planner/agent.md) |
| Orchestrate specific | orchestrator | [scope](roles/orchestrator/agent.md) |
| Execute specific | executor | [scope](roles/executor/agent.md) |

Each directory has agent.md (responsibility), scope.yaml (structured boundary), playbook.md (procedure), and output-contract.md (completion evidence). The architect also includes a checklist and detailed concept procedure.

The [assignment](contracts/assignment.schema.json), [handoff](contracts/handoff.schema.json) and [scope](contracts/scope.schema.json) schemas describe our protocol, not an industry-standard agent configuration. See [examples](examples/README.md), [boundary tests](boundary-tests.md), and the first [Codex adapter](adapters/codex/README.md).

Authority: the doctrine and stage contract define the role ceiling; scope.yaml expresses it for validation. An assignment narrows that ceiling. Agent files and playbooks must agree, not introduce extra grants. Actual host restrictions may narrow it further. An explicit user exception must be recorded with its scope and expiry; an agent cannot authorize its own exception. Higher-priority host instructions still apply and conflicts are reported honestly.

Keep domain rules in framework/. Keep prototype plans and implementation evidence in their prototype. Skills may package reusable procedures later; loading one never grants a role or enlarges authority. Generated/native adapter files are translations, not independent policy sources.

No dispatcher, permission broker, automatic schema gate or model-evaluation runner is installed by these files. Manual admission and review are required in this pilot.

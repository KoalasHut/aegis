# Stage contracts

Version: 0.1.0

## Admission

Validate the assignment shape, role, approval source, input revisions, named read/write files, expected output and host controls. Inspect only the assigned role and direct inputs initially. Read expansion needs an assignment amendment when outside its boundary. Invalid assignment: REJECTED. Missing information/control: BLOCKED. Authority conflict: ESCALATED. Work already completed upstream need not be reapproved merely to hand it off.

No assignment: identify the missing role/scope and remain read-only while requesting it. Do not default to executor. A plain-language assignment is acceptable for conversation, but the dispatcher must capture its structured equivalent before admitting writes or delegation.

## Stages and outputs

| Role | Required input | Required output | Permitted normal destination |
| --- | --- | --- | --- |
| discussion | User question/change intent and relevant context | Brief: intent, alternatives, approved decisions with provenance, proposals, open questions, explicit non-goals | architect, after required decisions are approved |
| architect | Approved brief, applicable framework rules, named packs and direct contracts | Consistent versioned Concept Packs, decisions, impact, scenarios, validation and implementation handoff | planner, only when required semantics are resolved |
| planner | Approved implementable contract versions and acceptance scenarios | Generic backlog: obligation IDs, exact contract references, dependencies, acceptance IDs and definition of done | implementation-planner |
| implementation-planner | Generic backlog, named target, existing implementation and permitted technology constraints | Derived task graph, complete obligation mapping, files/ownership, tests, technical dependencies and gaps | orchestrator |
| orchestrator | Admitted specific plan and execution authority | Bounded executor assignments; integrated results and per-obligation conformance evidence | executor for delegation; domain-owner for final review |
| executor | One bounded task or cohesive task set from the specific plan, dependencies and file ownership | Assigned changes, checks, evidence and unresolved gaps | orchestrator |

The domain owner is a routing responsibility, not a seventh processing stage. Dispatch/integration may be performed manually in this pilot. Orchestrator delegation is internal to its work window: each child has a separate executor assignment and session. Orchestrator closes only when integration is reviewed or blocked, not after merely dispatching children. Executors never fan out. Other roles return a handoff instead of launching the next role.

## Outcomes

- COMPLETED: all assignment deliverables and evidence are present; no mandatory issues remain. It means ready for recipient review, not automatic approval, merge, publication or deployment.
- BLOCKED: required input, decision, dependency, verification environment or enforcement is missing; include partial artifacts, what is missing and owner. No dependent work proceeds.
- REJECTED: input fails the admission contract; identify the invalid fields or versions and corrective action.
- ESCALATED: requested behavior exceeds role authority or reveals a cross-stage conflict; explain the decision and responsible role needed.

All outcomes close the assignment. Include assignment ID, role, input revisions, artifact references, verification evidence, known limitations, and next responsible role. Non-completed outcomes require at least one issue. COMPLETED requires deliverables and evidence and no issues. Warning-level product gaps belong in limitations; mandatory gaps cannot be hidden there.

## Semantic gates (not provided by JSON Schema)

The dispatcher checks provenance and role/assignment matching, input freshness, role ceiling versus assigned files/effects, exception validity, and allowed routing. The reviewer independently inventories changed/deleted/new files (not only a worker's list), maps every required acceptance criterion to evidence, checks dependencies and unresolved issues, and rejects out-of-scope changes. Worker-created evidence is a claim until reviewed. Technical constraints cannot silently revise generic acceptance criteria.

For executor integration the orchestrator may combine approved worker outputs and run assigned tests. Novel code fixes and conflict resolutions that require design choices return to a bounded executor task; the orchestrator does not become an unassigned programmer. No role may alter upstream obligations to make a failing implementation pass.

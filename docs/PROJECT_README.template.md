# {{PROJECT_NAME}}

{{PROJECT_DESCRIPTION}}

Created with Aegis {{AEGIS_VERSION}}. The pinned template version is recorded in
`project.json`; template upgrades require explicit review.

Keep the project's core—decisions, glossary, domain rules and expected behavior—
independent of the stack so it can survive a change of implementation. Contexts
own rules and structured scenarios; capability contracts reference their IDs.

Start with [the draft discussion brief](discussion/initial-brief.md) and
[assignment worksheet](discussion/initial-assignment.draft.md). These drafts
contain no approvals and authorize no agent work.

Begin with the problem, people and context, desired outcome, success signals and
evidence. Explore alternatives and candidate rules/scenarios before committing
to features. Throwaway mockups are question tools, never implementation precedent.

Read [getting started](GETTING_STARTED.md) and the root `AGENTS.md` before admitting
the first discussion assignment. Follow Discuss → Consolidate → Plan → Plan
specific → Orchestrate specific → Execute specific.

Install `requirements-dev.txt` in a virtual environment and run
`python3 scripts/validate.py` from the project root to check core artifacts.
The initializer itself remains dependency-free. Validation checks structure and
references; it does not execute scenarios or prove implementation conformance.
Conformance drivers, workflow lanes, provisional-rule flow and legacy extraction
are deferred beyond this milestone.

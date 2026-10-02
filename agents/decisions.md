# Workflow decisions

This file is narrative. [decisions.yaml](decisions.yaml) is authoritative for
validation; approval status and provenance are not inferred from Markdown.
OD-6, OD-7 and OD-13 map to D-AEGIS-006, D-AEGIS-007 and D-AEGIS-013 here.
Other owner defaults are in [the framework YAML log](../framework/decisions.yaml).

Aegis framework maintenance decisions follow. They define the reusable framework;
they are not approvals for a generated project's product behavior or permission
to start work. The reusable workflow rules remain in doctrine.md and
stage-contracts.md. Copying this template grants no assignment or execution authority.

## Aegis 0.2.0 approval provenance

Owner/issuer: Diego. Source: the current Aegis maintenance conversation, as captured
by the dispatcher in assignment `aegis-020-workflow` and orchestration plan
`aegis-020-orchestrator`: authority to perform or delegate the approved milestone
and confirmation of defaults OD-1 through OD-7. This record transcribes that
approval; it is not an approval issued by an executor.

Reviewed proposal: *Aegis — Core Preservation Improvement Plan*, SHA-256
`9f0412c5c4c2048e7454fceba3ee31b5c0b31d426268f036600b7a835cd5da29`.
Starting Aegis revision: `4937d8d996cf0169b495f990adfbaa437826229f`.
Effective release: 0.2.0; the handoff pins the resulting artifacts. Approved
implementation scope is phases 1 and 2 plus task 4.1 and minimum release docs.
The proposal's remaining phases are not approved as completed work.

### OD-6 — Change lanes (approved direction; implementation deferred)

Decision: changes to domain rules, scenarios or public contracts use the full
chain. A future implementation lane is reserved for work that leaves the core
unchanged. The proposal also places glossary meaning changes in the core lane.
Rationale: protect the long-lived core while eventually reducing ceremony for
implementation-only changes. Alternatives: use one chain indefinitely or allow
unverified shortcuts. Consequence for 0.2.0: the existing full chain remains in
effect; no lane enforcement, shortened route, `--diff` lane gate or conformance
report workflow is introduced. Owner and approval source: the record above.

### OD-7 — Release 0.2.0 (approved)

Decision: publish this core-preservation milestone under template version 0.2.0
with manual migration notes for 0.1.0 projects. Rationale: domain rules and
structured scenario artifacts require an explicit adoption step. Alternative:
silently alter the 0.1.0 template. Consequences: existing projects are not updated
automatically; initialization remains creation-only. The agent protocol stays
0.1.0 because this milestone does not revise its assignment/handoff schema.
Affected artifacts: VERSION, changelog, onboarding and migration documentation.
Owner and approval source: the record above. OD-1 through OD-5 are recorded in
[framework decisions](../framework/decisions.md).

For each future governance decision, retain its identifier, context, decision, alternatives, consequences, issuer, approval source and effective revision. Exceptions additionally need exact scope and expiry. Record decisions only from actual project approvals.

## Aegis 0.2.1 hardening provenance and OD-13

Diego approved OD-8 through OD-13 on 2026-10-02 in the current maintenance
conversation, captured by `aegis-021-orchestrator` and release assignment
`aegis-021-release`. The reviewed hardening-plan SHA-256 is
`de054ce52e20241f5de34d579112904e3d92ea7e0fa9a9ccde536709a8057af2`, against
starting revision `6e777262db08f497c878106fca0fb1610114d160`.

OD-13 selects GitHub Actions with Python 3.9/latest stable 3.x. CI uses strict
warnings, PR base comparison and JSON artifacts; owners still configure required
checks manually. It is an artifact gate, not behavioral conformance evidence.
Release 0.2.1 hardens the 0.2.0 milestone without changing agent protocol 0.1.0
or activating workflow lanes. Historical OD-1 through OD-7 approvals are dated
2026-10-01; their migration to YAML does not create new product approvals.

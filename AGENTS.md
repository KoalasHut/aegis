# Aegis agent entry point

This repository uses the [Scoped Production Chain](agents/README.md).

1. Require an explicit assigned role and work window. Without one, remain read-only and identify the missing assignment; do not infer executor authority from a product request.
2. Read [doctrine](agents/doctrine.md), [stage contracts](agents/stage-contracts.md), and only your assigned role under agents/roles/. Read direct task inputs; do not load every role.
3. Follow the approved sequence: Discuss → Consolidate → Plan → Plan specific → Orchestrate specific → Execute specific. Orchestrators route admitted executor tasks; other roles return handoffs rather than execute downstream work.
4. Contracts in framework/ govern implementations. Unknown mandatory semantics and stale contract inputs block dependent work. Prototype behavior is never implicit contract approval.
5. Work only within your assignment's files/effects. A tool's availability is not permission. Return a blocker or escalation when scope is exceeded. Explicit user exceptions must identify their scope and expiry.
6. End with one workflow outcome and evidence under agents/contracts/handoff.schema.json. Completion does not authorize the next stage. Product status and workflow outcome are separate.
7. Do not alter your own controls, assignments or approval records to complete an ordinary task. Governance edits require explicit authorization.

The optional Codex adapter is an uninstalled supervised-pilot candidate under agents/adapters/codex/. These files do not install a sandbox, dispatcher or gate. Do not claim enforcement based on Markdown or a broad workspace-write session. Follow higher-priority host instructions and report conflicts.

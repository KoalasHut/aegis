# Optional Codex adapter

Protocol: 0.1.0. These are uninstalled candidate templates. Compatibility with the operator's installed Codex version, native registration, live model behavior, automatic routing and effective enforcement are unverified.

## Supplied files

- Root AGENTS.md: repository instruction entry point.
- [Session prompt](session-prompt.md): fill-in assignment-loading prompt for separate stage sessions.
- native/*.toml: six candidate role definitions, each requesting read-only shell access; no model override is selected.
- [Control mapping](control-mapping.md) and [pilot procedure](pilot.md): operator checks and limitations.

Canonical policy remains agents/doctrine.md, stage-contracts.md and roles/. Native files load those instructions; they are not independent policy or authority. Review the adapter after policy changes.

## Activation is separate

Project initialization does not install these candidates or alter project/user Codex settings, global instructions, MCP connections or existing tasks. Consult current official Codex documentation and the installed CLI help before selecting configuration locations, supported fields or launch flags. Verify compatibility and all inherited effect channels before activation. TOML parsing alone proves neither runtime acceptance nor isolation.

Use separate explicitly assigned stage sessions and a manual dispatcher for a supervised pilot. Optional orchestrator-to-executor delegation needs admitted child assignments and host authorization. Do not reuse a session carrying earlier executor authority as a discussion session.

Every candidate requests read-only shell access. Writer roles need operator-supplied task controls or an explicitly acknowledged supervised pilot before edits. Agents must not escalate their own permissions. Loading AGENTS.md does not register native agents, restrict every connector or dispatch work.

Run the [boundary suite](../../boundary-tests.md) against the actual chosen runner configuration before claiming enforcement. No verified host configuration is distributed with this template.

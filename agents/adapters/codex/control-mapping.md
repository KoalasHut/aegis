# Control mapping

| Generic requirement | First Codex mapping | Actual status |
| --- | --- | --- |
| Repository discovery | Root AGENTS.md | Authored; a new session must confirm loading |
| One role/window | Separate session + explicit assignment + role files | Instruction and manual operator discipline; no automatic closing gate |
| No shell writes | Operator-verified read-only host configuration | Installed-version support and effective enforcement unverified |
| Writer file allowlist | Task-specific host/container permissions required | Not supplied by native templates; workspace-write alone is insufficient |
| Connector effect restrictions | Audit/restrict all inherited tools and MCP connections | Manual admission requirement; no tool allowlist installed |
| No downstream role switching | Role instructions + manual dispatcher | No hard transition router installed |
| Orchestrator fan-out | Custom executor candidate + per-task assignment | Registration/delegation not exercised; overlapping writes prohibited by process |
| Input freshness | Exact revisions/digests + independent admission review | Manual semantic gate; schemas only validate nonempty revision fields |
| Valid handoff | JSON Schema + independent evidence/routing review | Schemas provided; no automatic gate wired into Codex |
| Control-file protection | Host read-only mounts/permissions outside worker scope | Required for enforced mode; not configured by this package |

A request for enforcement that cannot be met returns BLOCKED. An operator may explicitly choose supervised-pilot mode and acknowledge gaps; this is never relabeled enforced. CLI flags do not retroactively change this desktop task's permissions. Do not claim a custom TOML sandbox setting governs every connector, child or app surface.

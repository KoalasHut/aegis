# Protocol contracts

Version 0.1.0 uses JSON Schema Draft 2020-12. YAML instances are accepted after parsing into JSON-compatible values. Unknown fields are rejected. These schemas check structure only.

Paths in assignments are repository-relative exact files or directory prefixes ending in /. No wildcard, parent traversal, absolute path or symlink escape may enlarge access. Empty writePaths means no artifact writes. ReadPaths are context boundaries, not confidentiality isolation unless host controls provide it. URLs and conversation evidence are referenced through inputs; any access effects must also be authorized. Narrow role ceilings further per assignment; do not copy broad role categories into writable-root grants.

revision is an immutable source revision or content digest, never 'latest'. For non-file approvals use a retained conversation/message reference. The operator checks provenance: schema validation does not authenticate approvals, detect stale content, enforce paths or verify evidence.

Read [stage contracts](../stage-contracts.md) for admission and semantic gates. The worker cannot self-issue approval, edit its assignment, mark host controls verified, or record operator acknowledgement. The dispatcher owns these fields. Example files are fixtures, not executable authorization.

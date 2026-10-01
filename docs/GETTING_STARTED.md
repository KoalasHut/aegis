# Starting a project

Use the [README](../README.md)'s GitHub template commands for a new repository with fresh
history. Replace `OWNER` with your account or organization. For prerequisite
checks and tool installation, follow [INSTALL.md](../INSTALL.md).

Alternatively, clone Aegis as an ordinary repository:

```bash
git clone https://github.com/KoalasHut/aegis.git my-project
cd my-project
python3 scripts/init.py --name my-project --description "What this project is for" --dry-run
python3 scripts/init.py --name my-project --description "What this project is for"
```

An ordinary clone retains Aegis history and its origin remote. Initialization
never changes remotes, history, branches, or GitHub settings. Configure your own
destination before pushing project changes. The template method avoids this
extra setup.

The name must be a lowercase slug (letters, digits, single hyphens), up to 80
characters. Description is optional, one line, at most 350 characters. Run the
same command to verify idempotence. The script finds the repository relative to
its own location, so it also works when invoked from another directory.

Initialization is deliberately conservative: any partial or modified generated
output blocks a new run. Review and preserve existing content manually; there
is no force-overwrite option. Once initialized, project documents are yours to
edit. Running initialization again is unnecessary. Changing `VERSION` or the
managed README template also causes a repeat initialization to fail against
existing output; initialization is not an upgrade mechanism.

## Admit the first discussion

1. Read `AGENTS.md`, `agents/doctrine.md`, and `agents/stage-contracts.md`.
2. Fill in `docs/discussion/initial-brief.md`, keeping proposals separate from
   approved decisions and retaining approval provenance.
3. Use `docs/discussion/initial-assignment.draft.md` as a worksheet. A domain owner
   and dispatcher must provide a real assignment, exact input revisions, scoped
   paths/effects, authority, and a bounded work window under the assignment schema.
4. Review actual host permissions. A supervised instruction-only pilot must be
   acknowledged as such; repository instructions are not enforced isolation.
5. Admit the discussion role and close its work with a handoff. Completion does
   not authorize the next stage.

## Framework updates

`project.json` records the Aegis version used to start your project. Template
updates are not applied automatically; review and adopt future changes explicitly.
For developing or publishing Aegis itself, see [the maintainer guide](../CONTRIBUTING.md).

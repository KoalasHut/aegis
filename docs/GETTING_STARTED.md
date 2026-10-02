# Starting a project

Keep the core—decisions, vocabulary, domain rules and expected behavior—independent
of the stack so it can outlive an implementation. Aegis 0.2.1 gives these artifacts
stable references and a validator; it does not execute conformance scenarios.

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
2. Fill in `docs/discussion/initial-brief.md`: Problem, Who and when, Desired
   outcome, Signals of success and Evidence come before alternatives and proposals.
   Separate symptoms from causes and cite observations or mark evidence missing.
   Propose candidate domain rules and plain-language scenarios before committing
   to features; retain approval provenance separately.
3. Use `docs/discussion/initial-assignment.draft.md` as a worksheet. A domain owner
   and dispatcher must provide a real assignment, exact input revisions, scoped
   paths/effects, authority, and a bounded work window under the assignment schema.
4. Review actual host permissions. A supervised instruction-only pilot must be
   acknowledged as such; repository instructions are not enforced isolation.
5. Admit the discussion role and close its work with a handoff. Completion does
   not authorize the next stage.

An explicitly assigned throwaway prototype or mockup can help answer a question.
Record the question and resulting decision in the brief; prototype behavior does
not approve semantics and is never implementation precedent. Candidate rules
stay in the brief until architect consolidation. The owner then reviews glossary,
domain rules and scenarios; the architect checks technical artifacts against them.

## Validate the core

Initialization requires no third-party Python packages. The validator and full
development tests require the dependencies declared in `requirements-dev.txt`:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
```

On Windows, use `.venv\Scripts\Activate.ps1` in PowerShell to activate. Run
`python3 scripts/validate.py --json` for machine-readable results. Correct errors
and review warnings. A successful check proves neither implemented behavior nor
authenticity of approvals; retain independent review and implementation evidence.

Keep approved decisions in `framework/decisions.yaml` or `agents/decisions.yaml`;
Markdown decision notes are explanatory only. Every approved rule needs a
same-scope approved decision with approver, date and source. Bundled Aegis
maintenance choices do not approve your product. Project references cannot be
satisfied by a teaching example or test fixture; each example validates separately.

Use [Tiny TODO](../framework/examples/tiny-todo/) to see rules, decisions,
contracts and scenarios together. New scenarios use ordered `given.steps` for
commands and clock advances; `given.commands` is a legacy 0.2.x migration form.
Expected objects match partially and arrays exactly unless an explicit matcher
changes that behavior. See the [scenario specification](../framework/language/scenario-spec.md)
for captures, setup errors, event scope and matching grammar. These semantics are
structurally checked now; a future runner will execute them.

Use the full stage chain for core changes. Conformance runners/drivers, workflow
lanes, provisional-rule flow and legacy extraction are deferred. The presence of
a proposed or provisional rule status does not authorize execution to invent
missing business semantics. Existing doctrine and stage contracts still apply.

## Continuous validation on GitHub

Projects created from this template inherit
[`.github/workflows/validate.yml`](../.github/workflows/validate.yml). When Actions
is enabled and allowed by repository/organization policy, pushes and pull requests
run `Aegis validation` on Python 3.9 and the latest stable 3.x. Each job installs
development dependencies, runs tests and validates the artifacts. PR jobs also
use `--base` against the fetched target branch to check approved-rule edits and
removed IDs. No branch name is assumed to be `main`.

Download the `validation-python-3.9` and `validation-python-3.x` artifacts from a
run to inspect `validation.json` and, for PRs, `base-validation.json`. Reports are
uploaded even after validator failure when dependency setup succeeded; an earlier
setup failure can leave no usable report. CI adds `--strict` to both validator
runs, so errors and warnings fail the job. Ordinary local validation fails on
errors only; use `python3 scripts/validate.py --json --strict` to reproduce CI's
warning policy. Review and resolve warnings before merging.

The owner configures merge protection manually:

1. Enable Actions if the repository or organization disables it, and allow the
   pinned official actions used by the workflow.
2. Let a push or PR produce the two checks and inspect their results.
3. In the repository's branch protection settings or branch ruleset, target the
   branch to protect and require status checks before merging. Select
   `Validate (Python 3.9)` and `Validate (Python 3.x)` from this workflow.
4. Save the rule and verify on a PR that a failing required check blocks merging
   for the intended users; review any allowed bypasses separately.

See GitHub's [protected-branch documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
for available controls and plan requirements. Template creation and initialization
do not configure these settings, so a workflow file alone does not block merging.

This is an artifact gate: schemas, references, traceability and historical rule
checks. It does not run the domain scenarios, prove behavioral conformance,
authenticate cited approvals or enforce agent access boundaries. Keep semantic
review and implementation evidence independent. Conformance runners and lanes
remain deferred.

## Framework updates

`project.json` records the Aegis version used to start your project. Template
updates are not applied automatically; review and adopt future changes explicitly.
For an existing 0.1.0 or 0.2.0 project, use the [manual migration guide](MIGRATION-0.2.md)
instead of rerunning initialization.
For developing or publishing Aegis itself, see [the maintainer guide](../CONTRIBUTING.md).

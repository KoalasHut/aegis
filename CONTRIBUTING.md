# Maintaining Aegis

This guide is for developing and publishing the reusable Aegis template.
To start a project with it, follow the [README](README.md).

## Keep the starter reusable

Aegis was extracted from the Chorus pilot. Keep reusable workflow controls,
schemas, patterns, and templates here; keep product contracts, approvals,
assignments, historical handoffs, and implementation evidence in their projects.

Leave the template uninitialized. Its registries start empty, and its project
folders use README files to remain tracked. Do not commit generated `project.json`,
`docs/PROJECT.md`, or initial discussion records into the starter.

Follow [AGENTS.md](AGENTS.md) for assigned work. Changes to doctrine, role
boundaries, schemas, or adapters require explicit governance scope. Preserve the
distinction between documented instructions and verified host enforcement.

## Repository map

| Path | Maintenance responsibility |
| --- | --- |
| `agents/` | Doctrine, stages, roles, schemas, examples, and optional adapters |
| `framework/` | Reusable specification language, rules, patterns, and templates |
| `scripts/init.py` | Dependency-free project initialization |
| `scripts/validate.py` | Structural, reference and coverage validation of core artifacts |
| `.github/workflows/validate.yml` | Push/PR artifact gate and Python compatibility matrix |
| `requirements-dev.txt` | Validator and development test dependencies |
| `docs/PROJECT_README.template.md` | Source for the generated project README |
| `tests/` | Initializer safety and validator fixtures/checks |
| `VERSION` | Aegis template version recorded in new project metadata |
| `README.md` | Primary user quickstart |
| `INSTALL.md` | Agent-readable prerequisites and project setup runbook |
| `docs/GETTING_STARTED.md` | Additional user setup details |

## Verify changes

From the repository root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests -v
python3 scripts/validate.py
python3 scripts/validate.py --json
```

Use `.venv\Scripts\Activate.ps1` in Windows PowerShell. Initialization and its
tests remain standard-library-only; the full suite and validator use the declared
dependencies. For an initializer-only check, use
`python3 -m unittest discover -s tests -p test_init.py -v`.

Validation is a structural/reference gate, not a scenario runner or approval
authenticator. Do not claim conformance, host enforcement, automated lanes or
provisional-rule integration from a passing validator. Those runtime/workflow
features and legacy extraction remain deferred in 0.2.0.
The 0.2.1 hardening release preserves these limits; its `--base` and `--strict`
checks strengthen artifact review without executing domain scenarios.

Keep project and example validation scopes isolated. The authoritative decision
logs are `framework/decisions.yaml`, `agents/decisions.yaml`, and each example's
own `decisions.yaml`; Markdown logs are narrative only. Preserve statuses and
actual approval provenance. A copied maintenance decision is not a product
approval, and a test fixture must not resolve project references.

When changing an approved domain rule, retain the old ID, mark the old rule
deprecated and put `supersedes: <old-id>` on the new rule. Run the validator with
`--base` against the reviewed baseline. Review warning-only title/rationale
clarifications as well; CI's strict mode makes warnings fail. Install all declared
format dependencies, and retain regressions for unavailable format checkers.

Tests use disposable copies and leave the template uninitialized. For documentation
changes, check relative links and ensure the commands match the initializer.
For initializer changes, verify dry runs, repeated runs, collisions, and generated
content in a disposable copy. Preserve existing project data on failure.

## Continuous validation

The [workflow](.github/workflows/validate.yml) runs on every push and pull request
with Python 3.9 and the latest stable 3.x. Each job installs `requirements-dev.txt`,
runs the full tests, saves validator JSON, and uploads it as
`validation-python-3.9` or `validation-python-3.x`. Reports are retained for 14 days.
Validation and upload are attempted after a test/validator failure when dependency
installation succeeded; earlier setup failures may leave no report.

On PRs, checkout fetches all branches/history and validation uses
`--base origin/<base-branch>`. It compares the checked-out PR merge tree with that
base, including approved-rule changes and removed IDs. Locally, fetch the intended
base before running, for example `python3 scripts/validate.py --base origin/main`;
replace `main` with the real base. This is a history-aware artifact check, not a
lane selector or behavioral conformance run. CI adds `--strict` to both validator
runs, making errors and warnings fail the check. Ordinary local validation still
fails on errors only; add `--strict` locally to reproduce CI's warning policy.

Maintain the minimal `contents: read` permission, disabled credential persistence,
full-commit action pins and quoted environment-variable handling of branch names.
Do not interpolate event-provided strings into shell source or switch to
`pull_request_target` to execute untrusted PR code. Review action-pin updates
against the official action repositories and rerun workflow checks.

Projects inherit the workflow file, not repository protection settings. Follow
[the owner setup steps](docs/GETTING_STARTED.md#continuous-validation-on-github)
to require both matrix checks. Preserve stable job names so required checks keep
matching. These files do not change remote settings, and local validation does
not establish that a hosted Actions run succeeded.

## Version changes

Review `VERSION` when releasing changes. Generated `project.json` files record the
version used at initialization; existing projects do not automatically receive
updates. Describe any manual migration needed when changing workflow controls or
file formats in the changelog; see [0.2 migration](docs/MIGRATION-0.2.md). The
template release version is separate from the agent protocol version, which
remains 0.1.0 in this release. The initializer is not an upgrade tool: changing its version or
README template can make a repeat run conflict with existing generated files.

## Publish the template

Aegis is public. Review the changes for project-specific data and secrets, then run the following
manually when ready to publish:

```bash
git status --short
python3 -m unittest discover -s tests -v
python3 scripts/validate.py
git add .
git diff --cached
git commit -m "Update Aegis starter"
git push -u origin HEAD
```

Enable the GitHub template setting once:

```bash
gh repo edit KoalasHut/aegis --template
```

This setting makes the README's `gh repo create --template` command available.
Initialization never commits, pushes, changes remotes, or changes GitHub settings.

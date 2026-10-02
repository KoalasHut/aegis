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

Tests use disposable copies and leave the template uninitialized. For documentation
changes, check relative links and ensure the commands match the initializer.
For initializer changes, verify dry runs, repeated runs, collisions, and generated
content in a disposable copy. Preserve existing project data on failure.

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

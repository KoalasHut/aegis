# Install Aegis for a new project

This is the setup runbook for a person or coding agent. Aegis is a public
repository template; there is no Aegis package to install. Its initializer and
initializer tests use only the Python standard library. The core validator and
full development test suite also require `requirements-dev.txt` dependencies.

## Agent task

When asked to set up a project with Aegis, follow this runbook through verification
and report the result. Use the user's supplied project details. Ask only for
missing choices that affect the destination, repository visibility, or project
identity. Work within the host's installation and filesystem permissions.
This runbook does not grant a standing role or override `AGENTS.md`; the caller's
setup assignment must cover the destination and required installation effects.

Collect:

- Project name: lowercase letters/digits separated by single hyphens, maximum 80 characters.
- Description: optional single line, maximum 350 characters.
- Destination directory and whether a project repository already exists.
- For GitHub creation: owner and explicit public/private visibility.
- Problem, people and context, desired outcome, success signals and evidence for
  the initial brief. Record unknowns rather than choosing features or a stack
  implicitly; keep any supplied technology constraints separate from domain rules.

If the project already exists, inspect it first. Do not overlay the starter onto
an unrelated codebase or overwrite files; that requires a separate migration plan.
If it is an uninitialized Aegis copy, skip repository creation and use that copy.

## 1. Check requirements

| Requirement | Needed for | Check |
| --- | --- | --- |
| Python 3.9 or newer | Initialization, validation and tests | `python3 --version` |
| Python venv and pip | Isolated validator/development dependencies | `python3 -m venv --help`, `python3 -m pip --version` |
| Git | Cloning and version control | `git --version` |
| GitHub CLI (`gh`) | Optional CLI repository creation | `gh --version` |
| GitHub authentication | Creating a repository, not reading the public template | `gh auth status` |
| AI coding tool | Working through agent assignments | Use the user's existing tool |

On Windows, try `py -3 --version` if `python3` is unavailable. Use `py -3` in
place of `python3` throughout this guide when that is the available interpreter.
Verify the actual version; install a currently supported Python release when
provisioning a new machine.

No pip packages are needed merely to initialize. Validation and the full test
suite require the declared development packages; install them in a virtual
environment below. These include RFC3339 format validation; a missing format
checker is an error, not a skipped check. Git is also required for `--base`
comparisons. No Node.js, Docker or database is required by Aegis.
Application dependencies depend on the project's later approved implementation plan.

## 2. Obtain missing tools

Inspect the operating system and available package manager. Install only missing
requirements using its normal permission mechanism, then rerun the checks above.
Do not replace a working environment merely to match an example command.

- **Debian/Ubuntu:** use `sudo apt-get update`, then
  `sudo apt-get install python3 python3-venv python3-pip git` for missing tools. Check the Python version
  afterward. For `gh`, follow the official Linux installation instructions below.
- **macOS with Homebrew already installed:** use `brew install python git`, and
  `brew install gh` when choosing CLI repository creation. Omit tools already present.
- **Windows:** obtain Python and Git from their official installers below. For
  GitHub CLI with WinGet available, use `winget install --id GitHub.cli --exact`.
  Open a fresh terminal afterward if PATH changes are not yet visible.
- **Other systems or no package manager:** use the official installation instructions
  for that platform. If host policy blocks installation, report the exact missing
  dependency and action needed; continue independent setup work where possible.

Official sources:

- [Python downloads](https://www.python.org/downloads/)
- [Git installation](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
- [GitHub CLI installation](https://github.com/cli/cli#installation)
- [GitHub CLI Linux packages](https://github.com/cli/cli/blob/trunk/docs/install_linux.md)

If repository creation needs authentication, use `gh auth login` and let the
user complete the interactive browser flow. Do not request passwords or tokens
in chat. Public HTTPS cloning requires no GitHub login.

## 3. Create the project

Choose one path. Replace the example owner/name/destination with the collected
values. Confirm the destination does not already contain unrelated work.

### GitHub template (recommended)

For a user-requested private project:

```bash
gh repo create OWNER/my-project --private --template KoalasHut/aegis --clone
cd my-project
```

Use `--public` instead when the user wants a public project. Aegis being public
does not determine the new project's visibility.

Without `gh`, open [Aegis on GitHub](https://github.com/KoalasHut/aegis), choose
**Use this template → Create a new repository**, select visibility, and clone
the resulting repository. This route gives the project its own history and remote.

### Local start without GitHub authentication

```bash
git clone https://github.com/KoalasHut/aegis.git my-project
cd my-project
git remote rename origin aegis-template
```

An ordinary clone retains Aegis history. Renaming the template remote makes its
purpose explicit; it does not create a project repository. When a destination
repository is supplied, add it as `origin`. Do not push project work to the Aegis
remote. If using an existing clone, inspect `git remote -v` before changing it.

## 4. Initialize and verify

From the project root:

```bash
python3 scripts/init.py --name my-project --description "Project purpose" --dry-run
python3 scripts/init.py --name my-project --description "Project purpose"
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests -v
python3 scripts/validate.py
git status --short
```

On Windows, activate the environment with `.venv\Scripts\Activate.ps1` in
PowerShell. If only initialization is in scope, its dependency-free checks are
`python3 -m unittest discover -s tests -p test_init.py -v`; report core validation
as not run until the declared dependencies are available. Do not present skipped
validation as a pass. `python3 scripts/validate.py --json` provides tooling output.
Validation checks artifact structure, references and coverage, not runtime behavior
or host enforcement. No conformance runner is installed by these commands.

Confirm that `project.json`, `docs/PROJECT.md`,
`docs/discussion/initial-brief.md`, and
`docs/discussion/initial-assignment.draft.md` exist, contain the intended identity,
and record the Aegis version. Check that the registries under `framework/registry/`
start empty. A matching repeat initialization is a no-op; conflicting or edited
outputs block initialization without overwriting them. Never delete existing
project documents simply to make initialization succeed.

Inspect the authoritative `framework/decisions.yaml` and `agents/decisions.yaml`
logs separately from generated project documents. First initialization replaces
only exactly recognized bundled maintenance logs with `[]`; modified or
unrecognized logs block initialization without being overwritten. New project
logs contain no product approvals. Project rules must cite approved decisions in
their own scope. Markdown narrative and isolated examples cannot satisfy them.
Skipping initialization leaves the maintenance logs and no `project.json`; the
validator warns that the project is not initialized and rejects any project rule
that cites a bundled `D-AEGIS-*` maintenance decision.

Do not run initialization in the Aegis template's own maintenance checkout.
Commit or push only when included in the user's setup request.

The template includes [a GitHub Actions workflow](.github/workflows/validate.yml)
for pushes and pull requests. It installs the same development dependencies,
tests Python 3.9 and the latest stable 3.x, validates artifacts, and uploads JSON
results. Pull requests additionally compare against their fetched base branch.
No credentials beyond the read-only workflow token or project secrets are needed.
Repository/organization Actions policy may require the owner to enable the workflow.
After an authorized push or PR, inspect the actual Actions results before claiming
CI passed. A local-only project has no GitHub Actions run.

Follow [continuous validation setup](docs/GETTING_STARTED.md#continuous-validation-on-github)
to make the checks required manually. Initialization does not configure branch
protection. CI uses `--strict`, so both errors and warnings fail the artifact gate;
ordinary local validation fails on errors only. A green
check is not proof of behavioral conformance or genuine approval provenance.

For 0.2.3 scenarios, define reusable records and enums in the owning context's
`types.yaml`; validation follows declared types through nested records, lists and
maps. Keep date-time expectations offset-bearing, integers within the JSON safe
range and exact decimals quoted when source precision matters. Capture paths
traverse record fields only and source/target types must match. Typed matching,
typed event payload assertions and one-to-one array matching are specified and
unit-tested in the reference matcher, but no scenario runner or driver is installed.

## 5. Hand over a ready project

Add the supplied project intent to the initial brief, keeping unknowns visible.
Begin with the problem and evidence, then explore alternatives and candidate
rules/scenarios before committing to a feature list. Keep the core independent
of the stack so it can outlive this implementation.
Keep the assignment draft unapproved until the owner supplies the required
admission details. Follow the [first-discussion guide](docs/GETTING_STARTED.md#admit-the-first-discussion)
for the next work window; setup is not permission to implement the application.

Report the destination, tools found or installed and their versions, repository
URL/visibility or local-only status, generated files, verification results, and
any unresolved prerequisites. Do not report installation, authentication, tests,
or admission as complete without checking them.

For template development and publishing, use [CONTRIBUTING.md](CONTRIBUTING.md).

# Install Aegis for a new project

This is the setup runbook for a person or coding agent. Aegis is a public
repository template; there is no Aegis package to install. Its initializer and
tests use only the Python standard library.

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
- Project purpose, intended users, constraints, and known technology choices for
  the initial brief. Record unknowns rather than choosing a stack implicitly.

If the project already exists, inspect it first. Do not overlay the starter onto
an unrelated codebase or overwrite files; that requires a separate migration plan.
If it is an uninitialized Aegis copy, skip repository creation and use that copy.

## 1. Check requirements

| Requirement | Needed for | Check |
| --- | --- | --- |
| Python 3.9 or newer | Initialization and tests | `python3 --version` |
| Git | Cloning and version control | `git --version` |
| GitHub CLI (`gh`) | Optional CLI repository creation | `gh --version` |
| GitHub authentication | Creating a repository, not reading the public template | `gh auth status` |
| AI coding tool | Working through agent assignments | Use the user's existing tool |

On Windows, try `py -3 --version` if `python3` is unavailable. Use `py -3` in
place of `python3` throughout this guide when that is the available interpreter.
Verify the actual version; install a currently supported Python release when
provisioning a new machine.

No Node.js, Docker, database, pip packages, or schema-validation libraries are
required for the starter. Application dependencies depend on the project's later
approved implementation plan.

## 2. Obtain missing tools

Inspect the operating system and available package manager. Install only missing
requirements using its normal permission mechanism, then rerun the checks above.
Do not replace a working environment merely to match an example command.

- **Debian/Ubuntu:** use `sudo apt-get update`, then
  `sudo apt-get install python3 git` for missing core tools. Check the Python version
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
python3 -m unittest discover -s tests -v
git status --short
```

Confirm that `project.json`, `docs/PROJECT.md`,
`docs/discussion/initial-brief.md`, and
`docs/discussion/initial-assignment.draft.md` exist, contain the intended identity,
and record the Aegis version. Check that the registries under `framework/registry/`
start empty. A matching repeat initialization is a no-op; conflicting or edited
outputs block initialization without overwriting them. Never delete existing
project documents simply to make initialization succeed.

Do not run initialization in the Aegis template's own maintenance checkout.
Commit or push only when included in the user's setup request.

## 5. Hand over a ready project

Add the supplied project intent to the initial brief, keeping unknowns visible.
Keep the assignment draft unapproved until the owner supplies the required
admission details. Follow the [first-discussion guide](docs/GETTING_STARTED.md#admit-the-first-discussion)
for the next work window; setup is not permission to implement the application.

Report the destination, tools found or installed and their versions, repository
URL/visibility or local-only status, generated files, verification results, and
any unresolved prerequisites. Do not report installation, authentication, tests,
or admission as complete without checking them.

For template development and publishing, use [CONTRIBUTING.md](CONTRIBUTING.md).

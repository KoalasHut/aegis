# Aegis

Aegis keeps a project's core—its decisions, domain rules, vocabulary and expected
behavior—independent of the stack, so that core can outlive any implementation.
Explicit roles, scoped assignments and reviewable handoffs carry it from the
first problem discussion to implementation.

Version 0.2.1 provides identified domain rules, structured scenarios and decisions,
isolated project/example validation, and checks for artifact references and
coverage. Validation does not
execute scenarios or prove an implementation conforms. A conformance runner,
driver protocol, workflow lanes, provisional-rule flow and legacy extraction
remain deferred. See [release notes](CHANGELOG.md) and
[migration from 0.1.0 or 0.2.0](docs/MIGRATION-0.2.md).

**Learn by building:** follow the [TODO app quickstart](QUICKSTART.md) for a
worked example with prompts, decisions, and expected outputs at every stage.
The [Tiny TODO artifacts](framework/examples/tiny-todo/) show the
structured core in its own example scope, separate from your project.

## 1. Create your project

Aegis is a public template. You need Python 3.9+, Git, and an authenticated
[GitHub CLI](https://cli.github.com/) for the repository-creation command below.
To have an agent check and install prerequisites, point it to
[INSTALL.md](INSTALL.md) with your project name and destination.
Replace `OWNER` with your GitHub account or organization and `my-project` with your
project name.

```bash
gh repo create OWNER/my-project --private --template KoalasHut/aegis --clone
cd my-project
```

The example creates a private project; use `--public` if you want a public one.

You can also choose **Use this template → Create a new repository** on GitHub,
then clone your new repository locally.

## 2. Initialize it

Preview the files Aegis will create, then initialize:

```bash
python3 scripts/init.py --name my-project --description "What this project is for" --dry-run
python3 scripts/init.py --name my-project --description "What this project is for"
```

Use a lowercase name with letters, digits, and single hyphens. Initialization
creates:

| File | What to do with it |
| --- | --- |
| `project.json` | Keep the project identity and starting Aegis version |
| `docs/PROJECT.md` | Describe your project as it develops |
| `docs/discussion/initial-brief.md` | Explain the problem, intended users, constraints, and open questions |
| `docs/discussion/initial-assignment.draft.md` | Prepare the first discussion assignment |

Authoritative decision logs live in `framework/decisions.yaml` and
`agents/decisions.yaml`. Initialization replaces the recognized bundled Aegis
maintenance logs with empty project logs; modified or unrecognized logs are
preserved as conflicts. Maintenance decisions are not product approvals. Record your own
decisions with unique IDs, actual approval sources and statuses. Markdown can
explain a decision, but does not authorize it for validation.

The same command can be repeated without changes. If generated files already
contain different content, initialization stops without overwriting them.

## 3. Start the first discussion

Open your new project in your AI coding tool and read [AGENTS.md](AGENTS.md).
Fill in the initial brief, then use the assignment draft to specify the discussion
role, input files, permitted actions, expected output, and work window.

As project owner, approve the assignment and have it checked against the
[stage contracts](agents/stage-contracts.md) before work starts. The draft itself
is not approval. See the [first-discussion guide](docs/GETTING_STARTED.md#admit-the-first-discussion)
for the admission checklist.

Begin with the problem, who experiences it and when, the desired outcome,
signals of success and supporting evidence. Explore alternatives, candidate
rules and scenarios before committing to features. An explicitly assigned
throwaway mockup can answer a question; its behavior does not approve a rule.

Aegis guides the project through:

**Discuss → Consolidate → Plan → Plan specific → Orchestrate specific → Execute specific**

Review each handoff before assigning the next stage. Repository instructions
provide the workflow; your tool's permissions provide actual access controls.
Optional [adapter instructions](agents/adapters/codex/README.md) describe separate
host setup; initialization does not install agents or a dispatcher.

## Validate the core

Initialization needs only Python's standard library. The validator and full
development test suite also need the packages in `requirements-dev.txt`:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
python3 scripts/validate.py
python3 scripts/validate.py --json
```

On Windows, activate with `.venv\Scripts\Activate.ps1` in PowerShell. Resolve
validation errors and review warnings before handing off core changes. Structural
checks do not authenticate owner approval, prove behavior or enforce host access.
The full stage chain remains in effect; there is no implementation-lane shortcut.

The inherited [GitHub Actions workflow](.github/workflows/validate.yml) runs tests
and artifact validation on pushes and pull requests using Python 3.9 and the
latest stable 3.x. Pull requests also compare approved rules with the fetched
base branch using `--base`. Each matrix job uploads JSON findings, including
validator failures. CI uses `--strict`, so errors and warnings both fail the
check; ordinary local validation fails on errors only. Review and resolve
warnings before merging.

CI checks artifact structure and traceability; it does not execute the domain
scenarios, prove behavioral conformance, authenticate approval evidence or enforce
agent permissions. The owner must enable Actions where needed and manually make
both checks required in branch protection. See
[CI setup](docs/GETTING_STARTED.md#continuous-validation-on-github).

## Where your work goes

- `framework/contexts/`: glossary, domain rules and context-owned scenarios.
- `framework/blocks/`: capability contracts referencing rule and scenario IDs.
- `framework/templates/`: starting points for new capability specifications.
- `docs/`: discussion briefs, decisions, and project documentation.
- `conformance/`: project acceptance mappings and verification evidence; no runner is bundled.
- `prototypes/`: optional implementation experiments.

See [setup details](docs/GETTING_STARTED.md) for ordinary cloning, input limits,
and initialization conflicts. For changes to Aegis itself, see
[CONTRIBUTING.md](CONTRIBUTING.md).

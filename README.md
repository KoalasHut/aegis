# Aegis

Aegis helps you build projects with AI through explicit roles, scoped assignments,
and reviewable handoffs—from the first discussion to implementation.

**Learn by building:** follow the [TODO app quickstart](QUICKSTART.md) for a
worked example with prompts, decisions, and expected outputs at every stage.

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

Aegis guides the project through:

**Discuss → Consolidate → Plan → Plan specific → Orchestrate specific → Execute specific**

Review each handoff before assigning the next stage. Repository instructions
provide the workflow; your tool's permissions provide actual access controls.
Optional [adapter instructions](agents/adapters/codex/README.md) describe separate
host setup; initialization does not install agents or a dispatcher.

## Where your work goes

- `framework/contexts/` and `framework/blocks/`: project concepts and contracts.
- `framework/templates/`: starting points for new capability specifications.
- `docs/`: discussion briefs, decisions, and project documentation.
- `conformance/`: acceptance mappings and verification evidence.
- `prototypes/`: optional implementation experiments.

See [setup details](docs/GETTING_STARTED.md) for ordinary cloning, input limits,
and initialization conflicts. For changes to Aegis itself, see
[CONTRIBUTING.md](CONTRIBUTING.md).

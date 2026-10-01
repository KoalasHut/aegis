# Build a TODO app with Aegis

Everybody needs somewhere to put “build a TODO app.” Let's make one.

This walkthrough takes a small app from an idea to reviewed implementation.
You'll act as project owner and manually route work between agent sessions.
The example prompts describe tasks; they are not preapproved assignments or
an automatic pipeline. No TODO application is bundled with Aegis.

## 1. Start your project

Follow [INSTALL.md](INSTALL.md) if you need prerequisites. Replace `OWNER` with
your GitHub account or organization:

```bash
gh repo create OWNER/tiny-todo --private --template KoalasHut/aegis --clone
cd tiny-todo
python3 scripts/init.py --name tiny-todo --description "A small personal TODO app" --dry-run
python3 scripts/init.py --name tiny-todo --description "A small personal TODO app"
```

Use `--public` if you want your app repository public. Open the new folder in your
AI coding tool. Work in this project copy, not the Aegis template checkout.

## 2. Describe the idea

Put the following in `docs/discussion/initial-brief.md` as your starting proposal:

```markdown
# Tiny TODO

Status: proposal for discussion; no approved product decisions yet.

## Intent
A single person can keep track of tasks in a small browser app.

## Proposed first version
- Add a task with a title.
- View tasks in creation order, newest last.
- Mark a task complete or active again.
- Delete a task.
- Filter by all, active, or completed tasks.
- Keep tasks after refreshing the page.

## Proposed boundaries
- No accounts, shared lists, due dates, or backend.
- One browser on one device; no synchronization between tabs or devices.
- Use ordinary HTML, CSS, and JavaScript for this learning project.

## Questions to resolve
- What happens to blank or whitespace-only titles?
- Are duplicate titles allowed?
- What happens if saving fails or stored data is invalid?
- Does deleting a task require confirmation?
```

Keeping this small makes it easier to see what each stage contributes. The
technology preference is an owner constraint to confirm, not a substitute for
specifying behavior.

## 3. Discuss the behavior

Start a fresh **discussion** session. Use
`docs/discussion/initial-assignment.draft.md` to prepare its assignment. A useful
task description is:

> Discuss Tiny TODO using the initial brief. Resolve the listed behavior questions
> with me, identify alternatives and explicit non-goals, and return a decision
> brief inline. Separate my approved decisions from your proposals. This window
> ends with your discussion handoff; do not write implementation files.

For each session in this guide, you or your dispatcher must fill in the
[assignment schema](agents/contracts/assignment.schema.json): role, approval
source, exact input revisions, read/write paths, permitted effects, expected
output, acceptance criteria, controls, and work window. Capture the structured
assignment before writes or delegation. The
[session prompt](agents/adapters/codex/session-prompt.md) shows how to load it.
Use only the current role and its inputs. A role change gets a fresh assignment
and session.

For this walkthrough, you might decide:

| Question | Example decision for you to approve |
| --- | --- |
| Empty title | Trim surrounding whitespace; reject an empty result without creating a task |
| Duplicate title | Allow it; tasks have distinct identifiers |
| Completion | Toggle either direction; preserve title and position |
| Filtering | Filtering changes the view, not the stored tasks |
| Delete | Delete immediately; no undo in this version |
| Persistence failure | Show an error; do not report the change as saved or replace the last saved state |
| Invalid stored data | Show a recovery message; preserve the data until the user explicitly resets it |

Review the returned brief and explicitly approve the decisions you want. Retain
the approval source and the reviewed revision. Unresolved mandatory behavior
returns to discussion before dependent work proceeds.

## 4. Consolidate into contracts

Assign an **architect** the approved brief and applicable framework rules:

> Consolidate Tiny TODO into a task-management context and the Concept Packs
> needed for adding, listing, completing, deleting, and filtering tasks. Specify
> state, inputs, outputs, errors, persistence boundaries, invariants, and acceptance
> scenarios. Use the approved decisions; return unresolved semantics to discussion.
> Produce an implementation handoff for the planner.

Give this assignment explicit write scope for the selected context, capability
packs, and affected registries under `framework/`. The
[block templates](framework/templates/block/concept.md) provide a starting point.
The architect chooses an appropriate decomposition; five UI actions need not
mean five independent implementation modules.

Review the contracts and scenarios. For example, the agreed behavior should be
checkable as:

| Scenario | Expected result |
| --- | --- |
| Add `  Buy milk  ` | One active task titled `Buy milk` appears |
| Add only spaces | Validation feedback appears; no task is added |
| Add the same title twice | Two independently addressable tasks exist |
| Complete and reopen a task | Its status changes without moving it |
| Filter completed tasks | Only completed tasks appear; switching to all restores the full view |
| Delete and refresh | The deleted task stays absent |
| Save fails | Visible error; no false success or silent loss of the prior saved state |
| Stored data is invalid | Recovery feedback appears; no automatic overwrite |

These are proposed acceptance scenarios until reviewed. They belong in the
project's versioned contracts, not just in this tutorial.

## 5. Plan the work

Use two separate sessions, with a reviewed handoff between them.

**Planner — what must be delivered:**

> Derive a generic backlog from the approved Tiny TODO contract revisions. Assign
> obligation IDs, map every acceptance scenario, record dependencies, and define
> completion evidence. Preserve error and persistence behavior as explicit work.

**Implementation planner — how to deliver it in this project:**

> Derive a concrete plan for the approved HTML/CSS/JavaScript browser target.
> Map every generic obligation to tasks, owned files, dependencies, and checks.
> Cover local storage failures and invalid data. Include instructions to run the
> app locally. Identify any required tooling before execution.

A possible output layout is below. These files are illustrative, not generated
by the initializer; admit the actual paths in the implementation plan:

```text
prototypes/web/
  index.html
  styles.css
  app.js
  README.md
conformance/todo/
  acceptance.md
```

For a small app, one cohesive executor task may be enough. Splitting work is
useful only when ownership and dependencies are clear. Approve the specific
plan and execution scope before orchestration.

## 6. Build and review

Assign an **orchestrator** the admitted implementation plan:

> Route the Tiny TODO plan into bounded executor assignments with exclusive file
> ownership. Integrate the results, verify every acceptance scenario, and return
> the evidence to me. Keep unresolved failures visible. Do not publish or deploy.

The orchestrator routes an **executor** task such as:

> Implement the assigned task IDs from the admitted plan in the named files.
> Follow the pinned contracts, run the assigned checks, and return changed-file
> references, results, and any gaps to the orchestrator. Stop at the handoff.

The orchestrator stays responsible for integration. A missing browser or test
runtime is an explicit verification gap, not a passed check. Fixes requiring new
code return to a bounded executor assignment.

For the illustrated static layout, the implementation may document a local
preview command like:

```bash
python3 -m http.server 8000 --bind 127.0.0.1 --directory prototypes/web
```

Open `http://127.0.0.1:8000`, then stop the server with Ctrl+C when done. Use the
same origin when checking refresh persistence. Follow the actual implementation's
README if the admitted plan chose a different layout.

## 7. Try the finished app

As owner, review the integration evidence and try the acceptance scenarios:
add two tasks, complete one, filter, refresh, reopen it, and delete it. Check
blank titles and the documented storage-error scenarios as well.

The result should include the app, run instructions, versioned contracts, and an
acceptance-to-evidence mapping. A `COMPLETED` handoff means ready for your review;
it does not automatically approve a commit, deployment, or the next feature.

Want due dates next? Open a new discussion assignment with that change request.
Aegis gives the new work the same path from a decision to verified behavior.

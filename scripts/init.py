#!/usr/bin/env python3
"""Initialize an Aegis project without dependencies or implicit authority."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


MAINTENANCE_LOG_HASHES = {
    "framework/decisions.yaml": "b48a85877f34d733f62b1bb75fa8d0bc144606bfa6624ebb4e5ae0ba859b60f8",
    "agents/decisions.yaml": "6a3ee20b0a32ed2dca001d71352e90c05ead957117b3337098237faec8caf463",
}


def checked(root, relative):
    path = root / relative
    current = root
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Refusing symlink: {relative}")
        if current != path and current.exists() and not current.is_dir():
            raise ValueError(f"Parent is not a directory: {relative}")
    return path


def file_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_output(path, content, replace):
    if replace:
        path.write_text(content, encoding="utf-8")
    else:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(content)


def initialize(root, name, description, dry_run=False, writer=None):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 80:
        raise ValueError("Name must be a lowercase slug, at most 80 characters (example: my-project).")
    if len(description) > 350 or any(ord(c) < 32 or ord(c) == 127 for c in description):
        raise ValueError("Description must be one line of at most 350 characters, without control characters.")
    version = checked(root, "VERSION").read_text().strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("VERSION must contain a semantic version such as 0.1.0.")
    # Everything is planned and checked before creating any file.
    template = checked(root, "docs/PROJECT_README.template.md").read_text()
    metadata = {"schemaVersion": 1, "name": name, "description": description,
                "aegis": {"version": version, "template": "KoalasHut/aegis"}}
    brief = f"""# {name}: initial discussion brief

Status: DRAFT — no decisions or approvals recorded.

## Problem

Starting description: {description or 'To be supplied by the domain owner.'}

Restate the problem in the owner's words. Separate observed symptoms from
possible causes; a feature request or stack choice is not yet the problem.

## Who and when

Who experiences it, in what context, and when? To be discussed.

## Desired outcome

What changes for those people if the problem is solved? To be discussed.

## Signals of success

What observable change would show improvement? To be agreed.

## Evidence

No evidence recorded yet. Cite observations and sources; label assumptions.

## Alternatives

Compare approaches, including a process change or doing nothing, before features.

## Proposals

### Candidate domain rules (status: proposed)

To be discussed; keep candidates here until owner review and consolidation.

### Candidate scenarios (plain language)

To be discussed; describe situations and expected outcomes without stack choices.

### Possible features

Consider only after the problem, alternatives, candidate rules and scenarios.
No feature commitment is implied by this draft.

## Approved decisions and provenance

None. Record the owner, approval source and reviewed revision for each decision.

## Open questions

- Who is the domain owner?
- Which evidence and mandatory behavior decisions are still missing?

## Question tools

Explicitly assigned throwaway prototypes or mockups may be question tools.
Record the question, findings and resulting decision here. Their behavior is
never implementation precedent or implicit approval.

## Non-goals

To be agreed. This draft authorizes no implementation.
"""
    assignment = f"""# Initial discussion assignment — DRAFT\n\nProject: {name}\nProposed role: discussion\nAdmission status: NOT ADMITTED\nApproval source: none\nWork window: not opened\n\nThis is a preparation worksheet, not an executable assignment. The domain owner\nand dispatcher must supply and validate authority before any agent starts work.\n\n## Required admission details\n\n- Assignment ID, issuer, and verifiable approval source.\n- Exact input revisions/digests, including the initial brief and applicable controls.\n- Named read/write paths, permitted effects, and explicit non-goals.\n- Expected discussion output, recipient, and work-window boundaries.\n- Host controls; acknowledge instruction-only operation if using a supervised pilot.\n\nUse `agents/contracts/assignment.schema.json` and `agents/stage-contracts.md`\nto prepare the admitted record. Proposed input: `docs/discussion/initial-brief.md`.\nNo approval, delegation, installation, or downstream execution is implied.\n"""
    outputs = {
        "project.json": json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        "framework/decisions.yaml": "[]\n",
        "agents/decisions.yaml": "[]\n",
        "docs/PROJECT.md": template.replace("{{PROJECT_NAME}}", name).replace("{{PROJECT_DESCRIPTION}}", description or "Project description pending.").replace("{{AEGIS_VERSION}}", version),
        "docs/discussion/initial-brief.md": brief,
        "docs/discussion/initial-assignment.draft.md": assignment,
    }
    paths = {relative: checked(root, relative) for relative in outputs}
    existing = [relative for relative, path in paths.items() if path.exists()]
    if (len(existing) == len(outputs) and
            all(paths[relative].is_file() and paths[relative].read_text(encoding="utf-8") == content
                for relative, content in outputs.items())):
        print("Already initialized with this configuration; no changes.")
        return

    actions = []
    collisions = []
    first_initialization = not any(relative not in MAINTENANCE_LOG_HASHES and path.exists()
                                   for relative, path in paths.items())
    for relative, path in paths.items():
        if not path.exists():
            actions.append((relative, path, "create"))
        elif (first_initialization and relative in MAINTENANCE_LOG_HASHES and path.is_file() and
              file_digest(path) == MAINTENANCE_LOG_HASHES[relative]):
            actions.append((relative, path, "replace"))
        else:
            collisions.append(relative)
    if collisions:
        raise ValueError("Initialization conflicts with existing or edited output; no files changed: " +
                         ", ".join(collisions))
    for relative, _, action in actions:
        verb = "replace" if action == "replace" else "create"
        print(("Would " if dry_run else "") + verb + " " + relative)
    if dry_run:
        return
    writer = writer or write_output
    created = []
    replaced = {}
    try:
        for relative, path, action in actions:
            if action == "create":
                path.parent.mkdir(parents=True, exist_ok=True)
                created.append(path)
            else:
                replaced[path] = path.read_bytes()
            writer(path, outputs[relative], action == "replace")
    except OSError:
        for path, original in replaced.items():
            path.write_bytes(original)
        for path in reversed(created):
            if path.exists():
                path.unlink()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        initialize(Path(__file__).resolve().parent.parent, args.name, args.description, args.dry_run)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

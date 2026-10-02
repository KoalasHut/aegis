#!/usr/bin/env python3
"""Initialize an Aegis project without dependencies or implicit authority."""
import argparse
import json
import re
import sys
from pathlib import Path


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


def initialize(root, name, description, dry_run=False):
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
        "docs/PROJECT.md": template.replace("{{PROJECT_NAME}}", name).replace("{{PROJECT_DESCRIPTION}}", description or "Project description pending.").replace("{{AEGIS_VERSION}}", version),
        "docs/discussion/initial-brief.md": brief,
        "docs/discussion/initial-assignment.draft.md": assignment,
    }
    paths = {relative: checked(root, relative) for relative in outputs}
    existing = [relative for relative, path in paths.items() if path.exists()]
    if existing:
        if len(existing) == len(outputs) and all(paths[r].is_file() and paths[r].read_text() == content for r, content in outputs.items()):
            print("Already initialized with this configuration; no changes.")
            return
        raise ValueError("Initialization conflicts with existing or edited output; no files changed: " + ", ".join(existing))
    for relative in outputs:
        print(("Would create " if dry_run else "Create ") + relative)
    if dry_run:
        return
    created = []
    try:
        for relative, content in outputs.items():
            path = paths[relative]
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8") as stream:
                created.append(path)
                stream.write(content)
    except OSError:
        for path in reversed(created):
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

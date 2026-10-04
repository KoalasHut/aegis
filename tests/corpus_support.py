"""Executable corpus operations shared by regression and mutation tests."""

from contextlib import contextmanager
from pathlib import Path
import shutil
import subprocess
import tempfile

import yaml

from scripts import validate as validator


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_FIXTURES = ROOT / "tests" / "fixtures" / "validate"


def _write_yaml(path, value):
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


@contextmanager
def project(overlay=None):
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "project"
        shutil.copytree(VALIDATE_FIXTURES / "valid", root)
        shutil.copytree(ROOT / "agents" / "contracts", root / "agents" / "contracts")
        if overlay:
            source = VALIDATE_FIXTURES / overlay
            for item in source.rglob("*"):
                if item.is_file():
                    target = root / item.relative_to(source)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target)
        yield root


def _commit(root):
    for command in (
        ("git", "init", "-q", str(root)),
        ("git", "-C", str(root), "config", "user.email", "corpus@example.invalid"),
        ("git", "-C", str(root), "config", "user.name", "Corpus fixture"),
        ("git", "-C", str(root), "add", "."),
        ("git", "-C", str(root), "commit", "-qm", "base"),
    ):
        subprocess.run(command, check=True, capture_output=True)


def _scenario(root):
    return root / "framework" / "contexts" / "tasks" / "scenarios" / "tasks.yaml"


def _rules(root):
    return root / "framework" / "contexts" / "tasks" / "rules" / "tasks.yaml"


def _decisions(root):
    return root / "framework" / "decisions.yaml"


def execute_project_operation(operation):
    """Apply one named mutation and return every visible production finding code."""
    overlay = operation.removeprefix("overlay:") if operation.startswith("overlay:") else None
    with project(overlay) as root:
        base = None
        if operation == "base-decision-edit":
            _commit(root)
            decisions = yaml.safe_load(_decisions(root).read_text())
            decisions[0]["decision"] = "Changed governed decision"
            _write_yaml(_decisions(root), decisions)
            base = "HEAD"
        elif operation == "base-rule-edit":
            _commit(root)
            rules = yaml.safe_load(_rules(root).read_text())
            rules[0]["statement"] = "A changed governed statement."
            _write_yaml(_rules(root), rules)
            base = "HEAD"
        elif operation == "maintenance-decision":
            rules = yaml.safe_load(_rules(root).read_text())
            rules[0]["decision"] = "D-AEGIS-999"
            _write_yaml(_rules(root), rules)
        elif operation == "expect-error-capture":
            scenarios = yaml.safe_load(_scenario(root).read_text())
            scenarios[0]["given"] = {"steps": [{
                "command": "tasks.add", "input": {"title": ""},
                "expectError": "TITLE_EMPTY", "as": "failed",
            }]}
            _write_yaml(_scenario(root), scenarios)
        elif operation == "duplicate-capture":
            scenarios = yaml.safe_load(_scenario(root).read_text())
            scenarios[0]["given"] = {"steps": [
                {"command": "tasks.add", "input": {"title": "one"}, "as": "saved"},
                {"command": "tasks.add", "input": {"title": "two"}, "as": "saved"},
            ]}
            _write_yaml(_scenario(root), scenarios)
        elif operation == "unknown-input":
            scenarios = yaml.safe_load(_scenario(root).read_text())
            scenarios[0]["when"]["input"]["unknown"] = True
            _write_yaml(_scenario(root), scenarios)
        elif operation == "missing-required":
            scenarios = yaml.safe_load(_scenario(root).read_text())
            scenarios[0]["when"]["input"] = {}
            _write_yaml(_scenario(root), scenarios)
        elif operation == "unknown-capture":
            scenarios = yaml.safe_load(_scenario(root).read_text())
            scenarios[0]["when"]["input"]["title"] = "${later.item.title}"
            _write_yaml(_scenario(root), scenarios)
        elif operation in {"unknown-capture-field", "indexed-capture", "capture-mismatch"}:
            scenarios = yaml.safe_load(_scenario(root).read_text())
            scenarios[0]["given"] = {"steps": [
                {"command": "tasks.add", "input": {"title": "one"}, "as": "saved"},
            ]}
            reference = {
                "unknown-capture-field": "${saved.item.missing}",
                "indexed-capture": "${saved.item.0}",
                "capture-mismatch": "${saved.item.id}",
            }[operation]
            scenarios[0]["when"]["input"]["title"] = reference
            _write_yaml(_scenario(root), scenarios)
        elif operation == "invalid-clock-step":
            scenarios = yaml.safe_load(_scenario(root).read_text())
            scenarios[0]["given"] = {"steps": [{"advanceClock": "not-a-duration"}]}
            _write_yaml(_scenario(root), scenarios)
        elif operation == "invalid-matcher":
            scenarios = yaml.safe_load(_scenario(root).read_text())
            scenarios[0]["then"]["output"] = {"item": {"$unknown": True}}
            _write_yaml(_scenario(root), scenarios)
        elif operation == "bare-capture":
            scenarios = yaml.safe_load(_scenario(root).read_text())
            scenarios[0]["given"] = {"steps": [
                {"command": "tasks.add", "input": {"title": "one"}, "as": "saved"},
            ]}
            scenarios[0]["when"]["input"]["title"] = "${saved}"
            _write_yaml(_scenario(root), scenarios)
        elif operation == "shadow-type":
            contract = root / "framework" / "blocks" / "tasks" / "contracts" / "add.yaml"
            value = yaml.safe_load(contract.read_text())
            value["types"]["Task"] = {"description": "Shadow.", "fields": {}}
            _write_yaml(contract, value)
        elif operation == "opaque-type":
            contract = root / "framework" / "blocks" / "tasks" / "contracts" / "add.yaml"
            value = yaml.safe_load(contract.read_text())
            value["types"]["Legacy"] = "Legacy opaque type."
            value["input"]["title"]["type"] = "Legacy"
            _write_yaml(contract, value)
        elif operation == "invalid-timezone":
            scenarios = yaml.safe_load(_scenario(root).read_text())
            scenarios[0]["given"] = {"timezone": "Mars/Olympus_Mons", "steps": []}
            _write_yaml(_scenario(root), scenarios)
        elif operation == "invalid-locale":
            rules = yaml.safe_load(_rules(root).read_text())
            rules[0]["collation"] = {"locale": "pt_BR"}
            _write_yaml(_rules(root), rules)
        elif operation == "unknown-error":
            scenarios = yaml.safe_load(_scenario(root).read_text())
            scenarios[0]["then"] = {"error": "NOT_DECLARED"}
            _write_yaml(_scenario(root), scenarios)
        elif operation == "rejected-decision":
            decisions = yaml.safe_load(_decisions(root).read_text())
            decisions[0]["status"] = "rejected"
            _write_yaml(_decisions(root), decisions)
        elif overlay is None:
            raise AssertionError("unknown project corpus operation: " + operation)
        findings = validator.validate(root, base=base)
        return sorted(item["code"] for item in findings.items)

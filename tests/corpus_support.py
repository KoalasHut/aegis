"""Executable corpus operations shared by regression and mutation tests."""

from contextlib import contextmanager
import json
from pathlib import Path
import shutil
import subprocess
import sys
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


def _contract(root, name):
    return root / "framework" / "blocks" / "tasks" / "contracts" / (name + ".yaml")


def _read_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _add_field(contract, section, name, declared_type, required=True):
    contract[section][name] = {
        "type": declared_type,
        "required": required,
        "description": "Corpus field.",
    }


def _normalize_findings(findings):
    """Return the public, location-bearing finding multiset used by the corpus."""
    return sorted(
        ({"severity": item["severity"], "code": item["code"],
          "path": item["path"], "fieldPath": item.get("fieldPath")}
         for item in findings),
        key=lambda item: (item["severity"], item["code"], item["path"],
                          item["fieldPath"] or ""),
    )


def _apply_corpus_mutation(root, mutation):
    """Apply one declared corpus edit to a supported project fixture."""
    scenario_path = _scenario(root)
    scenarios = _read_yaml(scenario_path)
    scenario = scenarios[0]
    types_path = root / "framework" / "contexts" / "tasks" / "types.yaml"
    types = _read_yaml(types_path)

    def input_of(declared_type, value):
        contract_path = _contract(root, "add")
        contract = _read_yaml(contract_path)
        _add_field(contract, "input", "corpus", declared_type)
        _write_yaml(contract_path, contract)
        scenario["when"]["input"] = {"title": "Write a note", "corpus": value}
        _write_yaml(scenario_path, scenarios)

    def output_of(declared_type, value):
        contract_path = _contract(root, "add")
        contract = _read_yaml(contract_path)
        _add_field(contract, "output", "corpus", declared_type)
        _write_yaml(contract_path, contract)
        scenario["then"]["output"] = {"corpus": value}
        _write_yaml(scenario_path, scenarios)

    if mutation == "MUT-01":
        scenario["when"]["input"] = {"titel": "x"}
        _write_yaml(scenario_path, scenarios)
    elif mutation == "MUT-02":
        types["types"]["TaskState"] = {"description": "State.", "enum": ["open", "complete"]}
        _write_yaml(types_path, types)
        input_of("TaskState", "Open")
    elif mutation == "MUT-03":
        input_of("datetime", "2026-10-02T09:00:00")
    elif mutation == "MUT-04":
        scenario["given"] = {"steps": [{
            "command": "tasks.add", "input": {"title": ""},
            "expectError": "TITLE_EMPTY", "as": "failed",
        }]}
        _write_yaml(scenario_path, scenarios)
    elif mutation == "MUT-05":
        decisions = _read_yaml(_decisions(root))
        decisions[0]["status"] = "rejected"
        _write_yaml(_decisions(root), decisions)
    elif mutation == "MUT-06":
        scenario["given"] = {"steps": [
            {"command": "tasks.add", "input": {"title": "one"}, "as": "saved"},
            {"command": "tasks.add", "input": {"title": "two"}, "as": "saved"},
        ]}
        _write_yaml(scenario_path, scenarios)
    elif mutation == "MUT-07":
        input_of("MissingType", "value")
    elif mutation == "MUT-08":
        types["types"]["OnlyTitle"] = {"description": "Only title.", "fields": {
            "title": {"type": "string", "required": True},
        }}
        _write_yaml(types_path, types)
        input_of("OnlyTitle", {})
    elif mutation == "MUT-09":
        input_of("integer", 9007199254740992)
    elif mutation == "MUT-10":
        input_of("integer", -9007199254740992)
    elif mutation == "MUT-11":
        input_of("date", "2026-02-30")
    elif mutation == "MUT-12":
        input_of("duration", "two-hours")
    elif mutation == "MUT-13":
        input_of("decimal", "one")
    elif mutation == "MUT-14":
        input_of("boolean", "true")
    elif mutation == "MUT-15":
        output_of("string", {"$length": 1})
    elif mutation == "MUT-16":
        output_of("string", {"$contains": ["x"]})
    elif mutation == "MUT-17":
        output_of("Task", {"$unordered": []})
    elif mutation == "MUT-18":
        output_of("string", None)
    elif mutation == "MUT-19":
        output_of("string", {"$absent": True})
    elif mutation == "MUT-20":
        scenario["given"] = {"steps": [
            {"command": "tasks.add", "input": {"title": "one"}, "as": "saved"},
        ]}
        scenario["when"]["input"]["title"] = "${saved.item.missing}"
        _write_yaml(scenario_path, scenarios)
    elif mutation == "MUT-21":
        scenario["given"] = {"steps": [
            {"command": "tasks.add", "input": {"title": "one"}, "as": "saved"},
        ]}
        scenario["when"]["input"]["title"] = "${saved.item.0}"
        _write_yaml(scenario_path, scenarios)
    elif mutation == "MUT-22":
        scenario["given"] = {"steps": [
            {"command": "tasks.add", "input": {"title": "one"}, "as": "saved"},
        ]}
        scenario["when"]["input"]["title"] = "${saved.item.id}"
        _write_yaml(scenario_path, scenarios)
    elif mutation == "MUT-23":
        contract_path = _contract(root, "add")
        contract = _read_yaml(contract_path)
        contract["types"]["Task"] = {"description": "Shadow.", "fields": {}}
        _write_yaml(contract_path, contract)
    elif mutation == "MUT-24":
        contract_path = _contract(root, "add")
        contract = _read_yaml(contract_path)
        contract["types"]["Legacy"] = "Legacy opaque type."
        contract["input"]["title"]["type"] = "Legacy"
        _write_yaml(contract_path, contract)
    elif mutation == "MUT-25":
        scenario["given"] = {"timezone": "Mars/Olympus_Mons", "steps": []}
        _write_yaml(scenario_path, scenarios)
    elif mutation == "MUT-26":
        rules = _read_yaml(_rules(root))
        rules[0]["collation"] = {"locale": "pt_BR"}
        _write_yaml(_rules(root), rules)
    elif mutation == "MUT-27":
        overlay = VALIDATE_FIXTURES / "missing-contract"
        for item in overlay.rglob("*"):
            if item.is_file():
                target = root / item.relative_to(overlay)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
    elif mutation == "MUT-28":
        scenario["then"] = {"error": "NOT_DECLARED"}
        _write_yaml(scenario_path, scenarios)
    elif mutation == "MUT-29":
        overlay = VALIDATE_FIXTURES / "duplicate-id"
        for item in overlay.rglob("*"):
            if item.is_file():
                target = root / item.relative_to(overlay)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
    elif mutation == "MUT-30":
        input_of("string", 3)
    elif mutation == "MUT-31":
        types["types"]["Task"]["fields"]["dueAt"] = {"type": "datetim"}
        _write_yaml(types_path, types)
    elif mutation == "MUT-32":
        contract_path = _contract(root, "list")
        contract = _read_yaml(contract_path)
        contract["output"]["items"]["type"] = "Taks[]"
        _write_yaml(contract_path, contract)
    elif mutation == "MUT-33":
        scenario["given"] = {"steps": [{
            "command": "tasks.add", "input": {"title": {"$any": True}},
        }]}
        _write_yaml(scenario_path, scenarios)
    elif mutation == "MUT-34":
        contract_path = _contract(root, "add")
        contract = _read_yaml(contract_path)
        _add_field(contract, "input", "dueAt", "datetime", required=False)
        _write_yaml(contract_path, contract)
        scenario["when"]["input"]["dueAt"] = {"$absent": True}
        _write_yaml(scenario_path, scenarios)
    elif mutation == "MUT-35":
        types["types"]["TaskState"] = {"description": "State.", "enum": ["open", "complete", "open"]}
        types["types"]["Task"]["fields"]["state"] = {"type": "TaskState", "required": True}
        _write_yaml(types_path, types)
    elif mutation == "MUT-36":
        scenario["when"]["input"]["title"] = "after ${task1.task.id}"
        _write_yaml(scenario_path, scenarios)
    elif mutation == "MUT-37":
        output_of("map<string>", {"caf\u00e9": "one", "cafe\u0301": "two"})
    elif mutation == "MUT-38":
        types["types"]["TaskState"] = {"description": "State.", "enum": ["open", "complete", "caf\u00e9", "cafe\u0301"]}
        types["types"]["Task"]["fields"]["state"] = {"type": "TaskState", "required": True}
        _write_yaml(types_path, types)
    elif mutation == "MUT-39":
        types["types"]["Node"] = {"description": "Node.", "fields": {
            "next": {"type": "Node", "required": True},
        }}
        _write_yaml(types_path, types)
    elif mutation == "MUT-40":
        types["types"]["A"] = {"description": "A.", "fields": {
            "b": {"type": "B", "required": True},
        }}
        types["types"]["B"] = {"description": "B.", "fields": {
            "a": {"type": "A", "required": True},
        }}
        _write_yaml(types_path, types)
    elif mutation == "K-9-list":
        types["types"]["Node"] = {"description": "Node.", "fields": {
            "children": {"type": "Node[]", "required": True},
        }}
        _write_yaml(types_path, types)
        contract_path = _contract(root, "add")
        contract = _read_yaml(contract_path)
        _add_field(contract, "output", "node", "Node")
        _write_yaml(contract_path, contract)
    elif mutation == "K-9-optional":
        types["types"]["Node"] = {"description": "Node.", "fields": {
            "next": {"type": "Node"},
        }}
        _write_yaml(types_path, types)
        contract_path = _contract(root, "add")
        contract = _read_yaml(contract_path)
        _add_field(contract, "output", "node", "Node")
        _write_yaml(contract_path, contract)
    elif mutation == "K-9-map":
        types["types"]["Node"] = {"description": "Node.", "fields": {
            "children": {"type": "map<Node>", "required": True},
        }}
        _write_yaml(types_path, types)
        contract_path = _contract(root, "add")
        contract = _read_yaml(contract_path)
        _add_field(contract, "output", "node", "Node")
        _write_yaml(contract_path, contract)
    else:
        raise AssertionError("unknown corpus mutation: " + mutation)


def execute_corpus_operation(operation, cli=False):
    """Execute a declared corpus edit through the public validator API and CLI."""
    with project() as root:
        _apply_corpus_mutation(root, operation)
        api = _normalize_findings(validator.validate(root).items)
        result = {"api": api}
        if cli:
            command = [sys.executable, str(ROOT / "scripts" / "validate.py"),
                       "--root", str(root), "--json"]
            completed = subprocess.run(command, text=True, capture_output=True, check=False)
            payload = json.loads(completed.stdout)
            result["cli"] = _normalize_findings(payload["findings"])
            result["exitCode"] = completed.returncode
            result["stderr"] = completed.stderr
        return result


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

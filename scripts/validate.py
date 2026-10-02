#!/usr/bin/env python3
"""Validate Aegis structural artifacts and core-preservation traceability."""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import jsonschema
import yaml


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
DECISION_PATTERN = re.compile(r"\bD-[A-Z][A-Z0-9-]*-[0-9]{3}\b")
DEFAULT_NEUTRALITY_WORDS = SCRIPT_ROOT / "framework" / "language" / "neutrality-words.txt"


class Findings:
    def __init__(self):
        self.items = []

    def add(self, severity, code, path, message):
        self.items.append({
            "severity": severity,
            "code": code,
            "path": str(path),
            "message": message,
        })

    @property
    def errors(self):
        return [item for item in self.items if item["severity"] == "error"]

    @property
    def warnings(self):
        return [item for item in self.items if item["severity"] == "warning"]


def relative(path, root):
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def load_document(path, findings, root):
    try:
        if path.suffix == ".json":
            return json.loads(path.read_text(encoding="utf-8"))
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        findings.add("error", "PARSE_ERROR", relative(path, root), str(exc))
        return None


def artifact_paths(root):
    ignored = {".git", "__pycache__", ".pytest_cache"}
    return sorted(
        path for path in root.rglob("*")
        if path.is_file() and path.suffix in {".yaml", ".yml", ".json"}
        and not any(part in ignored for part in path.parts)
        and "schemas" not in path.parts
        and "tests" not in path.parts
    )


def schema_for(root, name):
    candidate = root / "framework" / "language" / "schemas" / name
    if candidate.exists():
        return candidate
    return SCRIPT_ROOT / "framework" / "language" / "schemas" / name


def agent_schema_for(root, name):
    candidate = root / "agents" / "contracts" / name
    if candidate.exists():
        return candidate
    return SCRIPT_ROOT / "agents" / "contracts" / name


def load_neutrality_words(root, override, findings):
    candidate = override or root / "framework" / "language" / "neutrality-words.txt"
    path = candidate if candidate.exists() else DEFAULT_NEUTRALITY_WORDS
    try:
        return tuple(line.strip() for line in path.read_text(encoding="utf-8").splitlines()
                     if line.strip() and not line.lstrip().startswith("#"))
    except OSError as exc:
        findings.add("error", "NEUTRALITY_WORDS_UNAVAILABLE", path, str(exc))
        return ()


def is_template(path):
    return "templates" in path.parts


def is_scenario(path):
    return "scenarios" in path.parts and path.suffix in {".yaml", ".yml"}


def is_domain_rule(path, document):
    is_rule_location = "rules" in path.parts or path.name in {"rules.yaml", "rules.yml"}
    if not is_rule_location or "registry" in path.parts or is_template(path):
        return False
    values = document if isinstance(document, list) else [document]
    return any(isinstance(value, dict) and str(value.get("id", "")).startswith("BR-")
               for value in values)


def is_complete_example(path):
    if "examples" not in path.parts:
        return True
    index = path.parts.index("examples")
    if len(path.parts) <= index + 1:
        return False
    example_root = Path(*path.parts[:index + 2])
    has_rules = ((example_root / "rules").is_dir() or
                 (example_root / "rules.yaml").is_file() or
                 (example_root / "rules.yml").is_file())
    return has_rules and (example_root / "contracts").is_dir()


def is_semantic_artifact(path):
    return not is_template(path) and is_complete_example(path)


def validate_schema(document, schema_path, display_path, findings, each_item=False):
    if document is None or not schema_path.exists():
        return
    schema = load_document(schema_path, findings, schema_path.parent)
    if schema is None:
        return
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    documents = enumerate(document) if each_item and isinstance(document, list) else [(None, document)]
    for index, value in documents:
        for error in sorted(validator.iter_errors(value), key=lambda item: list(item.absolute_path)):
            location = ".".join(str(piece) for piece in error.absolute_path)
            prefix = "" if index is None else "[%s]" % index
            suffix = "%s%s" % (prefix, ("." + location) if location else "")
            findings.add("error", "SCHEMA_INVALID", display_path,
                         "%s: %s" % (suffix or "document", error.message))


def walk_mappings(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_mappings(child)


def walk_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_strings(child)


def add_id(index, identifier, path):
    if identifier:
        index.setdefault(identifier, []).append(path)


def add_neutrality_warnings(value, path, findings, words):
    if not words:
        return
    word_pattern = re.compile(r"\b(" + "|".join(re.escape(word) for word in words) + r")\b", re.IGNORECASE)
    for text in walk_strings(value):
        for match in word_pattern.finditer(text):
            findings.add("warning", "NEUTRALITY_WORD", path,
                         "stack-specific word '%s' requires review" % match.group(0))


def validate_references(scenarios, rules, contracts, decisions, reference_documents, findings):
    rule_by_id = {rule.get("id"): rule for rule, _ in rules if isinstance(rule, dict)}
    contract_by_id = {contract.get("id"): contract for contract, _ in contracts
                      if isinstance(contract, dict) and contract.get("id")}
    scenario_ids = {item.get("id") for item, _ in scenarios}

    for rule, path in rules:
        decision = rule.get("decision")
        if decision and decision not in decisions:
            findings.add("error", "UNKNOWN_DECISION", path,
                         "rule %s references unknown decision %s" % (rule.get("id"), decision))

    for document, path in reference_documents:
        if path.name in {"rules.yaml", "rules.yml"} and "registry" in path.parts:
            entries = document if isinstance(document, list) else []
            registry_ids = Counter(entry.get("id") for entry in entries
                                   if isinstance(entry, dict) and isinstance(entry.get("id"), str))
            for identifier, count in sorted(registry_ids.items()):
                if count > 1:
                    findings.add("error", "DUPLICATE_REGISTRY_ID", path,
                                 "rule registry contains %s more than once" % identifier)
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                identifier = entry.get("id")
                if not isinstance(identifier, str) or not identifier.startswith("BR-"):
                    continue
                canonical = rule_by_id.get(identifier)
                if entry.get("status") == "deprecated":
                    if canonical is not None and canonical.get("status") != "deprecated":
                        findings.add("error", "ID_REUSED", path,
                                     "deprecated registry ID %s collides with active rule" % identifier)
                elif canonical is None:
                    findings.add("error", "UNKNOWN_BR", path,
                                 "rule registry references unknown rule %s" % identifier)
        for mapping in walk_mappings(document):
            for key in ("scenarios", "scenario"):
                if key in mapping:
                    for identifier in walk_strings(mapping[key]):
                        if identifier.startswith("SC-") and identifier not in scenario_ids:
                            findings.add("error", "UNKNOWN_SC", path,
                                         "references unknown scenario %s" % identifier)
            if "rules" in mapping:
                for identifier in walk_strings(mapping["rules"]):
                    if identifier.startswith("BR-") and identifier not in rule_by_id:
                        findings.add("error", "UNKNOWN_BR", path,
                                     "references unknown rule %s" % identifier)
            if "registry" in path.parts:
                identifier = mapping.get("id")
                if isinstance(identifier, str) and identifier.startswith("SC-") and identifier not in scenario_ids:
                    findings.add("error", "UNKNOWN_SC", path,
                                 "registry references unknown scenario %s" % identifier)
                if (isinstance(identifier, str) and "contracts" in path.parts and
                        identifier not in contract_by_id):
                    findings.add("error", "UNKNOWN_CONTRACT", path,
                                 "registry references unknown contract %s" % identifier)

    def require_contract(name, expected_kind, path, location):
        contract = contract_by_id.get(name)
        if contract is None:
            findings.add("error", "UNKNOWN_CONTRACT", path,
                         "%s references unknown %s contract %s" % (location, expected_kind, name))
            return None
        if contract.get("kind") != expected_kind:
            findings.add("error", "CONTRACT_KIND_MISMATCH", path,
                         "%s references %s, which is %s rather than %s" %
                         (location, name, contract.get("kind"), expected_kind))
        return contract

    for scenario, path in scenarios:
        for rule_id in scenario.get("exercises", []):
            rule = rule_by_id.get(rule_id)
            if rule is None:
                findings.add("error", "UNKNOWN_BR", path,
                             "scenario %s exercises unknown rule %s" % (scenario.get("id"), rule_id))
            elif rule.get("status") != "approved":
                findings.add("error", "SCENARIO_RULE_NOT_APPROVED", path,
                             "scenario %s exercises %s with status %s" %
                             (scenario.get("id"), rule_id, rule.get("status")))

        given = scenario.get("given", {})
        for index, command in enumerate(given.get("commands", [])):
            if isinstance(command, dict):
                require_contract(command.get("command"), "command", path,
                                 "given.commands[%s]" % index)
        if isinstance(given.get("seed"), dict):
            require_contract(given["seed"].get("contract"), "port", path, "given.seed")

        when = scenario.get("when", {})
        if not isinstance(when, dict):
            continue
        if "command" in when:
            operation = require_contract(when.get("command"), "command", path, "when")
        else:
            operation = require_contract(when.get("query"), "query", path, "when")

        then = scenario.get("then", {})
        if not isinstance(then, dict):
            continue
        if then.get("error") and operation is not None:
            codes = {item.get("code") for item in operation.get("errors", []) if isinstance(item, dict)}
            if then["error"] not in codes:
                findings.add("error", "UNKNOWN_ERROR_CODE", path,
                             "then.error %s is not declared by %s" %
                             (then["error"], operation.get("id")))
        for event_ref in then.get("events", []):
            event_id, _, major = event_ref.rpartition("@")
            event = require_contract(event_id, "event", path, "then.events")
            if event is not None and event.get("version", "").split(".")[0] != major:
                findings.add("error", "EVENT_MAJOR_MISMATCH", path,
                             "%s does not match event contract %s" % (event_ref, event.get("version")))
        for index, observation in enumerate(then.get("observe", [])):
            if isinstance(observation, dict):
                require_contract(observation.get("query"), "query", path,
                                 "then.observe[%s]" % index)

    exercised = {rule_id for scenario, _ in scenarios for rule_id in scenario.get("exercises", [])}
    for rule, path in rules:
        if rule.get("status") == "approved" and rule.get("verification") == "automated" and rule.get("id") not in exercised:
            findings.add("warning", "AUTOMATED_RULE_UNCOVERED", path,
                         "approved automated rule %s has no scenario" % rule.get("id"))


def validate(root, neutrality_words_path=None):
    findings = Findings()
    neutrality_words = load_neutrality_words(root, neutrality_words_path, findings)
    documents = {}
    for path in artifact_paths(root):
        document = load_document(path, findings, root)
        if document is not None:
            documents[path] = document

    scenario_schema = schema_for(root, "scenario.schema.json")
    manifest_schema = schema_for(root, "manifest.schema.json")
    contract_schema = schema_for(root, "contract.schema.json")
    impact_schema = schema_for(root, "impact.schema.json")
    rule_schema = schema_for(root, "rule.schema.json")
    domain_rule_schema = schema_for(root, "domain-rule.schema.json")
    waiver_schema = schema_for(root, "waiver.schema.json")
    assignment_schema = agent_schema_for(root, "assignment.schema.json")
    handoff_schema = agent_schema_for(root, "handoff.schema.json")
    scope_schema = agent_schema_for(root, "scope.schema.json")

    ids = {}
    scenarios = []
    rules = []
    contracts = []
    reference_documents = []
    decisions = set()

    for path, document in documents.items():
        display_path = relative(path, root)
        if "constitution" in path.parts and "rules" in path.parts:
            validate_schema(document, rule_schema, display_path, findings, each_item=True)
        if is_scenario(path):
            validate_schema(document, scenario_schema, display_path, findings)
            if is_semantic_artifact(path) and isinstance(document, list):
                scenarios.extend((item, display_path) for item in document if isinstance(item, dict))
        if path.name == "manifest.yaml":
            validate_schema(document, manifest_schema, display_path, findings)
        if path.name == "impact.yaml" and not is_template(path):
            validate_schema(document, impact_schema, display_path, findings)
        if path.name == "scope.yaml" and "agents" in path.parts and not is_template(path):
            validate_schema(document, scope_schema, display_path, findings)
        if "waivers" in path.parts and not is_template(path):
            validate_schema(document, waiver_schema, display_path, findings)
        if isinstance(document, dict) and "kind" in document and "version" in document:
            validate_schema(document, contract_schema, display_path, findings)
            if is_semantic_artifact(path):
                contracts.append((document, display_path))
        if is_domain_rule(path, document):
            # The domain-rule schema owns the list envelope as well as its items.
            validate_schema(document, domain_rule_schema, display_path, findings)
            if is_semantic_artifact(path):
                values = document if isinstance(document, list) else [document]
                rules.extend((item, display_path) for item in values if isinstance(item, dict))
                add_neutrality_warnings(document, display_path, findings, neutrality_words)
        if isinstance(document, dict) and "assignmentId" in document and "objective" in document:
            validate_schema(document, assignment_schema, display_path, findings)
        if isinstance(document, dict) and "outcome" in document and "windowClosed" in document:
            validate_schema(document, handoff_schema, display_path, findings)
        if is_semantic_artifact(path):
            reference_documents.append((document, display_path))
            if "registry" not in path.parts:
                for mapping in walk_mappings(document):
                    identifier = mapping.get("id")
                    if isinstance(identifier, str):
                        add_id(ids, identifier, display_path)
            if "decisions" in path.parts or path.name.startswith("decisions"):
                for text in walk_strings(document):
                    decisions.update(DECISION_PATTERN.findall(text))
                if path.suffix == ".md":
                    decisions.update(DECISION_PATTERN.findall(path.read_text(encoding="utf-8")))

    for decision_path in root.rglob("*decisions*.md"):
        if not is_template(decision_path) and is_complete_example(decision_path):
            try:
                decisions.update(DECISION_PATTERN.findall(decision_path.read_text(encoding="utf-8")))
            except OSError as exc:
                findings.add("error", "PARSE_ERROR", relative(decision_path, root), str(exc))

    for identifier, paths in sorted(ids.items()):
        if len(paths) > 1:
            findings.add("error", "DUPLICATE_ID", paths[0],
                         "%s is declared more than once (%s)" %
                         (identifier, ", ".join(str(path) for path in paths)))
    for scenario, path in scenarios:
        add_neutrality_warnings(scenario, path, findings, neutrality_words)
    validate_references(scenarios, rules, contracts, decisions, reference_documents, findings)

    findings.items.sort(key=lambda item: (item["severity"], item["code"], item["path"], item["message"]))
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=SCRIPT_ROOT,
                        help="repository root to validate (default: validator repository)")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit machine-readable findings")
    parser.add_argument("--neutrality-words", type=Path,
                        help="path to a newline-separated neutrality warning vocabulary")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    findings = validate(root, args.neutrality_words)
    result = {
        "root": str(root),
        "errors": len(findings.errors),
        "warnings": len(findings.warnings),
        "findings": findings.items,
    }
    if args.as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for item in findings.items:
            print("%s %s %s: %s" %
                  (item["severity"].upper(), item["code"], item["path"], item["message"]))
        print("Validation completed: %s error(s), %s warning(s)." %
              (result["errors"], result["warnings"]))
    return 1 if findings.errors else 0


if __name__ == "__main__":
    sys.exit(main())

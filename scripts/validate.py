#!/usr/bin/env python3
"""Validate Aegis structural artifacts and core-preservation traceability."""

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import jsonschema
import yaml
from referencing import Registry, Resource


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
DECISION_PATTERN = re.compile(r"\bD-[A-Z][A-Z0-9-]*-[0-9]{3}\b")
DEFAULT_NEUTRALITY_WORDS = SCRIPT_ROOT / "framework" / "language" / "neutrality-words.txt"
CAPTURE_PATTERN = re.compile(r"\$\{([A-Za-z][A-Za-z0-9_]*)\.([A-Za-z][A-Za-z0-9_]*)(?:\.[^}]+)?\}")


def is_rfc3339_datetime(value):
    """Check the RFC3339 date-time subset accepted by Aegis scenario clocks."""
    if not isinstance(value, str) or "T" not in value:
        return False
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        return dt.datetime.fromisoformat(normalized).tzinfo is not None
    except ValueError:
        return False


FORMAT_CHECKER = jsonschema.FormatChecker()
if "date-time" not in FORMAT_CHECKER.checkers:
    FORMAT_CHECKER.checks("date-time")(is_rfc3339_datetime)


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


def excluded_from_scan(path, root, project_scope=False):
    """Apply every scan exclusion to root-relative path parts.

    A caller which explicitly names a tests directory as --root has no `tests`
    component below that root, so its fixtures remain inspectable. Repository
    validation still excludes development-only trees.
    """
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return True
    if any(part in {".git", "__pycache__", ".pytest_cache"} for part in parts):
        return True
    if any(part in {"tests", "templates", "schemas"} for part in parts):
        return True
    return project_scope and "examples" in parts


def artifact_paths(root, project_scope=False):
    return sorted(
        path for path in root.rglob("*")
        if path.is_file() and path.suffix in {".yaml", ".yml", ".json"}
        and not excluded_from_scan(path, root, project_scope)
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


def schema_registry(schema_path, findings):
    """Register every local language schema, including their canonical $id values."""
    registry = Registry()
    for path in sorted(schema_path.parent.glob("*.schema.json")):
        schema = load_document(path, findings, schema_path.parent)
        if not isinstance(schema, dict):
            continue
        # Schemas which predate $id still need a stable base for relative refs.
        canonical = schema.get("$id") or path.resolve().as_uri()
        if "$id" not in schema:
            schema = dict(schema)
            schema["$id"] = canonical
        resource = Resource.from_contents(schema)
        registry = registry.with_resource(canonical, resource)
        registry = registry.with_resource(path.resolve().as_uri(), resource)
    return registry


def schema_formats(schema):
    if isinstance(schema, dict):
        if isinstance(schema.get("format"), str):
            yield schema["format"]
        for value in schema.values():
            yield from schema_formats(value)
    elif isinstance(schema, list):
        for value in schema:
            yield from schema_formats(value)


def validate_schema(document, schema_path, display_path, findings, each_item=False):
    if document is None or not schema_path.exists():
        return
    schema = load_document(schema_path, findings, schema_path.parent)
    if schema is None:
        return
    unavailable = sorted(set(schema_formats(schema)) - set(FORMAT_CHECKER.checkers))
    if unavailable:
        findings.add("error", "FORMAT_CHECK_UNAVAILABLE", display_path,
                     "schema formats cannot be enforced: %s" % ", ".join(unavailable))
        return
    validator = jsonschema.Draft202012Validator(
        schema, registry=schema_registry(schema_path, findings), format_checker=FORMAT_CHECKER)
    documents = enumerate(document) if each_item and isinstance(document, list) else [(None, document)]
    for index, value in documents:
        try:
            errors = sorted(validator.iter_errors(value), key=lambda item: list(item.absolute_path))
        except jsonschema.exceptions._WrappedReferencingError as exc:
            findings.add("error", "SCHEMA_REFERENCE_UNRESOLVABLE", display_path, str(exc))
            continue
        for error in errors:
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


def load_neutrality_allowlist(scope_root):
    path = scope_root / "neutrality-allow.txt"
    if not path.is_file():
        return ()
    return tuple(line.strip().casefold() for line in path.read_text(encoding="utf-8").splitlines()
                 if line.strip() and not line.lstrip().startswith("#"))


def allowed_neutrality_words(path, scope_root):
    """Allowlists belong to a context, so the nearest ancestor wins."""
    current = path.parent
    while current == scope_root or scope_root in current.parents:
        allowlist = current / "neutrality-allow.txt"
        if allowlist.is_file():
            return load_neutrality_allowlist(current)
        if current == scope_root:
            break
        current = current.parent
    return ()


def add_neutrality_warnings(value, path, findings, words, allowed=()):
    if not words:
        return
    word_pattern = re.compile(r"\b(" + "|".join(re.escape(word) for word in words) + r")\b", re.IGNORECASE)
    for text in walk_strings(value):
        for match in word_pattern.finditer(text):
            if match.group(0).casefold() in allowed:
                continue
            findings.add("warning", "NEUTRALITY_WORD", path,
                         "stack-specific word '%s' requires review" % match.group(0))


def validate_fields(value, contract, field_name, path, location, findings, required=True):
    """Check a scenario object against a contract's top-level field declaration."""
    if not isinstance(value, dict) or contract is None:
        return
    declared = contract.get(field_name, {})
    if not isinstance(declared, dict):
        return
    for key in sorted(value):
        if key not in declared:
            findings.add("error", "UNKNOWN_%s_FIELD" % field_name.upper(), path,
                         "%s supplies undeclared %s field %s" % (location, field_name, key))
    if required:
        for key, definition in declared.items():
            if isinstance(definition, dict) and definition.get("required") and key not in value:
                findings.add("error", "MISSING_REQUIRED_%s" % field_name.upper(), path,
                             "%s omits required %s field %s" % (location, field_name, key))


def validate_capture_references(value, captures, path, location, findings):
    for text in walk_strings(value):
        for capture, output in CAPTURE_PATTERN.findall(text):
            if capture not in captures:
                findings.add("error", "UNKNOWN_CAPTURE", path,
                             "%s references capture %s before it is available" % (location, capture))
            elif output not in captures[capture]:
                findings.add("error", "UNKNOWN_CAPTURE_OUTPUT", path,
                             "%s references undeclared output %s.%s" % (location, capture, output))


def validate_supersession(records, kind, path_for, findings):
    """Validate one scope's replacement graph without treating retained history as duplicate."""
    by_id = {record.get("id"): record for record in records if isinstance(record, dict)}
    targets = Counter()
    graph = {}
    for identifier, record in by_id.items():
        target = record.get("supersedes")
        if not target:
            continue
        if target not in by_id:
            findings.add("error", "UNKNOWN_SUPERSEDED_%s" % kind, path_for(record),
                         "%s %s supersedes unknown %s" % (kind.lower(), identifier, target))
            continue
        expected_status = "deprecated" if kind == "RULE" else "superseded"
        if by_id[target].get("status") != expected_status:
            findings.add("error", "SUPERSEDED_%s_ACTIVE" % kind, path_for(record),
                         "superseded %s %s must retain %s status" %
                         (kind.lower(), target, expected_status))
        if record.get("status") not in {"deprecated", "superseded"}:
            targets[target] += 1
        graph[identifier] = target
    for target, count in targets.items():
        if count > 1:
            findings.add("error", "DUPLICATE_SUPERSESSION", path_for(by_id[target]),
                         "%s is superseded by %s active records" % (target, count))
    visiting, visited = set(), set()
    def visit(identifier):
        if identifier in visiting:
            findings.add("error", "SUPERSESSION_CYCLE", path_for(by_id[identifier]),
                         "%s supersession graph contains a cycle at %s" % (kind.lower(), identifier))
            return
        if identifier in visited:
            return
        visiting.add(identifier)
        if identifier in graph:
            visit(graph[identifier])
        visiting.remove(identifier)
        visited.add(identifier)
    for identifier in graph:
        visit(identifier)


def contract_language(contract):
    for name in ("summary", "semantics"):
        yield contract.get(name, "")
    for section in ("input", "output"):
        fields = contract.get(section, {})
        if isinstance(fields, dict):
            for field in fields.values():
                if isinstance(field, dict):
                    yield field.get("description", "")


def validate_references(scenarios, rules, contracts, decisions, reference_documents, findings):
    rule_by_id = {rule.get("id"): rule for rule, _ in rules if isinstance(rule, dict)}
    contract_by_id = {contract.get("id"): contract for contract, _ in contracts
                      if isinstance(contract, dict) and contract.get("id")}
    scenario_ids = {item.get("id") for item, _ in scenarios}

    for rule, path in rules:
        decision = rule.get("decision")
        decision_record = decisions.get(decision) if decision else None
        if decision and decision_record is None:
            findings.add("error", "UNKNOWN_DECISION", path,
                         "rule %s references unknown decision %s" % (rule.get("id"), decision))
        elif decision and decision_record.get("status") != "approved":
            findings.add("error", "DECISION_NOT_APPROVED", path,
                         "rule %s references decision %s with status %s" %
                         (rule.get("id"), decision, decision_record.get("status")))

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
        captures = {}
        setup_steps = given.get("steps", given.get("commands", [])) if isinstance(given, dict) else []
        for index, command in enumerate(setup_steps):
            if not isinstance(command, dict):
                continue
            if "advanceClock" in command:
                # The schema enforces duration syntax. Encountering it in the list preserves order.
                continue
            operation = require_contract(command.get("command"), "command", path,
                                         "given.steps[%s]" % index)
            validate_capture_references(command.get("input", {}), captures, path,
                                        "given.steps[%s].input" % index, findings)
            validate_fields(command.get("input", {}), operation, "input", path,
                            "given.steps[%s]" % index, findings)
            if command.get("expectError") and operation is not None:
                codes = {item.get("code") for item in operation.get("errors", [])
                         if isinstance(item, dict)}
                if command["expectError"] not in codes:
                    findings.add("error", "UNKNOWN_ERROR_CODE", path,
                                 "given.steps[%s].expectError %s is not declared by %s" %
                                 (index, command["expectError"], operation.get("id")))
            if command.get("as") and operation is not None:
                captures[command["as"]] = set(operation.get("output", {}))
        if isinstance(given.get("seed"), dict):
            seed = require_contract(given["seed"].get("contract"), "port", path, "given.seed")
            validate_capture_references(given["seed"].get("input", {}), captures, path,
                                        "given.seed.input", findings)
            validate_fields(given["seed"].get("input", {}), seed, "input", path,
                            "given.seed", findings)

        when = scenario.get("when", {})
        if not isinstance(when, dict):
            continue
        if "command" in when:
            operation = require_contract(when.get("command"), "command", path, "when")
        else:
            operation = require_contract(when.get("query"), "query", path, "when")
        validate_capture_references(when.get("input", {}), captures, path, "when.input", findings)
        validate_fields(when.get("input", {}), operation, "input", path, "when", findings)

        then = scenario.get("then", {})
        if not isinstance(then, dict):
            continue
        if then.get("error") and operation is not None:
            codes = {item.get("code") for item in operation.get("errors", []) if isinstance(item, dict)}
            if then["error"] not in codes:
                findings.add("error", "UNKNOWN_ERROR_CODE", path,
                             "then.error %s is not declared by %s" %
                             (then["error"], operation.get("id")))
        validate_capture_references(then.get("output", {}), captures, path, "then.output", findings)
        validate_fields(then.get("output", {}), operation, "output", path, "then", findings,
                        required=False)
        for event_ref in then.get("events", []):
            event_id, _, major = event_ref.rpartition("@")
            event = require_contract(event_id, "event", path, "then.events")
            if event is not None and event.get("version", "").split(".")[0] != major:
                findings.add("error", "EVENT_MAJOR_MISMATCH", path,
                             "%s does not match event contract %s" % (event_ref, event.get("version")))
        for index, observation in enumerate(then.get("observe", [])):
            if isinstance(observation, dict):
                query = require_contract(observation.get("query"), "query", path,
                                         "then.observe[%s]" % index)
                validate_capture_references(observation.get("input", {}), captures, path,
                                            "then.observe[%s].input" % index, findings)
                validate_capture_references(observation.get("expect", {}), captures, path,
                                            "then.observe[%s].expect" % index, findings)
                validate_fields(observation.get("input", {}), query, "input", path,
                                "then.observe[%s]" % index, findings)
                validate_fields(observation.get("expect", {}), query, "output", path,
                                "then.observe[%s]" % index, findings, required=False)

    exercised = {}
    for scenario, _ in scenarios:
        for rule_id in scenario.get("exercises", []):
            exercised.setdefault(rule_id, set()).add(scenario.get("verification"))
    for rule, path in rules:
        if (rule.get("status") == "approved" and rule.get("verification") == "automated" and
                "automated" not in exercised.get(rule.get("id"), set())):
            findings.add("warning", "AUTOMATED_RULE_UNCOVERED", path,
                         "approved automated rule %s has no scenario" % rule.get("id"))


def validate_scope(root, neutrality_words_path=None, scope_name="project", project_scope=False):
    findings = Findings()
    neutrality_words = load_neutrality_words(root, neutrality_words_path, findings)
    documents = {}
    for path in artifact_paths(root, project_scope):
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
    decisions = {}
    decision_records = []

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
                add_neutrality_warnings(document, display_path, findings, neutrality_words,
                                        allowed_neutrality_words(path, root))
        if isinstance(document, dict) and "assignmentId" in document and "objective" in document:
            validate_schema(document, assignment_schema, display_path, findings)
        if isinstance(document, dict) and "outcome" in document and "windowClosed" in document:
            validate_schema(document, handoff_schema, display_path, findings)
        if path.name == "decisions.yaml" and isinstance(document, list):
            decision_schema = schema_for(root, "decision.schema.json")
            validate_schema(document, decision_schema, display_path, findings)
            for entry in document:
                if isinstance(entry, dict) and isinstance(entry.get("id"), str):
                    if entry["id"] in decisions:
                        findings.add("error", "DUPLICATE_ID", display_path,
                                     "decision %s is declared more than once" % entry["id"])
                    decisions[entry["id"]] = entry
                    decision_records.append((entry, display_path))
        if is_semantic_artifact(path):
            reference_documents.append((document, display_path))
            if "registry" not in path.parts:
                for mapping in walk_mappings(document):
                    identifier = mapping.get("id")
                    if isinstance(identifier, str) and not identifier.startswith("${"):
                        add_id(ids, identifier, display_path)

    for identifier, paths in sorted(ids.items()):
        if len(paths) > 1:
            findings.add("error", "DUPLICATE_ID", paths[0],
                         "%s is declared more than once (%s)" %
                         (identifier, ", ".join(str(path) for path in paths)))
    for scenario, path in scenarios:
        add_neutrality_warnings(scenario, path, findings, neutrality_words,
                                allowed_neutrality_words(root / path, root))
    for contract, path in contracts:
        add_neutrality_warnings(list(contract_language(contract)), path, findings, neutrality_words,
                                allowed_neutrality_words(root / path, root))
    for glossary in root.rglob("glossary.md"):
        if excluded_from_scan(glossary, root, project_scope):
            continue
        add_neutrality_warnings(glossary.read_text(encoding="utf-8"), relative(glossary, root),
                                findings, neutrality_words, allowed_neutrality_words(glossary, root))
    rule_paths = {id(rule): path for rule, path in rules}
    decision_paths = {id(decision): path for decision, path in decision_records}
    validate_supersession([rule for rule, _ in rules], "RULE",
                          lambda rule: rule_paths[id(rule)], findings)
    validate_supersession([decision for decision, _ in decision_records], "DECISION",
                          lambda decision: decision_paths[id(decision)], findings)
    validate_references(scenarios, rules, contracts, decisions, reference_documents, findings)

    findings.items.sort(key=lambda item: (item["severity"], item["code"], item["path"], item["message"]))
    for item in findings.items:
        item["scope"] = scope_name
    return findings


def scoped_rules(root):
    found = {}
    paths = {}
    scratch = Findings()
    for path in artifact_paths(root, project_scope=True):
        document = load_document(path, scratch, root)
        if is_domain_rule(path, document):
            for rule in document if isinstance(document, list) else [document]:
                if isinstance(rule, dict) and rule.get("id"):
                    found[rule["id"]] = rule
                    paths[rule["id"]] = relative(path, root)
    return found, paths


def base_rules(root, base, findings):
    try:
        listed = subprocess.run(["git", "-C", str(root), "ls-tree", "-r", "--name-only", base,
                                 "--", "framework/contexts", "framework/constitution"],
                                text=True, capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        findings.add("error", "BASE_REF_UNAVAILABLE", root,
                     "cannot read git base %s: %s" % (base, getattr(exc, "stderr", str(exc)).strip()))
        return {}, {}
    found, paths = {}, {}
    for name in listed.stdout.splitlines():
        if not name.endswith((".yaml", ".yml")) or "rules" not in Path(name).parts:
            continue
        content = subprocess.run(["git", "-C", str(root), "show", "%s:%s" % (base, name)],
                                 text=True, capture_output=True)
        if content.returncode:
            continue
        try:
            document = yaml.safe_load(content.stdout)
        except yaml.YAMLError:
            continue
        if not is_domain_rule(Path(name), document):
            continue
        for rule in document if isinstance(document, list) else [document]:
            if isinstance(rule, dict) and rule.get("id"):
                found[rule["id"]] = rule
                paths[rule["id"]] = Path(name)
    return found, paths


def validate_base(root, base, findings):
    previous, previous_paths = base_rules(root, base, findings)
    current, current_paths = scoped_rules(root)
    for identifier, before in previous.items():
        after = current.get(identifier)
        path = current_paths.get(identifier, previous_paths[identifier])
        if after is None:
            findings.add("error", "RULE_ID_REMOVED", path,
                         "rule %s was removed since %s" % (identifier, base))
            continue
        if before.get("status") != "approved":
            continue
        if any(before.get(key) != after.get(key)
               for key in ("statement", "type", "verification", "decision", "decisionTable")):
            findings.add("error", "APPROVED_RULE_EDITED", path,
                         "approved rule %s changed its governed semantics since %s" % (identifier, base))
        if any(before.get(key) != after.get(key) for key in ("title", "rationale")):
            findings.add("warning", "APPROVED_RULE_TEXT_CHANGED", path,
                         "approved rule %s changed title or rationale since %s" % (identifier, base))


def validate(root, neutrality_words_path=None, base=None):
    combined = Findings()
    scopes = [(root, "project", True)]
    examples = root / "framework" / "examples"
    if examples.is_dir():
        scopes.extend((path, "example:" + path.name, False)
                      for path in sorted(examples.iterdir()) if path.is_dir())
    for scope_root, scope_name, project_scope in scopes:
        result = validate_scope(scope_root, neutrality_words_path, scope_name, project_scope)
        combined.items.extend(result.items)
    if base:
        base_findings = Findings()
        validate_base(root, base, base_findings)
        for item in base_findings.items:
            item["scope"] = "project"
        combined.items.extend(base_findings.items)
    combined.items.sort(key=lambda item: (item["scope"], item["severity"], item["code"], item["path"]))
    return combined


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=SCRIPT_ROOT,
                        help="repository root to validate (default: validator repository)")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit machine-readable findings")
    parser.add_argument("--neutrality-words", type=Path,
                        help="path to a newline-separated neutrality warning vocabulary")
    parser.add_argument("--base", help="git revision used to protect approved rule history")
    parser.add_argument("--strict", action="store_true",
                        help="return nonzero when warnings are present")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    findings = validate(root, args.neutrality_words, args.base)
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
            print("%s %s [%s] %s: %s" %
                  (item["severity"].upper(), item["code"], item["scope"], item["path"], item["message"]))
        print("Validation completed: %s error(s), %s warning(s)." %
              (result["errors"], result["warnings"]))
    return 1 if findings.errors or (args.strict and findings.warnings) else 0


if __name__ == "__main__":
    sys.exit(main())

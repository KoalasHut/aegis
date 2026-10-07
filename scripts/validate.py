#!/usr/bin/env python3
"""Validate Aegis structural artifacts and core-preservation traceability."""

import argparse
import datetime as dt
import hashlib
import fnmatch
import json
import re
import subprocess
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import jsonschema
import yaml
from referencing import Registry, Resource

try:
    from scripts.init import MAINTENANCE_LOG_HASHES
    from scripts.aegis_match import (
        SCALAR_TYPES, normalized_map_key_collisions, scalar_validation_error,
    )
except ModuleNotFoundError:  # Running this file directly outside the repository cwd.
    from init import MAINTENANCE_LOG_HASHES
    from aegis_match import SCALAR_TYPES, normalized_map_key_collisions, scalar_validation_error

try:
    from scripts.aegis_types import (
        TypeResolutionError, build_registry, is_poisoned_type, load_types_document,
        load_yaml_exact, parse_type_expression, poisoned_type, preflight_registry,
        resolve_type, structurally_equal, validate_type_tree,
    )
except ModuleNotFoundError:
    try:
        from aegis_types import (TypeResolutionError, build_registry, is_poisoned_type,
                                 load_types_document, load_yaml_exact, parse_type_expression,
                                 poisoned_type, preflight_registry, resolve_type,
                                 structurally_equal, validate_type_tree)
    except ModuleNotFoundError:  # Allows focused validator tests before type patch integration.
        TypeResolutionError = None
        build_registry = is_poisoned_type = load_types_document = load_yaml_exact = None
        parse_type_expression = poisoned_type = preflight_registry = None
        resolve_type = structurally_equal = validate_type_tree = None


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
DECISION_PATTERN = re.compile(r"\bD-[A-Z][A-Z0-9-]*-[0-9]{3}\b")
DEFAULT_NEUTRALITY_WORDS = SCRIPT_ROOT / "framework" / "language" / "neutrality-words.txt"
CAPTURE_NAME_PATTERN = re.compile(r"^[a-z][a-zA-Z0-9_]*$")
CAPTURE_PATH_PATTERN = re.compile(
    r"^([a-z][a-zA-Z0-9_]*)\.([A-Za-z][A-Za-z0-9_]*)(?:\.[A-Za-z0-9_]+)*$")
CANONICAL_AEGIS_ORIGIN = re.compile(
    r"^(?:git@github\.com:|https://github\.com/)KoalasHut/aegis(?:\.git)?/?$")


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


FINDING_PRIORITIES = {
    "SCHEMA_INVALID": 10,
    "UNKNOWN_DECISION": 20,
    "UNKNOWN_CAPTURE": 20,
    "MAINTENANCE_DECISION_CITED": 30,
    "CAPTURE_PATH_INVALID": 30,
    "INVALID_TYPE_DEFINITION": 30,
    "UNKNOWN_TYPE": 30,
    "TYPE_SHADOWED": 30,
    "UNSATISFIABLE_TYPE": 30,
    "MATCHER_IN_INPUT": 30,
    "INVALID_CAPTURE_REFERENCE": 30,
}


class Findings:
    def __init__(self, verbose=False):
        self.items = []
        self.suppressed = []
        self.verbose = verbose
        self._causes = {}

    def add(self, severity, code, path, message, cause=None, priority=None, field_path=None):
        """Add a finding, retaining only the highest-priority finding for one cause."""
        cause = cause or "%s:%s:%s" % (path, code, message)
        item = {
            "severity": severity,
            "code": code,
            "path": str(path),
            "message": message,
            "cause": cause,
        }
        if field_path is not None:
            item["fieldPath"] = field_path
        existing = self._causes.get(cause)
        item_priority = FINDING_PRIORITIES.get(code, 0) if priority is None else priority
        if existing is None:
            self.items.append(item)
            self._causes[cause] = (item, item_priority)
            return
        retained, retained_priority = existing
        if item_priority > retained_priority:
            self.items.remove(retained)
            retained["suppressed"] = True
            retained["suppressedBy"] = code
            self.suppressed.append(retained)
            self.items.append(item)
            self._causes[cause] = (item, item_priority)
        else:
            item["suppressed"] = True
            item["suppressedBy"] = retained["code"]
            self.suppressed.append(item)

    def extend(self, other):
        self.items.extend(other.items)
        self.suppressed.extend(other.suppressed)

    def visible_items(self):
        return self.items + self.suppressed if self.verbose else self.items

    @property
    def errors(self):
        return [item for item in self.items if item["severity"] == "error"]

    @property
    def warnings(self):
        return [item for item in self.items
                if item["severity"] == "warning" and not item.get("allowed")]


def add_internal_error(findings, path, operation, exc, field_path=None):
    """Report one unexpected operation failure at its owning artifact."""
    findings.add(
        "error", "INTERNAL_ERROR", path,
        "%s: %s: %s" % (operation, type(exc).__name__, str(exc)[:240]),
        cause="internal:%s:%s" % (path, operation), field_path=field_path,
    )


def relative(path, root):
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def load_document(path, findings, root):
    try:
        if path.suffix == ".json":
            return json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)
        return load_yaml_exact(path.read_text(encoding="utf-8"))
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
            cause = None
            finding_field_path = None
            absolute_parts = list(error.absolute_path)
            if "types" in absolute_parts:
                type_index = absolute_parts.index("types")
                if len(absolute_parts) > type_index + 1:
                    cause = "type-def:%s:%s" % (
                        display_path, absolute_parts[type_index + 1])
            if (cause is None and isinstance(error.instance, dict) and error.instance.get("as") and
                    error.instance.get("expectError")):
                cause = "capture:%s:%s" % (display_path, error.instance["as"])
            elif cause is None:
                pending = [error]
                indexed_capture = None
                capture_reference_location = None
                matcher_location = None
                nested_type_name = None
                while (pending and indexed_capture is None and
                       capture_reference_location is None and matcher_location is None and
                       nested_type_name is None):
                    detail = pending.pop()
                    pending.extend(detail.context)
                    detail_parts = list(detail.absolute_path)
                    if "types" in detail_parts:
                        type_index = detail_parts.index("types")
                        if len(detail_parts) > type_index + 1:
                            nested_type_name = detail_parts[type_index + 1]
                            continue
                    if (isinstance(detail.instance, dict) and
                            any(isinstance(key, str) and key.startswith("$")
                                for key in detail.instance)):
                        parts = list(detail.absolute_path)
                        if parts and isinstance(parts[0], int):
                            parts = parts[1:]
                        matcher_location = _location_from_parts(parts)
                        continue
                    if isinstance(detail.instance, str):
                        parts = _capture_parts(detail.instance)
                        if parts and any(segment.isdigit() for segment in parts[1:]):
                            indexed_capture = detail.instance
                        elif "${" in detail.instance:
                            whole_token = (detail.instance.startswith("${") and
                                           detail.instance.endswith("}"))
                            reference = detail.instance[2:-1] if whole_token else None
                            malformed = (not whole_token or
                                         ("." in reference and
                                          CAPTURE_PATH_PATTERN.fullmatch(reference) is None))
                            if malformed:
                                parts = list(detail.absolute_path)
                                if parts and isinstance(parts[0], int):
                                    parts = parts[1:]
                                capture_reference_location = _location_from_parts(parts)
                if nested_type_name is not None:
                    cause = "type-def:%s:%s" % (display_path, nested_type_name)
                elif indexed_capture is not None:
                    cause = "capture-path:%s:%s" % (display_path, indexed_capture)
                elif capture_reference_location is not None:
                    cause = "capture-reference:%s:%s" % (
                        display_path, _canonical_location(capture_reference_location))
                    finding_field_path = capture_reference_location
                elif matcher_location is not None:
                    cause = "matcher-input:%s:%s" % (
                        display_path, _canonical_location(matcher_location))
            findings.add("error", "SCHEMA_INVALID", display_path,
                         "%s: %s" % (suffix or "document", error.message), cause=cause,
                         field_path=finding_field_path)


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


def walk_strings_with_locations(value, location):
    """Yield every nested string with its mapping/list location."""
    if isinstance(value, str):
        yield value, location
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from walk_strings_with_locations(child, "%s.%s" % (location, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_strings_with_locations(child, "%s[%s]" % (location, index))


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


def is_capture_token(value):
    if not isinstance(value, str) or not value.startswith("${") or not value.endswith("}"):
        return False
    return CAPTURE_PATH_PATTERN.fullmatch(value[2:-1]) is not None


def is_matcher_object(value):
    return (isinstance(value, dict) and
            any(isinstance(key, str) and key.startswith("$") for key in value))


def _canonical_location(location):
    return re.sub(r"\[(\d+)\]", r".\1", location).lstrip(".")


def _location_from_parts(parts):
    location = ""
    for part in parts:
        if isinstance(part, int):
            location += "[%s]" % part
        else:
            location += ("." if location else "") + str(part)
    return location


def validate_concrete_input(value, path, location, findings):
    """Reject matcher-like mappings recursively in concrete scenario positions."""
    if isinstance(value, dict):
        if any(isinstance(key, str) and key.startswith("$") for key in value):
            findings.add(
                "error", "MATCHER_IN_INPUT", path,
                "%s contains a matcher; input positions require concrete values" % location,
                cause="matcher-input:%s:%s" % (path, _canonical_location(location)),
                field_path=location,
            )
            return
        for key, child in value.items():
            validate_concrete_input(child, path, "%s.%s" % (location, key), findings)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_concrete_input(child, path, "%s[%s]" % (location, index), findings)


def _type_kind(node):
    return node.get("kind") if isinstance(node, dict) else None


def _field_type(definition):
    if not isinstance(definition, dict):
        return definition
    return definition.get("type", definition)


def _field_required(record, name, definition):
    return (isinstance(definition, dict) and bool(definition.get("required"))) or (
        isinstance(record, dict) and name in record.get("required", ()))


def _resolve_node(node, registry):
    """Resolve one ref through aegis_types while leaving normalized nodes unchanged."""
    if _type_kind(node) == "ref" and resolve_type is not None:
        return resolve_type(node.get("name"), registry)
    return node


def _opaque_type_names(node, registry, seen=None):
    """Return opaque type names reachable from a normalized type expression."""
    seen = seen or set()
    kind = _type_kind(node)
    if kind == "opaque":
        return {node.get("name", "opaque")}
    if kind == "ref":
        name = node.get("name")
        if name in seen:
            return set()
        seen.add(name)
        return _opaque_type_names(_resolve_node(node, registry), registry, seen)
    if kind == "list":
        return _opaque_type_names(node.get("item"), registry, seen)
    if kind == "map":
        return _opaque_type_names(node.get("value"), registry, seen)
    if kind == "record":
        names = set()
        for definition in node.get("fields", {}).values():
            names.update(_opaque_type_names(_field_type(definition), registry, seen))
        return names
    return set()


def _capture_parts(value):
    if not isinstance(value, str) or not value.startswith("${") or not value.endswith("}"):
        return None
    return value[2:-1].split(".")


def resolve_capture_type(value, captures, findings, path, location):
    """Resolve a capture path through its source operation's normalized output tree."""
    parts = _capture_parts(value)
    if not parts or len(parts) < 2:
        return None
    capture = parts[0]
    source = captures.get(capture)
    missing_cause = "capture:%s:%s" % (path, capture)
    if source is None:
        findings.add("error", "UNKNOWN_CAPTURE", path,
                     "%s references capture %s before it is available" % (location, capture),
                     cause=missing_cause, field_path=location)
        return None
    registry = source.get("registry")
    node = source.get("output")
    for segment in parts[1:]:
        if segment.isdigit():
            findings.add("error", "CAPTURE_PATH_INVALID", path,
                         "%s uses forbidden list index %s" % (location, segment),
                         cause="capture-path:%s:%s" % (path, value), field_path=location)
            return None
        node = _resolve_node(node, registry)
        if _type_kind(node) == "opaque":
            return None
        if _type_kind(node) in {"list", "map"}:
            findings.add("error", "CAPTURE_PATH_INVALID", path,
                         "%s cannot traverse through a %s value" % (location, _type_kind(node)),
                         cause="capture-path:%s:%s" % (path, value), field_path=location)
            return None
        if _type_kind(node) != "record" or segment not in node.get("fields", {}):
            findings.add("error", "UNKNOWN_CAPTURE_FIELD", path,
                         "%s references unknown capture field %s" %
                         (location, ".".join(parts[1:])),
                         cause="capture-path:%s:%s" % (path, value), field_path=location)
            return None
        node = _field_type(node["fields"][segment])
    return _resolve_node(node, registry), registry


def validate_capture_type(value, target_type, target_registry, captures, path, location, findings):
    resolved = resolve_capture_type(value, captures, findings, path, location)
    if resolved is None:
        return
    source_type, source_registry = resolved
    if (is_poisoned_type and
            (is_poisoned_type(source_type, source_registry) or
             is_poisoned_type(target_type, target_registry))):
        return
    equal = structurally_equal(source_type, target_type, target_registry) if structurally_equal else (
        source_type == target_type and source_registry == target_registry)
    if not equal:
        findings.add("error", "CAPTURE_TYPE_MISMATCH", path,
                     "%s capture type does not equal the target field type" % location,
                     cause="capture-type:%s:%s" % (path, value), field_path=location)


def validate_typed_value(value, type_tree, registry, path, location, findings, *,
                         required=False, input_literal=False, captures=None):
    """Validate a scenario value recursively against one normalized Aegis type tree."""
    captures = captures or {}
    if is_capture_token(value):
        validate_capture_type(value, type_tree, registry, captures, path, location, findings)
        return
    node = _resolve_node(type_tree, registry)
    kind = _type_kind(node)
    if kind in {None, "opaque"}:
        return
    if is_matcher_object(value):
        if input_literal:
            return  # validate_concrete_input owns the single definition-site finding.
        list_matchers = {"$length", "$contains", "$unordered"}
        used = list_matchers.intersection(value)
        if used and kind != "list":
            findings.add("error", "MATCHER_TYPE_MISMATCH", path,
                         "%s uses %s on non-list type" % (location, sorted(used)[0]),
                         cause="typed:%s:%s:matcher" % (path, location), field_path=location)
            return
        if "$absent" in value and required:
            findings.add("error", "CONTRADICTORY_EXPECTATION", path,
                         "%s is required and cannot be absent" % location,
                         cause="typed:%s:%s:absence" % (path, location), field_path=location)
            return
        if kind == "list":
            members = value.get("$contains", value.get("$unordered", []))
            for member in members:
                validate_typed_value(member, node.get("item"), registry, path, location + "[]",
                                     findings, input_literal=input_literal, captures=captures)
        return
    if value is None:
        if required:
            code = "MISSING_REQUIRED_INPUT" if input_literal else "CONTRADICTORY_EXPECTATION"
            findings.add("error", code, path, "%s is required and cannot be null" % location,
                         cause="typed:%s:%s:absence" % (path, location), field_path=location)
        return
    if kind == "scalar":
        scalar = node.get("name")
        if scalar == "integer" and isinstance(value, int) and not isinstance(value, bool) and (
                abs(value) > 2 ** 53 - 1):
            findings.add("error", "UNSAFE_INTEGER", path,
                         "%s exceeds the portable integer range" % location,
                         cause="typed:%s:%s:value" % (path, location), field_path=location)
            return
        code = scalar_validation_error(value, scalar)
        if code:
            findings.add("error", code, path, "%s must be a valid %s literal" % (location, scalar),
                         cause="typed:%s:%s:value" % (path, location), field_path=location)
        return
    if kind == "enum":
        if not isinstance(value, str) or value not in node.get("values", ()):
            findings.add("error", "INVALID_ENUM_VALUE", path,
                         "%s is not one of %s" % (location, ", ".join(node.get("values", ()))),
                         cause="typed:%s:%s:value" % (path, location), field_path=location)
        return
    if kind == "list":
        if not isinstance(value, list):
            findings.add("error", "INVALID_TYPED_VALUE", path,
                         "%s must be a list" % location,
                         cause="typed:%s:%s:value" % (path, location), field_path=location)
            return
        for index, member in enumerate(value):
            validate_typed_value(member, node.get("item"), registry, path,
                                 "%s[%s]" % (location, index),
                                 findings, input_literal=input_literal, captures=captures)
        return
    if kind == "map":
        if not isinstance(value, dict):
            findings.add("error", "INVALID_TYPED_VALUE", path,
                         "%s must be a string-keyed map" % location,
                         cause="typed:%s:%s:value" % (path, location), field_path=location)
            return
        for collision in normalized_map_key_collisions(value):
            findings.add(
                "error", "DUPLICATE_MAP_KEY", path,
                "%s contains map keys equal after NFC: %s" %
                (location, ", ".join(repr(key) for key in collision["keys"])),
                cause="typed:%s:%s:duplicate-map-key:%s" %
                (path, location, collision["normalizedKey"]),
                field_path=location,
            )
        for key, member in value.items():
            validate_typed_value(member, node.get("value"), registry, path,
                                 "%s.%s" % (location, key), findings,
                                 input_literal=input_literal, captures=captures)
        return
    if kind == "record":
        if not isinstance(value, dict):
            findings.add("error", "INVALID_TYPED_VALUE", path,
                         "%s must be an object" % location,
                         cause="typed:%s:%s:value" % (path, location), field_path=location)
            return
        fields = node.get("fields", {})
        for key, member in value.items():
            if key not in fields:
                findings.add("error", "UNKNOWN_FIELD", path,
                             "%s.%s is not declared" % (location, key),
                             cause="typed:%s:%s.%s:field" % (path, location, key),
                             field_path="%s.%s" % (location, key))
                continue
            definition = fields[key]
            validate_typed_value(member, _field_type(definition), registry, path,
                                 "%s.%s" % (location, key), findings,
                                 required=_field_required(node, key, definition),
                                 input_literal=input_literal, captures=captures)
        if input_literal:
            for key, definition in fields.items():
                if _field_required(node, key, definition) and key not in value:
                    findings.add("error", "MISSING_REQUIRED_INPUT", path,
                                 "%s omits required field %s" % (location, key),
                                 cause="typed:%s:%s.%s:absence" % (path, location, key),
                                 field_path="%s.%s" % (location, key))


def contract_record(contract, field_name, registry, path, findings):
    """Resolve a contract input/output section into a synthetic record type."""
    fields = contract.get(field_name, {}) if isinstance(contract, dict) else {}
    if not isinstance(fields, dict):
        fields = {}  # Structural schema validation owns malformed contract sections.
    resolved = {}
    for name, definition in fields.items():
        if not isinstance(definition, dict):
            continue
        expression = definition.get("type")
        try:
            if expression in getattr(registry, "poisoned_expressions", ()):
                node = poisoned_type(str(expression), "UNKNOWN_TYPE")
            else:
                node = resolve_type(expression, registry) if resolve_type else None
        except Exception as exc:
            # Registry construction reports the contract defect once at its declaration.
            # Scenario traversal stays opaque so one root cause does not fan out by use site.
            node = {"kind": "opaque", "name": str(definition.get("type"))}
        resolved[name] = node
    return {"kind": "record", "fields": resolved,
            "required": [name for name, definition in fields.items()
                         if isinstance(definition, dict) and definition.get("required")]}


def validate_typed_literal(value, declared_type, path, location, findings):
    """Validate one top-level literal using the reference matcher's parser."""
    if declared_type not in SCALAR_TYPES or is_capture_token(value) or is_matcher_object(value):
        return
    code = scalar_validation_error(value, declared_type)
    if code:
        findings.add("error", code, path,
                     "%s must be a valid %s literal" % (location, declared_type))


def validate_fields(value, contract, field_name, path, location, findings, required=True,
                    registry=None, captures=None):
    """Check a scenario object recursively against a contract field declaration."""
    if not isinstance(value, dict) or contract is None:
        return
    if registry is not None:
        record = contract_record(contract, field_name, registry, path, findings)
        validate_typed_value(value, record, registry, path, location, findings,
                             input_literal=required, captures=captures)
        return
    declared = contract.get(field_name, {})
    if not isinstance(declared, dict):
        return
    for key in sorted(value):
        if key not in declared:
            findings.add("error", "UNKNOWN_%s_FIELD" % field_name.upper(), path,
                         "%s supplies undeclared %s field %s" % (location, field_name, key))
            continue
        definition = declared[key]
        if isinstance(definition, dict):
            validate_typed_literal(value[key], definition.get("type"), path,
                                   "%s.%s" % (location, key), findings)
    if required:
        for key, definition in declared.items():
            if isinstance(definition, dict) and definition.get("required") and key not in value:
                findings.add("error", "MISSING_REQUIRED_%s" % field_name.upper(), path,
                             "%s omits required %s field %s" % (location, field_name, key))


def validate_capture_references(value, captures, path, location, findings):
    for text, text_location in walk_strings_with_locations(value, location):
        if "${" not in text:
            continue
        if not (text.startswith("${") and text.endswith("}")):
            findings.add("error", "INVALID_CAPTURE_REFERENCE", path,
                         "%s contains an interpolated or malformed capture token" % text_location,
                         cause="capture-reference:%s:%s" %
                         (path, _canonical_location(text_location)),
                         field_path=text_location)
            continue
        reference = text[2:-1]
        if "." not in reference:
            findings.add("error", "BARE_CAPTURE_REFERENCE", path,
                         "%s references whole capture %s; use ${%s.field}" %
                         (text_location, reference, reference),
                         cause="capture-reference:%s:%s" %
                         (path, _canonical_location(text_location)),
                         field_path=text_location)
            continue
        match = CAPTURE_PATH_PATTERN.fullmatch(reference)
        if match is None:
            findings.add("error", "INVALID_CAPTURE_REFERENCE", path,
                         "%s contains invalid capture reference ${%s}" %
                         (text_location, reference),
                         cause="capture-reference:%s:%s" %
                         (path, _canonical_location(text_location)),
                         field_path=text_location)
            continue
        capture, output = match.group(1), match.group(2)
        if capture not in captures:
            findings.add("error", "UNKNOWN_CAPTURE", path,
                         "%s references capture %s before it is available" %
                         (text_location, capture),
                         cause="capture:%s:%s" % (path, capture), field_path=text_location)
        elif isinstance(captures[capture], set) and output not in captures[capture]:
            findings.add("error", "UNKNOWN_CAPTURE_OUTPUT", path,
                         "%s references undeclared output %s.%s" %
                         (text_location, capture, output), field_path=text_location)


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
        if ((kind == "DECISION" and record.get("status") == "approved") or
                (kind == "RULE" and record.get("status") != "deprecated")):
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


def contract_type_is_known(type_name, contract):
    if not isinstance(type_name, str):
        return True  # Structural schema validation owns missing or non-string names.
    base = type_name
    while base.endswith("[]"):
        base = base[:-2]
    return bool(base) and (base in SCALAR_TYPES or base in contract.get("types", {}))


def add_contract_type_warnings(contract, path, findings):
    for section in ("input", "output", "fields"):
        fields = contract.get(section, {})
        if not isinstance(fields, dict):
            continue
        for name, definition in fields.items():
            if not isinstance(definition, dict):
                continue
            type_name = definition.get("type")
            if not contract_type_is_known(type_name, contract):
                findings.add("warning", "UNKNOWN_SCALAR_TYPE", path,
                             "%s.%s declares unknown type %s; define it in types or use an "
                             "Aegis scalar" % (section, name, type_name))


def _add_preflight_errors(errors, path, findings):
    for error in errors:
        name = error.get("name") or "types"
        findings.add(
            "error", error.get("code", "INVALID_TYPE_DEFINITION"), path,
            error.get("message", "invalid type definition"),
            cause="type-def:%s:%s" % (path, name),
            field_path="types.%s" % name,
        )


def build_contract_registries(contracts, documents, root, findings, sibling_context_types=False):
    """Preflight scope definitions, then build silent poisoned contract registries."""
    if preflight_registry is None:
        return {}
    context_documents = {}
    context_paths = {}
    for source_path, document in documents.items():
        if source_path.name != "types.yaml" or "contexts" not in source_path.parts:
            continue
        index = source_path.parts.index("contexts")
        if len(source_path.parts) > index + 1:
            name = source_path.parts[index + 1]
            context_documents[name] = document
            context_paths[name] = relative(source_path, root)
    if sibling_context_types:
        sibling_path = root / "types.yaml"
        if sibling_path in documents:
            context_documents[None] = documents[sibling_path]
            context_paths[None] = relative(sibling_path, root)

    contexts = {}
    failed_contexts = set()
    for context_name, document in context_documents.items():
        try:
            registry, errors = preflight_registry(context_types=document)
            contexts[context_name] = registry
            _add_preflight_errors(errors, context_paths[context_name], findings)
        except Exception as exc:
            failed_contexts.add(context_name)
            add_internal_error(findings, context_paths[context_name], "context type registry",
                               exc, "types")

    registries = {}
    for contract, display_path in contracts:
        identifier = contract.get("id", "")
        context_name = identifier.split(".", 1)[0]
        selected_context = context_name if context_name in context_documents else None
        if selected_context in failed_contexts:
            continue
        try:
            registry, errors = preflight_registry(
                context_types=contexts.get(context_name, contexts.get(None)),
                local_types=contract.get("types", {}),
            )
            _add_preflight_errors(errors, display_path, findings)
            registries[identifier] = registry
        except Exception as exc:
            add_internal_error(findings, display_path, "contract type registry", exc, "types")
            continue
        for section in ("input", "output", "fields"):
            fields = contract.get(section, {})
            if not isinstance(fields, dict):
                continue  # Structural schema validation owns malformed section shapes.
            for field_name, definition in fields.items():
                if not isinstance(definition, dict):
                    continue
                expression = definition.get("type")
                try:
                    node = validate_type_tree(expression, registry)
                    if is_poisoned_type(node, registry):
                        registry.poisoned_expressions.add(expression)
                        continue
                except TypeResolutionError as exc:
                    code = getattr(exc, "code", "UNKNOWN_TYPE")
                    findings.add("error", code, display_path,
                                 "%s.%s: %s" % (section, field_name, exc),
                                 cause="type-field:%s:%s.%s" %
                                 (display_path, section, field_name),
                                 field_path="%s.%s" % (section, field_name))
                    registry.poisoned_expressions.add(expression)
                    continue
                except Exception as exc:
                    add_internal_error(findings, display_path, "contract field type resolution",
                                       exc, "%s.%s" % (section, field_name))
                    continue
                try:
                    opaque_names = _opaque_type_names(node, registry)
                except TypeResolutionError as exc:
                    code = getattr(exc, "code", "UNKNOWN_TYPE")
                    findings.add("error", code, display_path,
                                 "%s.%s: %s" % (section, field_name, exc),
                                 cause="type-field:%s:%s.%s" %
                                 (display_path, section, field_name),
                                 field_path="%s.%s" % (section, field_name))
                    registry.poisoned_expressions.add(expression)
                    continue
                except Exception as exc:
                    add_internal_error(findings, display_path, "contract field type traversal",
                                       exc, "%s.%s" % (section, field_name))
                    continue
                for opaque_name in sorted(opaque_names):
                    findings.add("warning", "OPAQUE_TYPE", display_path,
                                 "%s.%s uses opaque type %s" %
                                 (section, field_name, opaque_name),
                                 cause="type:%s:%s" % (display_path, opaque_name))
    for context_name, document in context_documents.items():
        if context_name in failed_contexts:
            continue
        definitions = document.get("types", {}) if isinstance(document, dict) else {}
        if not isinstance(definitions, dict):
            definitions = {}  # Structural schema validation owns malformed type envelopes.
        poisoned_names = contexts[context_name].poisoned_names
        used = set()

        def add_expression(expression):
            if not isinstance(expression, str):
                return
            try:
                node = parse_type_expression(expression)
            except Exception:
                return
            pending = [node]
            while pending:
                current = pending.pop()
                kind = _type_kind(current)
                if kind == "ref":
                    name = current.get("name")
                    if name in definitions and name not in used:
                        used.add(name)
                        definition = definitions[name]
                        if isinstance(definition, dict):
                            fields = definition.get("fields", {})
                            if not isinstance(fields, dict):
                                continue
                            for field in fields.values():
                                if isinstance(field, dict):
                                    add_expression(field.get("type"))
                    continue
                if kind == "list":
                    pending.append(current.get("item"))
                elif kind == "map":
                    pending.append(current.get("value"))

        for contract, _ in contracts:
            if (context_name is not None and
                    contract.get("id", "").split(".", 1)[0] != context_name):
                continue
            for section in ("input", "output", "fields"):
                fields = contract.get(section, {})
                if not isinstance(fields, dict):
                    continue
                for definition in fields.values():
                    if isinstance(definition, dict):
                        add_expression(definition.get("type"))
        for name in sorted(set(definitions) - used - poisoned_names):
            findings.add("warning", "UNUSED_TYPE", context_paths[context_name],
                         "context type %s is not used by a contract" % name,
                         cause="unused-type:%s:%s" % (context_paths[context_name], name))
    return registries


def validate_references(scenarios, rules, contracts, decisions, reference_documents, findings,
                        project_scope=False, contract_registries=None):
    rule_by_id = {rule.get("id"): rule for rule, _ in rules if isinstance(rule, dict)}
    contract_by_id = {contract.get("id"): contract for contract, _ in contracts
                      if isinstance(contract, dict) and contract.get("id")}
    contract_registries = contract_registries or {}

    def registry_for(contract):
        return contract_registries.get(contract.get("id")) if isinstance(contract, dict) else None
    scenario_ids = {item.get("id") for item, _ in scenarios}

    def validate_rule_reference(rule, path):
        decision = rule.get("decision")
        if project_scope and isinstance(decision, str) and decision.startswith("D-AEGIS-"):
            cause = "decision-citation:%s:%s" % (path, decision)
            findings.add("error", "MAINTENANCE_DECISION_CITED", path,
                         "rule %s cites maintenance decision %s; run scripts/init.py and "
                         "record a product decision instead" % (rule.get("id"), decision),
                         cause=cause)
        decision_record = decisions.get(decision) if decision else None
        if decision and decision_record is None:
            findings.add("error", "UNKNOWN_DECISION", path,
                         "rule %s references unknown decision %s" % (rule.get("id"), decision),
                         cause="decision-citation:%s:%s" % (path, decision))
        elif (decision and decision_record.get("status") != "approved" and
              rule.get("status") != "deprecated"):
            findings.add("error", "DECISION_NOT_APPROVED", path,
                         "rule %s references decision %s with status %s" %
                         (rule.get("id"), decision, decision_record.get("status")))

    for rule, path in rules:
        try:
            validate_rule_reference(rule, path)
        except Exception as exc:
            identifier = rule.get("id") if isinstance(rule, dict) else None
            field_path = "rule.%s" % identifier if identifier else "rule"
            add_internal_error(findings, path, "rule references", exc, field_path)

    def validate_reference_document(document, path):
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

    for document, path in reference_documents:
        try:
            validate_reference_document(document, path)
        except Exception as exc:
            add_internal_error(findings, path, "reference document", exc, "references")

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

    def validate_scenario_reference(scenario, path):
        exercises = scenario.get("exercises", [])
        if not isinstance(exercises, list):
            exercises = []  # Structural schema validation owns malformed exercise shapes.
        for rule_id in exercises:
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
        capture_steps = {}
        setup_steps = given.get("steps", given.get("commands", [])) if isinstance(given, dict) else []
        for index, command in enumerate(setup_steps):
            if not isinstance(command, dict):
                continue
            if "advanceClock" in command:
                # The schema enforces duration syntax. Encountering it in the list preserves order.
                continue
            operation = require_contract(command.get("command"), "command", path,
                                         "given.steps[%s]" % index)
            validate_concrete_input(command.get("input", {}), path,
                                    "given.steps[%s].input" % index, findings)
            validate_capture_references(command.get("input", {}), captures, path,
                                        "given.steps[%s].input" % index, findings)
            validate_fields(command.get("input", {}), operation, "input", path,
                            "given.steps[%s].input" % index, findings,
                            registry=registry_for(operation), captures=captures)
            if command.get("expectError") and operation is not None:
                codes = {item.get("code") for item in operation.get("errors", [])
                         if isinstance(item, dict)}
                if command["expectError"] not in codes:
                    findings.add("error", "UNKNOWN_ERROR_CODE", path,
                                 "given.steps[%s].expectError %s is not declared by %s" %
                                 (index, command["expectError"], operation.get("id")))
            capture = command.get("as")
            if capture:
                capture_is_valid = bool(CAPTURE_NAME_PATTERN.fullmatch(str(capture)))
                if not capture_is_valid:
                    findings.add("error", "SCHEMA_INVALID", path,
                                 "given.steps[%s].as must match ^[a-z][a-zA-Z0-9_]*$" % index)
                if capture in capture_steps:
                    findings.add("error", "DUPLICATE_CAPTURE", path,
                                 "capture %s is declared by both given.steps[%s] and "
                                 "given.steps[%s]" % (capture, capture_steps[capture], index))
                else:
                    capture_steps[capture] = index
                if command.get("expectError"):
                    findings.add("error", "SCHEMA_INVALID", path,
                                 "given.steps[%s]: a step with expectError cannot declare as" % index,
                                 cause="capture:%s:%s" % (path, capture))
                elif operation is not None and capture_is_valid and capture not in captures:
                    registry = registry_for(operation)
                    captures[capture] = ({"output": contract_record(operation, "output", registry,
                                                                      path, findings),
                                          "registry": registry}
                                         if registry is not None else set(operation.get("output", {})))
        if isinstance(given.get("seed"), dict):
            seed = require_contract(given["seed"].get("contract"), "port", path, "given.seed")
            validate_concrete_input(given["seed"].get("input", {}), path,
                                    "given.seed.input", findings)
            validate_capture_references(given["seed"].get("input", {}), captures, path,
                                        "given.seed.input", findings)
            validate_fields(given["seed"].get("input", {}), seed, "input", path,
                            "given.seed.input", findings, registry=registry_for(seed),
                            captures=captures)

        when = scenario.get("when", {})
        if not isinstance(when, dict):
            return
        if "command" in when:
            operation = require_contract(when.get("command"), "command", path, "when")
        else:
            operation = require_contract(when.get("query"), "query", path, "when")
        validate_concrete_input(when.get("input", {}), path, "when.input", findings)
        validate_capture_references(when.get("input", {}), captures, path, "when.input", findings)
        validate_fields(when.get("input", {}), operation, "input", path, "when.input",
                        findings, registry=registry_for(operation), captures=captures)

        then = scenario.get("then", {})
        if not isinstance(then, dict):
            return
        if then.get("error") and operation is not None:
            codes = {item.get("code") for item in operation.get("errors", []) if isinstance(item, dict)}
            if then["error"] not in codes:
                findings.add("error", "UNKNOWN_ERROR_CODE", path,
                             "then.error %s is not declared by %s" %
                             (then["error"], operation.get("id")))
        validate_capture_references(then.get("output", {}), captures, path, "then.output", findings)
        validate_fields(then.get("output", {}), operation, "output", path, "then.output",
                        findings, required=False, registry=registry_for(operation),
                        captures=captures)
        for event_assertion in then.get("events", []):
            event_ref = (event_assertion.get("event")
                         if isinstance(event_assertion, dict) else event_assertion)
            if not isinstance(event_ref, str):
                continue
            event_id, _, major = event_ref.rpartition("@")
            event = require_contract(event_id, "event", path, "then.events")
            if event is not None and event.get("version", "").split(".")[0] != major:
                findings.add("error", "EVENT_MAJOR_MISMATCH", path,
                             "%s does not match event contract %s" % (event_ref, event.get("version")))
            if isinstance(event_assertion, dict):
                payload = event_assertion.get("input", {})
                validate_capture_references(payload, captures, path, "then.events.input", findings)
                validate_fields(payload, event, "input", path, "then.events.input", findings,
                                required=False, registry=registry_for(event), captures=captures)
        for index, observation in enumerate(then.get("observe", [])):
            if isinstance(observation, dict):
                query = require_contract(observation.get("query"), "query", path,
                                         "then.observe[%s]" % index)
                validate_concrete_input(observation.get("input", {}), path,
                                        "then.observe[%s].input" % index, findings)
                validate_capture_references(observation.get("input", {}), captures, path,
                                            "then.observe[%s].input" % index, findings)
                validate_capture_references(observation.get("expect", {}), captures, path,
                                            "then.observe[%s].expect" % index, findings)
                validate_fields(observation.get("input", {}), query, "input", path,
                                "then.observe[%s].input" % index, findings,
                                registry=registry_for(query), captures=captures)
                validate_fields(observation.get("expect", {}), query, "output", path,
                                "then.observe[%s].expect" % index, findings, required=False,
                                registry=registry_for(query), captures=captures)

    for scenario, path in scenarios:
        try:
            validate_scenario_reference(scenario, path)
        except Exception as exc:
            identifier = scenario.get("id") if isinstance(scenario, dict) else None
            field_path = "scenario.%s" % identifier if identifier else "scenario"
            add_internal_error(findings, path, "scenario references", exc, field_path)

    exercised = {}
    for scenario, _ in scenarios:
        exercises = scenario.get("exercises", [])
        if not isinstance(exercises, list):
            continue  # Already reported by structural schema validation.
        for rule_id in exercises:
            exercised.setdefault(rule_id, set()).add(scenario.get("verification"))
    for rule, path in rules:
        if (rule.get("status") == "approved" and rule.get("verification") == "automated" and
                "automated" not in exercised.get(rule.get("id"), set())):
            findings.add("warning", "AUTOMATED_RULE_UNCOVERED", path,
                         "approved automated rule %s has no scenario" % rule.get("id"))


LOCAL_TIME_TERMS = re.compile(r"\b(today|this week|local time|local date)\b", re.IGNORECASE)
ZONE_BASIS_TERMS = re.compile(
    r"\b(UTC|time ?zone|timezone|user(?:'s)? zone|store(?:'s)? zone|[A-Za-z_]+/[A-Za-z_]+)\b",
    re.IGNORECASE,
)
LOCALE_TAG_PATTERN = re.compile(r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$")


def validate_environment_rules(scenarios, rules, findings):
    for scenario, path in scenarios:
        given = scenario.get("given", {})
        timezone = given.get("timezone") if isinstance(given, dict) else None
        if timezone is not None:
            try:
                ZoneInfo(timezone)
            except (ZoneInfoNotFoundError, ValueError, TypeError):
                findings.add("error", "INVALID_TIMEZONE", path,
                             "given.timezone is not an available IANA time-zone name",
                             cause="timezone:%s:%s" % (path, timezone))
    for rule, path in rules:
        statement = rule.get("statement", "")
        if (rule.get("type") in {"policy", "calculation"} and
                LOCAL_TIME_TERMS.search(statement) and not ZONE_BASIS_TERMS.search(statement)):
            findings.add("warning", "CPR-007-VIOLATION", path,
                         "rule %s uses local-time language without naming its zone basis" %
                         rule.get("id"), cause="cpr-007:%s:%s" % (path, rule.get("id")))
        collation = rule.get("collation")
        if (isinstance(collation, dict) and
                LOCALE_TAG_PATTERN.fullmatch(str(collation.get("locale", ""))) and
                rule.get("verification") == "automated"):
            findings.add("warning", "LOCALE_COLLATION_REQUIRES_MANUAL", path,
                         "rule %s uses locale collation and requires manual verification" %
                         rule.get("id"), cause="collation:%s:%s" % (path, rule.get("id")))


def apply_validation_allowances(allowance_documents, decisions, findings, repo_prefix=Path()):
    seen = set()
    for document, path in allowance_documents:
        if not isinstance(document, list):
            continue
        for index, allowance in enumerate(document):
            if not isinstance(allowance, dict):
                continue
            identity = (allowance.get("code"), allowance.get("path"))
            if identity in seen:
                findings.add("error", "DUPLICATE_ALLOWANCE", path,
                             "allowance[%s] duplicates code/path %s" % (index, identity),
                             cause="allowance:%s:%s" % (path, index))
                continue
            seen.add(identity)
            path_glob = allowance.get("path", "")
            if (path_glob in {"*", "**", "**/*"} or path_glob.startswith("/") or
                    ".." in Path(path_glob).parts):
                findings.add("error", "OVERBROAD_ALLOWANCE", path,
                             "allowance[%s] must use a bounded repo-relative path glob" % index,
                             cause="allowance:%s:%s" % (path, index))
                continue
            decision = decisions.get(allowance.get("decision"))
            if decision is None or decision.get("status") != "approved":
                findings.add("error", "ALLOWANCE_DECISION_NOT_APPROVED", path,
                             "allowance[%s] requires an approved decision" % index,
                             cause="allowance:%s:%s" % (path, index))
                continue
            matched = 0
            for finding in list(findings.items):
                repo_path = str(repo_prefix / finding.get("path", ""))
                if (finding.get("severity") == "warning" and
                        finding.get("code") == allowance.get("code") and
                        fnmatch.fnmatch(repo_path, path_glob)):
                    finding["allowed"] = True
                    finding["allowance"] = {
                        "decision": allowance["decision"],
                        "reason": allowance["reason"],
                        "path": str(path),
                    }
                    matched += 1
            if not matched:
                findings.add("warning", "STALE_ALLOWANCE", path,
                             "allowance[%s] matches no active warning" % index,
                             cause="allowance:%s:%s" % (path, index))


def validate_scope(root, neutrality_words_path=None, scope_name="project", project_scope=False,
                   verbose_findings=False, repo_prefix=Path()):
    findings = Findings(verbose=verbose_findings)
    neutrality_words = load_neutrality_words(root, neutrality_words_path, findings)
    documents = {}
    for path in artifact_paths(root, project_scope):
        try:
            document = load_document(path, findings, root)
        except Exception as exc:  # Safety net around custom loaders and future formats.
            findings.add("error", "INTERNAL_ERROR", relative(path, root),
                         "%s: %s" % (type(exc).__name__, str(exc)[:240]),
                         cause="internal:%s" % relative(path, root))
            continue
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
    allowance_schema = schema_for(root, "validation-allow.schema.json")
    types_schema = schema_for(root, "types.schema.json")

    ids = {}
    scenarios = []
    rules = []
    contracts = []
    reference_documents = []
    decisions = {}
    decision_records = []
    allowance_documents = []

    def process_document(path, document):
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
        if path.name == "validation-allow.yaml":
            validate_schema(document, allowance_schema, display_path, findings)
            allowance_documents.append((document, display_path))
        if (path.name == "types.yaml" and
                ("contexts" in path.parts or (not project_scope and path.parent == root))):
            validate_schema(document, types_schema, display_path, findings)
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

    for path, document in documents.items():
        try:
            process_document(path, document)
        except Exception as exc:  # Safety net: malformed artifacts must not abort the scope.
            findings.add(
                "error", "INTERNAL_ERROR", relative(path, root),
                "%s: %s" % (type(exc).__name__, str(exc)[:240]),
                cause="internal:%s" % relative(path, root),
            )

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
        if build_registry is None:
            add_contract_type_warnings(contract, path, findings)
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
    try:
        contract_registries = build_contract_registries(
            contracts, documents, root, findings, sibling_context_types=not project_scope)
    except Exception as exc:
        findings.add("error", "INTERNAL_ERROR", Path("types.yaml"),
                     "%s: %s" % (type(exc).__name__, str(exc)[:240]),
                     cause="internal:registry")
        contract_registries = {}
    for phase_name, phase in (
        ("references", lambda: validate_references(
            scenarios, rules, contracts, decisions, reference_documents, findings,
            project_scope, contract_registries)),
        ("environment", lambda: validate_environment_rules(scenarios, rules, findings)),
        ("allowances", lambda: apply_validation_allowances(
            allowance_documents, decisions, findings, repo_prefix)),
    ):
        try:
            phase()
        except Exception as exc:
            findings.add("error", "INTERNAL_ERROR", Path("."),
                         "%s: %s" % (type(exc).__name__, str(exc)[:240]),
                         cause="internal:%s" % phase_name)

    if project_scope and not (root / "project.json").is_file() and not is_aegis_template(root):
        findings.add("warning", "PROJECT_NOT_INITIALIZED", Path("project.json"),
                     "project.json is missing; run scripts/init.py before adding product artifacts")

    findings.items.sort(key=lambda item: (item["severity"], item["code"], item["path"], item["message"]))
    findings.suppressed.sort(
        key=lambda item: (item["severity"], item["code"], item["path"], item["message"]))
    for item in findings.items + findings.suppressed:
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


def scoped_decisions(root):
    found = {}
    paths = {}
    scratch = Findings()
    for path in artifact_paths(root, project_scope=True):
        if path.name != "decisions.yaml":
            continue
        document = load_document(path, scratch, root)
        for decision in document if isinstance(document, list) else []:
            if isinstance(decision, dict) and decision.get("id"):
                found[decision["id"]] = decision
                paths[decision["id"]] = relative(path, root)
    return found, paths


def is_aegis_template(root):
    """Recognize only canonical Aegis with the maintenance logs known by init.py."""
    for name, expected in MAINTENANCE_LOG_HASHES.items():
        path = root / name
        if not path.is_file():
            return False
        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            return False
        if actual != expected:
            return False
    try:
        origin = subprocess.run(
            ["git", "-C", str(root), "remote", "get-url", "origin"],
            text=True, capture_output=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return False
    return CANONICAL_AEGIS_ORIGIN.fullmatch(origin) is not None


def git_revision_documents(root, base, findings):
    """Load scoped YAML once from a git revision for all history protections."""
    try:
        listed = subprocess.run(["git", "-C", str(root), "ls-tree", "-r", "--name-only", base,
                                 "--"],
                                text=True, capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        findings.add("error", "BASE_REF_UNAVAILABLE", root,
                     "cannot read git base %s: %s" % (base, getattr(exc, "stderr", str(exc)).strip()))
        return []
    documents = []
    for name in listed.stdout.splitlines():
        path = Path(name)
        if path.suffix not in {".yaml", ".yml"} or excluded_from_scan(root / path, root, True):
            continue
        content = subprocess.run(["git", "-C", str(root), "show", "%s:%s" % (base, name)],
                                 text=True, capture_output=True)
        if content.returncode:
            findings.add("error", "BASE_ARTIFACT_UNAVAILABLE", path,
                         "cannot read %s from %s: %s" %
                         (path, base, content.stderr.strip()))
            continue
        try:
            document = load_yaml_exact(content.stdout)
        except yaml.YAMLError as exc:
            findings.add("error", "BASE_PARSE_ERROR", path,
                         "cannot parse %s from %s: %s" % (path, base, exc))
            continue
        documents.append((path, document))
    return documents


def rules_from_documents(documents, findings=None):
    found, paths = {}, {}
    for path, document in documents:
        if not is_domain_rule(path, document):
            continue
        for rule in document if isinstance(document, list) else [document]:
            if isinstance(rule, dict) and rule.get("id"):
                identifier = rule["id"]
                if identifier in found and findings is not None:
                    findings.add("error", "DUPLICATE_ID", path,
                                 "base revision declares rule %s more than once (%s, %s)" %
                                 (identifier, paths[identifier], path))
                    continue
                found[identifier] = rule
                paths[identifier] = path
    return found, paths


def decisions_from_documents(documents, findings=None):
    found, paths = {}, {}
    for path, document in documents:
        if path.name != "decisions.yaml":
            continue
        for decision in document if isinstance(document, list) else []:
            if isinstance(decision, dict) and decision.get("id"):
                identifier = decision["id"]
                if identifier in found and findings is not None:
                    findings.add("error", "DUPLICATE_ID", path,
                                 "base revision declares decision %s more than once (%s, %s)" %
                                 (identifier, paths[identifier], path))
                    continue
                found[identifier] = decision
                paths[identifier] = path
    return found, paths


def validate_base(root, base, findings):
    base_documents = git_revision_documents(root, base, findings)
    previous, previous_paths = rules_from_documents(base_documents, findings)
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

    previous_decisions, previous_decision_paths = decisions_from_documents(base_documents, findings)
    current_decisions, current_decision_paths = scoped_decisions(root)
    for identifier, before in previous_decisions.items():
        after = current_decisions.get(identifier)
        path = current_decision_paths.get(identifier, previous_decision_paths[identifier])
        if after is None:
            findings.add("error", "DECISION_ID_REMOVED", path,
                         "decision %s was removed since %s" % (identifier, base))
            continue
        if before.get("status") != "approved":
            continue
        governed_changed = any(before.get(key) != after.get(key)
                               for key in ("question", "decision", "approver", "date", "source",
                                           "supersedes"))
        status = after.get("status")
        if governed_changed or status not in {"approved", "superseded"}:
            findings.add("error", "APPROVED_DECISION_EDITED", path,
                         "approved decision %s changed governed fields since %s" %
                         (identifier, base))
        if any(before.get(key) != after.get(key) for key in ("title", "affects")):
            findings.add("warning", "APPROVED_DECISION_TEXT_CHANGED", path,
                         "approved decision %s changed title or affects since %s" %
                         (identifier, base))
        if status == "superseded":
            replacements = [decision for decision in current_decisions.values()
                            if decision.get("status") == "approved" and
                            decision.get("supersedes") == identifier]
            if not replacements:
                findings.add("error", "SUPERSESSION_MISSING", path,
                             "decision %s became superseded without an approved replacement" %
                             identifier)


def validate(root, neutrality_words_path=None, base=None, verbose_findings=False):
    combined = Findings(verbose=verbose_findings)
    scopes = [(root, "project", True)]
    examples = root / "framework" / "examples"
    if examples.is_dir():
        scopes.extend((path, "example:" + path.name, False)
                      for path in sorted(examples.iterdir()) if path.is_dir())
    for scope_root, scope_name, project_scope in scopes:
        prefix = relative(scope_root, root)
        prefix = Path() if prefix == Path(".") else prefix
        try:
            result = validate_scope(scope_root, neutrality_words_path, scope_name, project_scope,
                                    verbose_findings, prefix)
        except Exception as exc:
            result = Findings(verbose=verbose_findings)
            result.add("error", "INTERNAL_ERROR", relative(scope_root, root),
                       "%s: %s" % (type(exc).__name__, str(exc)[:240]),
                       cause="internal:scope:%s" % scope_name)
            for item in result.items:
                item["scope"] = scope_name
        combined.extend(result)
    if base:
        base_findings = Findings()
        validate_base(root, base, base_findings)
        for item in base_findings.items:
            item["scope"] = "project"
        combined.extend(base_findings)
    combined.items.sort(key=lambda item: (item["scope"], item["severity"], item["code"], item["path"]))
    combined.suppressed.sort(
        key=lambda item: (item["scope"], item["severity"], item["code"], item["path"]))
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
    parser.add_argument("--verbose-findings", action="store_true",
                        help="include lower-priority findings suppressed by the same root cause")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    findings = validate(root, args.neutrality_words, args.base, args.verbose_findings)
    visible = findings.visible_items()
    result = {
        "root": str(root),
        "errors": len(findings.errors),
        "warnings": len(findings.warnings),
        "findings": visible,
    }
    if args.as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for item in visible:
            suppression = " (suppressed by %s)" % item["suppressedBy"] if item.get("suppressed") else ""
            print("%s %s [%s] %s: %s%s" %
                  (item["severity"].upper(), item["code"], item["scope"], item["path"],
                   item["message"], suppression))
        print("Validation completed: %s error(s), %s warning(s)." %
              (result["errors"], result["warnings"]))
    return 1 if findings.errors or (args.strict and findings.warnings) else 0


if __name__ == "__main__":
    sys.exit(main())

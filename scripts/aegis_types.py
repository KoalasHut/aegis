#!/usr/bin/env python3
"""Shared normalized type model for Aegis contracts and scenario matching."""

from collections.abc import Mapping, Sequence
from decimal import Decimal
import re
import unicodedata

import yaml


SCALAR_TYPES = frozenset({
    "string", "boolean", "integer", "number", "decimal",
    "date", "datetime", "duration", "id",
})

_NAME = r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)*"
_TYPE_NAME = re.compile(rf"^{_NAME}$")
_LOCAL_TYPE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_QUALIFIED_TYPE_NAME = re.compile(
    r"^[A-Za-z][A-Za-z0-9_]*\.[A-Za-z][A-Za-z0-9_]*$"
)


class _ExactSafeLoader(yaml.SafeLoader):
    """Safe YAML loader that retains the exact value of floating lexemes."""


def _construct_exact_decimal(loader, node):
    lexeme = loader.construct_scalar(node).replace("_", "")
    lowered = lexeme.casefold()
    special = {
        ".inf": "Infinity", "+.inf": "Infinity", "-.inf": "-Infinity",
        ".nan": "NaN",
    }
    if lowered in special:
        return Decimal(special[lowered])
    if ":" in lexeme:
        # Preserve PyYAML's YAML 1.1 sexagesimal interpretation for documents
        # outside the Aegis numeric profile, while still avoiding a binary float.
        digits = lexeme.split(":")
        total = Decimal(0)
        for piece in digits:
            total = total * 60 + Decimal(piece)
        return total
    return Decimal(lexeme)


_ExactSafeLoader.add_constructor("tag:yaml.org,2002:float", _construct_exact_decimal)


def load_yaml_exact(text):
    """Safely load YAML while representing every floating lexeme as Decimal."""
    return yaml.load(text, Loader=_ExactSafeLoader)


class TypeResolutionError(ValueError):
    """A type declaration cannot be normalized or resolved."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class TypeRegistry(dict):
    """Resolved declarations plus poison metadata used by validator preflight."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.poisoned_names = set()
        self.poisoned_expressions = set()


def poisoned_type(name, code="INVALID_TYPE_DEFINITION"):
    """Return an opaque sentinel which silences checks beneath one broken type."""
    return {"kind": "opaque", "name": name, "poisoned": True, "poisonCode": code}


def parse_type_expression(expression):
    """Parse the closed Aegis type-expression grammar into a normalized node."""
    if not isinstance(expression, str) or not expression:
        raise TypeResolutionError("INVALID_TYPE_EXPRESSION", "type expression must be a non-empty string")
    list_depth = 0
    while expression.endswith("[]"):
        list_depth += 1
        expression = expression[:-2]
    if expression.startswith("map<") and expression.endswith(">"):
        inner = expression[4:-1]
        if not inner:
            raise TypeResolutionError("INVALID_TYPE_EXPRESSION", "map type requires a value type")
        node = {"kind": "map", "value": parse_type_expression(inner)}
    elif _TYPE_NAME.fullmatch(expression):
        name = expression
        node = ({"kind": "scalar", "name": name}
                if name in SCALAR_TYPES else {"kind": "ref", "name": name})
    else:
        raise TypeResolutionError("INVALID_TYPE_EXPRESSION", f"invalid type expression: {expression!r}")
    for _ in range(list_depth):
        node = {"kind": "list", "item": node}
    return node


def normalize_type_definition(name, definition):
    """Normalize one named type definition without eagerly expanding references."""
    if isinstance(definition, str):
        return {"kind": "opaque", "name": name, "description": definition}
    if not isinstance(definition, Mapping):
        raise TypeResolutionError("INVALID_TYPE_DEFINITION", f"type {name!r} must be prose or an object")
    description = definition.get("description")
    if not isinstance(description, str) or not description:
        raise TypeResolutionError("INVALID_TYPE_DEFINITION", f"type {name!r} requires a description")
    if "enum" in definition:
        values = definition["enum"]
        normalized = ([unicodedata.normalize("NFC", value) for value in values]
                      if isinstance(values, list) and all(isinstance(value, str) for value in values)
                      else [])
        if (not isinstance(values, list) or not values
                or any(not isinstance(value, str) or not value for value in values)
                or len(normalized) != len(set(normalized))):
            raise TypeResolutionError(
                "INVALID_TYPE_DEFINITION",
                f"enum {name!r} requires non-empty strings unique after NFC normalization",
            )
        return {"kind": "enum", "name": name, "values": tuple(values), "description": description}
    if "fields" in definition:
        raw_fields = definition["fields"]
        if not isinstance(raw_fields, Mapping):
            raise TypeResolutionError("INVALID_TYPE_DEFINITION", f"record {name!r} requires fields")
        fields = {}
        required = []
        for field_name, field in raw_fields.items():
            if not isinstance(field_name, str) or not field_name or not isinstance(field, Mapping):
                raise TypeResolutionError("INVALID_TYPE_DEFINITION", f"invalid field in record {name!r}")
            if set(field) - {"type", "required", "description"} or "type" not in field:
                raise TypeResolutionError("INVALID_TYPE_DEFINITION", f"invalid declaration for {name}.{field_name}")
            fields[field_name] = parse_type_expression(field["type"])
            if field.get("required", False):
                required.append(field_name)
        return {
            "kind": "record", "name": name, "fields": fields,
            "required": tuple(required), "description": description,
        }
    raise TypeResolutionError("INVALID_TYPE_DEFINITION", f"type {name!r} must declare enum or fields")


def build_registry(context_types=None, local_types=None, imports=None):
    """Build a lazy registry from local/context declarations and resolved imports.

    Local/context shadowing is rejected instead of silently overriding. Imports
    are a low-level integration seam: a mapping of pre-resolved qualified names
    (``context.Type``) to definitions or normalized nodes. Aegis 0.2.3 does not
    define a manifest syntax that constructs this mapping.
    """
    context_types = _declarations(context_types)
    local_types = local_types or {}
    imports = imports or {}
    if not isinstance(local_types, Mapping) or not isinstance(imports, Mapping):
        raise TypeResolutionError("INVALID_TYPE_DEFINITION", "type declarations must be objects")
    for name in (*context_types, *local_types):
        if not isinstance(name, str) or not _LOCAL_TYPE_NAME.fullmatch(name):
            raise TypeResolutionError("INVALID_TYPE_NAME", f"invalid local/context type name: {name!r}")
    for name in imports:
        if not isinstance(name, str) or not _QUALIFIED_TYPE_NAME.fullmatch(name):
            raise TypeResolutionError("INVALID_TYPE_NAME", f"imported type name must be qualified: {name!r}")
    shadowed = set(context_types) & set(local_types)
    if shadowed:
        names = ", ".join(sorted(shadowed))
        raise TypeResolutionError("TYPE_SHADOWED", f"contract-local types shadow context types: {names}")
    collisions = (set(context_types) | set(local_types)) & set(imports)
    if collisions:
        names = ", ".join(sorted(collisions))
        raise TypeResolutionError("TYPE_SHADOWED", f"imported types collide with local types: {names}")
    registry = TypeRegistry()
    for declarations in (context_types, local_types, imports):
        for name, definition in declarations.items():
            if (isinstance(definition, Mapping) and definition.get("kind") in
                    {"scalar", "enum", "record", "list", "map", "ref", "opaque"}):
                registry[name] = definition
            else:
                registry[name] = normalize_type_definition(name, definition)
    return registry


def preflight_registry(context_types=None, local_types=None, imports=None):
    """Build a registry without failing fast and poison invalid definitions.

    Returns ``(registry, errors)``. Each error is a mapping with ``name``,
    ``source``, ``code`` and ``message``. References to a poisoned declaration
    are valid but opaque, preventing one definition error from fanning out at
    every contract and scenario use site.
    """
    errors = []
    sources = []
    for source, document in (("context", context_types), ("local", local_types),
                             ("import", imports)):
        try:
            declarations = _declarations(document)
        except TypeResolutionError as exc:
            errors.append({"name": None, "source": source, "code": exc.code,
                           "message": str(exc)})
            declarations = {}
        sources.append((source, declarations))

    registry = TypeRegistry()
    owners = {}
    for source, declarations in sources:
        if not isinstance(declarations, Mapping):
            continue
        for name, definition in declarations.items():
            name_pattern = _QUALIFIED_TYPE_NAME if source == "import" else _LOCAL_TYPE_NAME
            if not isinstance(name, str) or not name_pattern.fullmatch(name):
                message = (f"imported type name must be qualified: {name!r}"
                           if source == "import" else
                           f"invalid local/context type name: {name!r}")
                errors.append({"name": str(name), "source": source,
                               "code": "INVALID_TYPE_NAME", "message": message})
                continue
            if name in registry:
                errors.append({
                    "name": name, "source": source, "code": "TYPE_SHADOWED",
                    "message": f"{source} type {name!r} collides with {owners[name]} type",
                })
                registry[name] = poisoned_type(name, "TYPE_SHADOWED")
                registry.poisoned_names.add(name)
                continue
            try:
                node = (definition if isinstance(definition, Mapping) and definition.get("kind") in
                        {"scalar", "enum", "record", "list", "map", "ref", "opaque"}
                        else normalize_type_definition(name, definition))
            except TypeResolutionError as exc:
                errors.append({"name": name, "source": source, "code": exc.code,
                               "message": str(exc)})
                node = poisoned_type(name, exc.code)
                registry.poisoned_names.add(name)
            if isinstance(node, Mapping) and node.get("poisoned"):
                registry.poisoned_names.add(name)
            registry[name] = node
            owners[name] = source

    for name in tuple(registry):
        if name in registry.poisoned_names:
            continue
        try:
            validate_type_tree(registry[name], registry)
        except TypeResolutionError as exc:
            errors.append({"name": name, "source": owners.get(name, "context"),
                           "code": exc.code, "message": str(exc)})
            registry[name] = poisoned_type(name, exc.code)
            registry.poisoned_names.add(name)

    # Dependent declarations inherit poison silently. Compute that closure
    # before satisfiability so one root resolution error cannot fan out into
    # UNSATISFIABLE_TYPE or UNUSED_TYPE findings.
    for name, node in registry.items():
        if name not in registry.poisoned_names and _node_reaches_poison(node, registry, {name}):
            registry.poisoned_names.add(name)

    satisfiable = {name for name, node in registry.items()
                   if name in registry.poisoned_names or node.get("kind") != "record"}
    changed = True
    while changed:
        changed = False
        for name, node in registry.items():
            if name in satisfiable or node.get("kind") != "record":
                continue
            if all(_node_is_satisfiable(node["fields"][field], registry, satisfiable, set())
                   for field in node.get("required", ())):
                satisfiable.add(name)
                changed = True
    for name, node in tuple(registry.items()):
        if node.get("kind") == "record" and name not in satisfiable:
            errors.append({"name": name, "source": owners.get(name, "context"),
                           "code": "UNSATISFIABLE_TYPE",
                           "message": f"record type {name!r} has no finite value"})
            registry[name] = poisoned_type(name, "UNSATISFIABLE_TYPE")
            registry.poisoned_names.add(name)
    return registry, tuple(errors)


def validate_type_tree(declared_type, registry=None):
    """Validate every reference reachable from one type expression."""
    registry = registry or {}
    node = _normalize_hint(declared_type)
    _validate_node_references(node, registry, set())
    return node


def is_poisoned_type(declared_type, registry=None):
    """Whether a type expression reaches a poisoned declaration."""
    registry = registry or {}
    return _node_reaches_poison(_normalize_hint(declared_type), registry, set())


def _validate_node_references(node, registry, active):
    if node is None:
        return
    kind = node.get("kind")
    if kind == "ref":
        name = node.get("name")
        if name not in registry:
            raise TypeResolutionError("UNKNOWN_TYPE", f"unknown type: {name}")
        if name in active or registry[name].get("poisoned"):
            return
        _validate_node_references(registry[name], registry, active | {name})
    elif kind == "record":
        for child in node.get("fields", {}).values():
            _validate_node_references(child, registry, active)
    elif kind == "list":
        _validate_node_references(node.get("item"), registry, active)
    elif kind == "map":
        _validate_node_references(node.get("value"), registry, active)


def _node_reaches_poison(node, registry, active):
    if node is None:
        return False
    if node.get("poisoned"):
        return True
    kind = node.get("kind")
    if kind == "ref":
        name = node.get("name")
        if name not in registry or name in active:
            return False
        return _node_reaches_poison(registry[name], registry, active | {name})
    if kind == "record":
        return any(_node_reaches_poison(child, registry, active)
                   for child in node.get("fields", {}).values())
    if kind == "list":
        return _node_reaches_poison(node.get("item"), registry, active)
    if kind == "map":
        return _node_reaches_poison(node.get("value"), registry, active)
    return False


def _node_is_satisfiable(node, registry, satisfiable, active):
    kind = node.get("kind")
    if kind in {"scalar", "enum", "opaque", "list", "map"}:
        return True
    if kind == "ref":
        return node.get("name") in satisfiable
    if kind == "record":
        marker = id(node)
        if marker in active:
            return False
        return all(_node_is_satisfiable(node["fields"][field], registry, satisfiable,
                                        active | {marker})
                   for field in node.get("required", ()))
    return True


def load_types_document(document):
    """Normalize the ``types`` mapping from a context ``types.yaml`` document."""
    declarations = _declarations(document)
    for name in declarations:
        if not isinstance(name, str) or not _LOCAL_TYPE_NAME.fullmatch(name):
            raise TypeResolutionError("INVALID_TYPE_NAME", f"invalid context type name: {name!r}")
    return {name: normalize_type_definition(name, definition)
            for name, definition in declarations.items()}


def _declarations(document):
    if document is None:
        return {}
    if not isinstance(document, Mapping):
        raise TypeResolutionError("INVALID_TYPE_DEFINITION", "type declarations must be an object")
    if set(document) == {"types"}:
        document = document["types"]
        if not isinstance(document, Mapping):
            raise TypeResolutionError("INVALID_TYPE_DEFINITION", "types must be an object")
    return document


def resolve_type(declared_type, registry=None):
    """Normalize a type hint and expand one reference through *registry*.

    The function also accepts the 0.2.2 direct-helper forms: a mapping of child
    field hints and a one-element sequence for list items.
    """
    registry = registry or {}
    node = _normalize_hint(declared_type)
    seen = set()
    while isinstance(node, Mapping) and node.get("kind") == "ref":
        name = node["name"]
        if name in seen:
            return node
        seen.add(name)
        if name not in registry:
            raise TypeResolutionError("UNKNOWN_TYPE", f"unknown type: {name}")
        node = registry[name]
    return node


def _normalize_hint(declared_type):
    if declared_type is None:
        return None
    if isinstance(declared_type, str):
        return parse_type_expression(declared_type)
    if isinstance(declared_type, Mapping):
        if declared_type.get("kind") in {"scalar", "enum", "record", "list", "map", "ref", "opaque"}:
            return declared_type
        return {
            "kind": "record", "fields": {
                key: _normalize_hint(value) for key, value in declared_type.items()
            }, "required": (),
        }
    if (isinstance(declared_type, Sequence)
            and not isinstance(declared_type, (str, bytes)) and len(declared_type) == 1):
        return {"kind": "list", "item": _normalize_hint(declared_type[0])}
    raise TypeResolutionError("INVALID_TYPE_EXPRESSION", f"unsupported type hint: {declared_type!r}")


def structurally_equal(left, right, registry=None):
    """Compare resolved type identity without infinitely expanding recursion."""
    registry = registry or {}
    return _type_key(_normalize_hint(left), registry, {}) == _type_key(_normalize_hint(right), registry, {})


def _type_key(node, registry, active):
    if node is None:
        return None
    kind = node["kind"]
    if kind == "ref":
        name = node["name"]
        if name in active:
            return ("cycle", active[name])
        if name not in registry:
            raise TypeResolutionError("UNKNOWN_TYPE", f"unknown type: {name}")
        nested = dict(active)
        nested[name] = len(active)
        return _type_key(registry[name], registry, nested)
    if kind == "scalar":
        return (kind, node["name"])
    if kind == "enum":
        return (kind, tuple(node["values"]))
    if kind == "opaque":
        return (kind, node.get("name"))
    if kind == "list":
        return (kind, _type_key(node["item"], registry, active))
    if kind == "map":
        return (kind, _type_key(node["value"], registry, active))
    return (kind, tuple(sorted(
        (name, _type_key(child, registry, active)) for name, child in node["fields"].items()
    )), tuple(sorted(node.get("required", ()))))

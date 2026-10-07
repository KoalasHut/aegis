#!/usr/bin/env python3
"""Pure reference implementation of Aegis scenario value matching.

The language specifications are authoritative.  This module exists so runner
authors can exercise the specified recursive, typed, and one-to-one behavior.
"""

import datetime as dt
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from collections.abc import Mapping, Sequence

try:
    from scripts.aegis_types import SCALAR_TYPES, resolve_type
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from aegis_types import SCALAR_TYPES, resolve_type


class MatchError(ValueError):
    """The expected value uses matcher syntax outside the closed vocabulary."""


_MISSING = object()
_MATCHERS = {"$contains", "$unordered", "$length", "$absent", "$any"}
MAX_SAFE_INTEGER = 2 ** 53 - 1
_AEGIS_DATETIME = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})[Tt](\d{2}):(\d{2})"
    r"(?::(\d{2})(?:\.(\d+))?)?([Zz]|[+-]\d{2}:\d{2})$"
)
_LOCAL_DATETIME = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})[Tt](\d{2}):(\d{2})"
    r"(?::(\d{2})(?:\.(\d+))?)?$"
)
_DURATION = re.compile(
    r"^P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)W)?(?:(\d+)D)?"
    r"(?:T(?:(\d+)H)?(?:(\d+)M)?"
    r"(?:(\d+(?:\.\d+)?)S)?)?$"
)


def normalized_map_key_collisions(value, path=()):
    """Return location-bearing NFC-equivalent key groups from one map.

    The helper is public so validators and runners can turn the same condition
    into their layer-specific ``DUPLICATE_MAP_KEY`` or contract finding.
    ``path`` identifies the map in its typed value tree. Non-string keys are
    ignored here and rejected cleanly by :func:`match`; JSON keys are strings.
    """
    if not isinstance(value, Mapping):
        return ()
    groups = {}
    for key in value:
        if isinstance(key, str):
            groups.setdefault(unicodedata.normalize("NFC", key), []).append(key)
    return tuple({"path": tuple(path), "normalizedKey": normalized, "keys": tuple(keys)}
                 for normalized, keys in groups.items() if len(keys) > 1)


def typed_map_key_collisions(value, type_tree, registry=None, path=()):
    """Return every map-key collision in a complete resolved typed value."""
    node = resolve_type(type_tree, registry or {}) if type_tree is not None else None
    if not isinstance(node, Mapping):
        return ()
    kind = node.get("kind")
    collisions = []
    if kind == "map" and isinstance(value, Mapping):
        collisions.extend(normalized_map_key_collisions(value, path))
        for key, child in value.items():
            collisions.extend(typed_map_key_collisions(
                child, node["value"], registry, tuple(path) + (key,)))
    elif kind == "record" and isinstance(value, Mapping):
        for key, child_type in node.get("fields", {}).items():
            if key in value:
                collisions.extend(typed_map_key_collisions(
                    value[key], child_type, registry, tuple(path) + (key,)))
    elif kind == "list" and isinstance(value, list):
        for index, child in enumerate(value):
            collisions.extend(typed_map_key_collisions(
                child, node["item"], registry, tuple(path) + (index,)))
    return tuple(collisions)


def _has_non_string_map_key(value, type_tree, registry):
    node = resolve_type(type_tree, registry) if type_tree is not None else None
    if not isinstance(node, Mapping):
        return False
    kind = node.get("kind")
    if kind == "map" and isinstance(value, Mapping):
        return (any(not isinstance(key, str) for key in value)
                or any(_has_non_string_map_key(child, node["value"], registry)
                       for child in value.values()))
    if kind == "record" and isinstance(value, Mapping):
        return any(key in value and _has_non_string_map_key(
            value[key], child_type, registry)
                   for key, child_type in node.get("fields", {}).items())
    if kind == "list" and isinstance(value, list):
        return any(_has_non_string_map_key(child, node["item"], registry)
                   for child in value)
    return False


def match(expected, actual, type_tree=None, registry=None, **compatibility):
    """Return whether *actual* satisfies an Aegis expected value.

    ``type_tree`` is a normalized node from :mod:`aegis_types`. For 0.2.2
    callers, scalar strings, child mappings, one-element list hints, and the
    deprecated ``declared_type=`` keyword remain accepted.
    """
    if "declared_type" in compatibility:
        if type_tree is not None or len(compatibility) != 1:
            raise TypeError("declared_type cannot be combined with type_tree")
        type_tree = compatibility["declared_type"]
    elif compatibility:
        raise TypeError("unexpected keyword arguments: " + ", ".join(compatibility))
    registry = registry or {}
    node = resolve_type(type_tree, registry) if type_tree is not None else None
    if (typed_map_key_collisions(expected, node, registry)
            or typed_map_key_collisions(actual, node, registry)
            or _has_non_string_map_key(expected, node, registry)
            or _has_non_string_map_key(actual, node, registry)):
        return False
    return _match(expected, actual, node, registry)


def scalar_validation_error(value, declared_type):
    """Return an Aegis diagnostic code when a typed scalar literal is invalid.

    ``None`` means the literal is valid. Unknown type names also return
    ``None`` because the validator reports those separately as
    ``UNKNOWN_SCALAR_TYPE`` during the 0.2.x migration.
    """
    if declared_type not in SCALAR_TYPES:
        return None
    if declared_type == "datetime":
        if _parse_datetime(value) is not None:
            return None
        if (isinstance(value, str) and _LOCAL_DATETIME.fullmatch(value)
                and _parse_datetime(value + "Z") is not None):
            return "DATETIME_WITHOUT_OFFSET"
        return "INVALID_TYPED_VALUE"
    if declared_type == "date":
        valid = _parse_date(value) is not None
    elif declared_type == "duration":
        valid = _parse_duration(value) is not None
    elif declared_type in {"integer", "number", "decimal"}:
        number = _finite_decimal(value, allow_string=declared_type == "decimal")
        valid = (number is not None
                 and (declared_type != "integer" or number == number.to_integral_value()))
        if valid and declared_type == "integer" and abs(number) > MAX_SAFE_INTEGER:
            return "UNSAFE_INTEGER"
    elif declared_type in {"string", "id"}:
        valid = isinstance(value, str)
    else:
        valid = isinstance(value, bool)
    return None if valid else "INVALID_TYPED_VALUE"


def _match(expected, actual, declared_type, registry):
    node = resolve_type(declared_type, registry) if declared_type is not None else None
    if node is not None and node["kind"] == "opaque":
        return actual is not _MISSING and type(expected) is type(actual) and expected == actual
    if expected is None:
        return actual is _MISSING or actual is None

    matcher = _matcher_name(expected)
    if matcher is not None:
        return _match_explicit(matcher, expected[matcher], actual, node, registry)

    if isinstance(expected, Mapping):
        if actual is _MISSING or not isinstance(actual, Mapping):
            return False
        if node is not None and node.get("kind") == "map":
            actual_by_key = {
                unicodedata.normalize("NFC", key): value
                for key, value in actual.items()
            }
            for key, value in expected.items():
                normalized = unicodedata.normalize("NFC", key)
                candidate = actual_by_key.get(normalized, _MISSING)
                if not _match(value, candidate, node["value"], registry):
                    return False
            return True
        for key, value in expected.items():
            candidate = actual[key] if key in actual else _MISSING
            if not _match(value, candidate, _child_type(node, key), registry):
                return False
        return True

    if isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            return False
        item_type = _child_type(node)
        return all(_match(left, right, item_type, registry)
                   for left, right in zip(expected, actual))

    if actual is _MISSING:
        return False
    return _match_scalar(expected, actual, node)


def _matcher_name(expected):
    if not isinstance(expected, Mapping):
        return None
    matcher_keys = [key for key in expected if isinstance(key, str) and key.startswith("$")]
    if not matcher_keys:
        return None
    if len(expected) != 1 or len(matcher_keys) != 1 or matcher_keys[0] not in _MATCHERS:
        raise MatchError("unknown or combined matcher keys: %s" % ", ".join(matcher_keys))
    return matcher_keys[0]


def _match_explicit(name, operand, actual, declared_type, registry):
    if name == "$absent":
        return operand is True and (actual is _MISSING or actual is None)
    if name == "$any":
        return operand is True and actual is not _MISSING and actual is not None
    if not isinstance(actual, list):
        return False
    if name == "$length":
        return isinstance(operand, int) and not isinstance(operand, bool) and len(actual) == operand
    if not isinstance(operand, list):
        return False
    if name == "$unordered" and len(operand) != len(actual):
        return False
    if name == "$contains" and len(operand) > len(actual):
        return False
    return _has_one_to_one_assignment(operand, actual, _child_type(declared_type), registry)


def _has_one_to_one_assignment(expected, actual, item_type, registry):
    """Find a complete expected-to-actual assignment by augmenting paths."""
    edges = [
        [actual_index for actual_index, candidate in enumerate(actual)
         if _match(value, candidate, item_type, registry)]
        for value in expected
    ]
    assigned_expected = [-1] * len(actual)

    def augment(expected_index, seen):
        for actual_index in edges[expected_index]:
            if actual_index in seen:
                continue
            seen.add(actual_index)
            previous = assigned_expected[actual_index]
            if previous == -1 or augment(previous, seen):
                assigned_expected[actual_index] = expected_index
                return True
        return False

    return all(augment(index, set()) for index in range(len(expected)))


def _child_type(declared_type, key=None):
    if not isinstance(declared_type, Mapping):
        return None
    if key is not None and declared_type.get("kind") == "record":
        return declared_type.get("fields", {}).get(key)
    if key is None and declared_type.get("kind") == "list":
        return declared_type["item"]
    return None


def _match_scalar(expected, actual, declared_type):
    kind = declared_type.get("kind") if isinstance(declared_type, Mapping) else None
    name = declared_type.get("name") if kind == "scalar" else None
    if kind == "enum":
        return (isinstance(expected, str) and isinstance(actual, str)
                and expected in declared_type["values"]
                and actual in declared_type["values"] and expected == actual)
    if name == "datetime":
        return _match_datetime(expected, actual)
    if name == "date":
        return _match_date(expected, actual)
    if name == "duration":
        return _match_duration(expected, actual)
    if name in {"integer", "number", "decimal"}:
        return _match_number(expected, actual, name)
    if name == "string":
        return (isinstance(expected, str) and isinstance(actual, str)
                and unicodedata.normalize("NFC", expected) == unicodedata.normalize("NFC", actual))
    if name == "id":
        return isinstance(expected, str) and isinstance(actual, str) and expected == actual
    if name == "boolean":
        return isinstance(expected, bool) and isinstance(actual, bool) and expected == actual
    return type(expected) is type(actual) and expected == actual


def _finite_decimal(value, allow_string=False):
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal, str)):
        return None
    if isinstance(value, str) and (not allow_string or not re.fullmatch(
            r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", value)):
        return None
    try:
        number = Decimal(str(value))
        return number if number.is_finite() else None
    except InvalidOperation:  # pragma: no cover - guarded by accepted runtime types/forms
        return None


def _match_number(expected, actual, declared_type):
    if (scalar_validation_error(expected, declared_type) is not None
            or scalar_validation_error(actual, declared_type) is not None):
        return False
    allow_string = declared_type == "decimal"
    return (_finite_decimal(expected, allow_string=allow_string)
            == _finite_decimal(actual, allow_string=allow_string))


def _parse_datetime(value):
    if not isinstance(value, str):
        return None
    found = _AEGIS_DATETIME.fullmatch(value)
    if not found:
        return None
    year, month, day, hour, minute, second, fraction, offset = found.groups()
    second = second or "0"
    try:
        date = dt.date(int(year), int(month), int(day))
        if int(hour) > 23 or int(minute) > 59 or int(second) > 59:
            return None
        if offset.casefold() == "z":
            offset_seconds = 0
        else:
            sign = 1 if offset[0] == "+" else -1
            offset_hours, offset_minutes = (int(piece) for piece in offset[1:].split(":"))
            if offset_hours > 23 or offset_minutes > 59:
                return None
            offset_seconds = sign * (offset_hours * 3600 + offset_minutes * 60)
    except ValueError:
        return None
    days = (date - dt.date(1970, 1, 1)).days
    whole = days * 86400 + int(hour) * 3600 + int(minute) * 60 + int(second) - offset_seconds
    fractional = Decimal("0." + fraction) if fraction else Decimal(0)
    if fraction:
        expected_unit = Decimal(1).scaleb(-len(fraction))
    elif found.group(6) is not None:
        expected_unit = Decimal(1)
    else:
        expected_unit = Decimal(60)
    return Decimal(whole) + fractional, expected_unit


def _match_datetime(expected, actual):
    expected_value = _parse_datetime(expected)
    actual_value = _parse_datetime(actual)
    if expected_value is None or actual_value is None:
        return False
    expected_instant, unit = expected_value
    actual_instant, _ = actual_value
    return expected_instant <= actual_instant < expected_instant + unit


def _match_date(expected, actual):
    left = _parse_date(expected)
    right = _parse_date(actual)
    return left is not None and left == right


def _parse_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def _parse_duration(value):
    if not isinstance(value, str):
        return None
    found = _DURATION.fullmatch(value)
    if not found or not any(piece is not None for piece in found.groups()):
        return None
    years, months, weeks, days, hours, minutes, seconds = found.groups()
    if "T" in value and not any(piece is not None for piece in (hours, minutes, seconds)):
        return None
    if weeks is not None and any(piece is not None
                                 for piece in (years, months, days, hours, minutes, seconds)):
        return None
    total = (Decimal(weeks or 0) * Decimal(604800)
             + Decimal(days or 0) * Decimal(86400)
             + Decimal(hours or 0) * Decimal(3600)
             + Decimal(minutes or 0) * Decimal(60)
             + Decimal(seconds or 0))
    return Decimal(years or 0), Decimal(months or 0), total


def _match_duration(expected, actual):
    left = _parse_duration(expected)
    right = _parse_duration(actual)
    if left is None or right is None:
        return False
    return left == right

#!/usr/bin/env python3
"""Pure reference implementation of Aegis scenario value matching.

The language specifications are authoritative.  This module exists so runner
authors can exercise the specified recursive, typed, and one-to-one behavior.
"""

import datetime as dt
import re
from decimal import Decimal, InvalidOperation
from collections.abc import Mapping, Sequence


class MatchError(ValueError):
    """The expected value uses matcher syntax outside the closed vocabulary."""


_MISSING = object()
_MATCHERS = {"$contains", "$unordered", "$length", "$absent", "$any"}
SCALAR_TYPES = frozenset({
    "string", "boolean", "integer", "number", "decimal",
    "date", "datetime", "duration", "id",
})
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


def match(expected, actual, declared_type=None):
    """Return whether *actual* satisfies an Aegis expected value.

    ``declared_type`` is normally one scalar type string for the top-level
    contract field.  A mapping or one-element sequence can also describe child
    types when this helper is used directly; the 0.2.x validator deliberately
    limits contract validation to top-level fields.
    """
    return _match(expected, actual, declared_type)


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
        number = _finite_decimal(value)
        valid = (number is not None
                 and (declared_type != "integer" or number == number.to_integral_value()))
    elif declared_type in {"string", "id"}:
        valid = isinstance(value, str)
    else:
        valid = isinstance(value, bool)
    return None if valid else "INVALID_TYPED_VALUE"


def _match(expected, actual, declared_type):
    matcher = _matcher_name(expected)
    if matcher is not None:
        return _match_explicit(matcher, expected[matcher], actual, declared_type)

    if isinstance(expected, Mapping):
        if actual is _MISSING or not isinstance(actual, Mapping):
            return False
        for key, value in expected.items():
            candidate = actual[key] if key in actual else _MISSING
            if not _match(value, candidate, _child_type(declared_type, key)):
                return False
        return True

    if isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            return False
        item_type = _child_type(declared_type)
        return all(_match(left, right, item_type)
                   for left, right in zip(expected, actual))

    if actual is _MISSING:
        return False
    return _match_scalar(expected, actual, declared_type)


def _matcher_name(expected):
    if not isinstance(expected, Mapping):
        return None
    matcher_keys = [key for key in expected if isinstance(key, str) and key.startswith("$")]
    if not matcher_keys:
        return None
    if len(expected) != 1 or len(matcher_keys) != 1 or matcher_keys[0] not in _MATCHERS:
        raise MatchError("unknown or combined matcher keys: %s" % ", ".join(matcher_keys))
    return matcher_keys[0]


def _match_explicit(name, operand, actual, declared_type):
    if name == "$absent":
        return operand is True and actual is _MISSING
    if name == "$any":
        return operand is True and actual is not _MISSING
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
    return _has_one_to_one_assignment(operand, actual, _child_type(declared_type))


def _has_one_to_one_assignment(expected, actual, item_type):
    """Find a complete expected-to-actual assignment by augmenting paths."""
    edges = [
        [actual_index for actual_index, candidate in enumerate(actual)
         if _match(value, candidate, item_type)]
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
    if isinstance(declared_type, Mapping) and key is not None:
        return declared_type.get(key)
    if (key is None and isinstance(declared_type, Sequence)
            and not isinstance(declared_type, (str, bytes)) and len(declared_type) == 1):
        return declared_type[0]
    return None


def _match_scalar(expected, actual, declared_type):
    if declared_type == "datetime":
        return _match_datetime(expected, actual)
    if declared_type == "date":
        return _match_date(expected, actual)
    if declared_type == "duration":
        return _match_duration(expected, actual)
    if declared_type in {"integer", "number", "decimal"}:
        return _match_number(expected, actual, declared_type)
    if declared_type in {"string", "id"}:
        return isinstance(expected, str) and isinstance(actual, str) and expected == actual
    if declared_type == "boolean":
        return isinstance(expected, bool) and isinstance(actual, bool) and expected == actual
    return type(expected) is type(actual) and expected == actual


def _finite_decimal(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        return None
    try:
        number = Decimal(str(value))
        return number if number.is_finite() else None
    except InvalidOperation:
        return None


def _match_number(expected, actual, declared_type):
    if (scalar_validation_error(expected, declared_type) is not None
            or scalar_validation_error(actual, declared_type) is not None):
        return False
    return _finite_decimal(expected) == _finite_decimal(actual)


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
    if years is not None or months is not None:
        return "calendar", value
    total = (Decimal(weeks or 0) * Decimal(604800)
             + Decimal(days or 0) * Decimal(86400)
             + Decimal(hours or 0) * Decimal(3600)
             + Decimal(minutes or 0) * Decimal(60)
             + Decimal(seconds or 0))
    return "fixed", total


def _match_duration(expected, actual):
    left = _parse_duration(expected)
    right = _parse_duration(actual)
    if left is None or right is None or left[0] != right[0]:
        return False
    return left[1] == right[1]

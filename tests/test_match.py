from decimal import Decimal
import json
from pathlib import Path
import unittest

import jsonschema
from referencing import Registry, Resource

from scripts.aegis_match import MatchError, match, scalar_validation_error


SOURCE = Path(__file__).resolve().parents[1]
SCHEMAS = SOURCE / "framework" / "language" / "schemas"


def schema_validator(name):
    registry = Registry()
    loaded = {}
    for path in SCHEMAS.glob("*.schema.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        loaded[path.name] = schema
        resource = Resource.from_contents(schema)
        registry = registry.with_resource(schema.get("$id", path.resolve().as_uri()), resource)
        registry = registry.with_resource(path.resolve().as_uri(), resource)
    return jsonschema.Draft202012Validator(loaded[name], registry=registry)


class MatcherTests(unittest.TestCase):
    def test_objects_are_partial_and_arrays_are_exact_and_ordered(self):
        self.assertTrue(match({"task": {"state": "open"}},
                              {"task": {"id": "a", "state": "open"}, "revision": 2}))
        self.assertTrue(match([{"state": "open"}], [{"id": "a", "state": "open"}]))
        self.assertFalse(match([1, 2], [2, 1]))
        self.assertFalse(match([1], [1, 2]))

    def test_presence_and_length_matchers_work_when_nested(self):
        self.assertTrue(match({"item": {"secret": {"$absent": True},
                                               "value": {"$any": True}}},
                              {"item": {"value": None, "extra": 1}}))
        self.assertFalse(match({"item": {"secret": {"$absent": True}}},
                               {"item": {"secret": None}}))
        self.assertTrue(match({"items": {"$length": 2}}, {"items": [1, 2]}))
        self.assertFalse(match({"items": {"$length": 1}}, {"items": [1, 2]}))

    def test_unknown_or_combined_matchers_are_rejected(self):
        with self.assertRaises(MatchError):
            match({"$some": []}, [])
        with self.assertRaises(MatchError):
            match({"$length": 1, "$any": True}, [1])

    def test_f6_unordered_requires_distinct_actual_elements(self):
        expected = {"$unordered": [{"state": "open"}, {"state": "open"}]}
        actual = [{"id": "a", "state": "open"}, {"id": "b", "state": "complete"}]
        self.assertFalse(match(expected, actual))

    def test_contains_uses_assignment_instead_of_greedy_first_match(self):
        expected = {"$contains": [{"state": "open"}, {"id": "a"}]}
        actual = [{"id": "a", "state": "open"}, {"id": "b", "state": "open"}]
        self.assertTrue(match(expected, actual))
        self.assertTrue(match({"$contains": [{"id": "a"}]}, actual))
        self.assertFalse(match({"$contains": [{"state": "missing"}]}, actual))

    def test_nested_matchers_compose(self):
        expected = {
            "groups": {"$unordered": [
                {"items": {"$contains": [{"value": {"$any": True}}]}},
                {"items": {"$length": 0}},
            ]}
        }
        actual = {"groups": [{"items": []}, {"items": [{"value": 3, "extra": True}]}]}
        self.assertTrue(match(expected, actual))

    def test_f5_datetimes_compare_as_instants_and_accept_serialization_variants(self):
        expected = "2026-10-02T09:00:00Z"
        for actual in ("2026-10-02T11:00:00+02:00",
                       "2026-10-02T09:00:00.000Z",
                       "2026-10-02T09:00Z"):
            with self.subTest(actual=actual):
                self.assertTrue(match(expected, actual, "datetime"))

    def test_datetime_uses_expected_subsecond_precision_and_requires_offsets(self):
        self.assertTrue(match("2026-10-02T09:00:00Z",
                              "2026-10-02T09:00:00.999Z", "datetime"))
        self.assertFalse(match("2026-10-02T09:00:00Z",
                               "2026-10-02T09:00:01Z", "datetime"))
        self.assertTrue(match("2026-10-02T09:00:00.12Z",
                              "2026-10-02T09:00:00.129Z", "datetime"))
        self.assertFalse(match("2026-10-02T09:00:00.130Z",
                               "2026-10-02T09:00:00.129Z", "datetime"))
        self.assertFalse(match("2026-10-02T09:00:00", "2026-10-02T09:00:00Z", "datetime"))
        self.assertFalse(match("2026-10-02T09:00:00Z", "2026-10-02T09:00:00", "datetime"))

    def test_minute_precision_expectation_is_a_half_open_timeline_interval(self):
        expected = "2026-10-02T09:00Z"
        self.assertTrue(match(expected, "2026-10-02T09:00:59.999Z", "datetime"))
        self.assertFalse(match(expected, "2026-10-02T09:01:00Z", "datetime"))
        self.assertFalse(match(expected, "2026-10-02T08:59:59.999Z", "datetime"))

    def test_numbers_compare_by_value_without_string_or_boolean_coercion(self):
        self.assertTrue(match(1, 1.0, "number"))
        self.assertTrue(match(Decimal("0.10"), Decimal("0.1"), "decimal"))
        self.assertFalse(match("1", 1, "number"))
        self.assertFalse(match(True, 1, "integer"))
        for value in (float("nan"), float("inf"), float("-inf"),
                      Decimal("NaN"), Decimal("Infinity")):
            with self.subTest(value=value):
                self.assertFalse(match(value, value, "number"))
                self.assertFalse(match(1, value, "decimal"))
        self.assertFalse(match(1.5, 1.5, "integer"))

    def test_string_that_looks_typed_remains_strict(self):
        value = "2026-10-02T09:00:00Z"
        self.assertFalse(match(value, "2026-10-02T11:00:00+02:00", "string"))
        self.assertFalse(match("1", 1, "string"))
        self.assertTrue(match("opaque-01", "opaque-01", "id"))

    def test_dates_and_durations_follow_declared_semantics(self):
        self.assertTrue(match("2026-10-02", "2026-10-02", "date"))
        self.assertFalse(match("2026-02-30", "2026-02-30", "date"))
        self.assertTrue(match("PT120M", "PT2H", "duration"))
        self.assertTrue(match("P1D", "PT24H", "duration"))
        self.assertTrue(match("P2W", "P14D", "duration"))
        self.assertFalse(match("P1M", "P30D", "duration"))
        self.assertTrue(match("P1M", "P1M", "duration"))
        self.assertTrue(match("P1M1D", "P1M1D", "duration"))
        self.assertFalse(match("P1M1D", "P1MT24H", "duration"))
        self.assertFalse(match("P1Y", "P12M", "duration"))

    def test_invalid_or_unsupported_duration_forms_do_not_match(self):
        for value in ("P", "PT", "-PT1H", "PT1.5H", "P1W1D", "P1DT", "pt1h"):
            with self.subTest(value=value):
                self.assertFalse(match(value, value, "duration"))

    def test_type_hints_flow_through_arrays_and_objects(self):
        self.assertTrue(match(
            {"times": {"$unordered": ["2026-10-02T09:00:00Z"]}},
            {"times": ["2026-10-02T11:00:00+02:00"]},
            {"times": ["datetime"]},
        ))


class LanguageSchemaTests(unittest.TestCase):
    def scenario(self):
        return [{
            "id": "SC-TODO-001",
            "title": "Record a task",
            "exercises": ["BR-TODO-001"],
            "verification": "automated",
            "given": {"steps": []},
            "when": {"command": "tasks.add", "input": {"title": "one"}},
            "then": {"output": {"task": {"$any": True}}},
        }]

    def test_capture_name_and_failed_capture_constraints(self):
        validator = schema_validator("scenario.schema.json")
        scenario = self.scenario()
        scenario[0]["given"]["steps"] = [
            {"command": "tasks.add", "input": {}, "as": "Task"},
        ]
        self.assertTrue(list(validator.iter_errors(scenario)))

        scenario[0]["given"]["steps"] = [
            {"command": "tasks.add", "input": {},
             "expectError": "TITLE_REQUIRED", "as": "failed"},
        ]
        self.assertTrue(list(validator.iter_errors(scenario)))

    def test_capture_references_must_be_complete_valid_scalar_tokens(self):
        validator = schema_validator("scenario.schema.json")
        invalid = (
            "${task1}",
            "prefix ${task1.id}",
            "${task1.id} suffix",
            "${task1.}",
            "${Task.id}",
            "${task1..id}",
            "${task1.id",
        )
        for location in ("input", "expected"):
            for value in invalid:
                with self.subTest(location=location, value=value):
                    scenario = self.scenario()
                    if location == "input":
                        scenario[0]["when"]["input"]["taskId"] = value
                    else:
                        scenario[0]["then"]["output"] = {"id": value}
                    self.assertTrue(list(validator.iter_errors(scenario)))

            with self.subTest(location=location, value="valid"):
                scenario = self.scenario()
                if location == "input":
                    scenario[0]["when"]["input"]["taskId"] = "${task1.task.id}"
                else:
                    scenario[0]["then"]["output"] = {"id": "${task1.task.id}"}
                self.assertEqual(list(validator.iter_errors(scenario)), [])

    def test_scalar_vocabulary_is_central_and_unknown_names_remain_schema_valid(self):
        common = json.loads((SCHEMAS / "common.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(
            common["$defs"]["scalarType"]["enum"],
            ["string", "boolean", "integer", "number", "decimal",
             "date", "datetime", "duration", "id"],
        )
        contract = {
            "id": "tasks.add", "version": "1.0.0", "kind": "command",
            "summary": "Add a task", "types": {"Task": "A task."},
            "input": {"dueAt": {"type": "futureScalar", "required": False,
                                  "description": "Optional due time."}},
            "output": {}, "errors": [], "semantics": ["Records a task."],
        }
        self.assertEqual(list(schema_validator("contract.schema.json").iter_errors(contract)), [])


class ScalarLiteralValidationTests(unittest.TestCase):
    def test_every_scalar_type_uses_the_matcher_parsers(self):
        valid = {
            "string": "one",
            "boolean": True,
            "integer": 1.0,
            "number": 1.5,
            "decimal": Decimal("0.10"),
            "date": "2026-10-02",
            "datetime": "2026-10-02T09:00Z",
            "duration": "PT120M",
            "id": "opaque-1",
        }
        for declared_type, value in valid.items():
            with self.subTest(declared_type=declared_type):
                self.assertIsNone(scalar_validation_error(value, declared_type))

        invalid = {
            "string": 1,
            "boolean": 1,
            "integer": 1.5,
            "number": float("inf"),
            "decimal": Decimal("NaN"),
            "date": "2026-02-30",
            "datetime": "not-a-date",
            "duration": "PT1.5H",
            "id": 10,
        }
        for declared_type, value in invalid.items():
            with self.subTest(declared_type=declared_type):
                self.assertEqual(scalar_validation_error(value, declared_type),
                                 "INVALID_TYPED_VALUE")

    def test_datetime_without_offset_has_its_own_diagnostic(self):
        self.assertEqual(scalar_validation_error("2026-10-02T09:00", "datetime"),
                         "DATETIME_WITHOUT_OFFSET")
        self.assertEqual(scalar_validation_error("2026-02-30T09:00", "datetime"),
                         "INVALID_TYPED_VALUE")
        self.assertEqual(scalar_validation_error("2026-10-02T99:00", "datetime"),
                         "INVALID_TYPED_VALUE")

    def test_unknown_type_is_left_to_the_unknown_type_diagnostic(self):
        self.assertIsNone(scalar_validation_error(object(), "FutureScalar"))


if __name__ == "__main__":
    unittest.main()

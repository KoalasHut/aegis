from decimal import Decimal
import datetime as dt
import itertools
import json
from pathlib import Path
import unittest

import jsonschema
from referencing import Registry, Resource
from hypothesis import given, strategies as st

from scripts.aegis_match import (
    MatchError, match, normalized_map_key_collisions, scalar_validation_error,
    typed_map_key_collisions,
)
from scripts.aegis_types import (
    TypeResolutionError, build_registry, load_types_document, load_yaml_exact,
    parse_type_expression, structurally_equal,
)


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
                              {"item": {"value": 0, "extra": 1}}))
        self.assertTrue(match({"item": {"secret": {"$absent": True}}},
                              {"item": {"secret": None}}))
        self.assertFalse(match({"item": {"value": {"$any": True}}},
                               {"item": {"value": None}}))
        self.assertTrue(match({"items": {"$length": 2}}, {"items": [1, 2]}))
        self.assertFalse(match({"items": {"$length": 1}}, {"items": [1, 2]}))

    def test_unknown_or_combined_matchers_are_rejected(self):
        with self.assertRaises(MatchError):
            match({"$some": []}, [])
        with self.assertRaises(MatchError):
            match({"$length": 1, "$any": True}, [1])
        with self.assertRaises(TypeError):
            match(1, 1, "integer", declared_type="integer")
        with self.assertRaises(TypeError):
            match(1, 1, future_option=True)
        self.assertTrue(match(1, 1, declared_type="integer"))

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

    def test_malformed_matcher_operands_and_shapes_do_not_match(self):
        self.assertFalse(match({"$length": 1}, {}))
        self.assertFalse(match({"$length": True}, [1]))
        self.assertFalse(match({"$contains": "one"}, ["one"]))
        self.assertFalse(match({"$contains": [1, 2]}, [1]))
        self.assertFalse(match({"$unordered": [1]}, [1, 2]))
        self.assertFalse(match({"field": 1}, []))
        self.assertFalse(match({"field": 1}, {}))
        self.assertFalse(match([1], "not-a-list"))

    def test_f5_datetimes_compare_as_instants_and_accept_serialization_variants(self):
        expected = "2026-10-02T09:00:00Z"
        for actual in ("2026-10-02T11:00:00+02:00",
                       "2026-10-02t09:00:00Z",
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
        self.assertTrue(match(True, True, "boolean"))
        self.assertFalse(match(True, 1, "boolean"))

    def test_dates_and_durations_follow_declared_semantics(self):
        self.assertTrue(match("2026-10-02", "2026-10-02", "date"))
        self.assertFalse(match("2026-02-30", "2026-02-30", "date"))
        self.assertTrue(match("PT120M", "PT2H", "duration"))
        self.assertTrue(match("P1D", "PT24H", "duration"))
        self.assertTrue(match("P2W", "P14D", "duration"))
        self.assertFalse(match("P1M", "P30D", "duration"))
        self.assertTrue(match("P1M", "P1M", "duration"))
        self.assertTrue(match("P1M1D", "P1M1D", "duration"))
        self.assertTrue(match("P1M1D", "P1MT24H", "duration"))
        self.assertFalse(match("P1Y", "P12M", "duration"))
        self.assertTrue(match("P1M", "P01M", "duration"))
        self.assertTrue(match("P1Y2M", "P1Y2MT0S", "duration"))

    def test_invalid_or_unsupported_duration_forms_do_not_match(self):
        for value in ("P", "PT", "-PT1H", "PT1.5H", "P1W1D", "P1DT", "pt1h", 1):
            with self.subTest(value=value):
                self.assertFalse(match(value, value, "duration"))

    def test_type_hints_flow_through_arrays_and_objects(self):
        self.assertTrue(match(
            {"times": {"$unordered": ["2026-10-02T09:00:00Z"]}},
            {"times": ["2026-10-02T11:00:00+02:00"]},
            {"times": ["datetime"]},
        ))

    def test_resolved_named_types_flow_at_every_depth(self):
        registry = build_registry(context_types={
            "State": {"description": "Closed state.", "enum": ["open", "complete"]},
            "Task": {"description": "A task.", "fields": {
                "state": {"type": "State", "required": True},
                "dueAt": {"type": "datetime"},
                "labels": {"type": "map<string>"},
            }},
            "Envelope": {"description": "Nested result.", "fields": {
                "tasks": {"type": "Task[]", "required": True},
            }},
        })
        expected = {"tasks": [{"state": "open", "dueAt": "2026-10-02T09:00:00Z",
                               "labels": {"name": "é"}}]}
        actual = {"tasks": [{"state": "open", "dueAt": "2026-10-02T06:00:00-03:00",
                             "labels": {"name": "é", "other": "kept"}}]}
        self.assertTrue(match(expected, actual, "Envelope", registry))
        actual["tasks"][0]["state"] = "Open"
        self.assertFalse(match(expected, actual, "Envelope", registry))

    def test_map_keys_compare_after_nfc_but_record_fields_remain_raw(self):
        self.assertTrue(match({"café": "yes"}, {"café": "yes"},
                              "map<string>"))
        record = {"kind": "record", "fields": {"café": {"kind": "scalar", "name": "string"}}}
        self.assertFalse(match({"café": "yes"}, {"café": "yes"}, record))

    def test_nfc_colliding_map_keys_are_detected_and_do_not_match(self):
        collision = {"café": "one", "café": "two"}
        self.assertEqual(normalized_map_key_collisions(collision, ("labels",)), ({
            "path": ("labels",), "normalizedKey": "café", "keys": ("café", "café"),
        },))
        self.assertEqual(normalized_map_key_collisions([]), ())
        self.assertFalse(match({"café": "one"}, collision, "map<string>"))
        self.assertFalse(match(collision, {"café": "one"}, "map<string>"))
        self.assertTrue(match({"café": "one"}, {"café": "one"}, "map<string>"))
        self.assertFalse(match({"missing": "one"}, {"café": "one"}, "map<string>"))

    def test_nested_maps_and_list_maps_normalize_and_report_collision_paths(self):
        registry = build_registry(context_types={
            "Payload": {"description": "Nested maps.", "fields": {
                "labels": {"type": "map<string>", "required": True},
                "groups": {"type": "map<string>[]", "required": True},
            }},
        })
        expected = {"labels": {"café": "one"}, "groups": [{"résumé": "two"}]}
        actual = {"labels": {"café": "one"}, "groups": [{"résumé": "two"}]}
        self.assertTrue(match(expected, actual, "Payload", registry))

        actual["groups"][0]["résumé"] = "duplicate"
        self.assertEqual(typed_map_key_collisions(actual, "Payload", registry), ({
            "path": ("groups", 0), "normalizedKey": "résumé",
            "keys": ("résumé", "résumé"),
        },))
        self.assertFalse(match({"labels": {}}, actual, "Payload", registry))

    def test_non_string_map_keys_are_clean_non_matches_at_any_depth(self):
        self.assertFalse(match({"valid": "one"}, {1: "one"}, "map<string>"))
        self.assertFalse(match([{1: "one"}], [{1: "one"}], "map<string>[]"))

    def test_no_value_decimal_number_nfc_and_id_semantics(self):
        self.assertTrue(match({"note": None}, {}))
        self.assertTrue(match({"note": None}, {"note": None}))
        self.assertTrue(match("10.50", 10.5, "decimal"))
        self.assertFalse(match(0.3, 0.1 + 0.2, "number"))
        self.assertTrue(match("é", "é", "string"))
        self.assertFalse(match("é", "é", "id"))
        self.assertFalse(match("not-an-object", {}, "string"))
        self.assertFalse(match("value", {}, "string"))

    def test_exact_yaml_numbers_retain_precision_before_matching(self):
        values = load_yaml_exact(
            "number: 0.100000000000000005\nshort: 0.1\ndecimal: 0.100000000000000005\n"
        )
        self.assertIsInstance(values["number"], Decimal)
        self.assertFalse(match(values["number"], values["short"], "number"))
        self.assertTrue(match(values["decimal"], "0.100000000000000005", "decimal"))
        for left, right in (("1.2300e2", "+123"), ("-0e9", "+0.000")):
            self.assertTrue(match(left, right, "decimal"))

    def test_invalid_datetime_offset_and_non_string_date_do_not_match(self):
        self.assertFalse(match("2026-10-02T09:00:00+24:00",
                               "2026-10-02T09:00:00Z", "datetime"))
        self.assertFalse(match(20261002, 20261002, "date"))
        self.assertFalse(match(20261002, 20261002, "datetime"))

    def test_opaque_type_compares_the_complete_value_strictly(self):
        registry = build_registry(local_types={"Rule": "A legacy prose-only rule."})
        self.assertTrue(match({"statement": "same"}, {"statement": "same"}, "Rule", registry))
        self.assertFalse(match({"statement": "same"},
                               {"statement": "same", "extra": True}, "Rule", registry))
        self.assertFalse(match({"value": None}, {}, "Rule", registry))
        self.assertTrue(match([], [], {"kind": "record", "fields": {}, "required": ()}))


class SharedTypeModelTests(unittest.TestCase):
    def test_context_document_enum_record_collections_and_recursion(self):
        document = {"types": {
            "State": {"description": "State.", "enum": ["open", "complete"]},
            "Tree": {"description": "Recursive tree.", "fields": {
                "state": {"type": "State", "required": True},
                "children": {"type": "Tree[]"},
            }},
        }}
        loaded = load_types_document(document)
        registry = build_registry(context_types=document)
        self.assertEqual(loaded["State"]["kind"], "enum")
        self.assertEqual(registry["Tree"]["fields"]["children"]["kind"], "list")
        self.assertTrue(structurally_equal("State", "State", registry))
        self.assertEqual(parse_type_expression("map<string[]>[]")["kind"], "list")

        parallel = build_registry(context_types={
            "OtherTree": {"description": "Equivalent recursive tree.", "fields": {
                "state": {"type": "State", "required": True},
                "children": {"type": "OtherTree[]"},
            }},
            "State": {"description": "State.", "enum": ["open", "complete"]},
        })
        combined = {**registry, **parallel}
        self.assertTrue(structurally_equal("Tree", "OtherTree", combined))

    def test_shadowing_and_unknown_types_have_stable_codes(self):
        definition = {"description": "State.", "enum": ["open"]}
        with self.assertRaises(TypeResolutionError) as found:
            build_registry(context_types={"State": definition}, local_types={"State": definition})
        self.assertEqual(found.exception.code, "TYPE_SHADOWED")
        with self.assertRaises(TypeResolutionError) as found:
            match("open", "open", "Missing", {})
        self.assertEqual(found.exception.code, "UNKNOWN_TYPE")
        for left, right in (("Missing", "Missing"), ("Missing", "string")):
            with self.subTest(left=left, right=right):
                with self.assertRaises(TypeResolutionError) as found:
                    structurally_equal(left, right, {})
                self.assertEqual(found.exception.code, "UNKNOWN_TYPE")

    def test_registry_constrains_local_and_pre_resolved_import_names(self):
        definition = {"description": "State.", "enum": ["open"]}
        for kwargs in ({"local_types": {"bad name": definition}},
                       {"context_types": {"tasks.State": definition}},
                       {"imports": {"State": definition}}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(TypeResolutionError) as found:
                    build_registry(**kwargs)
                self.assertEqual(found.exception.code, "INVALID_TYPE_NAME")
        registry = build_registry(imports={"tasks.State": definition})
        self.assertEqual(registry["tasks.State"]["kind"], "enum")


class MatcherPropertyTests(unittest.TestCase):
    @given(st.integers(min_value=0, max_value=86400 * 365),
           st.integers(min_value=-56, max_value=56).map(lambda value: value * 15),
           st.integers(min_value=0, max_value=999999),
           st.booleans())
    def test_datetime_reserialization_preserves_instants(
            self, seconds, offset_minutes, micros, lowercase):
        instant = (dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc)
                   + dt.timedelta(seconds=seconds, microseconds=micros))
        expected = instant.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        offset = dt.timezone(dt.timedelta(minutes=offset_minutes))
        actual = instant.astimezone(offset).isoformat(timespec="microseconds")
        if lowercase:
            actual = actual.replace("T", "t")
            if actual.endswith("+00:00"):
                actual = actual[:-6] + "z"
        self.assertTrue(match(expected, actual, "datetime"))

    @given(st.integers(min_value=0, max_value=58))
    def test_datetime_precision_is_a_half_open_window(self, second):
        expected = f"2026-10-02T09:00:{second:02d}Z"
        inside = f"2026-10-02T09:00:{second:02d}.999999999Z"
        outside = f"2026-10-02T09:00:{second + 1:02d}Z"
        self.assertTrue(match(expected, inside, "datetime"))
        self.assertFalse(match(expected, outside, "datetime"))

    @given(st.decimals(allow_nan=False, allow_infinity=False, places=6,
                       min_value=Decimal("-1000000"), max_value=Decimal("1000000")))
    def test_decimal_formatting_is_invariant(self, value):
        rendered = format(value, "f")
        self.assertTrue(match(rendered, value, "decimal"))
        self.assertTrue(match(rendered + "0", rendered, "decimal"))

    @given(st.integers(min_value=0, max_value=9999),
           st.integers(min_value=0, max_value=9999))
    def test_duration_zero_padding_and_component_identity(self, years, months):
        plain = f"P{years}Y{months}M"
        padded = f"P{years:05d}Y{months:05d}MT0S"
        self.assertTrue(match(plain, padded, "duration"))
        self.assertFalse(match(f"P{years + 1}Y{months}M", padded, "duration"))

    @given(st.text(alphabet=st.sampled_from(list("aeiouAEIOU")), min_size=1, max_size=20))
    def test_nfc_and_nfd_are_equal_only_for_strings(self, prefix):
        composed = prefix + "é"
        decomposed = prefix + "é"
        self.assertTrue(match(composed, decomposed, "string"))
        self.assertFalse(match(composed, decomposed, "id"))

    @given(st.booleans())
    def test_absent_and_null_are_observationally_equal(self, emit_null):
        actual = {"value": None} if emit_null else {}
        self.assertTrue(match({"value": None}, actual))
        self.assertTrue(match({"value": {"$absent": True}}, actual))

    @given(
        st.lists(st.fixed_dictionaries({
            "id": st.integers(min_value=0, max_value=3),
            "state": st.sampled_from(["open", "complete"]),
        }), max_size=6),
        st.lists(st.one_of(
            st.fixed_dictionaries({"id": st.integers(min_value=0, max_value=3)}),
            st.fixed_dictionaries({"state": st.sampled_from(["open", "complete"])}),
        ), max_size=6),
    )
    def test_one_to_one_assignment_matches_brute_force(self, actual, expected):
        brute = (len(expected) <= len(actual) and any(
            all(match(item, candidate) for item, candidate in zip(expected, chosen))
            for chosen in itertools.permutations(actual, len(expected))
        ))
        self.assertEqual(brute, match({"$contains": expected}, actual))


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

    def test_capture_references_must_be_complete_valid_value_tokens(self):
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

    def test_input_positions_are_concrete_at_every_depth(self):
        validator = schema_validator("scenario.schema.json")
        locations = ("given", "when", "observe")
        for location in locations:
            scenario = self.scenario()
            if location == "given":
                scenario[0]["given"]["steps"] = [{"command": "tasks.add", "input": {"nested": [{"$any": True}]}}]
            elif location == "when":
                scenario[0]["when"]["input"] = {"$absent": True}
            else:
                scenario[0]["then"]["observe"] = [{"query": "tasks.list", "input": {"$any": True}, "expect": {}}]
            with self.subTest(location=location):
                self.assertTrue(list(validator.iter_errors(scenario)))

        scenario = self.scenario()
        scenario[0]["then"]["output"] = {"items": {"$contains": []}}
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

    def test_context_types_schema_accepts_records_enums_and_prose(self):
        document = {"types": {
            "State": {"description": "State.", "enum": ["open", "complete"]},
            "Task": {"description": "Task.", "fields": {
                "state": {"type": "State", "required": True},
                "children": {"type": "Task[]"},
            }},
            "Legacy": "An opaque migration type.",
        }}
        self.assertEqual(list(schema_validator("types.schema.json").iter_errors(document)), [])

    def test_contracts_may_use_context_types_only_and_existing_unions_remain_valid(self):
        validator = schema_validator("contract.schema.json")
        operation = {
            "id": "tasks.list", "version": "1.0.0", "kind": "query",
            "summary": "List tasks", "types": {}, "input": {},
            "output": {"tasks": {"type": "Task[]", "required": True,
                                  "description": "Current tasks."}},
            "errors": [], "semantics": ["Returns tasks."],
        }
        union = {
            "id": "content.block", "version": "1.0.0", "kind": "union",
            "summary": "One content block", "types": {},
            "semantics": ["Exactly one variant applies."],
            "variants": {
                "text": {"contract": "content.text@1"},
                "image": {"contract": "content.image@1"},
            },
        }
        self.assertEqual(list(validator.iter_errors(operation)), [])
        self.assertEqual(list(validator.iter_errors(union)), [])
        invalid = dict(operation, types={"bad name": "Unreachable."})
        self.assertTrue(list(validator.iter_errors(invalid)))


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

    def test_decimal_strings_and_integer_safe_range(self):
        self.assertIsNone(scalar_validation_error("10.50", "decimal"))
        self.assertIsNone(scalar_validation_error("+1.2300e-2", "decimal"))
        self.assertEqual(scalar_validation_error(str(10), "integer"), "INVALID_TYPED_VALUE")
        self.assertEqual(scalar_validation_error(2 ** 53, "integer"), "UNSAFE_INTEGER")


if __name__ == "__main__":
    unittest.main()

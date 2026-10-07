from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
import unittest

from hypothesis import example, given, settings, strategies as st
import yaml

from scripts import validate as validator


SOURCE = Path(__file__).resolve().parents[1]
VALID = SOURCE / "tests" / "fixtures" / "validate" / "valid"


OPERATIONS = (
        "insert_type_character",
        "delete_type_character",
        "swap_type_characters",
        "delete_type",
        "rename_type",
        "delete_type_field",
        "rename_type_field",
        "delete_enum_value",
        "rename_enum_value",
        "matcher_given_step",
        "matcher_seed",
        "matcher_when",
        "matcher_observe",
        "matcher_optional_when_due_at",
        "scalar_type_replacement",
        "broken_capture",
        "embedded_capture",
        "duplicate_enum",
        "unsatisfiable_type",
        "duplicate_scenario_id",
        "truncate_exercises",
        "duplicate_exercise",
        "drop_required_key",
)

MUTATIONS = st.tuples(
    st.sampled_from(OPERATIONS),
    st.integers(min_value=0, max_value=1_000_000),
)


@st.composite
def mutation_sets(draw):
    count = draw(st.integers(min_value=1, max_value=2))
    return draw(st.lists(MUTATIONS, min_size=count, max_size=count))


def read_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_yaml(path, document):
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def matcher_literal(value):
    """Put a matcher below one or more ordinary YAML containers."""
    matcher = {"$any": True}
    for depth in range(1 + value % 3):
        matcher = ({"nested%d" % depth: matcher}
                   if (value + depth) % 2 else [matcher])
    return matcher


def apply_mutation(root, mutation):
    operation, value = mutation
    types_path = root / "framework/contexts/tasks/types.yaml"
    add_path = root / "framework/blocks/tasks/contracts/add.yaml"
    list_path = root / "framework/blocks/tasks/contracts/list.yaml"
    scenario_path = root / "framework/contexts/tasks/scenarios/tasks.yaml"

    if operation in {"insert_type_character", "delete_type_character", "delete_type",
                     "rename_type", "delete_type_field", "rename_type_field",
                     "delete_enum_value", "rename_enum_value", "duplicate_enum",
                     "unsatisfiable_type"}:
        document = read_yaml(types_path)
        if operation == "insert_type_character":
            task = document.get("types", {}).get("Task")
            if task and "title" in task.get("fields", {}):
                task["fields"]["title"]["type"] = "str%sing" % chr(97 + value % 26)
        elif operation == "delete_type_character":
            task = document.get("types", {}).get("Task")
            if task:
                task.setdefault("fields", {})["dueAt"] = {"type": "datetim"}
        elif operation == "delete_type":
            document["types"].pop("Task", None)
        elif operation == "rename_type":
            task = document.get("types", {}).pop("Task", None)
            if task is not None:
                document["types"]["RenamedTask%d" % value] = task
        elif operation == "delete_type_field":
            document.get("types", {}).get("Task", {}).get("fields", {}).pop("title", None)
        elif operation == "rename_type_field":
            fields = document.get("types", {}).get("Task", {}).get("fields", {})
            if "title" in fields:
                fields["renamed%d" % value] = fields.pop("title")
        elif operation in {"delete_enum_value", "rename_enum_value"}:
            enum = document.setdefault("types", {}).setdefault("TaskState", {
                "description": "Mutated task state.", "enum": ["open", "complete"],
            })["enum"]
            if operation == "delete_enum_value" and enum:
                enum.pop(value % len(enum))
            elif operation == "rename_enum_value" and enum:
                enum[value % len(enum)] = "renamed%d" % value
        elif operation == "duplicate_enum":
            document["types"]["TaskState"] = {
                "description": "Mutated task state.",
                "enum": ["open", "complete", "open"],
            }
        elif operation == "unsatisfiable_type":
            document["types"]["Node"] = {
                "description": "Required recursive node.",
                "fields": {"next": {"type": "Node", "required": True}},
            }
        write_yaml(types_path, document)
        return

    if operation == "swap_type_characters":
        document = read_yaml(list_path)
        document["output"]["items"]["type"] = "Taks[]"
        write_yaml(list_path, document)
        return

    scenarios = read_yaml(scenario_path)
    scenario = scenarios[0]
    if operation == "matcher_given_step":
        given = scenario.setdefault("given", {})
        steps = given.setdefault("steps", [])
        if not steps:
            given.pop("commands", None)
            steps.append({"command": "tasks.add", "input": {"title": "Write a note"}})
        steps[value % len(steps)].setdefault("input", {})["title"] = matcher_literal(value)
    elif operation == "matcher_seed":
        seed = scenario.setdefault("given", {}).setdefault(
            "seed", {"contract": "tasks.seed", "input": {}})
        seed.setdefault("input", {})["generated"] = matcher_literal(value)
    elif operation == "matcher_when":
        scenario.setdefault("when", {}).setdefault("input", {})["title"] = matcher_literal(value)
    elif operation == "matcher_observe":
        observations = scenario.setdefault("then", {}).setdefault("observe", [])
        if not observations:
            observations.append({"query": "tasks.list", "input": {}, "expect": {}})
        observations[value % len(observations)].setdefault("input", {})["generated"] = (
            matcher_literal(value)
        )
    elif operation == "matcher_optional_when_due_at":
        contract = read_yaml(add_path)
        contract["input"]["dueAt"] = {
            "type": "datetime", "description": "Optional due instant.",
        }
        write_yaml(add_path, contract)
        scenario.setdefault("when", {}).setdefault("input", {})["dueAt"] = {
            "$absent": True
        }
    elif operation == "scalar_type_replacement":
        replacements = (None, bool(value % 2), value, [value], {"value": value})
        scenario.setdefault("when", {}).setdefault("input", {})["title"] = (
            replacements[value % len(replacements)]
        )
    elif operation == "broken_capture":
        scenario.setdefault("when", {}).setdefault("input", {})["title"] = (
            "${missing%d.item.id" % value
        )
    elif operation == "embedded_capture":
        scenario.setdefault("when", {}).setdefault("input", {})["title"] = (
            "after ${missing%d.item.id}" % value
        )
    elif operation == "duplicate_scenario_id":
        duplicate = deepcopy(scenario)
        scenarios.append(duplicate)
    elif operation == "truncate_exercises":
        exercises = scenario.setdefault("exercises", ["BR-TASKS-001"])
        if exercises:
            exercises.pop()
    elif operation == "duplicate_exercise":
        exercises = scenario.setdefault("exercises", ["BR-TASKS-001"])
        exercises.append(exercises[0])
    elif operation == "drop_required_key":
        key = ("id", "title", "exercises", "verification", "when", "then")[value % 6]
        scenario.pop(key, None)
    write_yaml(scenario_path, scenarios)


class RobustnessTests(unittest.TestCase):
    def test_profile_contains_every_promised_edit_family(self):
        self.assertEqual({
            "insert_type_character", "delete_type_character", "swap_type_characters",
            "delete_type", "rename_type", "delete_type_field", "rename_type_field",
            "delete_enum_value", "rename_enum_value", "matcher_given_step",
            "matcher_seed", "matcher_when", "matcher_observe",
            "matcher_optional_when_due_at", "scalar_type_replacement", "broken_capture",
            "embedded_capture", "truncate_exercises", "duplicate_exercise",
            "duplicate_scenario_id", "drop_required_key", "duplicate_enum",
            "unsatisfiable_type",
        }, set(OPERATIONS))

    def test_scalar_replacement_uses_each_wrong_yaml_shape(self):
        expected = ((0, type(None)), (1, bool), (2, int), (3, list), (4, dict))
        for value, expected_type in expected:
            with self.subTest(value=value, expected_type=expected_type.__name__):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary) / "project"
                    shutil.copytree(VALID, root)
                    apply_mutation(root, ("scalar_type_replacement", value))
                    scenario = read_yaml(
                        root / "framework/contexts/tasks/scenarios/tasks.yaml")[0]
                replacement = scenario["when"]["input"]["title"]
                self.assertIs(type(replacement), expected_type)

    def test_matcher_mutations_change_concrete_input_values_at_nested_paths(self):
        cases = (
            ("matcher_given_step", lambda scenario: scenario["given"]["steps"][0]
             ["input"]["title"]),
            ("matcher_seed", lambda scenario: scenario["given"]["seed"]
             ["input"]["generated"]),
            ("matcher_when", lambda scenario: scenario["when"]["input"]["title"]),
            ("matcher_observe", lambda scenario: scenario["then"]["observe"][0]
             ["input"]["generated"]),
        )
        for operation, target in cases:
            with self.subTest(operation=operation):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary) / "project"
                    shutil.copytree(VALID, root)
                    apply_mutation(root, (operation, 1))
                    scenario = read_yaml(
                        root / "framework/contexts/tasks/scenarios/tasks.yaml")[0]
                value = target(scenario)
                self.assertIsInstance(value, (dict, list))
                self.assertTrue(any("$any" in mapping for mapping in validator.walk_mappings(value)))

    @settings(max_examples=200, deadline=None, database=None, derandomize=True)
    @example(mutations=[("delete_type_character", 1)])  # K-1
    @example(mutations=[("swap_type_characters", 2)])  # K-2
    @example(mutations=[("matcher_given_step", 1)])  # K-3, nested $any
    @example(mutations=[("matcher_optional_when_due_at", 4)])  # K-4
    @example(mutations=[("duplicate_enum", 5)])  # K-5
    @example(mutations=[("embedded_capture", 6)])  # K-6
    @example(mutations=[("unsatisfiable_type", 9)])  # K-9
    @example(mutations=[("insert_type_character", 10), ("matcher_observe", 11)])
    @given(mutations=mutation_sets())
    def test_pinned_bounded_mutations_return_without_internal_error(self, mutations):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            shutil.copytree(VALID, root)
            shutil.copytree(SOURCE / "agents" / "contracts", root / "agents" / "contracts")
            for mutation in mutations:
                apply_mutation(root, mutation)

            findings = validator.validate(root)

        self.assertNotIn("INTERNAL_ERROR", {item["code"] for item in findings.items})
        for finding in findings.items:
            self.assertTrue(finding.get("code"))
            self.assertTrue(finding.get("scope"))
            self.assertTrue(str(finding.get("path", "")))


if __name__ == "__main__":
    unittest.main()

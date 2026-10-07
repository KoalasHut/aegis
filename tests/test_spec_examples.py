from pathlib import Path
import re
import unicodedata
import unittest

from scripts import validate as validator
from scripts.aegis_match import match
from scripts.aegis_types import (
    TypeResolutionError, build_registry, load_yaml_exact, resolve_type,
)


SOURCE = Path(__file__).resolve().parents[1]
EXAMPLES = SOURCE / "framework" / "language" / "examples" / "matching.yaml"


class MatchingSpecificationExamples(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = load_yaml_exact(EXAMPLES.read_text(encoding="utf-8"))
        cls.registry = build_registry(context_types=cls.document["types"])

    def test_numbered_examples_are_unique_contiguous_and_executable(self):
        examples = self.document["examples"]
        self.assertEqual([item["id"] for item in examples],
                         [f"M-{index:02d}" for index in range(1, len(examples) + 1)])
        for item in examples:
            with self.subTest(example=item["id"]):
                kind = item.get("kind", "match")
                if kind == "match":
                    observed = match(item["expected"], item["actual"],
                                     item.get("type"), self.registry)
                    self.assertIs(observed, item["result"])
                elif kind == "capture":
                    findings = validator.Findings()
                    captures = {"saved": {
                        "output": resolve_type("CaptureOutput", self.registry),
                        "registry": self.registry,
                    }}
                    validator.validate_typed_value(
                        item["value"], resolve_type(item["targetType"], self.registry),
                        self.registry, EXAMPLES, item["id"], findings, captures=captures,
                    )
                    codes = {finding["code"] for finding in findings.items}
                    if "finding" in item:
                        self.assertEqual(codes, {item["finding"]})
                    else:
                        self.assertEqual(codes, set())
                elif kind == "registry":
                    with self.assertRaises(TypeResolutionError) as found:
                        build_registry(imports={item["importName"]: {
                            "description": "Imported test type.", "enum": ["value"],
                        }})
                    self.assertEqual(found.exception.code, item["finding"])
                elif kind == "shadow":
                    definition = {"description": "Shadow test.", "enum": ["value"]}
                    with self.assertRaises(TypeResolutionError) as found:
                        build_registry(context_types={item["typeName"]: definition},
                                       local_types={item["typeName"]: definition})
                    self.assertEqual(found.exception.code, item["finding"])
                elif kind == "resolve":
                    with self.assertRaises(TypeResolutionError) as found:
                        resolve_type(item["type"], self.registry)
                    self.assertEqual(found.exception.code, item["finding"])
                elif kind == "schema":
                    scenario = [{
                        "id": "SC-TEST-001", "title": "Schema example",
                        "exercises": ["BR-TEST-001"], "verification": "automated",
                        "given": {"steps": []},
                        "when": {"command": "test.run", "input": {"value": item["value"]}},
                        "then": {"output": {}},
                    }]
                    findings = validator.Findings()
                    validator.validate_schema(
                        scenario,
                        SOURCE / "framework/language/schemas/scenario.schema.json",
                        EXAMPLES,
                        findings,
                    )
                    self.assertIs(not findings.items, item["schemaValid"])
                else:
                    self.assertEqual(kind, "runtime")
                    findings = validator.Findings()
                    validator.validate_typed_value(
                        item["value"], resolve_type(item["targetType"], self.registry),
                        self.registry, EXAMPLES, item["id"], findings,
                        captures={"saved": {
                            "output": resolve_type("CaptureOutput", self.registry),
                            "registry": self.registry,
                        }},
                    )
                    self.assertEqual(findings.items, [])
                    self.assertEqual(item["runtimeResultWhenAbsent"], "error")

    def test_normative_clauses_and_examples_have_two_way_references(self):
        specs = [SOURCE / "framework" / "language" / "scenario-spec.md",
                 SOURCE / "framework" / "language" / "type-spec.md"]
        clauses = set()
        for path in specs:
            clauses.update(re.findall(r"\*\*((?:SS|TS)-\d{3})\.\*\*",
                                      path.read_text(encoding="utf-8")))
        references = {clause for item in self.document["examples"]
                      for clause in item.get("clauses", [])}
        self.assertEqual(references, clauses)
        for item in self.document["examples"]:
            self.assertTrue(item.get("clauses"), item["id"])

    def test_examples_cover_each_type_and_matcher_branch(self):
        serialized = EXAMPLES.read_text(encoding="utf-8")
        for token in ("datetime", "date", "duration", "integer", "number", "decimal",
                      "string", "id", "enum", "$contains", "$unordered", "$length",
                      "$absent", "$any", "map<", "[]"):
            with self.subTest(token=token):
                self.assertIn(token, serialized)

    def test_m52_uses_nfc_equivalent_enum_spellings_but_compares_raw(self):
        example = next(item for item in self.document["examples"] if item["id"] == "M-52")
        self.assertEqual(
            unicodedata.normalize("NFC", example["expected"]),
            unicodedata.normalize("NFC", example["actual"]),
        )
        self.assertNotEqual(example["expected"], example["actual"])
        self.assertFalse(match(example["expected"], example["actual"],
                               example["type"], self.registry))


if __name__ == "__main__":
    unittest.main()

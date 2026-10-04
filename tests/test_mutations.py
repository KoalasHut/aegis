from pathlib import Path
import unittest

import yaml

from scripts import validate as validator
from scripts.aegis_types import TypeResolutionError, resolve_type
from tests.corpus_support import execute_project_operation


ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = ROOT / "tests" / "fixtures" / "mutations.yaml"


class ValidatorMutationArchitectureTests(unittest.TestCase):
    def test_thirty_isolated_mutations_are_detected(self):
        mutations = yaml.safe_load(MUTATIONS.read_text())["mutations"]
        self.assertEqual([f"MUT-{number:02d}" for number in range(1, 31)],
                         [item["id"] for item in mutations])
        self.assertEqual(len(mutations), len({item["edit"] for item in mutations}))
        scalar = lambda name: {"kind": "scalar", "name": name}
        nodes = {
            name: scalar(name) for name in
            ("string", "boolean", "integer", "decimal", "date", "datetime", "duration")
        }
        nodes["enum"] = {"kind": "enum", "values": ["open", "complete"]}
        nodes["record"] = {
            "kind": "record",
            "fields": {"title": {"type": nodes["string"], "required": True}},
            "required": ["title"],
        }
        for mutation in mutations:
            with self.subTest(mutation=mutation["id"]):
                if mutation["mode"].startswith("typed"):
                    findings = validator.Findings()
                    validator.validate_typed_value(
                        mutation["value"], nodes[mutation["node"]], None,
                        Path("mutated-scenario.yaml"), "when.input", findings,
                        input_literal=mutation.get("input", False),
                        required=mutation["mode"] == "typed-required",
                    )
                    self.assertEqual(mutation["expectedFindings"],
                                     sorted(item["code"] for item in findings.items))
                elif mutation["mode"] == "type-error":
                    with self.assertRaises(TypeResolutionError) as found:
                        resolve_type(mutation["type"], {})
                    self.assertEqual(mutation["expectedFindings"], [found.exception.code])
                elif mutation["mode"] == "project":
                    self.assertEqual(mutation["expectedFindings"],
                                     execute_project_operation(mutation["operation"]))
                else:
                    self.fail("unknown mutation mode: " + mutation["mode"])


if __name__ == "__main__":
    unittest.main()

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1]
VALIDATOR = SOURCE / "scripts" / "validate.py"
FIXTURES = SOURCE / "tests" / "fixtures" / "validate"


class ValidationTests(unittest.TestCase):
    def make_root(self, *overlays):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "project"
        shutil.copytree(FIXTURES / "valid", root)
        # Assignment and handoff schemas are part of every initialized project.
        shutil.copytree(SOURCE / "agents" / "contracts", root / "agents" / "contracts")
        for name in overlays:
            source = FIXTURES / name
            for item in source.rglob("*"):
                if item.is_file():
                    target = root / item.relative_to(source)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target)
        return root

    def run_validator(self, root, as_json=True, *extra):
        command = [sys.executable, str(VALIDATOR), "--root", str(root)]
        if as_json:
            command.append("--json")
        command.extend(extra)
        return subprocess.run(command, text=True, capture_output=True)

    def codes(self, root):
        result = self.run_validator(root)
        payload = json.loads(result.stdout)
        return result, {item["code"] for item in payload["findings"]}, payload

    def test_valid_project_passes(self):
        result, codes, payload = self.codes(self.make_root())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(codes, set())
        self.assertEqual(payload["errors"], 0)

    def test_registry_indexes_are_references_not_duplicate_declarations(self):
        result, codes, _ = self.codes(self.make_root("indexed-rule"))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("DUPLICATE_ID", codes)

    def test_bare_rule_registry_id_must_resolve_to_a_canonical_rule(self):
        result, codes, _ = self.codes(self.make_root("missing-indexed-rule"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("UNKNOWN_BR", codes)

    def test_deprecated_rule_registry_tombstone_is_retained_without_reuse(self):
        for fixture in ("deprecated-tombstone", "deprecated-canonical"):
            with self.subTest(fixture=fixture):
                result, codes, _ = self.codes(self.make_root(fixture))
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertNotIn("ID_REUSED", codes)

    def test_duplicate_rule_registry_id_fails_clearly(self):
        result, codes, _ = self.codes(self.make_root("duplicate-indexed-rule"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DUPLICATE_REGISTRY_ID", codes)

    def test_schema_validation_includes_scenarios_and_handoffs(self):
        result, codes, _ = self.codes(self.make_root("invalid-schema"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SCHEMA_INVALID", codes)
        result, codes, _ = self.codes(self.make_root("schema-artifacts"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SCHEMA_INVALID", codes)

    def test_schema_validation_includes_impact_scope_and_waiver_routes(self):
        result, codes, payload = self.codes(self.make_root("schema-routes"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SCHEMA_INVALID", codes)
        paths = {item["path"] for item in payload["findings"]}
        self.assertIn("framework/blocks/tasks/impact.yaml", paths)
        self.assertIn("agents/roles/example/scope.yaml", paths)
        self.assertIn("framework/waivers/bad.yaml", paths)

    def test_unique_and_retired_ids_fail_clearly(self):
        for fixture, code in (("duplicate-id", "DUPLICATE_ID"), ("retired-id", "ID_REUSED")):
            result, codes, _ = self.codes(self.make_root(fixture))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(code, codes)

    def test_rule_scenario_decision_contract_and_error_references_fail_clearly(self):
        cases = (
            ("missing-br", "UNKNOWN_BR"),
            ("missing-sc", "UNKNOWN_SC"),
            ("missing-decision", "UNKNOWN_DECISION"),
            ("missing-contract", "UNKNOWN_CONTRACT"),
            ("invalid-error", "UNKNOWN_ERROR_CODE"),
        )
        for fixture, code in cases:
            with self.subTest(fixture=fixture):
                result, codes, _ = self.codes(self.make_root(fixture))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(code, codes)

    def test_non_approved_rule_reference_is_an_error(self):
        result, codes, _ = self.codes(self.make_root("non-approved"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SCENARIO_RULE_NOT_APPROVED", codes)

    def test_coverage_and_neutrality_are_warnings(self):
        for fixture, code in (("coverage", "AUTOMATED_RULE_UNCOVERED"),
                              ("neutrality", "NEUTRALITY_WORD")):
            with self.subTest(fixture=fixture):
                result, codes, payload = self.codes(self.make_root(fixture))
                self.assertEqual(result.returncode, 0)
                self.assertIn(code, codes)
                self.assertGreater(payload["warnings"], 0)

    def test_custom_neutrality_vocabulary_changes_warnings(self):
        root = self.make_root("custom-neutrality")
        default_result, default_codes, _ = self.codes(root)
        self.assertEqual(default_result.returncode, 0)
        self.assertNotIn("NEUTRALITY_WORD", default_codes)
        vocabulary = root / "custom-neutrality-words.txt"
        vocabulary.write_text("# Project term\nharbor\n", encoding="utf-8")
        result = self.run_validator(root, True, "--neutrality-words", str(vocabulary))
        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0)
        self.assertIn("NEUTRALITY_WORD", {item["code"] for item in payload["findings"]})

    def test_human_and_json_output(self):
        root = self.make_root("missing-br")
        human = self.run_validator(root, as_json=False)
        machine = self.run_validator(root, as_json=True)
        self.assertNotEqual(human.returncode, 0)
        self.assertIn("ERROR UNKNOWN_BR", human.stdout)
        self.assertNotEqual(machine.returncode, 0)
        self.assertIn("UNKNOWN_BR", json.loads(machine.stdout)["findings"][0]["code"])

    def test_default_root_is_independent_of_current_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run([sys.executable, str(VALIDATOR), "--json"],
                                    cwd=temporary, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["errors"], 0)


if __name__ == "__main__":
    unittest.main()

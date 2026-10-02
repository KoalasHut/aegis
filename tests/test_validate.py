import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import jsonschema
import yaml
from referencing import Registry, Resource


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

    def commit_root(self, root):
        for command in (("git", "init", "-q", str(root)),
                        ("git", "-C", str(root), "config", "user.email", "test@example.invalid"),
                        ("git", "-C", str(root), "config", "user.name", "Validator test"),
                        ("git", "-C", str(root), "add", "."),
                        ("git", "-C", str(root), "commit", "-qm", "base")):
            subprocess.run(command, check=True, capture_output=True)

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

    def test_scope_regressions_for_decisions_and_examples(self):
        root = self.make_root()
        rule = root / "framework/contexts/tasks/rules/tasks.yaml"
        rule.write_text(rule.read_text().replace("D-TASKS-001", "D-CORE-001"))
        example = root / "framework/examples/core-preservation"
        (example / "decisions.yaml").parent.mkdir(parents=True, exist_ok=True)
        (example / "decisions.yaml").write_text("- {id: D-CORE-001, status: approved}\n")
        result, codes, _ = self.codes(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("UNKNOWN_DECISION", codes)

    def test_rejected_structured_decision_and_manual_coverage(self):
        root = self.make_root()
        decisions = root / "framework/decisions.yaml"
        decisions.write_text(decisions.read_text().replace("status: approved", "status: rejected"))
        result, codes, _ = self.codes(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DECISION_NOT_APPROVED", codes)
        root = self.make_root()
        scenario = root / "framework/contexts/tasks/scenarios/tasks.yaml"
        scenario.write_text(scenario.read_text().replace("verification: automated", "verification: manual"))
        result, codes, payload = self.codes(root)
        self.assertEqual(result.returncode, 0)
        self.assertIn("AUTOMATED_RULE_UNCOVERED", codes)
        self.assertTrue(all("scope" in finding for finding in payload["findings"]))

    def test_schema_registry_enforces_rfc3339_and_reports_unavailable_formats(self):
        root = self.make_root()
        scenario = root / "framework/contexts/tasks/scenarios/tasks.yaml"
        scenario.write_text(scenario.read_text().replace("commands: []", "clock: not-a-date\n    commands: []"),
                            encoding="utf-8")
        result, codes, _ = self.codes(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SCHEMA_INVALID", codes)

        root = self.make_root()
        schemas = root / "framework/language/schemas"
        shutil.copytree(SOURCE / "framework/language/schemas", schemas)
        scenario_schema = schemas / "scenario.schema.json"
        scenario_schema.write_text(scenario_schema.read_text(encoding="utf-8").replace(
            '"format": "date-time"', '"format": "aegis-missing-format"'), encoding="utf-8")
        result, codes, _ = self.codes(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FORMAT_CHECK_UNAVAILABLE", codes)

    def test_contract_fields_and_ordered_setup_captures_are_checked(self):
        root = self.make_root()
        scenario = root / "framework/contexts/tasks/scenarios/tasks.yaml"
        document = yaml.safe_load(scenario.read_text(encoding="utf-8"))
        item = document[0]
        item["given"] = {"steps": [
            {"command": "tasks.add", "input": {"title": "one"}, "as": "item"},
            {"advanceClock": "PT1H"},
            {"command": "tasks.add", "input": {"title": "two"}, "expectError": "NOT_DECLARED"},
        ]}
        item["when"]["input"] = {"unknown": "${later.item.id}"}
        item["then"]["output"] = {"unknown": "${item.item.id}"}
        item["then"]["observe"][0]["expect"] = {"unknown": True}
        scenario.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
        result, codes, _ = self.codes(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue({"UNKNOWN_INPUT_FIELD", "MISSING_REQUIRED_INPUT", "UNKNOWN_OUTPUT_FIELD",
                         "UNKNOWN_CAPTURE", "UNKNOWN_ERROR_CODE"}.issubset(codes), codes)

    def test_rule_and_decision_supersession_failures_are_checked_per_scope(self):
        root = self.make_root()
        rules_path = root / "framework/contexts/tasks/rules/tasks.yaml"
        rules = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        rules[0]["status"] = "deprecated"
        successor = dict(rules[0], id="BR-TASKS-002", status="approved", supersedes="BR-NOPE-001")
        rules.append(successor)
        rules_path.write_text(yaml.safe_dump(rules, sort_keys=False), encoding="utf-8")
        decisions_path = root / "framework/decisions.yaml"
        decisions = yaml.safe_load(decisions_path.read_text(encoding="utf-8"))
        decisions[0]["status"] = "superseded"
        decisions.append(dict(decisions[0], id="D-TASKS-002", status="approved", supersedes="D-TASKS-001"))
        decisions.append(dict(decisions[0], id="D-TASKS-003", status="approved", supersedes="D-TASKS-001"))
        decisions_path.write_text(yaml.safe_dump(decisions, sort_keys=False), encoding="utf-8")
        result, codes, _ = self.codes(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("UNKNOWN_SUPERSEDED_RULE", codes)
        self.assertIn("DUPLICATE_SUPERSESSION", codes)

    def test_supersession_state_and_cycles_are_rejected(self):
        root = self.make_root()
        rules_path = root / "framework/contexts/tasks/rules/tasks.yaml"
        rules = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        successor = dict(rules[0], id="BR-TASKS-002", supersedes="BR-TASKS-001")
        rules[0]["supersedes"] = "BR-TASKS-002"
        rules.append(successor)
        rules_path.write_text(yaml.safe_dump(rules, sort_keys=False), encoding="utf-8")
        decisions_path = root / "framework/decisions.yaml"
        decisions = yaml.safe_load(decisions_path.read_text(encoding="utf-8"))
        decisions.append(dict(decisions[0], id="D-TASKS-002", supersedes="D-TASKS-001"))
        decisions[0]["supersedes"] = "D-TASKS-002"
        decisions_path.write_text(yaml.safe_dump(decisions, sort_keys=False), encoding="utf-8")
        result, codes, _ = self.codes(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SUPERSEDED_RULE_ACTIVE", codes)
        self.assertIn("SUPERSEDED_DECISION_ACTIVE", codes)
        self.assertIn("SUPERSESSION_CYCLE", codes)

    def test_base_comparison_protects_approved_rules_and_distinguishes_text(self):
        root = self.make_root()
        for command in (("git", "init", "-q", str(root)),
                        ("git", "-C", str(root), "config", "user.email", "test@example.invalid"),
                        ("git", "-C", str(root), "config", "user.name", "Validator test"),
                        ("git", "-C", str(root), "add", "."),
                        ("git", "-C", str(root), "commit", "-qm", "base")):
            subprocess.run(command, check=True, capture_output=True)
        path = root / "framework/contexts/tasks/rules/tasks.yaml"
        changed = path.read_text(encoding="utf-8").replace("meaningful title", "changed title")
        path.write_text(changed, encoding="utf-8")
        result = self.run_validator(root, True, "--base", "HEAD")
        payload = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("APPROVED_RULE_EDITED", {item["code"] for item in payload["findings"]})
        path.write_text(path.read_text(encoding="utf-8").replace("title: A task has a title", "title: Renamed"),
                        encoding="utf-8")
        result = self.run_validator(root, True, "--base", "HEAD")
        payload = json.loads(result.stdout)
        self.assertIn("APPROVED_RULE_TEXT_CHANGED", {item["code"] for item in payload["findings"]})
        path.write_text("[]\n", encoding="utf-8")
        result = self.run_validator(root, True, "--base", "HEAD")
        payload = json.loads(result.stdout)
        self.assertIn("RULE_ID_REMOVED", {item["code"] for item in payload["findings"]})

    def test_base_comparison_detects_all_removals_and_allows_deprecate_supersede(self):
        root = self.make_root()
        rules_path = root / "framework/contexts/tasks/rules/tasks.yaml"
        rules = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        proposed = dict(rules[0], id="BR-TASKS-002", status="proposed")
        proposed.pop("decision")
        rules.append(proposed)
        rules_path.write_text(yaml.safe_dump(rules, sort_keys=False), encoding="utf-8")
        for command in (("git", "init", "-q", str(root)),
                        ("git", "-C", str(root), "config", "user.email", "test@example.invalid"),
                        ("git", "-C", str(root), "config", "user.name", "Validator test"),
                        ("git", "-C", str(root), "add", "."),
                        ("git", "-C", str(root), "commit", "-qm", "base")):
            subprocess.run(command, check=True, capture_output=True)
        rules_path.write_text("[]\n", encoding="utf-8")
        result = self.run_validator(root, True, "--base", "HEAD")
        self.assertIn("RULE_ID_REMOVED", self.codes_from_result(result))

        root = self.make_root()
        for command in (("git", "init", "-q", str(root)),
                        ("git", "-C", str(root), "config", "user.email", "test@example.invalid"),
                        ("git", "-C", str(root), "config", "user.name", "Validator test"),
                        ("git", "-C", str(root), "add", "."),
                        ("git", "-C", str(root), "commit", "-qm", "base")):
            subprocess.run(command, check=True, capture_output=True)
        rules_path = root / "framework/contexts/tasks/rules/tasks.yaml"
        rules = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        rules[0]["status"] = "deprecated"
        rules.append(dict(rules[0], id="BR-TASKS-002", status="approved",
                          supersedes="BR-TASKS-001"))
        rules_path.write_text(yaml.safe_dump(rules, sort_keys=False), encoding="utf-8")
        scenarios_path = root / "framework/contexts/tasks/scenarios/tasks.yaml"
        scenarios_path.write_text(scenarios_path.read_text(encoding="utf-8").replace(
            "BR-TASKS-001", "BR-TASKS-002"), encoding="utf-8")
        result = self.run_validator(root, True, "--base", "HEAD")
        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("APPROVED_RULE_EDITED", {item["code"] for item in payload["findings"]})

    @staticmethod
    def codes_from_result(result):
        return {item["code"] for item in json.loads(result.stdout)["findings"]}

    def test_root_relative_exclusions_and_scope_isolation_regressions(self):
        root = self.make_root()
        rule = root / "framework/contexts/tasks/rules/tasks.yaml"
        rule.write_text(rule.read_text(encoding="utf-8").replace("D-TASKS-001", "D-TEST-001"),
                        encoding="utf-8")
        tests_log = root / "tests/decisions.yaml"
        tests_log.parent.mkdir()
        tests_log.write_text("- {id: D-TEST-001, title: Test, question: Test, decision: Test, status: approved, approver: test, date: '2026-10-02', source: test}\n",
                             encoding="utf-8")
        result, codes, _ = self.codes(root)
        self.assertIn("UNKNOWN_DECISION", codes)  # R-2: default root excludes tests.

        shutil.rmtree(root / "tests")
        explicit_root = root / "tests"
        shutil.copytree(FIXTURES / "valid", explicit_root)
        result, codes, _ = self.codes(explicit_root)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(codes, set())

        root = self.make_root()
        example = root / "framework/examples/isolation"
        (example / "rules").mkdir(parents=True)
        (example / "contracts").mkdir()
        (example / "decisions.yaml").write_text(
            "- {id: D-EXAMPLE-001, title: Example, question: Example, decision: Example, status: approved, approver: example, date: '2026-10-02', source: example}\n",
            encoding="utf-8")
        (example / "rules/rules.yaml").write_text(
            "- {id: BR-EXAMPLE-001, title: Example, statement: Example rule., type: invariant, status: approved, owner: example, decision: D-EXAMPLE-001, rationale: Example, verification: review}\n",
            encoding="utf-8")
        (example / "contracts/add.yaml").write_text(
            "id: tasks.add\nversion: 1.0.0\nkind: command\nsummary: Example command.\ntypes: {Value: Example value.}\ninput: {}\noutput: {}\nerrors: []\nsemantics: [Example behavior.]\n",
            encoding="utf-8")
        result, codes, _ = self.codes(root)
        self.assertEqual(result.returncode, 0, result.stdout)  # R-3: scopes are isolated.
        self.assertNotIn("DUPLICATE_ID", codes)

    def test_phrase_regressions_scan_glossaries_but_not_ordinary_rest(self):
        root = self.make_root()
        rules = root / "framework/contexts/tasks/rules/tasks.yaml"
        rules.write_text(rules.read_text(encoding="utf-8").replace(
            "A recorded task has a meaningful title.", "The rest of a recorded task has a meaningful title."),
            encoding="utf-8")
        result, codes, _ = self.codes(root)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("NEUTRALITY_WORD", codes)  # R-8

        glossary = root / "framework/contexts/tasks/glossary.md"
        glossary.write_text("| Term | Meaning |\n| --- | --- |\n| Service | REST API |\n", encoding="utf-8")
        result, codes, _ = self.codes(root)
        self.assertEqual(result.returncode, 0)
        self.assertIn("NEUTRALITY_WORD", codes)  # R-9

    def test_common_identifier_references_are_consistent(self):
        schemas = SOURCE / "framework/language/schemas"
        common = json.loads((schemas / "common.schema.json").read_text(encoding="utf-8"))
        registry = Registry().with_resource(common["$id"], Resource.from_contents(common))
        references = {
            "ruleId": ("BR-CORE-PRESERVATION-001", "BR-A--001"),
            "scenarioId": ("SC-CORE-PRESERVATION-001", "SC-A--001"),
            "decisionId": ("D-CORE-PRESERVATION-001", "D-A--001"),
            "eventRef": ("tasks.task-added@1", "tasks.task-added@x"),
        }
        for definition, (accepted, rejected) in references.items():
            validator = jsonschema.Draft202012Validator(
                {"$id": "https://aegis.dev/framework/language/schemas/test.schema.json",
                 "$ref": "common.schema.json#/$defs/" + definition}, registry=registry)
            self.assertFalse(list(validator.iter_errors(accepted)), definition)
            self.assertTrue(list(validator.iter_errors(rejected)), definition)
        for name in ("domain-rule.schema.json", "scenario.schema.json", "decision.schema.json",
                     "manifest.schema.json"):
            self.assertIn("common.schema.json#/$defs/", (schemas / name).read_text(encoding="utf-8"))

    def test_scenario_matcher_capture_setup_error_and_clock_regressions(self):
        matchers = ({"$contains": []}, {"$unordered": []}, {"$length": 0},
                    {"$absent": True}, {"$any": True})
        for matcher in matchers:
            with self.subTest(matcher=matcher):
                root = self.make_root()
                path = root / "framework/contexts/tasks/scenarios/tasks.yaml"
                scenario = yaml.safe_load(path.read_text(encoding="utf-8"))
                scenario[0]["then"]["output"] = {"item": matcher}
                path.write_text(yaml.safe_dump(scenario, sort_keys=False), encoding="utf-8")
                result, codes, _ = self.codes(root)
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertEqual(codes, set())

        root = self.make_root()
        path = root / "framework/contexts/tasks/scenarios/tasks.yaml"
        scenario = yaml.safe_load(path.read_text(encoding="utf-8"))
        scenario[0]["then"]["output"] = {"item": {"$contians": []}}
        path.write_text(yaml.safe_dump(scenario, sort_keys=False), encoding="utf-8")
        result, codes, _ = self.codes(root)
        self.assertIn("SCHEMA_INVALID", codes)

        def write_capture(root, reference):
            path = root / "framework/contexts/tasks/scenarios/tasks.yaml"
            scenario = yaml.safe_load(path.read_text(encoding="utf-8"))
            scenario[0]["given"] = {"steps": [
                {"command": "tasks.add", "input": {"title": "first"}, "as": "saved"}
            ]}
            scenario[0]["when"]["input"] = {"title": reference}
            path.write_text(yaml.safe_dump(scenario, sort_keys=False), encoding="utf-8")

        root = self.make_root()
        write_capture(root, "${saved.item.id}")
        result, codes, _ = self.codes(root)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(codes, set())
        root = self.make_root()
        write_capture(root, "${missing.item.id}")
        result, codes, _ = self.codes(root)
        self.assertIn("UNKNOWN_CAPTURE", codes)
        root = self.make_root()
        write_capture(root, "${saved.missing.id}")
        result, codes, _ = self.codes(root)
        self.assertIn("UNKNOWN_CAPTURE_OUTPUT", codes)

        for expected, code in (("TITLE_EMPTY", None), ("NOT_DECLARED", "UNKNOWN_ERROR_CODE")):
            root = self.make_root()
            path = root / "framework/contexts/tasks/scenarios/tasks.yaml"
            scenario = yaml.safe_load(path.read_text(encoding="utf-8"))
            scenario[0]["given"] = {"steps": [
                {"command": "tasks.add", "input": {"title": ""}, "expectError": expected}
            ]}
            path.write_text(yaml.safe_dump(scenario, sort_keys=False), encoding="utf-8")
            result, codes, _ = self.codes(root)
            if code:
                self.assertIn(code, codes)
            else:
                self.assertEqual(result.returncode, 0, result.stdout)

        for advance, valid in (("PT1H", True), ("tomorrow", False)):
            root = self.make_root()
            path = root / "framework/contexts/tasks/scenarios/tasks.yaml"
            scenario = yaml.safe_load(path.read_text(encoding="utf-8"))
            scenario[0]["given"] = {"clock": "2026-10-02T08:00:00Z", "steps": [{"advanceClock": advance}]}
            path.write_text(yaml.safe_dump(scenario, sort_keys=False), encoding="utf-8")
            result, codes, _ = self.codes(root)
            if valid:
                self.assertEqual(result.returncode, 0, result.stdout)
            else:
                self.assertIn("SCHEMA_INVALID", codes)

    def test_phrase_neutrality_glossary_contract_and_allowlist(self):
        root = self.make_root()
        glossary = root / "framework/contexts/tasks/glossary.md"
        glossary.write_text("| Term | Meaning |\n| --- | --- |\n| Service | REST API |\n", encoding="utf-8")
        contract = root / "framework/blocks/tasks/contracts/add.yaml"
        contract.write_text(contract.read_text(encoding="utf-8").replace("Record a task.", "REST API task."),
                            encoding="utf-8")
        result, codes, _ = self.codes(root)
        self.assertEqual(result.returncode, 0)
        self.assertIn("NEUTRALITY_WORD", codes)
        (root / "framework/contexts/tasks/neutrality-allow.txt").write_text("REST API\n", encoding="utf-8")
        (root / "framework/blocks/tasks/neutrality-allow.txt").write_text("REST API\n", encoding="utf-8")
        result, codes, _ = self.codes(root)
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("NEUTRALITY_WORD", codes)

    def test_strict_keeps_json_and_fails_warnings_only(self):
        root = self.make_root("coverage")
        normal = self.run_validator(root)
        strict = self.run_validator(root, True, "--strict")
        self.assertEqual(normal.returncode, 0)
        self.assertNotEqual(strict.returncode, 0)
        payload = json.loads(strict.stdout)
        self.assertEqual(payload["errors"], 0)
        self.assertGreater(payload["warnings"], 0)

    def test_base_comparison_protects_approved_decision_meaning_and_identity(self):
        changes = {
            "question": "May title-free tasks be recorded?",
            "decision": "Permit a title-free task",
            "status": "rejected",
            "approver": "another steward",
            "date": "2026-10-02",
            "source": "another source",
        }
        for field, replacement in changes.items():
            with self.subTest(field=field):
                root = self.make_root()
                self.commit_root(root)
                decisions_path = root / "framework/decisions.yaml"
                decisions = yaml.safe_load(decisions_path.read_text(encoding="utf-8"))
                decisions[0][field] = replacement
                decisions_path.write_text(yaml.safe_dump(decisions, sort_keys=False), encoding="utf-8")
                result = self.run_validator(root, True, "--base", "HEAD")
                self.assertIn("APPROVED_DECISION_EDITED",
                              self.codes_from_result(result))  # F-1 / CPR-006

        root = self.make_root()
        self.commit_root(root)
        decisions_path = root / "framework/decisions.yaml"
        decisions_path.write_text("[]\n", encoding="utf-8")
        result = self.run_validator(root, True, "--base", "HEAD")
        self.assertIn("DECISION_ID_REMOVED", self.codes_from_result(result))  # F-2

    def test_base_comparison_protects_approved_decision_supersedes_retargeting(self):
        root = self.make_root()
        decisions_path = root / "framework/decisions.yaml"
        decisions = yaml.safe_load(decisions_path.read_text(encoding="utf-8"))
        old = decisions[0]
        old["status"] = "superseded"
        other = dict(old, id="D-TASKS-002", title="Other old decision")
        current = dict(old, id="D-TASKS-003", title="Current", status="approved",
                       decision="Current decision", supersedes="D-TASKS-001")
        decisions.extend([other, current])
        decisions_path.write_text(yaml.safe_dump(decisions, sort_keys=False), encoding="utf-8")
        rules_path = root / "framework/contexts/tasks/rules/tasks.yaml"
        rules_path.write_text(rules_path.read_text(encoding="utf-8").replace(
            "D-TASKS-001", "D-TASKS-003"), encoding="utf-8")
        self.commit_root(root)

        decisions[-1]["supersedes"] = "D-TASKS-002"
        decisions_path.write_text(yaml.safe_dump(decisions, sort_keys=False), encoding="utf-8")
        result = self.run_validator(root, True, "--base", "HEAD")
        self.assertIn("APPROVED_DECISION_EDITED", self.codes_from_result(result))

    def test_base_comparison_warns_for_decision_text_and_allows_proposal_edits(self):
        root = self.make_root()
        decisions_path = root / "framework/decisions.yaml"
        decisions = yaml.safe_load(decisions_path.read_text(encoding="utf-8"))
        decisions[0]["affects"] = ["framework/contexts/tasks"]
        decisions.append({
            "id": "D-TASKS-002", "title": "Draft", "question": "Old question",
            "decision": "Old proposal", "status": "proposed",
        })
        decisions_path.write_text(yaml.safe_dump(decisions, sort_keys=False), encoding="utf-8")
        self.commit_root(root)

        decisions[0]["title"] = "Editorially renamed"
        decisions[0]["affects"] = ["framework/contexts/tasks", "docs"]
        decisions[1]["question"] = "New question"
        decisions[1]["decision"] = "A completely revised proposal"
        decisions_path.write_text(yaml.safe_dump(decisions, sort_keys=False), encoding="utf-8")
        result = self.run_validator(root, True, "--base", "HEAD")
        codes = self.codes_from_result(result)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("APPROVED_DECISION_TEXT_CHANGED", codes)
        self.assertNotIn("APPROVED_DECISION_EDITED", codes)

    def test_approved_decision_supersession_requires_and_accepts_replacement(self):
        root = self.make_root()
        self.commit_root(root)
        decisions_path = root / "framework/decisions.yaml"
        decisions = yaml.safe_load(decisions_path.read_text(encoding="utf-8"))
        decisions[0]["status"] = "superseded"
        decisions_path.write_text(yaml.safe_dump(decisions, sort_keys=False), encoding="utf-8")
        result = self.run_validator(root, True, "--base", "HEAD")
        codes = self.codes_from_result(result)
        self.assertIn("SUPERSESSION_MISSING", codes)
        self.assertIn("DECISION_NOT_APPROVED", codes)

        replacement = dict(decisions[0], id="D-TASKS-002", status="approved",
                           title="Replacement", decision="Require a useful title",
                           supersedes="D-TASKS-001")
        decisions.append(replacement)
        decisions_path.write_text(yaml.safe_dump(decisions, sort_keys=False), encoding="utf-8")
        rules_path = root / "framework/contexts/tasks/rules/tasks.yaml"
        rules = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        rules[0]["status"] = "deprecated"
        rules.append(dict(rules[0], id="BR-TASKS-002", status="approved",
                          decision="D-TASKS-002", supersedes="BR-TASKS-001"))
        rules_path.write_text(yaml.safe_dump(rules, sort_keys=False), encoding="utf-8")
        scenarios_path = root / "framework/contexts/tasks/scenarios/tasks.yaml"
        scenarios_path.write_text(scenarios_path.read_text(encoding="utf-8").replace(
            "BR-TASKS-001", "BR-TASKS-002"), encoding="utf-8")
        result = self.run_validator(root, True, "--base", "HEAD")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("SUPERSESSION_MISSING", self.codes_from_result(result))

    def test_capture_names_are_unique_and_failed_steps_produce_no_capture(self):
        root = self.make_root()
        path = root / "framework/contexts/tasks/scenarios/tasks.yaml"
        scenarios = yaml.safe_load(path.read_text(encoding="utf-8"))
        scenarios[0]["given"] = {"steps": [
            {"command": "tasks.add", "input": {"title": "first"}, "as": "saved"},
            {"command": "tasks.add", "input": {"title": "second"}, "as": "saved"},
        ]}
        path.write_text(yaml.safe_dump(scenarios, sort_keys=False), encoding="utf-8")
        result, codes, payload = self.codes(root)
        self.assertIn("DUPLICATE_CAPTURE", codes)  # F-3
        duplicate = next(item for item in payload["findings"]
                         if item["code"] == "DUPLICATE_CAPTURE")
        self.assertIn("given.steps[0]", duplicate["message"])
        self.assertIn("given.steps[1]", duplicate["message"])

        root = self.make_root()
        path = root / "framework/contexts/tasks/scenarios/tasks.yaml"
        scenarios = yaml.safe_load(path.read_text(encoding="utf-8"))
        scenarios[0]["given"] = {"steps": [{
            "command": "tasks.add", "input": {"title": ""},
            "expectError": "TITLE_EMPTY", "as": "failed",
        }]}
        scenarios[0]["when"]["input"]["title"] = "${failed.item.id}"
        path.write_text(yaml.safe_dump(scenarios, sort_keys=False), encoding="utf-8")
        result, codes, _ = self.codes(root)
        self.assertTrue({"SCHEMA_INVALID", "UNKNOWN_CAPTURE"}.issubset(codes), codes)  # F-4

    def test_bare_capture_reference_is_rejected(self):
        root = self.make_root()
        path = root / "framework/contexts/tasks/scenarios/tasks.yaml"
        scenarios = yaml.safe_load(path.read_text(encoding="utf-8"))
        scenarios[0]["given"] = {"steps": [
            {"command": "tasks.add", "input": {"title": "first"}, "as": "saved"},
        ]}
        scenarios[0]["when"]["input"]["title"] = "${saved}"
        path.write_text(yaml.safe_dump(scenarios, sort_keys=False), encoding="utf-8")
        result, codes, _ = self.codes(root)
        self.assertIn("BARE_CAPTURE_REFERENCE", codes)

        root = self.make_root()
        path = root / "framework/contexts/tasks/scenarios/tasks.yaml"
        scenarios = yaml.safe_load(path.read_text(encoding="utf-8"))
        scenarios[0]["given"] = {"steps": [
            {"command": "tasks.add", "input": {"title": "first"}, "as": "Saved"},
        ]}
        path.write_text(yaml.safe_dump(scenarios, sort_keys=False), encoding="utf-8")
        result, codes, _ = self.codes(root)
        self.assertIn("SCHEMA_INVALID", codes)

        for reference in ("prefix ${saved.item.id}", "${saved.item.id", "${saved.item.id} suffix"):
            with self.subTest(reference=reference):
                root = self.make_root()
                path = root / "framework/contexts/tasks/scenarios/tasks.yaml"
                scenarios = yaml.safe_load(path.read_text(encoding="utf-8"))
                scenarios[0]["given"] = {"steps": [
                    {"command": "tasks.add", "input": {"title": "first"}, "as": "saved"},
                ]}
                scenarios[0]["when"]["input"]["title"] = reference
                path.write_text(yaml.safe_dump(scenarios, sort_keys=False), encoding="utf-8")
                result, codes, _ = self.codes(root)
                self.assertIn("INVALID_CAPTURE_REFERENCE", codes)

    def test_project_initialization_and_maintenance_decision_guards(self):
        root = self.make_root()
        (root / "project.json").unlink()
        result, codes, payload = self.codes(root)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("PROJECT_NOT_INITIALIZED", codes)
        self.assertEqual(payload["errors"], 0)

        root = self.make_root()
        decisions_path = root / "framework/decisions.yaml"
        decisions = yaml.safe_load(decisions_path.read_text(encoding="utf-8"))
        decisions.append({
            "id": "D-AEGIS-001", "title": "Maintenance", "question": "How maintained?",
            "decision": "Maintain Aegis", "status": "approved", "approver": "maintainer",
            "date": "2026-10-02", "source": "maintenance",
        })
        decisions_path.write_text(yaml.safe_dump(decisions, sort_keys=False), encoding="utf-8")
        rules_path = root / "framework/contexts/tasks/rules/tasks.yaml"
        rules_path.write_text(rules_path.read_text(encoding="utf-8").replace(
            "D-TASKS-001", "D-AEGIS-001"), encoding="utf-8")
        result, codes, _ = self.codes(root)
        self.assertIn("MAINTENANCE_DECISION_CITED", codes)  # F-7

    def test_unknown_contract_types_warn_but_local_types_and_collections_pass(self):
        root = self.make_root()
        contract_path = root / "framework/blocks/tasks/contracts/add.yaml"
        contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
        contract["input"]["title"]["type"] = "MysteryScalar"
        contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
        result, codes, payload = self.codes(root)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("UNKNOWN_SCALAR_TYPE", codes)
        self.assertEqual(payload["errors"], 0)

        contract["types"]["MysteryScalar"] = "A locally defined semantic value."
        contract["input"]["title"]["type"] = "MysteryScalar[]"
        contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
        result, codes, _ = self.codes(root)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("UNKNOWN_SCALAR_TYPE", codes)

    def test_typed_literals_use_contract_declared_scalar_types(self):
        valid_values = {
            "string": "text", "boolean": True, "integer": 1, "number": 1.5,
            "decimal": 1.25, "date": "2026-10-02",
            "datetime": "2026-10-02T09:00Z", "duration": "PT2H", "id": "opaque-1",
        }
        root = self.make_root()
        contract_path = root / "framework/blocks/tasks/contracts/add.yaml"
        contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
        scenario_path = root / "framework/contexts/tasks/scenarios/tasks.yaml"
        scenarios = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
        for declared_type, value in valid_values.items():
            contract["input"][declared_type] = {
                "type": declared_type, "required": False, "description": declared_type,
            }
            scenarios[0]["when"]["input"][declared_type] = value
        contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
        scenario_path.write_text(yaml.safe_dump(scenarios, sort_keys=False), encoding="utf-8")
        result, codes, _ = self.codes(root)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("INVALID_TYPED_VALUE", codes)

        invalid_values = {
            "string": 1, "boolean": "true", "integer": 1.5, "number": "1",
            "decimal": "1.25", "date": "2026-02-30",
            "datetime": "not-a-date", "duration": "two hours", "id": 7,
        }
        for declared_type, value in invalid_values.items():
            with self.subTest(declared_type=declared_type):
                root = self.make_root()
                contract_path = root / "framework/blocks/tasks/contracts/add.yaml"
                contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
                contract["input"]["title"]["type"] = declared_type
                contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
                scenario_path = root / "framework/contexts/tasks/scenarios/tasks.yaml"
                scenarios = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
                scenarios[0]["when"]["input"]["title"] = value
                scenario_path.write_text(yaml.safe_dump(scenarios, sort_keys=False), encoding="utf-8")
                result, codes, _ = self.codes(root)
                self.assertIn("INVALID_TYPED_VALUE", codes)

        root = self.make_root()
        contract_path = root / "framework/blocks/tasks/contracts/add.yaml"
        contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
        contract["input"]["title"]["type"] = "datetime"
        contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
        scenario_path = root / "framework/contexts/tasks/scenarios/tasks.yaml"
        scenarios = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
        scenarios[0]["when"]["input"]["title"] = "2026-10-02T09:00"
        scenario_path.write_text(yaml.safe_dump(scenarios, sort_keys=False), encoding="utf-8")
        result, codes, _ = self.codes(root)
        self.assertIn("DATETIME_WITHOUT_OFFSET", codes)

    def test_typed_validation_covers_output_and_observation_expect(self):
        for route in ("output", "expect"):
            with self.subTest(route=route):
                root = self.make_root()
                scenario_path = root / "framework/contexts/tasks/scenarios/tasks.yaml"
                scenarios = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
                if route == "output":
                    contract_path = root / "framework/blocks/tasks/contracts/add.yaml"
                    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
                    contract["output"]["item"]["type"] = "datetime"
                    scenarios[0]["then"]["output"]["item"] = "not-a-date"
                else:
                    contract_path = root / "framework/blocks/tasks/contracts/list.yaml"
                    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
                    contract["output"]["items"]["type"] = "date"
                    scenarios[0]["then"]["observe"][0]["expect"]["items"] = "not-a-date"
                contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
                scenario_path.write_text(yaml.safe_dump(scenarios, sort_keys=False), encoding="utf-8")
                result, codes, _ = self.codes(root)
                self.assertIn("INVALID_TYPED_VALUE", codes)

    def test_typed_validation_skips_captures_matchers_and_opaque_nested_values(self):
        root = self.make_root()
        contract_path = root / "framework/blocks/tasks/contracts/add.yaml"
        contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
        contract["input"]["title"]["type"] = "datetime"
        contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
        scenario_path = root / "framework/contexts/tasks/scenarios/tasks.yaml"
        scenarios = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
        scenarios[0]["given"] = {"steps": [
            {"command": "tasks.add", "input": {"title": {"$any": True}}, "as": "saved"},
        ]}
        scenarios[0]["when"]["input"]["title"] = "${saved.item.title}"
        scenario_path.write_text(yaml.safe_dump(scenarios, sort_keys=False), encoding="utf-8")
        result, codes, _ = self.codes(root)
        self.assertNotIn("INVALID_TYPED_VALUE", codes)

        root = self.make_root()
        contract_path = root / "framework/blocks/tasks/contracts/add.yaml"
        contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
        contract["input"]["title"]["type"] = "Task"
        contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
        scenario_path = root / "framework/contexts/tasks/scenarios/tasks.yaml"
        scenarios = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
        scenarios[0]["when"]["input"]["title"] = {"dueAt": "not-a-date"}
        scenario_path.write_text(yaml.safe_dump(scenarios, sort_keys=False), encoding="utf-8")
        result, codes, _ = self.codes(root)
        self.assertNotIn("INVALID_TYPED_VALUE", codes)

    def test_base_loader_reports_malformed_yaml_and_duplicate_ids(self):
        root = self.make_root()
        decisions_path = root / "framework/decisions.yaml"
        valid_decisions = decisions_path.read_text(encoding="utf-8")
        decisions_path.write_text("- id: [unterminated\n", encoding="utf-8")
        self.commit_root(root)
        decisions_path.write_text(valid_decisions, encoding="utf-8")
        result = self.run_validator(root, True, "--base", "HEAD")
        self.assertIn("BASE_PARSE_ERROR", self.codes_from_result(result))

        for artifact in ("decision", "rule"):
            with self.subTest(artifact=artifact):
                root = self.make_root()
                if artifact == "decision":
                    path = root / "framework/decisions.yaml"
                else:
                    path = root / "framework/contexts/tasks/rules/tasks.yaml"
                records = yaml.safe_load(path.read_text(encoding="utf-8"))
                records.append(dict(records[0]))
                path.write_text(yaml.safe_dump(records, sort_keys=False), encoding="utf-8")
                self.commit_root(root)
                path.write_text(yaml.safe_dump(records[:1], sort_keys=False), encoding="utf-8")
                result = self.run_validator(root, True, "--base", "HEAD")
                self.assertIn("DUPLICATE_ID", self.codes_from_result(result))

    def test_template_hash_exemption_requires_canonical_origin(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "template-derived"
        (root / "framework").mkdir(parents=True)
        (root / "agents").mkdir()
        for relative in ("framework/decisions.yaml", "agents/decisions.yaml"):
            shutil.copy2(SOURCE / relative, root / relative)
        subprocess.run(("git", "init", "-q", str(root)), check=True)
        subprocess.run(("git", "-C", str(root), "remote", "add", "origin",
                        "git@github.com:someone-else/aegis.git"), check=True)
        result, codes, _ = self.codes(root)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("PROJECT_NOT_INITIALIZED", codes)

        subprocess.run(("git", "-C", str(root), "remote", "set-url", "origin",
                        "https://github.com/KoalasHut/aegis.git"), check=True)
        result, codes, _ = self.codes(root)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("PROJECT_NOT_INITIALIZED", codes)


if __name__ == "__main__":
    unittest.main()

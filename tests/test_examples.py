import datetime as dt
from pathlib import Path
import unittest
from zoneinfo import ZoneInfo

import yaml

from scripts.aegis_match import match
from scripts.aegis_types import build_registry


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "framework" / "examples"


class ShippedExampleMigrationTests(unittest.TestCase):
    def test_tiny_todo_has_one_task_and_task_state_definition(self):
        tiny = EXAMPLES / "tiny-todo"
        types = yaml.safe_load((tiny / "types.yaml").read_text())
        self.assertEqual({"Task", "TaskState"}, set(types["types"]))
        for contract_path in sorted((tiny / "contracts").glob("*.yaml")):
            contract = yaml.safe_load(contract_path.read_text())
            self.assertEqual({}, contract.get("types"), contract_path.name)
        registry = build_registry(context_types=types)
        expected = {"dueAt": "2026-10-02T09:00:00Z", "state": "open"}
        actual = {
            "id": "task-1", "title": "Review", "position": 1,
            "state": "open", "dueAt": "2026-10-02T06:00:00-03:00",
        }
        self.assertTrue(match(expected, actual, "Task", registry))

    def test_core_preservation_uses_one_structured_rule_definition(self):
        core = EXAMPLES / "core-preservation"
        types = yaml.safe_load((core / "types.yaml").read_text())
        rule = types["types"]["Rule"]
        self.assertIn("fields", rule)
        self.assertEqual({"title", "owner", "decision", "status"},
                         set(rule["fields"]))
        for contract_path in sorted((core / "contracts").glob("*.yaml")):
            contract = yaml.safe_load(contract_path.read_text())
            self.assertEqual({}, contract.get("types"), contract_path.name)

    def test_timezone_pair_changes_only_zone_and_expected_local_date_outcome(self):
        scenarios = yaml.safe_load(
            (EXAMPLES / "tiny-todo" / "scenarios" / "task-lifecycle.yaml").read_text())
        by_id = {scenario["id"]: scenario for scenario in scenarios}
        utc = by_id["SC-TODO-005"]
        sao_paulo = by_id["SC-TODO-006"]
        self.assertEqual("UTC", utc["given"]["timezone"])
        self.assertEqual("America/Sao_Paulo", sao_paulo["given"]["timezone"])
        for key in ("clock", "steps"):
            self.assertEqual(utc["given"][key], sao_paulo["given"][key])
        self.assertEqual(utc["when"], sao_paulo["when"])
        utc_item = utc["then"]["output"]["items"]["$contains"][0]
        sao_item = sao_paulo["then"]["output"]["items"]["$contains"][0]
        self.assertEqual({key: value for key, value in utc_item.items() if key != "urgency"},
                         {key: value for key, value in sao_item.items() if key != "urgency"})
        self.assertEqual(("due-today", "scheduled"),
                         (utc_item["urgency"], sao_item["urgency"]))

        def instant(value):
            return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))

        due_at = instant(utc["given"]["steps"][0]["input"]["dueAt"])
        local_date_equalities = []
        for scenario in (utc, sao_paulo):
            zone = ZoneInfo(scenario["given"]["timezone"])
            local_date_equalities.append(
                due_at.astimezone(zone).date()
                == instant(scenario["given"]["clock"]).astimezone(zone).date()
            )
        self.assertEqual([True, False], local_date_equalities)

        tiny = EXAMPLES / "tiny-todo"
        rules = {item["id"]: item for item in yaml.safe_load(
            (tiny / "rules" / "rules.yaml").read_text())}
        decisions = {item["id"]: item for item in yaml.safe_load(
            (tiny / "decisions.yaml").read_text())}
        self.assertEqual("D-TODO-007", rules["BR-TODO-007"]["decision"])
        self.assertEqual("approved", decisions["D-TODO-007"]["status"])


if __name__ == "__main__":
    unittest.main()

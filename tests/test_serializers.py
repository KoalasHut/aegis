import json
from pathlib import Path
import subprocess
import unittest

import yaml

from scripts.aegis_match import match


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests" / "fixtures" / "serializers"


class SerializerCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = yaml.safe_load((CORPUS / "manifest.yaml").read_text())

    def test_every_executed_fixture_has_checked_in_source_and_provenance(self):
        self.assertEqual({"Python", "JavaScript", ".NET"},
                         {item["stack"] for item in self.manifest["executed"]})
        for entry in self.manifest["executed"]:
            with self.subTest(stack=entry["stack"]):
                fixture = json.loads((CORPUS / entry["fixture"]).read_text())
                self.assertEqual("verified-local", entry["status"])
                self.assertEqual(entry["stack"], fixture["stack"])
                self.assertTrue((CORPUS / entry["source"]).is_file())
                self.assertTrue(fixture["runtime"])
                self.assertTrue(fixture["library"])
                self.assertTrue(fixture["options"])

    def test_corpus_values_match_canonical_protocol_values(self):
        python = json.loads((CORPUS / "python.json").read_text())
        javascript = json.loads((CORPUS / "javascript.json").read_text())
        dotnet = json.loads((CORPUS / "dotnet.json").read_text())
        self.assertTrue(match("2026-10-02T09:00:00Z",
                              python["observed"]["datetime"], "datetime"))
        self.assertTrue(match("2026-10-02T09:00:00Z",
                              javascript["observed"]["datetime"], "datetime"))
        dotnet_default = json.loads(dotnet["observed"]["serializedDefault"])
        self.assertTrue(match("2026-10-02T09:00:00Z",
                              dotnet_default["Datetime"], "datetime"))
        self.assertTrue(match("10.50", dotnet_default["Decimal"], "decimal"))
        self.assertIsNone(dotnet_default["Note"])
        self.assertNotIn("Note", json.loads(dotnet["observed"]["serializedOmitNull"]))
        self.assertEqual(9007199254740992,
                         javascript["observed"]["unsafeInteger"])

    def test_unavailable_stacks_are_deferred_without_claimed_fixtures(self):
        deferred = {item["stack"]: item for item in self.manifest["deferred"]}
        self.assertEqual({"Kotlin/JVM", "Swift"}, set(deferred))
        self.assertTrue(all(item["status"] == "unavailable-unverified"
                            for item in deferred.values()))
        self.assertNotIn("fixture", deferred["Kotlin/JVM"])
        self.assertNotIn("fixture", deferred["Swift"])


if __name__ == "__main__":
    unittest.main()

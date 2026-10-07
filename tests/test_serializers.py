import json
import os
from pathlib import Path
import shlex
import shutil
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
        self.assertEqual("0.2.4", self.manifest["protocolVersion"])
        self.assertEqual({"Python", "JavaScript", ".NET", "Kotlin/JVM"},
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
                self.assertTrue(entry["command"])

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

    def test_kotlin_probe_reproduces_checked_in_fixture(self):
        entry = next(item for item in self.manifest["executed"]
                     if item["stack"] == "Kotlin/JVM")
        self.assertEqual("kotlin/Probe.kt", entry["source"])
        self.assertEqual("kotlin/probe.sh", entry["runner"])
        cache_root = Path(os.environ.get("GRADLE_USER_HOME", Path.home() / ".gradle"))
        artifacts = (
            ("org.jetbrains.kotlin/kotlin-compiler-embeddable", "2.1.20",
             "kotlin-compiler-embeddable-2.1.20.jar"),
            ("org.jetbrains.kotlin/kotlin-stdlib", "2.1.20", "kotlin-stdlib-2.1.20.jar"),
            ("org.jetbrains.kotlin/kotlin-reflect", "2.1.20", "kotlin-reflect-2.1.20.jar"),
            ("org.jetbrains.intellij.deps/trove4j", "1.0.20200330", "trove4j-1.0.20200330.jar"),
            ("org.jetbrains.kotlinx/kotlinx-coroutines-core-jvm", "1.8.0",
             "kotlinx-coroutines-core-jvm-1.8.0.jar"),
            ("com.fasterxml.jackson.core/jackson-databind", "2.11.1", "jackson-databind-2.11.1.jar"),
            ("com.fasterxml.jackson.core/jackson-core", "2.11.1", "jackson-core-2.11.1.jar"),
            ("com.fasterxml.jackson.core/jackson-annotations", "2.11.1", "jackson-annotations-2.11.1.jar"),
        )
        available = all(any((cache_root / "caches/modules-2/files-2.1" / coordinate / version).glob(
            "*/" + filename)) for coordinate, version, filename in artifacts)
        if not available or shutil.which("java") is None:
            self.skipTest("pinned local Kotlin/Jackson probe toolchain is unavailable")
        result = subprocess.run(shlex.split(entry["command"]), cwd=ROOT,
                                text=True, capture_output=True)
        self.assertEqual(0, result.returncode, result.stderr)
        observed = json.loads(result.stdout)
        fixture = json.loads((CORPUS / entry["fixture"]).read_text())
        self.assertEqual(fixture, observed)
        self.assertTrue(match("2026-10-02T09:00:00Z",
                              observed["observed"]["instant"], "datetime"))
        self.assertEqual("2026-10-02T09:00Z",
                         observed["observed"]["offsetDateTime"])
        self.assertEqual("10.50", observed["observed"]["decimalSerialized"])
        self.assertEqual('{"note":null}', observed["observed"]["serializedDefault"])
        self.assertEqual("{}", observed["observed"]["serializedOmitNull"])

    def test_unavailable_stacks_are_deferred_without_claimed_fixtures(self):
        deferred = {item["stack"]: item for item in self.manifest["deferred"]}
        self.assertEqual({"Swift"}, set(deferred))
        self.assertTrue(all(item["status"] == "unavailable-unverified"
                            for item in deferred.values()))
        self.assertNotIn("fixture", deferred["Swift"])
        self.assertNotIn("observed", deferred["Swift"])


if __name__ == "__main__":
    unittest.main()

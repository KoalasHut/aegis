from pathlib import Path
import unittest

import yaml

from scripts.aegis_match import match
from scripts.aegis_types import load_types_document
from tests.corpus_support import execute_corpus_operation, execute_project_operation


ROOT = Path(__file__).resolve().parents[1]
REGRESSIONS = ROOT / "tests" / "regressions"


class HistoricalRegressionCorpusTests(unittest.TestCase):
    def test_manifest_is_complete_unique_and_has_no_orphans(self):
        manifest = yaml.safe_load((REGRESSIONS / "manifest.yaml").read_text())["ids"]
        expected = ([f"R-{number}" for number in range(1, 10)]
                    + [f"F-{number}" for number in range(1, 8)]
                    + [f"G-{number}" for number in range(1, 7)]
                    + [f"K-{number}" for number in range(1, 11)])
        self.assertEqual(expected, manifest)
        self.assertEqual(len(manifest), len(set(manifest)))
        fixtures = sorted(path.parent.name for path in REGRESSIONS.glob("*/case.yaml"))
        self.assertEqual(sorted(manifest), fixtures)

    def test_every_fixture_has_one_exact_executable_outcome(self):
        for path in sorted(REGRESSIONS.glob("*/case.yaml")):
            case = yaml.safe_load(path.read_text())
            with self.subTest(regression=case["id"]):
                self.assertEqual(path.parent.name, case["id"])
                if case["kind"] == "match":
                    self.assertIs(case["result"], match(
                        case["expected"], case["actual"], case.get("type")))
                elif case["kind"] == "validator":
                    for run in case["runs"]:
                        with self.subTest(operation=run["operation"]):
                            self.assertEqual(run["expectedFindings"],
                                             execute_project_operation(run["operation"]))
                elif case["kind"] == "artifact":
                    document = yaml.safe_load((ROOT / case["path"]).read_text())
                    declarations = load_types_document(document)
                    self.assertEqual(set(case["requiredTypes"]),
                                     set(case["requiredTypes"]) & set(declarations))
                elif case["kind"] == "production":
                    result = execute_corpus_operation(case["operation"], case.get("cli", False))
                    self.assertEqual(case["expectedFindings"], result["api"])
                    if case.get("cli"):
                        self.assertEqual(case["expectedFindings"], result["cli"])
                        self.assertEqual(case.get("exitNonzero", False), result["exitCode"] != 0)
                        if case.get("noTraceback"):
                            self.assertNotIn("Traceback", result["stderr"])
                elif case["kind"] == "production-runs":
                    for run in case["runs"]:
                        with self.subTest(operation=run["operation"]):
                            self.assertEqual(
                                run["expectedFindings"],
                                execute_corpus_operation(run["operation"])["api"],
                            )
                else:
                    self.fail("unknown regression kind: " + case["kind"])


if __name__ == "__main__":
    unittest.main()

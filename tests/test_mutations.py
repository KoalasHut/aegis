from pathlib import Path
import unittest

import yaml

from tests.corpus_support import execute_corpus_operation


ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = ROOT / "tests" / "fixtures" / "mutations.yaml"


class ValidatorMutationArchitectureTests(unittest.TestCase):
    def test_all_mutations_have_exact_visible_production_findings(self):
        mutations = yaml.safe_load(MUTATIONS.read_text())["mutations"]
        self.assertEqual([f"MUT-{number:02d}" for number in range(1, 41)],
                         [item["id"] for item in mutations])
        self.assertEqual(len(mutations), len({item["edit"] for item in mutations}))
        for mutation in mutations:
            with self.subTest(mutation=mutation["id"]):
                self.assertEqual(
                    mutation["expectedFindings"],
                    execute_corpus_operation(mutation["operation"])["api"],
                )

    def test_type_definition_mutations_stay_at_the_definition_site(self):
        mutations = yaml.safe_load(MUTATIONS.read_text())["mutations"]
        by_id = {mutation["id"]: mutation for mutation in mutations}
        for mutation_id in ("MUT-31", "MUT-35", "MUT-38", "MUT-39", "MUT-40"):
            with self.subTest(mutation=mutation_id):
                findings = execute_corpus_operation(by_id[mutation_id]["operation"])["api"]
                self.assertTrue(findings)
                self.assertTrue(all(item["path"] == "framework/contexts/tasks/types.yaml"
                                    for item in findings))


if __name__ == "__main__":
    unittest.main()

import hashlib
import json
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import jsonschema


SOURCE = Path(__file__).resolve().parents[1]


class InitializationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "clone"
        self.root.mkdir()
        for relative in ("VERSION", "scripts/init.py", "docs/PROJECT_README.template.md", "README.md",
                         "framework/decisions.yaml", "agents/decisions.yaml"):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / relative, target)

    def run_init(self, *extra, name="sample-project"):
        return subprocess.run([sys.executable, str(self.root / "scripts/init.py"),
                               "--name", name, *extra], cwd=self.temp.name,
                              text=True, capture_output=True)

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob("*") if p.is_file()}

    def test_success_and_identical_repeat_from_other_directory(self):
        before = (self.root / "README.md").read_bytes()
        result = self.run_init("--description", "A test project")
        self.assertEqual(result.returncode, 0, result.stderr)
        metadata = json.loads((self.root / "project.json").read_text())
        self.assertEqual(metadata["name"], "sample-project")
        self.assertEqual(metadata["aegis"]["version"], "0.2.4")
        self.assertIn("NOT ADMITTED", (self.root / "docs/discussion/initial-assignment.draft.md").read_text())
        self.assertEqual((self.root / "framework/decisions.yaml").read_text(), "[]\n")
        self.assertEqual((self.root / "agents/decisions.yaml").read_text(), "[]\n")
        self.assertEqual(before, (self.root / "README.md").read_bytes())
        snapshot = self.snapshot()
        mtimes = {p: p.stat().st_mtime_ns for p in self.root.rglob("*")}
        self.assertEqual(self.run_init("--description", "A test project").returncode, 0)
        self.assertEqual(snapshot, self.snapshot())
        self.assertEqual(mtimes, {p: p.stat().st_mtime_ns for p in self.root.rglob("*")})

    def test_dry_run_writes_nothing(self):
        before = self.snapshot()
        result = self.run_init("--dry-run")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Would replace framework/decisions.yaml", result.stdout)
        self.assertIn("Would create project.json", result.stdout)
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.root / "docs/discussion").exists())

    def test_exact_bundled_maintenance_logs_are_replaced_with_valid_empty_project_logs(self):
        result = self.run_init()
        self.assertEqual(result.returncode, 0, result.stderr)
        for relative in ("framework/decisions.yaml", "agents/decisions.yaml"):
            self.assertEqual((self.root / relative).read_bytes(), b"[]\n")
        schema = json.loads((SOURCE / "framework/language/schemas/decision.schema.json").read_text())
        validator = jsonschema.Draft202012Validator(schema)
        validator.validate([])

    def test_bundled_maintenance_hashes_match_the_release_logs(self):
        spec = importlib.util.spec_from_file_location("aegis_test_init_hashes", SOURCE / "scripts/init.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual({
            "framework/decisions.yaml": "658ed7b34f44b2870803f6365e8a1843c40df1a0f8be8e8a3655c78a85127c76",
            "agents/decisions.yaml": "73e67f6a4aa119079e8b41b0697f1996c89bc0911efdacc4fc20411d5025ec01",
        }, module.MAINTENANCE_LOG_HASHES)
        for relative, expected in module.MAINTENANCE_LOG_HASHES.items():
            actual = hashlib.sha256((SOURCE / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, relative)

    def test_edited_or_unrecognized_maintenance_log_is_a_preflight_collision(self):
        log = self.root / "framework/decisions.yaml"
        log.write_text("[]\n", encoding="utf-8")
        before = self.snapshot()
        result = self.run_init()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, self.snapshot())

    def test_mutation_failure_rolls_back_replaced_logs_and_created_outputs(self):
        spec = importlib.util.spec_from_file_location("aegis_test_init", self.root / "scripts/init.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        calls = []

        def fail_after_two(path, content, replace):
            calls.append(path)
            if len(calls) == 3:
                raise OSError("simulated interrupted write")
            module.write_output(path, content, replace)

        before = self.snapshot()
        with self.assertRaises(OSError):
            module.initialize(self.root, "sample-project", "", writer=fail_after_two)
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.root / "project.json").exists())

    def test_brief_starts_with_problem_and_preserves_proposal_status(self):
        result = self.run_init("--description", "People lose track of follow-up work")
        self.assertEqual(result.returncode, 0, result.stderr)
        brief = (self.root / "docs/discussion/initial-brief.md").read_text()
        sections = ["## Problem", "## Who and when", "## Desired outcome",
                    "## Signals of success", "## Evidence", "## Alternatives",
                    "## Proposals"]
        positions = [brief.index(section) for section in sections]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("People lose track of follow-up work", brief)
        self.assertIn("Candidate domain rules (status: proposed)", brief)
        self.assertIn("Candidate scenarios (plain language)", brief)
        self.assertIn("no decisions or approvals recorded", brief)
        self.assertIn("question tools", brief)
        self.assertIn("never implementation precedent", brief)

    def test_upgrade_does_not_overwrite_existing_project_documents(self):
        self.assertEqual(self.run_init().returncode, 0)
        (self.root / "VERSION").write_text("0.3.0\n")
        before = self.snapshot()
        result = self.run_init()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, self.snapshot())

    def test_configuration_change_is_non_destructive(self):
        self.assertEqual(self.run_init().returncode, 0)
        before = self.snapshot()
        for args in (("--description", "changed"), ()):
            result = self.run_init(*args, name="different-project")
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(before, self.snapshot())

    def test_unicode_description_is_preserved(self):
        description = "Colaboração com decisões explícitas 🛡"
        result = self.run_init("--description", description)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root / "project.json").read_text())["description"], description)
        self.assertIn(description, (self.root / "docs/PROJECT.md").read_text())

    def test_late_collision_prevents_all_writes(self):
        target = self.root / "docs/discussion/initial-assignment.draft.md"
        target.parent.mkdir()
        target.write_text("User work")
        before = self.snapshot()
        self.assertNotEqual(self.run_init().returncode, 0)
        self.assertEqual(before, self.snapshot())

    def test_symlink_parent_cannot_escape(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (self.root / "docs/discussion").symlink_to(outside, target_is_directory=True)
        self.assertNotEqual(self.run_init().returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.root / "project.json").exists())

    def test_dangling_output_symlink_refused(self):
        (self.root / "project.json").symlink_to(Path(self.temp.name) / "absent")
        self.assertNotEqual(self.run_init().returncode, 0)
        self.assertFalse((self.root / "docs/PROJECT.md").exists())

    def test_bad_inputs_write_nothing(self):
        before = self.snapshot()
        for name in ("../escape", "Bad Name", "", "a" * 81, "a--b"):
            self.assertNotEqual(self.run_init(name=name).returncode, 0)
        for description in ("x" * 351, "two\nlines", "tab\there"):
            self.assertNotEqual(self.run_init("--description", description).returncode, 0)
        self.assertEqual(before, self.snapshot())


if __name__ == "__main__":
    unittest.main()

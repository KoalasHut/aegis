import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1]


class InitializationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "clone"
        self.root.mkdir()
        for relative in ("VERSION", "scripts/init.py", "docs/PROJECT_README.template.md", "README.md"):
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
        self.assertEqual(metadata["aegis"]["version"], "0.1.0")
        self.assertIn("NOT ADMITTED", (self.root / "docs/discussion/initial-assignment.draft.md").read_text())
        self.assertEqual(before, (self.root / "README.md").read_bytes())
        snapshot = self.snapshot()
        mtimes = {p: p.stat().st_mtime_ns for p in self.root.rglob("*")}
        self.assertEqual(self.run_init("--description", "A test project").returncode, 0)
        self.assertEqual(snapshot, self.snapshot())
        self.assertEqual(mtimes, {p: p.stat().st_mtime_ns for p in self.root.rglob("*")})

    def test_dry_run_writes_nothing(self):
        before = self.snapshot()
        self.assertEqual(self.run_init("--dry-run").returncode, 0)
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.root / "docs/discussion").exists())

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

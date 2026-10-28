import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "enumerate_diff.py"


class EnumerateDiffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        self.write("src/counter.py", "def main(value):\n    return value\n\ndef removed():\n    return 0\n")
        self.write("tests/test_counter.py", "def test_count():\n    assert main(1) == 1\n")
        self.write("old.txt", "old\n")
        self.write("delete.txt", "gone\n")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.base_head = self.git("rev-parse", "HEAD")
        self.git("switch", "-qc", "change")
        self.write("src/counter.py", "def main(value):\n    # pragma: no cover\n    return value + 1\n")
        self.write("tests/test_counter.py", "import pytest\n@pytest.mark.skip\ndef test_count():\n    label = 'it.skip()'\n    # xfail is only a comment\n    assert main(1) == 2\n")
        self.write("new.txt", "new\n")
        (self.root / "delete.txt").unlink()
        (self.root / "old.txt").rename(self.root / "renamed.txt")
        self.git("add", "-A")
        self.git("commit", "-qm", "head")

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, text=True).stdout.strip()

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.root, capture_output=True, text=True)

    def enumerate(self):
        out = self.root / "result.json"
        before = (self.git("rev-parse", "HEAD"), self.git("write-tree"), (self.root / "src/counter.py").read_bytes())
        proc = self.run_cli("--cwd", str(self.root), "--base", "main", "--out", str(out))
        after = (self.git("rev-parse", "HEAD"), self.git("write-tree"), (self.root / "src/counter.py").read_bytes())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "")
        self.assertEqual(before, after)
        return json.loads(out.read_text(encoding="utf-8"))

    def test_requires_all_cli_arguments(self):
        self.assertEqual(self.run_cli().returncode, 2)

    def test_reports_missing_ref_as_error(self):
        proc = self.run_cli("--cwd", str(self.root), "--base", "no-such-ref", "--out", "out.json")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("enumerate_diff.py:", proc.stderr)

    def test_enumerates_file_statuses_and_python_changes_without_mutation(self):
        data = self.enumerate()
        files = {item["path"]: item for item in data["files"]}
        self.assertEqual({item["status"] for item in files.values()}, {"added", "deleted", "modified", "renamed"})
        self.assertEqual(files["renamed.txt"]["old_path"], "old.txt")
        counter = files["src/counter.py"]
        main = next(item for item in counter["functions"] if item["name"] == "main")
        removed = next(item for item in counter["functions"] if item["name"] == "removed")
        self.assertEqual((main["change"], main["base"]["start_line"], main["head"]["start_line"]), ("modified", 1, 1))
        self.assertEqual(removed["change"], "deleted")
        test = next(item for item in files["tests/test_counter.py"]["tests"] if item["name"] == "test_count")
        self.assertTrue(test["body_changed"])
        self.assertIn("main(1) == 1", test["base"]["body"])
        self.assertIn("main(1) == 2", test["head"]["body"])
        self.assertEqual([item["marker"] for item in files["tests/test_counter.py"]["markers_added"]], ["pytest.mark.skip"])
        self.assertTrue(any(item["key"] == "pragma: no cover" for item in counter["coverage_changes"]))
        self.assertTrue(counter["hunks"])
        changed_line = next(line for line in counter["hunks"][0]["lines"] if line["kind"] == "added")
        self.assertEqual(changed_line["head_line"], 2)
        self.assertEqual(data["summary"]["changed_files"], len(data["files"]))
        self.assertEqual(data["summary"]["function_changes"], sum(len(item["functions"]) for item in data["files"]))
        self.assertEqual(data["summary"]["declaration_changes"], sum(len(item["declarations"]) for item in data["files"]))
        self.assertEqual(data["summary"]["test_changes"], sum(len(item["tests"]) for item in data["files"]))
        self.assertEqual(data["summary"]["coverage_changes"], sum(len(item["coverage_changes"]) for item in data["files"]))
        self.assertEqual(data["summary"]["unsupported"], len(data["unsupported"]))


if __name__ == "__main__":
    unittest.main()

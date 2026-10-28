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
        self.write("src/counter.py", "def main(value):\n    # pragma: no cover\n    return value + 1\n\ndef added():\n    return 2\n")
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


    def test_masks_strings_before_comments_without_exposing_string_contents(self):
        sys.path.insert(0, str(SCRIPT.parent))
        import enumerate_diff
        masked = enumerate_diff.mask_non_code('x = "test.skip // example"')
        self.assertEqual(len(masked), len('x = "test.skip // example"'))
        self.assertNotIn('test.skip', masked)
        self.assertIn('#[ignore]', enumerate_diff.mask_non_code('#[ignore]', 'rust'))
        source = 'x = "# pragma: no cover" # comment'
        masked = enumerate_diff.mask_non_code(source, 'python')
        self.assertEqual(len(masked), len(source))
        self.assertNotIn('pragma: no cover', masked)

    def test_generic_symbols_ignores_control_keywords_and_braces_in_strings(self):
        sys.path.insert(0, str(SCRIPT.parent))
        import enumerate_diff
        source = 'function foo(a) {\n  if (a) { return 1 }\n  const s = "}";\n}\n'
        symbols = enumerate_diff.generic_symbols(source, 'javascript')
        foo = next(item for item in symbols if item['name'] == 'foo')
        self.assertEqual(foo['end_line'], 4)
        self.assertFalse(any(item['name'] == 'if' for item in symbols))

    def test_generic_test_calls_are_named_test_symbols(self):
        sys.path.insert(0, str(SCRIPT.parent))
        import enumerate_diff
        symbols = enumerate_diff.generic_symbols('it("adds", () => { expect(1).toBe(1) })\ntest.each([1])(\'works\', () => {})', 'javascript')
        self.assertEqual([(item['kind'], item['name']) for item in symbols if item['kind'] == 'test'], [('test', 'adds'), ('test', 'works')])

    def test_rust_test_attribute_marks_function_as_test(self):
        sys.path.insert(0, str(SCRIPT.parent))
        import enumerate_diff
        symbols = enumerate_diff.generic_symbols('#[test]\nfn adds() { assert_eq!(1, 1); }', 'rust')
        self.assertEqual([(item['kind'], item['name']) for item in symbols], [('test', 'adds')])

    def test_coverage_config_scopes_pyproject_and_keeps_unknown_changes(self):
        sys.path.insert(0, str(SCRIPT.parent))
        import enumerate_diff
        hunks = enumerate_diff.parse_hunks('@@ -1,2 +1,3 @@\n [tool.other]\n-exclude = ["old"]\n+[tool.coverage.run]\n+omit = ["generated/*"]\n')
        changes = enumerate_diff.coverage_changes('pyproject.toml', hunks)
        self.assertEqual([(item['category'], item['key']) for item in changes], [('unknown', 'omit')])

    def test_python_function_ranges_include_added_and_both_modified_ends(self):
        data = self.enumerate()
        counter = {item['path']: item for item in data['files']}['src/counter.py']
        main = next(item for item in counter['functions'] if item['name'] == 'main')
        removed = next(item for item in counter['functions'] if item['name'] == 'removed')
        added = next(item for item in counter['functions'] if item['name'] == 'added')
        self.assertEqual((main['base']['end_line'], main['head']['end_line']), (2, 3))
        self.assertEqual(removed['base']['end_line'], 5)
        self.assertEqual((added['change'], added['head']['start_line'], added['head']['end_line']), ('added', 5, 6))


if __name__ == "__main__":
    unittest.main()

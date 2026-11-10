#!/usr/bin/env python3
"""Enumerate mechanically detectable facts in a Git base...HEAD diff."""

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path


LANGUAGES = {".py": "python", ".ts": "typescript", ".tsx": "typescript", ".mts": "typescript", ".cts": "typescript", ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".rs": "rust", ".svelte": "svelte"}
MARKER_RE = re.compile(r"pytest\.mark\.(skip|skipif|xfail)|unittest\.(skip|skipIf)|\.(skip|todo|only|fails)\b|\b(xit|xtest|xdescribe|fit|fdescribe)\b|#\s*\[\s*ignore\s*\]")
COVER_RE = re.compile(r"pragma:\s*no cover|istanbul ignore|#\s*\[\s*cfg\s*\(\s*not\s*\(\s*tarpaulin\s*\)\s*\)\s*\]")


def mask_strings(line):
    return re.sub(r"(['\"`])(?:\\.|(?!\1).)*\1", lambda match: " " * len(match.group(0)), line)


def mask_non_code(line, lang=None):
    line = mask_strings(line)
    line = re.sub(r"//.*|/\*.*?\*/", lambda match: " " * len(match.group(0)), line)
    if lang != "rust":
        line = re.sub(r"#.*", lambda match: " " * len(match.group(0)), line)
    return line


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True).stdout


def language(path):
    return LANGUAGES.get(Path(path).suffix.lower())


def parse_hunks(patch):
    result = []
    current = None
    base_line = head_line = 0
    for line in patch.splitlines():
        match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)", line)
        if match:
            current = {"header": line, "base": {"start_line": int(match[1]), "line_count": int(match[2] or 1)}, "head": {"start_line": int(match[3]), "line_count": int(match[4] or 1)}, "lines": [], "patch": line + "\n"}
            result.append(current)
            base_line, head_line = int(match[1]), int(match[3])
        elif current is not None and line[:1] in (" ", "+", "-"):
            kind = {" ": "context", "+": "added", "-": "removed"}[line[0]]
            current["lines"].append({"kind": kind, "text": line[1:], "base_line": base_line if kind != "added" else None, "head_line": head_line if kind != "removed" else None})
            current["patch"] += line + "\n"
            if kind != "added": base_line += 1
            if kind != "removed": head_line += 1
    return result


def python_symbols(text):
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [], [{"path": "", "area": "python-parse", "reason": "Python source could not be parsed", "base_lines": "file", "head_lines": "file"}]
    found = []
    def walk(nodes, scope=""):
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                kind = "class" if isinstance(node, ast.ClassDef) else "function"
                name = f"{scope}.{node.name}" if scope else node.name
                end = getattr(node, "end_lineno", node.lineno)
                segment = ast.get_source_segment(text, node) or ""
                signature = segment.splitlines()[0].strip()
                found.append({"kind": kind, "name": name, "start_line": node.lineno, "end_line": end, "signature": signature, "body": segment})
                walk(node.body, name)
    walk(tree.body)
    return found, []


def generic_symbols(text, lang):
    source = text
    if lang == "svelte":
        source = re.sub(r"<script\b[^>]*>(.*?)</script\s*>", lambda match: "\n" * match.group(0).count("\n") + match.group(1), text, flags=re.S | re.I)
        source = re.sub(r"<script\b[^>]*>.*", "", source, flags=re.S | re.I)
    masked = "\n".join(mask_non_code(line, lang) for line in source.splitlines())
    patterns = [
        ("function", re.compile(r"\b(?:function\s+|fn\s+|(?:async\s+)?)([A-Za-z_$][\w$]*)\s*\([^;{}]*\)\s*(?:->[^{}]+)?\{")),
        ("declaration", re.compile(r"\b(const|let|var|class|struct|enum|type)\s+([A-Za-z_$][\w$]*)")),
    ]
    symbols = []
    reserved = {"if", "for", "while", "switch", "catch", "match", "return", "else", "do", "try", "new", "throw", "typeof", "await", "yield"}
    for kind, pattern in patterns:
        for match in pattern.finditer(masked):
            if kind == "function" and match[1] in reserved:
                continue
            start = source.count("\n", 0, match.start()) + 1
            end = match.end()
            if kind == "function" or match[1] in {"class", "struct", "enum", "type"}:
                opening = masked.find("{", match.start(), min(len(source), match.end() + 160))
                if opening >= 0:
                    depth = 0
                    for offset in range(opening, len(masked)):
                        if masked[offset] == "{": depth += 1
                        elif masked[offset] == "}":
                            depth -= 1
                            if depth == 0:
                                end = offset + 1
                                break
            segment = source[match.start():end]
            name = match[1] if kind == "function" else match[2]
            symbol_kind = "test" if lang == "rust" and re.search(r"#\s*\[\s*test\s*\]\s*$", source[:match.start()]) else kind
            symbols.append({"kind": symbol_kind, "name": name, "start_line": start, "end_line": source.count("\n", 0, end) + 1, "signature": match[0].strip(), "body": segment})
    if lang in {"javascript", "typescript", "svelte"}:
        test_call = re.compile(r"\b(?:it|test|describe)(?:\.\w+)*(?:\([^()]*\))?\s*\(\s*(['\"`])((?:\\.|(?!\1).)+?)\1")
        code_for_calls = re.sub(r"//.*|/\*.*?\*/", lambda match: " " * len(match.group(0)), source)
        for match in test_call.finditer(code_for_calls):
            start = match.start()
            opening = masked.find("{", match.end())
            end = match.end()
            if opening >= 0:
                depth = 0
                for offset in range(opening, len(masked)):
                    if masked[offset] == "{": depth += 1
                    elif masked[offset] == "}":
                        depth -= 1
                        if depth == 0:
                            end = offset + 1
                            break
            symbols.append({"kind": "test", "name": match[2], "start_line": source.count("\n", 0, start) + 1, "end_line": source.count("\n", 0, end) + 1, "signature": match[0].strip(), "body": source[start:end]})
    return symbols


def removed_branches(hunks):
    branches = []
    for index, hunk in enumerate(hunks):
        additions = [line["text"] for line in hunk["lines"] if line["kind"] == "added"]
        for line in hunk["lines"]:
            if line["kind"] == "removed" and re.search(r"\b(if|else|elif|match|case|return|throw|panic!|assert)\b", line["text"]):
                branches.append({"base_line": line["base_line"], "text": line["text"], "function": None, "hunk_index": index, "added_candidates": additions})
    return branches


def coverage_changes(path, hunks):
    changes = []
    config_file = Path(path).name in {".coveragerc", "codecov.yml", "codecov.yaml"} or Path(path).name.startswith("vitest.config.") or Path(path).name == "pyproject.toml"
    for hunk in hunks:
        removed, added = [], []
        section = ""
        for line in hunk["lines"]:
            if Path(path).name == "pyproject.toml" and line["kind"] != "added":
                header = re.match(r"\s*\[([^]]+)\]", line["text"])
                if header:
                    section = header[1]
            elif Path(path).name == "pyproject.toml" and line["kind"] == "added":
                header = re.match(r"\s*\[([^]]+)\]", line["text"])
                if header:
                    section = header[1]
            if line["kind"] not in {"added", "removed"}:
                continue
            if Path(path).name == "pyproject.toml" and re.match(r"\s*\[[^]]+\]", line["text"]):
                continue
            found = COVER_RE.search(mask_strings(line["text"]))
            if found:
                (added if line["kind"] == "added" else removed).append(("pragma", "exclusion", found.group(0), line))
                continue
            if not config_file:
                continue
            if Path(path).name == "pyproject.toml" and not section.startswith("tool.coverage"):
                continue
            name = line["text"].strip()
            category = "threshold" if re.search(r"(?i)(threshold|fail_under|precision|project:|patch:)", name) else ("include" if re.search(r"(?i)include", name) else ("exclude" if re.search(r"(?i)exclude", name) else None))
            if not category:
                category = "unknown"
            key = name.split("=", 1)[0].split(":", 1)[0].strip(" -")
            (added if line["kind"] == "added" else removed).append(("config", category, key, line))
        while removed or added:
            before = removed.pop(0) if removed else None
            after = next((item for item in added if before and item[2] == before[2]), None)
            if after:
                added.remove(after)
            elif added and before is None:
                after = added.pop(0)
            elif before is None:
                break
            action = "modified" if before and after else ("removed" if before else "added")
            def info(item):
                return {"line": item[3]["base_line"] if item[3]["kind"] == "removed" else item[3]["head_line"], "text": item[3]["text"]} if item else None
            source = after or before
            changes.append({"kind": source[0], "action": action, "category": source[1], "key": source[2], "base": info(before), "head": info(after)})
    return changes


def symbol_changes(old, new, path):
    changes, unsupported = [], []
    old_names, new_names = {}, {}
    for item in old: old_names.setdefault((item["kind"], item["name"]), []).append(item)
    for item in new: new_names.setdefault((item["kind"], item["name"]), []).append(item)
    for key in old_names.keys() | new_names.keys():
        before, after = old_names.get(key, []), new_names.get(key, [])
        if len(before) > 1 or len(after) > 1:
            unsupported.append({"path": path, "area": "symbol-match", "reason": f"ambiguous {key[1]} declaration", "base_lines": [x["start_line"] for x in before] or "none", "head_lines": [x["start_line"] for x in after] or "none"})
            continue
        left, right = (before or [None])[0], (after or [None])[0]
        if left and right and left["body"] == right["body"]: continue
        change = "modified" if left and right else ("added" if right else "deleted")
        def side(item):
            return {k: item[k] for k in ("start_line", "end_line", "signature")} if item else None
        changes.append({"change": change, "kind": key[0], "name": key[1], "base": side(left), "head": side(right), "_base_body": left["body"] if left else None, "_head_body": right["body"] if right else None})
    return changes, unsupported


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cwd = Path(args.cwd).resolve()
    try:
        merge_base = git(cwd, "merge-base", args.base, "HEAD").decode().strip()
        head = git(cwd, "rev-parse", "HEAD").decode().strip()
        statuses = git(cwd, "diff", "--find-renames", "--name-status", "-z", f"{args.base}...HEAD").decode().split("\0")
        records, i = [], 0
        while i < len(statuses) and statuses[i]:
            status = statuses[i]; i += 1
            if status.startswith("R"):
                old_path, path = statuses[i:i+2]; i += 2; records.append(("renamed", old_path, path))
            else:
                path = statuses[i]; i += 1
                records.append(({"A":"added", "D":"deleted", "M":"modified"}.get(status[0], "modified"), path if status[0] == "D" else None, path))
        files, unsupported_all = [], []
        for status, old_path, path in records:
            diff_path = old_path or path
            patch = git(cwd, "diff", "--find-renames", "--no-ext-diff", "--unified=3", f"{args.base}...HEAD", "--", diff_path).decode("utf-8", "replace")
            hunks = parse_hunks(patch)
            lang = language(path)
            old_text = git(cwd, "show", f"{merge_base}:{old_path or path}").decode("utf-8", "replace") if status != "added" else ""
            new_text = git(cwd, "show", f"HEAD:{path}").decode("utf-8", "replace") if status != "deleted" else ""
            def symbols(text):
                if lang == "python": return python_symbols(text)
                if lang: return generic_symbols(text, lang), []
                return [], []
            old_symbols, old_unsupported = symbols(old_text)
            new_symbols, new_unsupported = symbols(new_text)
            changes, match_unsupported = symbol_changes(old_symbols, new_symbols, path) if lang else ([], [])
            functions, declarations = [], []
            for item in changes:
                if item["kind"] != "test":
                    destination = functions if item["kind"] == "function" else declarations
                    destination.append({key: value for key, value in item.items() if not key.startswith("_")})
            unsupported = old_unsupported + new_unsupported + match_unsupported
            if lang is None:
                unsupported.append({"path": path, "area": "language", "reason": "language is outside the supported set; only diff hunks were enumerated", "base_lines": "file" if old_text else "none", "head_lines": "file" if new_text else "none"})
            for item in unsupported: item["path"] = path
            unsupported_all.extend(unsupported)
            tests, markers_added = [], []
            coverage = coverage_changes(path, hunks)
            is_test = bool(re.search(r"(?:\.test\.|\.spec\.|(?:^|/)(?:tests?|__tests__|spec)/|_test\.|(?:^|/)test_[^/]*\.py$)", path)) or (lang == "rust" and "#[cfg(test)]" in old_text + new_text)
            for change in changes:
                is_python_test = change["name"].rsplit(".", 1)[-1].startswith("test")
                is_rust_test = lang == "rust" and is_test
                is_generic_test = change["kind"] == "test"
                if is_test and (is_generic_test or (change["kind"] == "function" and (is_python_test or is_rust_test))):
                    old_symbol = next((s for s in old_symbols if s["name"] == change["name"]), None)
                    new_symbol = next((s for s in new_symbols if s["name"] == change["name"]), None)
                    def test_side(symbol, text):
                        if not symbol: return None
                        source_lines = text.splitlines()
                        start = max(0, symbol["start_line"] - 6)
                        end = min(len(source_lines), symbol["end_line"])
                        marker_text = "\n".join(source_lines[start:end])
                        markers = [m.group(0) for source_line in marker_text.splitlines() for m in MARKER_RE.finditer(mask_non_code(source_line, lang))]
                        return {"start_line": symbol["start_line"], "end_line": symbol["end_line"], "body": symbol["body"], "markers": markers}
                    tests.append({"change": change["change"], "kind": change["kind"], "name": change["name"], "base": test_side(old_symbol, old_text), "head": test_side(new_symbol, new_text), "body_changed": bool(old_symbol and new_symbol and old_symbol["body"] != new_symbol["body"])})
            for hunk_index, hunk in enumerate(hunks):
                for line in hunk["lines"]:
                    if line["kind"] != "added": continue
                    for marker in MARKER_RE.finditer(mask_non_code(line["text"], lang)): markers_added.append({"marker": marker.group(0), "test": None, "head_line": line["head_line"]})
            hunks = hunks
            files.append({"path":path, "old_path":old_path, "status":status, "language":lang, "is_test_file":is_test, "hunks":hunks, "functions":functions, "declarations":declarations, "removed_branch_candidates":removed_branches(hunks), "tests":tests, "markers_added":markers_added, "coverage_changes":coverage})
        out = Path(args.out)
        if not out.is_absolute(): out = cwd / out
        out.parent.mkdir(parents=True, exist_ok=True)
        summary = {"changed_files":len(files), "function_changes":sum(len(f["functions"]) for f in files), "declaration_changes":sum(len(f["declarations"]) for f in files), "test_changes":sum(len(f["tests"]) for f in files), "coverage_changes":sum(len(f["coverage_changes"]) for f in files), "unsupported":len(unsupported_all)}
        out.write_text(json.dumps({"schema_version":1, "comparison":{"cwd":str(cwd), "base_ref":args.base, "merge_base":merge_base, "head_commit":head, "diff_spec":"base...HEAD"}, "summary":summary, "files":files, "unsupported":unsupported_all}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    except (OSError, subprocess.CalledProcessError) as error:
        detail = error.stderr.decode("utf-8", "replace").strip() if isinstance(error, subprocess.CalledProcessError) else str(error)
        print(f"enumerate_diff.py: {detail}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

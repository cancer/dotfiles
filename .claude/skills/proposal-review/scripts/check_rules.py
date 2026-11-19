"""Run deterministic checks against proposal outlines and Slides decks."""

from __future__ import annotations

from functools import lru_cache
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
RULES_PATH = SCRIPT_DIR / "rules.json"
CORE_ROLES = (
    "cover",
    "understanding",
    "hypothesis",
    "approach",
    "why_us",
    "process",
    "questions_next",
)
SLIDE_HEADER = re.compile(r"^##\s+S(\d+)\s+\[([^]]+)\]\s+(.+?)\s*$")
SLIDE_HEADER_PREFIX = re.compile(r"^##\s+S\d+\b")
FRONTMATTER_KEY = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*?)\s*$")
POLITE_ENDING = re.compile(r"(?:です|ます|でした|ました|ません|ございます|ください|でしょう)[。！？!?]?$")
PLAIN_ENDING = re.compile(r"(?:であった|である|ではない|だった|した|する|しない|ない|だ)[。！？!?]?$")
VOID_ELEMENTS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
BLOCK_ELEMENTS = {
    "article",
    "br",
    "div",
    "h1",
    "h2",
    "h3",
    "li",
    "p",
    "section",
    "table",
    "td",
    "th",
    "tr",
}


@lru_cache(maxsize=1)
def load_rules() -> dict[str, Any]:
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def _finding(rule: str, slide_number: str | None, source: str = "script") -> dict[str, Any]:
    config = load_rules()["rules"][rule]
    suffix = f"S{slide_number}" if slide_number else "all"
    return {
        "id": f"{rule}@{suffix}",
        "rule": rule,
        "slide": suffix if slide_number else None,
        "category": config["category"],
        "message": config["message"],
        "source": source,
    }


def _read_outline(path: Path) -> tuple[dict[str, str], list[dict[str, Any]], bool]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    metadata: dict[str, str] = {}
    malformed_heading = False
    if lines and lines[0].strip() == "---":
        closing = next((index for index in range(1, len(lines)) if lines[index].strip() == "---"), None)
        if closing is None:
            malformed_heading = True
        else:
            for line in lines[1:closing]:
                match = FRONTMATTER_KEY.match(line)
                if match:
                    metadata[match.group(1)] = match.group(2)

    slides: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in lines:
        match = SLIDE_HEADER.match(line)
        if match:
            if current is not None:
                slides.append(current)
            current = {
                "number": match.group(1),
                "role": match.group(2),
                "heading": match.group(3),
                "body": [],
            }
            continue
        if SLIDE_HEADER_PREFIX.match(line):
            malformed_heading = True
        if current is not None:
            current["body"].append(line)
    if current is not None:
        slides.append(current)
    return metadata, slides, malformed_heading


def _collapse_adjacent(values: list[str]) -> list[str]:
    collapsed: list[str] = []
    for value in values:
        if not collapsed or collapsed[-1] != value:
            collapsed.append(value)
    return collapsed


def _format_is_valid(metadata: dict[str, str], slides: list[dict[str, Any]], malformed_heading: bool) -> bool:
    if malformed_heading or metadata.get("cost_requested", "").lower() not in {"true", "false"}:
        return False
    slide_numbers = [slide["number"] for slide in slides]
    if len(slide_numbers) != len(set(slide_numbers)):
        return False
    roles = [slide["role"] for slide in slides]
    if any(role not in (*CORE_ROLES, "cost") for role in roles):
        return False
    # 依頼で費用を求められたら費用スライドは必須
    if metadata["cost_requested"].lower() == "true" and "cost" not in roles:
        return False
    core_sequence = _collapse_adjacent([role for role in roles if role != "cost"])
    if core_sequence != list(CORE_ROLES):
        return False
    for index, role in enumerate(roles):
        if role != "cost":
            continue
        previous = next((value for value in reversed(roles[:index]) if value != "cost"), None)
        following = next((value for value in roles[index + 1 :] if value != "cost"), None)
        if previous != "process" or following != "questions_next":
            return False
    return True


def _is_table_row(line: str) -> bool:
    # 表の行は「|」で始まり「|」で終わる行だけとする（「|」を含む箇条や挿絵は表ではない）
    value = line.strip()
    return len(value) > 1 and value.startswith("|") and value.endswith("|")


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_table_separator(line: str) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", cell) for cell in _table_cells(line))


def _plain_markdown(line: str) -> list[str]:
    if _is_table_row(line):
        if _is_table_separator(line):
            return []
        return [cell for cell in _table_cells(line) if cell]
    value = line.strip()
    if value.startswith("- "):
        value = value[2:].strip()
    if value.startswith("挿絵:"):
        return []
    if not value or value == "---":
        return []
    value = re.sub(r"(\*\*|__|`)", "", value)
    value = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", value)
    value = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", value)
    return [value]


def outline_slide_texts(slides: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for slide in slides:
        parts = [slide["heading"]]
        for line in slide["body"]:
            parts.extend(_plain_markdown(line))
        slide_id = f"s{slide['number']}"
        result[slide_id] = _normalize_text(" ".join(parts))
    return result


def _table_style_is_mixed(body: list[str]) -> bool:
    table_lines: list[str] = []
    tables: list[list[str]] = []
    for line in body:
        if _is_table_row(line):
            table_lines.append(line)
        elif table_lines:
            tables.append(table_lines)
            table_lines = []
    if table_lines:
        tables.append(table_lines)

    for table in tables:
        polite = False
        plain = False
        for line in table:
            if _is_table_separator(line):
                continue
            for value in _table_cells(line):
                if POLITE_ENDING.search(value):
                    polite = True
                elif PLAIN_ENDING.search(value):
                    plain = True
        if polite and plain:
            return True
    return False


def _term_pattern(term: str) -> re.Pattern[str]:
    # ASCII の語は英単語の一部（rapid の api など）に一致させない
    if term.isascii():
        return re.compile(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", re.IGNORECASE)
    return re.compile(re.escape(term))


def _terms_in(text: str, terms: list[str]) -> list[str]:
    return [term for term in terms if _term_pattern(term).search(text)]


def check_outline(outline_path: Path | str) -> list[dict[str, Any]]:
    path = Path(outline_path)
    metadata, slides, malformed_heading = _read_outline(path)
    rules = load_rules()
    findings: list[dict[str, Any]] = []

    if not _format_is_valid(metadata, slides, malformed_heading):
        findings.append(_finding("R-format", None))
    for slide in slides:
        # C1: 本文の「- 」行は 1 スライド 3 行まで
        bullet_count = sum(1 for line in slide["body"] if line.lstrip().startswith("- "))
        if bullet_count > 3:
            findings.append(_finding("R-points", slide["number"]))

    if metadata.get("cost_requested", "").lower() == "false":
        for slide in slides:
            if slide["role"] == "cost":
                findings.append(_finding("R-cost", slide["number"]))

    for slide in slides:
        text = " ".join([slide["heading"], *slide["body"]])
        if _terms_in(text, rules["negative_words"]):
            findings.append(_finding("R-words-negative", slide["number"]))
        if _terms_in(text, rules["internal_phrases"]):
            findings.append(_finding("R-internal", slide["number"]))
        if _terms_in(text, rules["technical_terms"]):
            findings.append(_finding("R-tech-terms", slide["number"]))
        if _table_style_is_mixed(slide["body"]):
            findings.append(_finding("R-table-style", slide["number"]))
    return findings


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        hidden = self.ignored_depth > 0 or tag in {"aside", "script", "style"} or "data-fixed" in attributes
        if hidden:
            if tag not in VOID_ELEMENTS:
                self.ignored_depth += 1
            return
        if tag in BLOCK_ELEMENTS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if self.ignored_depth > 0:
            if tag not in VOID_ELEMENTS:
                self.ignored_depth -= 1
            return
        if tag in BLOCK_ELEMENTS:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if self.ignored_depth == 0:
            self.parts.append(data)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def visible_html_text(path: Path | str) -> str:
    parser = _VisibleTextParser()
    parser.feed(Path(path).read_text(encoding="utf-8"))
    parser.close()
    # 区切りはブロック要素が入れる空白だけにし、インライン要素（strong・a など）の前後に空白を足さない
    return _normalize_text("".join(parser.parts))


def deck_visible_texts(workdir: Path | str, order: list[str] | None = None) -> dict[str, str]:
    project = Path(workdir) / "deck" / "project"
    slides_dir = project / "slides"
    slide_ids = order if order is not None else sorted(path.stem for path in slides_dir.glob("*.html"))
    return {
        slide_id: visible_html_text(slides_dir / f"{slide_id}.html")
        for slide_id in slide_ids
        if (slides_dir / f"{slide_id}.html").is_file()
    }


def check_deck(workdir: Path | str) -> list[dict[str, Any]]:
    root = Path(workdir)
    metadata, slides, _ = _read_outline(root / "outline.md")
    expected_texts = outline_slide_texts(slides)
    expected_order = list(expected_texts)
    project = root / "deck" / "project"
    deck_json = json.loads((project / "deck.json").read_text(encoding="utf-8"))
    declared_order = deck_json.get("order") if isinstance(deck_json, dict) else None
    slides_dir = project / "slides"
    actual_files = sorted(path.stem for path in slides_dir.glob("*.html"))
    count_matches = (
        isinstance(deck_json, dict)
        and deck_json.get("v") == 4
        and isinstance(declared_order, list)
        and declared_order == expected_order
        and len(actual_files) == len(expected_order)
        and set(actual_files) == set(expected_order)
    )
    findings: list[dict[str, Any]] = []
    if not count_matches:
        findings.append(_finding("R-deck-count", None))

    actual_texts = deck_visible_texts(root, declared_order if isinstance(declared_order, list) else None)
    for slide_id, expected_text in expected_texts.items():
        if slide_id not in actual_texts or actual_texts[slide_id] != expected_text:
            slide_number = slide_id.removeprefix("s")
            findings.append(_finding("R-deck-diff", slide_number))
    return findings

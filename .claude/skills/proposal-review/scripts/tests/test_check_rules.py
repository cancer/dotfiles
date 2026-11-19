import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
FIXTURES = SCRIPT_DIR / "fixtures"
sys.path.insert(0, str(SCRIPT_DIR))

from check_rules import check_deck, check_outline, load_rules  # noqa: E402


FRONTMATTER = "---\nclient: 青海物流\ntrigger: 入出庫記録を見直したい\ncost_requested: {cost}\n---\n# 青海物流のご提案\n"
CORE_ROLES = ("cover", "understanding", "hypothesis", "approach", "why_us", "process", "questions_next")
# check_rules.py の POLITE_ENDING / PLAIN_ENDING の選択肢と末尾の記号
POLITE_ENDINGS = ("です", "ます", "でした", "ました", "ません", "ございます", "ください", "でしょう")
PLAIN_ENDINGS = ("であった", "である", "ではない", "だった", "した", "する", "しない", "ない", "だ")
ENDING_MARKS = ("", "。", "！", "？", "!", "?")
# 太字・リンク・強調・表・区切り線・「|」を含む箇条を持つスライドと、それを正しく HTML にしたもの
MARKDOWN_SLIDE = (
    "## S2 [understanding] 現場の情報を共有します\n"
    "- **入出庫担当**と[管理担当](https://example.com/staff)の情報を`台帳`でつなぐ\n"
    "- 引き継ぎ時に*必要な*記録を__確認する__\n"
    "- 入荷 | 出荷 の記録を分けて確認する\n"
    "\n"
    "| 項目 | 内容 |\n"
    "|:---|---:|\n"
    "| 記録 | 紙の台帳 |\n"
    "| 確認 | 毎日の点検 |\n"
    "---\n"
)
MARKDOWN_SLIDE_HTML = (
    '<section id="s2"><h1>現場の情報を共有します</h1>'
    '<ul><li><strong>入出庫担当</strong>と<a href="https://example.com/staff">管理担当</a>の情報を<code>台帳</code>でつなぐ</li>'
    "<li>引き継ぎ時に<em>必要な</em>記録を<strong>確認する</strong></li>"
    "<li>入荷 | 出荷 の記録を分けて確認する</li></ul>"
    "<table><tr><th>項目</th><th>内容</th></tr>"
    "<tr><td>記録</td><td>{record}</td></tr>"
    "<tr><td>確認</td><td>毎日の点検</td></tr></table></section>"
)


def outline_text(roles, *, cost="false", bodies=None, frontmatter=None):
    """roles の順に S1.. のスライドを並べた outline.md の文字列を作る。"""
    slide_bodies = bodies or {}
    header = FRONTMATTER.format(cost=cost) if frontmatter is None else frontmatter
    slides = [
        f"## S{number} [{role}] 現場の記録を確認します\n{slide_bodies.get(number, '- 記録方法を確認する')}\n"
        for number, role in enumerate(roles, start=1)
    ]
    return header + "\n" + "\n".join(slides)


class OutlineRuleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def check_text(self, text):
        path = self.root / "outline.md"
        path.write_text(text, encoding="utf-8")
        return {item["id"] for item in check_outline(path)}

    def test_clean_outline_has_no_findings(self):
        self.assertEqual(check_outline(FIXTURES / "clean" / "outline.md"), [])

    def test_violations_outline_reports_exactly_the_expected_slides(self):
        finding_ids = {item["id"] for item in check_outline(FIXTURES / "violations" / "outline.md")}

        self.assertEqual(
            finding_ids,
            {
                "R-format@all",
                "R-points@S3",
                "R-cost@S2",
                "R-words-negative@S1",
                "R-words-negative@S2",
                "R-internal@S1",
                "R-tech-terms@S1",
                "R-table-style@S2",
            },
        )

    def test_valid_outline_with_requested_cost_and_repeated_roles_has_no_findings(self):
        roles = ("cover", "understanding", "understanding", "hypothesis", "approach", "why_us",
                 "process", "process", "cost", "questions_next")

        self.assertEqual(self.check_text(outline_text(roles, cost="true")), set())

    def test_each_format_violation_alone_triggers_r_format(self):
        cases = {
            "frontmatter_unclosed": outline_text(
                CORE_ROLES, frontmatter="---\nclient: 青海物流\ncost_requested: false\n# 青海物流のご提案\n"
            ),
            "frontmatter_missing": outline_text(CORE_ROLES, frontmatter="# 青海物流のご提案\n"),
            "cost_requested_not_boolean": outline_text(CORE_ROLES, cost="yes"),
            "duplicate_slide_number": outline_text(CORE_ROLES).replace("## S2 ", "## S1 "),
            "unknown_role": outline_text((*CORE_ROLES[:3], "summary", *CORE_ROLES[3:])),
            "core_order": outline_text(("cover", "hypothesis", "understanding", *CORE_ROLES[3:])),
            "core_role_missing": outline_text(CORE_ROLES[:-1]),
            "cost_before_process": outline_text((*CORE_ROLES[:5], "cost", *CORE_ROLES[5:]), cost="true"),
            "cost_after_questions_next": outline_text((*CORE_ROLES, "cost"), cost="true"),
            "malformed_slide_heading": outline_text(CORE_ROLES).replace("## S3 [hypothesis]", "## S3 hypothesis"),
            # 依頼で費用を求められたら費用スライドは必須
            "cost_requested_without_cost_slide": outline_text(CORE_ROLES, cost="true"),
        }
        for name, text in cases.items():
            with self.subTest(case=name):
                self.assertIn("R-format@all", self.check_text(text))

    def test_cost_slide_without_request_reports_r_cost_only_on_that_slide(self):
        roles = (*CORE_ROLES[:6], "cost", "questions_next")

        self.assertEqual(self.check_text(outline_text(roles, cost="false")), {"R-cost@S7"})

    def test_points_boundary_is_three_bullets_per_slide(self):
        three = "- 一つ目を確認する\n- 二つ目を確認する\n- 三つ目を確認する"
        four = three + "\n- 四つ目を確認する"
        table_only = "|項目|内容|\n|---|---|\n|記録|紙の台帳|"

        self.assertEqual(self.check_text(outline_text(CORE_ROLES, bodies={2: three})), set())
        self.assertEqual(self.check_text(outline_text(CORE_ROLES, bodies={2: four})), {"R-points@S2"})
        self.assertEqual(self.check_text(outline_text(CORE_ROLES, bodies={2: table_only})), set())

    def test_uniform_table_style_is_not_reported(self):
        polite = "|項目|内容|\n|---|---|\n|確認方法|担当者に確認します。|\n|責任者|現場の責任者です。|"
        plain = "|項目|内容|\n|---|---|\n|確認方法|担当者に確認する。|\n|責任者|現場の責任者である。|"

        self.assertEqual(self.check_text(outline_text(CORE_ROLES, bodies={2: polite})), set())
        self.assertEqual(self.check_text(outline_text(CORE_ROLES, bodies={2: plain})), set())

    def test_each_ending_mixed_with_the_other_style_reports_table_style(self):
        cases = [("polite", ending, "確認する") for ending in POLITE_ENDINGS]
        cases += [("plain", ending, "確認します") for ending in PLAIN_ENDINGS]
        for style, ending, other in cases:
            for mark in ENDING_MARKS:
                body = f"|項目|内容|\n|---|---|\n|方法|記録{ending}{mark}|\n|担当|{other}。|"
                with self.subTest(style=style, ending=ending, mark=mark):
                    self.assertEqual(
                        self.check_text(outline_text(CORE_ROLES, bodies={2: body})), {"R-table-style@S2"}
                    )

    def test_each_ending_in_a_single_style_table_is_not_reported(self):
        for ending in (*POLITE_ENDINGS, *PLAIN_ENDINGS):
            body = f"|項目|内容|\n|---|---|\n|方法|記録{ending}。|\n|担当|確認{ending}|"
            with self.subTest(ending=ending):
                self.assertEqual(self.check_text(outline_text(CORE_ROLES, bodies={2: body})), set())

    def test_lines_not_wrapped_in_pipes_are_not_table_rows(self):
        polite_table = "|項目|内容|\n|---|---|\n|方法|記録します。|"
        cases = {
            "bullet": polite_table + "\n- 方法 | 記録する。",
            "illustration": polite_table + "\n挿絵: 担当者 | 記録する。",
        }
        for name, body in cases.items():
            with self.subTest(case=name):
                self.assertEqual(self.check_text(outline_text(CORE_ROLES, bodies={2: body})), set())

    def test_ascii_technical_terms_match_whole_words_only(self):
        partial = "- rapid な改善と dbms の比較とapiaryを確認する"
        whole = "- 既存のAPIを確認する"

        self.assertEqual(self.check_text(outline_text(CORE_ROLES, bodies={2: partial})), set())
        self.assertEqual(self.check_text(outline_text(CORE_ROLES, bodies={2: whole})), {"R-tech-terms@S2"})

    def test_every_vocabulary_entry_alone_triggers_its_rule(self):
        rules = load_rules()
        vocabularies = {
            "R-words-negative": rules["negative_words"],
            "R-internal": rules["internal_phrases"],
            "R-tech-terms": rules["technical_terms"],
        }
        for rule, terms in vocabularies.items():
            for term in terms:
                # 前後を日本語で挟み、非 ASCII の語は部分一致の経路を通す
                body = f"- 既存の{term}を確認する"
                with self.subTest(rule=rule, term=term):
                    self.assertEqual(
                        self.check_text(outline_text(CORE_ROLES, bodies={2: body})), {f"{rule}@S2"}
                    )

    def test_ascii_technical_terms_ignore_case(self):
        ascii_terms = [term for term in load_rules()["technical_terms"] if term.isascii()]
        for term in ascii_terms:
            for variant in {term.lower(), term.capitalize(), term.upper()}:
                body = f"- 既存の {variant} を確認する"
                with self.subTest(term=term, variant=variant):
                    self.assertEqual(
                        self.check_text(outline_text(CORE_ROLES, bodies={2: body})), {"R-tech-terms@S2"}
                    )


class DeckRuleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.workdir = Path(self.temporary.name) / "deck_case"
        shutil.copytree(FIXTURES / "deck_clean", self.workdir)
        self.project = self.workdir / "deck" / "project"

    def tearDown(self):
        self.temporary.cleanup()

    def write_deck_json(self, value):
        (self.project / "deck.json").write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def finding_ids(self):
        return {item["id"] for item in check_deck(self.workdir)}

    def test_clean_deck_has_no_findings_and_ignores_fixed_and_note_text(self):
        self.assertEqual(check_deck(FIXTURES / "deck_clean"), [])

    def test_deck_drift_reports_only_the_changed_slide_and_the_order(self):
        finding_ids = {item["id"] for item in check_deck(FIXTURES / "deck_drift")}

        self.assertEqual(finding_ids, {"R-deck-diff@S3", "R-deck-count@all"})

    def write_markdown_slide(self, record):
        outline = (self.workdir / "outline.md").read_text(encoding="utf-8")
        start = outline.index("## S2 ")
        end = outline.index("## S3 ")
        (self.workdir / "outline.md").write_text(outline[:start] + MARKDOWN_SLIDE + "\n" + outline[end:], encoding="utf-8")
        (self.project / "slides" / "s2.html").write_text(MARKDOWN_SLIDE_HTML.format(record=record), encoding="utf-8")

    def test_markdown_decoration_and_tables_match_their_html(self):
        self.write_markdown_slide("紙の台帳")

        self.assertEqual(self.finding_ids(), set())

    def test_changed_table_cell_reports_diff(self):
        self.write_markdown_slide("紙の帳簿")

        self.assertEqual(self.finding_ids(), {"R-deck-diff@S2"})

    def test_extra_slide_reports_count(self):
        shutil.copy(self.project / "slides" / "s7.html", self.project / "slides" / "s8.html")
        self.write_deck_json({"v": 4, "title": "t", "order": [f"s{n}" for n in range(1, 9)]})

        self.assertEqual(self.finding_ids(), {"R-deck-count@all"})

    def test_missing_slide_in_order_and_files_reports_count_and_diff(self):
        (self.project / "slides" / "s7.html").unlink()
        self.write_deck_json({"v": 4, "title": "t", "order": [f"s{n}" for n in range(1, 7)]})

        self.assertEqual(self.finding_ids(), {"R-deck-count@all", "R-deck-diff@S7"})

    def test_missing_slide_file_reports_count_and_diff(self):
        (self.project / "slides" / "s4.html").unlink()

        self.assertEqual(self.finding_ids(), {"R-deck-count@all", "R-deck-diff@S4"})

    def test_wrong_version_reports_count(self):
        self.write_deck_json({"v": 3, "title": "t", "order": [f"s{n}" for n in range(1, 8)]})

        self.assertEqual(self.finding_ids(), {"R-deck-count@all"})

    def test_order_that_is_not_a_list_reports_count(self):
        self.write_deck_json({"v": 4, "title": "t", "order": "s1,s2,s3,s4,s5,s6,s7"})

        self.assertEqual(self.finding_ids(), {"R-deck-count@all"})


if __name__ == "__main__":
    unittest.main()

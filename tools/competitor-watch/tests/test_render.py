import os
import unittest

import helpers
from competitor_watch.diffing import Change, diff_snapshots, health_lines
from competitor_watch.render import ISSUE_LIMIT, KILL_CLAUSE, cell, render_changes, render_snapshot, render_thesis, thesis_rows
from competitor_watch.snapshot import Fetched, build_entry, carry_over, new_snapshot

fixture, ok, bad = helpers.fixture, helpers.ok, helpers.bad
GOLDEN = helpers.FIXTURES / "expected_snapshot.md"
T1, T2 = "2026-10-01T06:00:00Z", "2026-10-08T06:00:00Z"

KAI_HTML = (
    "<h1>Synthetic Knowledge Platform</h1><p>A platform that detects contradictions between documents and detects conflicts in real time, "
    "so that teams can trust what their AI tools read. It connects to Confluence and several other repositories.</p>"
    "<ul><li>Finds duplicates, contradictions and obsolete documents</li></ul>"
)

SOURCES = [
    helpers.source("hygiene", name="Example Hygiene", provenance="Named in the brief. SYNTHETIC."),
    helpers.source("evergreen", "search", name="Evergreen AI for Confluence", kill_clause_subject=True, expect_text="Evergreen", min_text_chars=0, note="NOT LOCATED (synthetic note)."),
    helpers.source("kai", "page", name="Synthetic Knowledge Platform"),
    helpers.source("flaky", "page", name="Flaky Source"),
    helpers.source("atlassian", "page", name="Atlassian Release Notes", role="atlassian", mentions=[{"id": "documentation-agent", "all": ["documentation agent"]}]),
]
CFG = helpers.make_config(SOURCES)


def entry(sid, html):
    s = next(x for x in CFG.sources if x.id == sid)
    return build_entry(s, [Fetched(f"https://example.test/{sid}", ok(f"https://example.test/{sid}", html))], CFG)


def failed(sid):
    s = next(x for x in CFG.sources if x.id == sid)
    return build_entry(s, [Fetched(f"https://example.test/{sid}", bad(f"https://example.test/{sid}", "HTTP 503"))], CFG)


def sample():
    hygiene = fixture("listing_jsonld.html").replace("Keeps your Confluence knowledge base clean", "Detects contradictions in your knowledge base")
    previous = new_snapshot({"flaky": entry("flaky", "<p>" + "Flaky source text that was fine last week. " * 8 + "</p>")}, T1)
    snap = new_snapshot(
        {
            "hygiene": entry("hygiene", hygiene),
            "evergreen": entry("evergreen", fixture("search_empty.html")),
            "kai": entry("kai", KAI_HTML),
            "flaky": failed("flaky"),
            "atlassian": entry("atlassian", fixture("release_notes.html")),
        },
        T2,
    )
    carry_over(snap, previous)
    return snap


class Thesis(unittest.TestCase):
    def rows(self):
        return {r["id"]: r for r in thesis_rows(sample(), CFG)}

    def test_only_competitors_get_rows(self):
        self.assertEqual(set(self.rows()), {"hygiene", "evergreen", "kai", "flaky"})

    def test_evergreen_unlocated_means_the_clause_cannot_be_evaluated(self):
        r = self.rows()["evergreen"]
        self.assertEqual((r["subject"], r["located"]), ("yes", "NO"))
        self.assertTrue(r["indicator"].startswith("UNKNOWN: not located"))

    def test_contradiction_words_alone(self):
        r = self.rows()["hygiene"]
        self.assertEqual((r["contradiction"], r["change_time"]), ("1", "0"))
        self.assertEqual(r["indicator"], "contradiction words present: read the snippets")

    def test_both_kinds_of_words_say_review_now(self):
        r = self.rows()["kai"]
        self.assertTrue(r["indicator"].startswith("REVIEW NOW"))

    def test_a_failed_source_is_unknown_and_says_the_data_is_old(self):
        self.assertEqual(self.rows()["flaky"]["indicator"], "UNKNOWN: source failed (last good data shown)")

    def test_a_clean_competitor_is_not_seen(self):
        snap = new_snapshot({"hygiene": entry("hygiene", fixture("listing_jsonld.html"))}, T2)
        self.assertEqual(thesis_rows(snap, CFG)[0]["indicator"], "not seen")

    def test_an_unreadable_search_is_unknown_not_not_found(self):
        snap = new_snapshot({"evergreen": entry("evergreen", "<h1>Marketplace</h1><p>" + "Browse apps for your team. " * 20 + "</p>")}, T2)
        r = thesis_rows(snap, CFG)[0]
        self.assertIn("unknown", r["located"])
        self.assertTrue(r["indicator"].startswith("UNKNOWN"))

    def test_the_section_quotes_the_clause_and_flags_a_missing_subject(self):
        text = render_thesis(sample(), CFG)
        self.assertIn(KILL_CLAUSE, text)
        self.assertIn("docs/competitors/differentiation-thesis.md", text)
        self.assertIn("(../differentiation-thesis.md)", text, "the link is relative to docs/competitors/snapshots/, where latest.md is written")
        no_subject = helpers.make_config([helpers.source("hygiene")])
        snap = new_snapshot({"hygiene": build_entry(no_subject.sources[0], [Fetched("u", ok("u", fixture("listing_jsonld.html")))], no_subject)}, T2)
        self.assertIn("No source is marked `kill_clause_subject`", render_thesis(snap, no_subject))


class SnapshotMarkdown(unittest.TestCase):
    def test_matches_the_golden_file(self):
        text = render_snapshot(sample(), CFG)
        if os.environ.get("UPDATE_GOLDEN"):
            GOLDEN.write_text(text, encoding="utf-8")
        self.assertEqual(text, GOLDEN.read_text(encoding="utf-8"), "run with UPDATE_GOLDEN=1 to regenerate, and read the diff")

    def test_it_is_deterministic(self):
        self.assertEqual(render_snapshot(sample(), CFG), render_snapshot(sample(), CFG))

    def test_it_follows_the_config_order(self):
        text = render_snapshot(sample(), CFG)
        positions = [text.index(f"\n## {name}\n") for name in ("Example Hygiene", "Evergreen AI for Confluence", "Synthetic Knowledge Platform", "Flaky Source", "Atlassian Release Notes")]
        self.assertEqual(positions, sorted(positions))

    def test_a_stale_source_is_marked_and_a_pipe_in_a_value_cannot_break_a_table(self):
        text = render_snapshot(sample(), CFG)
        self.assertIn("showing last good data from 2026-10-01T06:00:00Z", text)
        self.assertEqual(cell("a|b\nc"), "a\\|b c")
        self.assertEqual(len(cell("x" * 500)), 160)


class ChangeReport(unittest.TestCase):
    def reports(self):
        old = new_snapshot({"hygiene": entry("hygiene", fixture("listing_jsonld.html"))}, T1)
        new = new_snapshot({"hygiene": entry("hygiene", fixture("listing_jsonld.html").replace("Keeps your Confluence knowledge base clean", "Detects contradictions in your knowledge base").replace("1,234 installs", "1,400 installs"))}, T2)
        cs = diff_snapshots(old, new, CFG)
        return cs, render_changes(cs, health_lines(old, new), old, new, CFG)

    def test_material_is_flagged_in_the_title_and_comes_before_routine(self):
        cs, text = self.reports()
        self.assertTrue(text.startswith("# competitor-watch: 2 change(s) (MATERIAL)"))
        self.assertLess(text.index("## Material"), text.index("## Routine"))
        self.assertIn("new 'contradiction' mention", text)
        self.assertIn("after: ", text)
        self.assertIn("## What to do", text)

    def test_a_baseline_report_says_there_is_nothing_to_compare(self):
        new = new_snapshot({"hygiene": entry("hygiene", fixture("listing_jsonld.html"))}, T1)
        text = render_changes([], [], None, new, CFG)
        self.assertTrue(text.startswith("# competitor-watch: baseline taken 2026-10-01T06:00:00Z"))
        self.assertIn("nothing to compare", text)

    def test_routine_only_changes_are_not_flagged_material(self):
        old = new_snapshot({"hygiene": entry("hygiene", fixture("listing_jsonld.html"))}, T1)
        new = new_snapshot({"hygiene": entry("hygiene", fixture("listing_jsonld.html").replace("1,234 installs", "1,400 installs"))}, T2)
        text = render_changes(diff_snapshots(old, new, CFG), [], old, new, CFG)
        self.assertTrue(text.startswith("# competitor-watch: 1 change(s)\n"))
        self.assertNotIn("What to do", text)

    def test_health_lines_are_included(self):
        old = new_snapshot({"hygiene": entry("hygiene", fixture("listing_jsonld.html"))}, T1)
        new = new_snapshot({"hygiene": failed("hygiene")}, T2)
        carry_over(new, old)
        text = render_changes([], health_lines(old, new), old, new, CFG)
        self.assertTrue(text.startswith("# competitor-watch: a source could not be read"))
        self.assertIn("## Health", text)
        self.assertIn("FAILED hygiene", text)

    def test_a_huge_report_is_truncated_below_the_issue_limit_and_says_so(self):
        cs = [Change("hygiene", "material", "keyword", f"new mention {i}", None, "x" * 300) for i in range(400)]
        new = new_snapshot({"hygiene": entry("hygiene", fixture("listing_jsonld.html"))}, T2)
        text = render_changes(cs, [], new, new, CFG)
        self.assertLessEqual(len(text), ISSUE_LIMIT + 300)
        self.assertIn("report truncated", text)

    def test_long_lists_are_cut_with_a_count(self):
        cs = [Change("hygiene", "material", "feature", "30 feature(s) added", None, [f"feature {i}" for i in range(30)])]
        new = new_snapshot({"hygiene": entry("hygiene", fixture("listing_jsonld.html"))}, T2)
        text = render_changes(cs, [], new, new, CFG)
        self.assertIn("after: … and 18 more", text)


if __name__ == "__main__":
    unittest.main()

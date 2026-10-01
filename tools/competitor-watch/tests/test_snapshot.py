import copy
import unittest

import helpers
from competitor_watch.snapshot import Fetched, build_entry, canonical, carry_over, new_snapshot

fixture, ok, bad = helpers.fixture, helpers.ok, helpers.bad
T1, T2 = "2026-10-01T06:00:00Z", "2026-10-08T06:00:00Z"


def build(html=None, kind="marketplace-listing", pages=None, **src):
    """One source; `html` is its single required page, or pass `pages` as [(html_or_FetchResult, optional)]."""
    cfg = helpers.make_config([helpers.source("a", kind, **src)])
    s = cfg.sources[0]
    fetched = []
    for i, (h, optional) in enumerate(pages if pages is not None else [(html, False)]):
        url = f"https://example.test/a/{i}"
        fetched.append(Fetched(url, h if not isinstance(h, str) else ok(url, h), optional))
    return build_entry(s, fetched, cfg)


class BuildEntry(unittest.TestCase):
    def test_a_good_listing(self):
        e = build(fixture("listing_jsonld.html"), require_any_field=["installs", "rating"])
        self.assertEqual(e["status"], "ok")
        self.assertEqual(e["problems"], [])
        self.assertEqual(e["fields"]["installs"]["value"], 1234)
        self.assertEqual(len(e["features"]), 3)
        self.assertEqual(e["headings"], ["Highlights", "Details"])
        self.assertEqual(e["title"], "Example Page Hygiene for Confluence | Atlassian Marketplace")
        page = e["pages"][0]
        self.assertEqual((page["ok"], page["http_status"], page["js_shell"], page["bot_wall"], page["json_blobs"]), (True, 200, False, False, 1))
        self.assertEqual(len(page["text_sha256"]), 16)

    def test_keywords_are_scanned_over_title_description_and_text(self):
        html = fixture("listing_jsonld.html").replace("clean and current", "free of contradictions as you edit")
        e = build(html)
        self.assertEqual(e["keywords"]["contradiction"]["count"], 1)
        self.assertEqual(e["keywords"]["change_time"]["count"], 1)
        self.assertEqual(e["keywords"]["contradiction"]["hits"][0]["term"], "contradictions")

    def test_a_javascript_shell_fails_loudly_and_says_what_to_do(self):
        e = build(fixture("js_shell.html"))
        self.assertEqual(e["status"], "failed")
        self.assertIn("drawn by JavaScript", e["problems"][0])
        self.assertEqual(e["fields"], {})

    def test_a_bot_wall_fails(self):
        e = build(fixture("bot_wall.html"))
        self.assertEqual(e["status"], "failed")
        self.assertIn("bot wall", e["problems"][0])

    def test_a_http_error_fails_with_the_reason(self):
        e = build(pages=[(bad("https://example.test/a/0", "HTTP 404", 404), False)])
        self.assertEqual(e["status"], "failed")
        self.assertIn("HTTP 404", e["problems"][0])

    def test_too_little_text_fails(self):
        e = build("<p>tiny</p>", min_text_chars=100)
        self.assertEqual(e["status"], "failed")
        self.assertIn("only 4 characters", e["problems"][0])

    def test_a_failed_optional_page_is_a_warning_and_the_source_stays_ok(self):
        e = build(pages=[(fixture("listing_jsonld.html"), False), (bad("https://example.test/a/1", "HTTP 404", 404), True)])
        self.assertEqual((e["status"], e["problems"]), ("ok", []))
        self.assertIn("HTTP 404", e["warnings"][0])

    def test_a_failed_required_page_with_a_good_optional_one_is_a_failure(self):
        e = build(pages=[(bad("https://example.test/a/0"), False), (fixture("listing_jsonld.html"), True)])
        self.assertEqual(e["status"], "failed")

    def test_one_good_and_one_bad_required_page_is_partial(self):
        e = build(pages=[(fixture("listing_jsonld.html"), False), (fixture("js_shell.html"), False)])
        self.assertEqual(e["status"], "partial")

    def test_readable_text_but_no_structured_fact_is_partial_and_keywords_still_work(self):
        html = "<h1>Thing</h1><p>" + "A tool that finds contradictions between pages. " * 6 + "</p>"
        e = build(html, require_any_field=["installs", "rating", "price_text"])
        self.assertEqual(e["status"], "partial")
        self.assertIn("no structured fact found", e["problems"][0])
        self.assertEqual(e["keywords"]["contradiction"]["count"], 6)

    def test_fields_from_several_pages_first_page_wins(self):
        a = "<p>1,234 installs and 4.5 out of 5 and some more words to be long enough for the minimum length of text in the page.</p>"
        b = "<p>9,999 installs and $13.97 USD per month and some more words to be long enough for the minimum length of text.</p>"
        e = build(pages=[(a, False), (b, False)])
        self.assertEqual(e["fields"]["installs"]["value"], 1234)
        self.assertEqual(e["fields"]["price_text"]["value"], "$13.97 USD per month")

    def test_mentions_are_collected_for_pages(self):
        e = build(
            fixture("release_notes.html"),
            "page",
            mentions=[{"id": "documentation-agent", "all": ["documentation agent"]}],
        )
        self.assertEqual(len(e["mentions"]["documentation-agent"]), 1)

    def test_search_found(self):
        e = build(fixture("search_results.html"), "search", expect_text="Evergreen", min_text_chars=0)
        self.assertEqual(e["status"], "ok")
        self.assertTrue(e["discovery"]["found"])

    def test_search_not_found_is_ok_and_says_so(self):
        e = build(fixture("search_empty.html"), "search", expect_text="Evergreen", min_text_chars=0)
        self.assertEqual(e["status"], "ok")
        self.assertEqual((e["discovery"]["found"], e["discovery"]["readable"]), (False, True))

    def test_an_unreadable_search_page_is_failed_not_not_found(self):
        e = build(fixture("js_shell.html"), "search", expect_text="Evergreen", min_text_chars=0)
        self.assertEqual(e["status"], "failed")
        self.assertIsNone(e["discovery"])

    def test_a_search_page_with_text_but_no_results_markup_is_partial(self):
        html = "<h1>Marketplace</h1><p>" + "Browse apps for your team and your workflow. " * 8 + "</p>"
        e = build(html, "search", expect_text="Evergreen", min_text_chars=0)
        self.assertEqual(e["status"], "partial")
        self.assertIn("no readable results", e["problems"][0])

    def test_the_config_facts_travel_with_the_entry(self):
        e = build(fixture("listing_jsonld.html"), kill_clause_subject=True, provenance="why", note="n")
        self.assertEqual((e["kill_clause_subject"], e["provenance"], e["note"], e["role"], e["kind"]), (True, "why", "n", "competitor", "marketplace-listing"))


class CarryOver(unittest.TestCase):
    def snapshot(self, taken, html=None, failed=False):
        entry = build(pages=[(bad("https://example.test/a/0", "HTTP 503"), False)]) if failed else build(html)
        return new_snapshot({"a": entry}, taken)

    def test_a_failed_source_keeps_its_last_good_facts_marked_stale(self):
        prev = self.snapshot(T1, fixture("listing_jsonld.html"))
        now = self.snapshot(T2, failed=True)
        carry_over(now, prev)
        e = now["sources"]["a"]
        self.assertEqual((e["status"], e["stale"], e["last_good_at"]), ("failed", True, T1))
        self.assertEqual(e["fields"]["installs"]["value"], 1234)
        self.assertEqual(e["last_attempt"], {"at": T2, "problems": ["https://example.test/a/0: HTTP 503"]})

    def test_failing_twice_keeps_the_original_last_good_date(self):
        week1 = self.snapshot(T1, fixture("listing_jsonld.html"))
        week2 = self.snapshot(T2, failed=True)
        carry_over(week2, week1)
        week3 = self.snapshot("2026-10-15T06:00:00Z", failed=True)
        carry_over(week3, week2)
        self.assertEqual(week3["sources"]["a"]["last_good_at"], T1)

    def test_nothing_good_to_keep_means_nothing_is_carried(self):
        prev = self.snapshot(T1, failed=True)
        now = self.snapshot(T2, failed=True)
        before = copy.deepcopy(now)
        carry_over(now, prev)
        self.assertEqual(now, before)

    def test_a_good_week_is_left_alone_and_no_previous_is_fine(self):
        now = self.snapshot(T2, fixture("listing_text.html"))
        before = copy.deepcopy(now)
        carry_over(now, self.snapshot(T1, fixture("listing_jsonld.html")))
        carry_over(now, None)
        self.assertEqual(now, before)

    def test_a_new_source_that_fails_has_no_history_to_carry(self):
        now = new_snapshot({"b": build(pages=[(bad("https://example.test/a/0"), False)])}, T2)
        carry_over(now, self.snapshot(T1, fixture("listing_jsonld.html")))
        self.assertNotIn("stale", now["sources"]["b"])


class Canonical(unittest.TestCase):
    def test_volatile_keys_are_removed_at_every_depth(self):
        snap = self.snapshot = new_snapshot({"a": build(fixture("listing_jsonld.html"))}, T1)
        c = canonical(snap)
        self.assertNotIn("taken_at", c)
        page = c["sources"]["a"]["pages"][0]
        for key in ("fetched_at", "bytes", "text_sha256", "http_status", "final_url", "attempts"):
            self.assertNotIn(key, page)
        self.assertIn("url", page)

    def test_two_runs_a_week_apart_with_the_same_world_are_equal(self):
        a = new_snapshot({"a": build(fixture("listing_jsonld.html"))}, T1)
        b = new_snapshot({"a": build(fixture("listing_jsonld.html"))}, T2)
        b["sources"]["a"]["pages"][0]["fetched_at"] = "2026-10-08T06:00:05Z"
        self.assertEqual(canonical(a), canonical(b))

    def test_a_real_difference_survives(self):
        a = new_snapshot({"a": build(fixture("listing_jsonld.html"))}, T1)
        b = new_snapshot({"a": build(fixture("listing_jsonld.html").replace("1,234 installs", "2,345 installs"))}, T2)
        self.assertNotEqual(canonical(a), canonical(b))


if __name__ == "__main__":
    unittest.main()

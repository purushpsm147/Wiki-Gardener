import unittest

import helpers
from competitor_watch.config import Mention
from competitor_watch.extract import (
    extract_features,
    extract_fields,
    extract_headings,
    find_candidates,
    find_mentions,
    json_fields,
    parse_count,
    parse_html,
    scan_keywords,
    text_fields,
    text_sha256,
)

fixture = helpers.fixture


class Parser(unittest.TestCase):
    def setUp(self):
        self.page = parse_html(fixture("listing_jsonld.html"), "https://marketplace.example/apps/1/x")

    def test_title_and_meta(self):
        self.assertEqual(self.page.title, "Example Page Hygiene for Confluence | Atlassian Marketplace")
        self.assertEqual(self.page.meta["description"], "Keeps Confluence pages clean and current.")
        self.assertEqual(self.page.meta["og:title"], "Example Page Hygiene for Confluence")

    def test_navigation_footer_scripts_and_the_html_comment_are_not_text(self):
        text = self.page.text
        for banned in ("must be ignored", "SYNTHETIC", "999999", "window.__analytics", "softwareVersion"):
            self.assertNotIn(banned, text)
        self.assertIn("Keeps your Confluence knowledge base clean", text)

    def test_blocks_become_lines_and_inline_tags_do_not(self):
        page = parse_html("<p>One <b>bold</b> word.</p><div>Two<br>lines</div>")
        self.assertEqual(page.blocks, ["One bold word.", "Two", "lines"])

    def test_headings_and_list_items(self):
        self.assertEqual([h for h in self.page.headings if h[0] == "h2"], [("h2", "Highlights"), ("h2", "Details")])
        self.assertIn("Finds stubs, outdated pages and orphaned pages", self.page.list_items)
        self.assertNotIn("Marketplace navigation item that must be ignored by the parser", self.page.list_items)

    def test_json_ld_is_parsed_and_other_scripts_are_counted_but_not_parsed(self):
        self.assertEqual(len(self.page.json_blobs), 1)
        self.assertEqual(self.page.json_blobs[0]["@type"], "SoftwareApplication")
        self.assertEqual(self.page.script_count, 2)
        self.assertEqual(self.page.json_errors, 0)

    def test_broken_json_is_counted_not_raised(self):
        page = parse_html('<script type="application/ld+json">{oops</script><p>x</p>')
        self.assertEqual((page.json_blobs, page.json_errors), ([], 1))

    def test_links_are_made_absolute(self):
        page = parse_html('<a href="/apps/9/x">Nine</a><a href="https://e.test/y">Why</a><a>no href</a>', "https://marketplace.example/search")
        self.assertEqual(page.links, [("https://marketplace.example/apps/9/x", "Nine"), ("https://e.test/y", "Why")])

    def test_nested_skip_tags_and_unbalanced_markup_do_not_crash(self):
        page = parse_html("<nav><ul><li>skip</li></ul></nav><p>keep<p>keep too<div>")
        self.assertEqual(page.blocks, ["keep", "keep too"])

    def test_an_empty_single_page_app_is_a_js_shell(self):
        page = parse_html(fixture("js_shell.html"))
        self.assertTrue(page.js_shell)
        self.assertFalse(parse_html(fixture("listing_text.html")).js_shell)

    def test_a_short_page_with_a_challenge_phrase_is_a_bot_wall_but_a_long_one_is_not(self):
        self.assertTrue(parse_html(fixture("bot_wall.html")).bot_wall)
        long_text = "<p>" + ("Real content about access denied pages in Confluence. " * 80) + "</p>"
        self.assertFalse(parse_html(long_text).bot_wall)

    def test_text_hash_ignores_whitespace(self):
        self.assertEqual(text_sha256("a  b\n c"), text_sha256("a b c"))
        self.assertNotEqual(text_sha256("a b c"), text_sha256("a b d"))


class Counts(unittest.TestCase):
    def test_parse_count(self):
        cases = {"1,234": 1234, "10,000+": 10000, "1.2k": 1200, "3M": 3_000_000, 5: 5, 5.0: 5, " 42 ": 42}
        for raw, want in cases.items():
            self.assertEqual(parse_count(raw), want, raw)
        for raw in ("many", "", None, True, -1, "1,2,3x"):
            self.assertIsNone(parse_count(raw), raw)


class JsonFields(unittest.TestCase):
    def test_json_ld(self):
        f = extract_fields(parse_html(fixture("listing_jsonld.html")))
        self.assertEqual(f["name"]["value"], "Example Page Hygiene for Confluence")
        self.assertEqual(f["rating"]["value"], 4.5)
        self.assertEqual(f["review_count"]["value"], 23)
        self.assertEqual(f["version"]["value"], "4.2.0")
        self.assertEqual(f["last_updated"]["value"], "2026-03-16")
        self.assertEqual(f["vendor"]["value"], "Example Vendor")
        self.assertEqual(f["price_samples"]["value"], [{"key": "price", "value": 13.97}])
        self.assertEqual(f["price_currency"]["value"], "USD")
        self.assertTrue(f["rating"]["source"].startswith("json:$.aggregateRating"))

    def test_json_ld_beats_text_patterns_and_the_text_still_fills_gaps(self):
        f = extract_fields(parse_html(fixture("listing_jsonld.html")))
        self.assertTrue(f["rating"]["source"].startswith("json:"))
        self.assertEqual(f["installs"], {"value": 1234, "source": "text:installs"})

    def test_embedded_next_data_is_searched_by_key_name_not_position(self):
        f = extract_fields(parse_html(fixture("listing_nextdata.html")))
        self.assertEqual(f["installs"]["value"], 1234)
        self.assertEqual(f["downloads"]["value"], 5000)
        self.assertEqual(f["review_count"]["value"], 23)
        self.assertEqual(f["rating"]["value"], 4.5)
        self.assertEqual(f["last_updated"]["value"], "2026-03-16T10:00:00Z")
        self.assertEqual(f["version"]["value"], "4.2.0")
        self.assertEqual(f["vendor"]["value"], "Example Vendor")
        self.assertTrue(f["installs"]["source"].endswith("totalInstalls"))
        self.assertEqual([p["value"] for p in f["price_samples"]["value"]], [0.0, 13.97, 27.5])

    def test_values_that_cannot_be_what_they_claim_are_ignored(self):
        f = json_fields([{"rating": 17, "stars": "lots", "installs": "many", "version": "latest", "count": 5}])
        self.assertEqual(f, {})

    def test_a_count_only_counts_as_reviews_under_a_reviews_key(self):
        self.assertEqual(json_fields([{"tags": {"count": 9}}]), {})
        self.assertEqual(json_fields([{"reviews": {"count": 9}}])["review_count"]["value"], 9)

    def test_json_in_a_list_and_deeply_nested_json(self):
        self.assertEqual(json_fields([[{"installs": 7}]])["installs"]["value"], 7)
        deep = cur = {}
        for _ in range(40):
            cur["x"] = {}
            cur = cur["x"]
        cur["installs"] = 5
        self.assertEqual(json_fields([deep]), {}, "depth is capped, so a hostile page cannot recurse forever")

    def test_at_most_six_price_samples(self):
        f = json_fields([{"items": [{"price": i} for i in range(20)]}])
        self.assertEqual(len(f["price_samples"]["value"]), 6)


class TextFields(unittest.TestCase):
    def test_patterns(self):
        f = extract_fields(parse_html(fixture("listing_text.html")))
        self.assertEqual(f["installs"]["value"], 1234)
        self.assertEqual(f["review_count"]["value"], 23)
        self.assertEqual(f["rating"]["value"], 4.5)
        self.assertEqual(f["version"]["value"], "4.2.0")
        self.assertEqual(f["last_updated"]["value"], "March 16th, 2026")
        self.assertEqual(f["price_text"]["value"], "$13.97 USD per month")
        self.assertEqual(f["free_tier"]["value"].lower(), "free for up to 10 users")
        self.assertTrue(all(v["source"].startswith("text:") for v in f.values() if v["source"] != "meta:description"))

    def test_date_shapes(self):
        for text, want in (("Last updated: Mar 16, 2026", "Mar 16, 2026"), ("Updated 16 March 2026", "16 March 2026"), ("released 2026-03-16", "2026-03-16")):
            self.assertEqual(text_fields(text)["last_updated"]["value"], want, text)

    def test_an_out_of_range_rating_is_not_taken(self):
        self.assertNotIn("rating", text_fields("9 out of 5"))

    def test_no_match_no_field(self):
        self.assertEqual(text_fields("Nothing to see here."), {})


class Keywords(unittest.TestCase):
    classes = {k: tuple(v) for k, v in helpers.KEYWORDS.items()}

    def test_counts_and_context(self):
        text = "Our tool finds contradictions between pages and prevents stale answers. It flags conflicting policies as you edit."
        r = scan_keywords(text, self.classes, width=20)
        self.assertEqual(r["contradiction"]["count"], 2)
        self.assertEqual([h["term"] for h in r["contradiction"]["hits"]], ["contradictions", "conflicting"])
        self.assertIn("finds contradictions between", r["contradiction"]["hits"][0]["snippet"])
        self.assertEqual({h["term"] for h in r["change_time"]["hits"]}, {"prevents", "as you edit"})

    def test_classes_are_independent_and_empty_ones_are_present(self):
        r = scan_keywords("Nothing relevant.", self.classes)
        self.assertEqual(r, {"contradiction": {"count": 0, "hits": []}, "change_time": {"count": 0, "hits": []}})

    def test_case_insensitive(self):
        self.assertEqual(scan_keywords("CONTRADICTION", self.classes)["contradiction"]["count"], 1)

    def test_a_nearby_second_match_does_not_repeat_the_snippet(self):
        r = scan_keywords("conflict conflict conflict", {"contradiction": ("conflict",)}, width=40)
        self.assertEqual(r["contradiction"]["count"], 3)
        self.assertEqual(len(r["contradiction"]["hits"]), 1)

    def test_hit_cap_and_stable_hashes(self):
        text = " ".join(f"filler{i} " * 40 + "conflict" for i in range(60))
        r = scan_keywords(text, {"contradiction": ("conflict",)}, max_hits=5)
        self.assertEqual(len(r["contradiction"]["hits"]), 5)
        again = scan_keywords(text, {"contradiction": ("conflict",)}, max_hits=5)
        self.assertEqual(r, again)

    def test_release_note_fixture(self):
        text = parse_html(fixture("release_notes.html")).text
        r = scan_keywords(text, self.classes)
        self.assertEqual(r["contradiction"]["count"], 1, "the Bitbucket 'merge conflict' sentence matches, and a human has to judge it")
        self.assertIn("merge conflict", r["contradiction"]["hits"][0]["snippet"])


class Mentions(unittest.TestCase):
    text = parse_html(fixture("release_notes.html")).text

    def test_all_terms_required(self):
        r = find_mentions(self.text, (Mention("doc-agent", ("documentation agent",)),))
        self.assertEqual(len(r["doc-agent"]), 1)
        self.assertIn("staleness", r["doc-agent"][0]["text"])

    def test_all_and_any(self):
        m = Mention("rovo-quality", ("rovo",), ("outdated", "stale", "contradict"))
        r = find_mentions(self.text, (m,))
        self.assertEqual(len(r["rovo-quality"]), 2)

    def test_no_match_gives_an_empty_list_not_a_missing_key(self):
        self.assertEqual(find_mentions(self.text, (Mention("x", ("zzz",)),)), {"x": []})

    def test_sentences_are_deduplicated_and_truncated(self):
        r = find_mentions("Rovo is great. Rovo is great. " + "Rovo " * 200, (Mention("r", ("rovo",)),))
        self.assertEqual(len(r["r"]), 2)
        self.assertLessEqual(max(len(x["text"]) for x in r["r"]), 400)


class FeaturesAndDiscovery(unittest.TestCase):
    def test_features_are_list_items_of_plausible_length_without_repeats_or_navigation(self):
        page = parse_html(fixture("listing_jsonld.html"))
        self.assertEqual(
            extract_features(page),
            ["Scores every page for freshness, clarity and context", "Finds stubs, outdated pages and orphaned pages", "Bulk remediation: label pages or notify their owners"],
        )

    def test_headings(self):
        self.assertEqual(extract_headings(parse_html(fixture("listing_jsonld.html"))), ["Highlights", "Details"])

    def test_search_finds_a_matching_app_link(self):
        page = parse_html(fixture("search_results.html"), "https://marketplace.example/search?q=Evergreen")
        self.assertEqual(find_candidates(page, "Evergreen"), {"found": True, "readable": True, "candidates": ["https://marketplace.example/apps/111/evergreen-docs-keeper"]})

    def test_search_with_results_but_no_match_is_not_found_but_readable(self):
        page = parse_html(fixture("search_results.html"), "https://marketplace.example/search")
        d = find_candidates(page, "Nonexistent")
        self.assertEqual((d["found"], d["readable"]), (False, True))

    def test_empty_results_are_readable_and_not_found(self):
        d = find_candidates(parse_html(fixture("search_empty.html")), "Evergreen")
        self.assertEqual((d["found"], d["readable"], d["candidates"]), (False, True, []))

    def test_an_unreadable_search_page_is_not_a_negative(self):
        d = find_candidates(parse_html(fixture("js_shell.html")), "Evergreen")
        self.assertEqual((d["found"], d["readable"]), (False, False))

    def test_the_query_echoed_in_the_page_text_does_not_count_as_found(self):
        page = parse_html("<h1>Results for Evergreen</h1><a href='/apps/1/other'>Other</a>")
        self.assertFalse(find_candidates(page, "Evergreen")["found"])


if __name__ == "__main__":
    unittest.main()

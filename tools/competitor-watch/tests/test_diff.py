import unittest

import helpers
from competitor_watch.diffing import diff_snapshots, health_lines, should_open_issue
from competitor_watch.snapshot import Fetched, build_entry, carry_over, new_snapshot

fixture, ok, bad = helpers.fixture, helpers.ok, helpers.bad
T1, T2 = "2026-10-01T06:00:00Z", "2026-10-08T06:00:00Z"
BASE = fixture("listing_jsonld.html")


def entry(html, kind="marketplace-listing", cfg=None, **src):
    cfg = cfg or helpers.make_config([helpers.source("a", kind, **src)])
    s = cfg.sources[0]
    return build_entry(s, [Fetched("https://example.test/a", ok("https://example.test/a", html))], cfg)


def snap(taken, **entries):
    return new_snapshot(entries, taken)


CFG = helpers.make_config([helpers.source("a")])


def changes(old_html, new_html, **kw):
    return diff_snapshots(snap(T1, a=entry(old_html, **kw)), snap(T2, a=entry(new_html, **kw)), CFG)


class Baseline(unittest.TestCase):
    def test_no_previous_snapshot_means_no_changes(self):
        self.assertEqual(diff_snapshots(None, snap(T1, a=entry(BASE)), CFG), [])

    def test_identical_snapshots_have_no_changes(self):
        self.assertEqual(changes(BASE, BASE), [])


class Numbers(unittest.TestCase):
    def test_small_install_drift_is_ignored_and_a_big_move_is_routine(self):
        self.assertEqual(changes(BASE, BASE.replace("1,234 installs", "1,250 installs")), [])
        cs = changes(BASE, BASE.replace("1,234 installs", "1,400 installs"))
        self.assertEqual([(c.severity, c.kind, c.before, c.after) for c in cs], [("routine", "field", 1234, 1400)])

    def test_rating_moves_below_the_threshold_are_ignored(self):
        self.assertEqual(changes(BASE, BASE.replace('"ratingValue":4.5', '"ratingValue":4.55')), [])
        cs = changes(BASE, BASE.replace('"ratingValue":4.5', '"ratingValue":4.2'))
        self.assertEqual([(c.severity, c.summary) for c in cs], [("routine", "rating: 4.5 to 4.2")])

    def test_a_new_release_is_always_reported(self):
        cs = changes(BASE, BASE.replace('"softwareVersion":"4.2.0"', '"softwareVersion":"4.3.0"').replace('"dateModified":"2026-03-16"', '"dateModified":"2026-09-30"'))
        self.assertEqual({c.summary for c in cs}, {"version: 4.2.0 to 4.3.0", "last_updated: 2026-03-16 to 2026-09-30"})
        self.assertTrue(all(c.severity == "routine" for c in cs))

    def test_the_threshold_comes_from_the_config(self):
        cfg = helpers.make_config([helpers.source("a")], numeric_change_pct=0.5)
        cs = diff_snapshots(snap(T1, a=entry(BASE)), snap(T2, a=entry(BASE.replace("1,234 installs", "1,250 installs"))), cfg)
        self.assertEqual(len(cs), 1)

    def test_a_count_appearing_or_vanishing_is_reported(self):
        cs = changes(BASE, BASE.replace("1,234 installs.", "Installs hidden."))
        self.assertEqual([(c.kind, c.before, c.after) for c in cs], [("field", 1234, None)])


class Material(unittest.TestCase):
    def test_a_price_change_is_material(self):
        cs = changes(BASE, BASE.replace('"price":"13.97"', '"price":"15.00"'))
        self.assertEqual([(c.severity, c.summary) for c in cs], [("material", "price_samples changed")])

    def test_a_changed_summary_or_name_is_material(self):
        cs = changes(BASE, BASE.replace("flags stale pages for their owners", "finds contradictions between pages"))
        self.assertIn(("material", "summary changed"), [(c.severity, c.summary) for c in cs])

    def test_features_added_and_removed_are_grouped_and_material(self):
        html = BASE.replace("<li>Finds stubs, outdated pages and orphaned pages</li>", "<li>Detects contradictions between pages automatically</li>")
        cs = changes(BASE, html)
        feature = {c.summary: c for c in cs if c.kind == "feature"}
        self.assertEqual(set(feature), {"1 feature(s) added", "1 feature(s) removed"})
        self.assertEqual(feature["1 feature(s) added"].after, ["Detects contradictions between pages automatically"])
        self.assertTrue(all(c.severity == "material" for c in feature.values()))

    def test_a_new_contradiction_claim_is_material_and_carries_its_context(self):
        html = BASE.replace("Keeps your Confluence knowledge base clean", "Detects contradictions in your Confluence knowledge base")
        kw = [c for c in changes(BASE, html) if c.kind == "keyword"]
        self.assertEqual(len(kw), 1)
        self.assertEqual((kw[0].severity, kw[0].summary), ("material", "new 'contradiction' mention: \"contradictions\""))
        self.assertIn("Detects contradictions in your Confluence", kw[0].after)

    def test_a_new_change_time_claim_is_material(self):
        html = BASE.replace("tells page owners which pages", "tells authors as you edit which pages")
        kw = [c for c in changes(BASE, html) if c.kind == "keyword"]
        self.assertEqual([(c.severity, c.summary) for c in kw], [("material", "new 'change_time' mention: \"as you edit\"")])

    def test_a_claim_that_disappears_is_also_reported(self):
        html = BASE.replace("Keeps your Confluence knowledge base clean", "Detects contradictions in your Confluence knowledge base")
        kw = [c for c in changes(html, BASE) if c.kind == "keyword"]
        self.assertEqual([c.summary for c in kw], ["'contradiction' mention gone: \"contradictions\""])

    def test_keyword_classes_outside_the_thesis_are_routine(self):
        cfg = helpers.make_config([helpers.source("a")], keywords={**helpers.KEYWORDS, "pricing_words": ["discount"]})
        old, new = entry(BASE, cfg=cfg), entry(BASE.replace("Details", "Details and a discount"), cfg=cfg)
        cs = diff_snapshots(snap(T1, a=old), snap(T2, a=new), cfg)
        self.assertEqual([(c.severity, c.kind) for c in cs if c.kind == "keyword"], [("routine", "keyword")])

    def test_new_mentions_on_atlassian_pages_are_material(self):
        src = {"mentions": [{"id": "documentation-agent", "all": ["documentation agent"]}]}
        old_html = fixture("release_notes.html").replace("Documentation Agent", "Docs Helper")
        cs = changes(old_html, fixture("release_notes.html"), kind="page", **src)
        self.assertEqual([(c.severity, c.kind, c.summary) for c in cs if c.kind == "mention"], [("material", "mention", "new 'documentation-agent' sentence")])

    def test_a_listing_appearing_in_search_is_material(self):
        s = {"expect_text": "Evergreen", "min_text_chars": 0}
        cs = changes(fixture("search_empty.html"), fixture("search_results.html"), kind="search", **s)
        self.assertEqual([(c.severity, c.kind) for c in cs if c.kind == "discovery"], [("material", "discovery")])
        gone = changes(fixture("search_results.html"), fixture("search_empty.html"), kind="search", **s)
        self.assertIn("no longer in the results", [c.summary for c in gone if c.kind == "discovery"][0])

    def test_an_unreadable_search_does_not_claim_the_listing_vanished(self):
        s = {"expect_text": "Evergreen", "min_text_chars": 0}
        unreadable = "<h1>Marketplace</h1><p>" + "Browse apps for your team. " * 20 + "</p>"
        self.assertEqual([c for c in changes(fixture("search_results.html"), unreadable, kind="search", **s) if c.kind == "discovery"], [])


class Structure(unittest.TestCase):
    def test_material_sorts_before_routine(self):
        html = BASE.replace("1,234 installs", "9,999 installs").replace('"price":"13.97"', '"price":"15.00"')
        self.assertEqual([c.severity for c in changes(BASE, html)], ["material", "routine"])

    def test_sources_added_and_removed(self):
        old = snap(T1, a=entry(BASE))
        new = snap(T2, a=entry(BASE), b=entry(BASE))
        self.assertEqual([(c.source, c.kind, c.severity) for c in diff_snapshots(old, new, CFG)], [("b", "source", "material")])
        self.assertEqual([(c.source, c.summary) for c in diff_snapshots(new, old, CFG)], [("b", "source removed from the watch list")])

    def test_a_stale_entry_is_never_diffed(self):
        old = snap(T1, a=entry(BASE))
        failed = snap(T2, a=build_entry(CFG.sources[0], [Fetched("https://example.test/a", bad("https://example.test/a"))], CFG))
        carry_over(failed, old)
        self.assertEqual(diff_snapshots(old, failed, CFG), [], "a bad week must not read as 'the competitor removed every feature'")

    def test_a_source_that_was_stale_is_compared_with_its_last_good_data_when_it_recovers(self):
        old = snap(T1, a=entry(BASE))
        outage = snap(T2, a=build_entry(CFG.sources[0], [Fetched("https://example.test/a", bad("https://example.test/a"))], CFG))
        carry_over(outage, old)
        back = snap("2026-10-15T06:00:00Z", a=entry(BASE.replace('"price":"13.97"', '"price":"15.00"')))
        self.assertEqual([c.summary for c in diff_snapshots(outage, back, CFG)], ["price_samples changed"])

    def test_a_source_with_no_baseline_yet_is_not_diffed_against_nothing(self):
        failed = build_entry(CFG.sources[0], [Fetched("https://example.test/a", bad("https://example.test/a"))], CFG)
        self.assertEqual(diff_snapshots(snap(T1, a=failed), snap(T2, a=entry(BASE)), CFG), [], "no features-added flood on the first good week")

    def test_the_title_counts_as_routine(self):
        cs = changes(BASE, BASE.replace("<title>Example Page Hygiene", "<title>Renamed Page Hygiene"))
        self.assertIn(("routine", "title"), [(c.severity, c.kind) for c in cs])


class IssueGate(unittest.TestCase):
    def test_default_opens_an_issue_for_any_change_and_nothing_for_none(self):
        cs = changes(BASE, BASE.replace("1,234 installs", "1,400 installs"))
        self.assertTrue(should_open_issue(cs, CFG))
        self.assertFalse(should_open_issue([], CFG))

    def test_material_only_mode_ignores_routine_changes(self):
        cfg = helpers.make_config([helpers.source("a")], issue_on="material")
        routine = changes(BASE, BASE.replace("1,234 installs", "1,400 installs"))
        material = changes(BASE, BASE.replace('"price":"13.97"', '"price":"15.00"'))
        self.assertFalse(should_open_issue(routine, cfg))
        self.assertTrue(should_open_issue(material, cfg))


class Health(unittest.TestCase):
    def test_failed_partial_and_recovered(self):
        good = entry(BASE)
        failed = build_entry(CFG.sources[0], [Fetched("https://example.test/a", bad("https://example.test/a"))], CFG)
        old = snap(T1, a=good, b=failed, c=good)
        partial = entry("<p>" + "words that are long enough but hold no facts at all. " * 5 + "</p>", require_any_field=["installs"])
        new = snap(T2, a=failed, b=good, c=partial)
        carry_over(new, old)
        lines = health_lines(old, new)
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[0].startswith("FAILED a (showing last good data from 2026-10-01T06:00:00Z)"))
        self.assertEqual(lines[1], "RECOVERED b: was failed, now ok")
        self.assertTrue(lines[2].startswith("PARTIAL c: no structured fact found"))

    def test_a_brand_new_failing_source_says_there_is_nothing_to_show(self):
        failed = build_entry(CFG.sources[0], [Fetched("https://example.test/a", bad("https://example.test/a", "blocked by robots.txt", None))], CFG)
        self.assertIn("nothing usable and no earlier data): https://example.test/a: blocked by robots.txt", health_lines(None, snap(T1, a=failed))[0])

    def test_all_healthy_gives_no_lines(self):
        self.assertEqual(health_lines(snap(T1, a=entry(BASE)), snap(T2, a=entry(BASE))), [])


if __name__ == "__main__":
    unittest.main()

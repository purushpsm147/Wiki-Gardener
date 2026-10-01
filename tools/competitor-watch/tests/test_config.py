import json
import unittest

import helpers  # noqa: F401  (puts competitor_watch on the path)
from competitor_watch.config import ConfigError, load_config, parse_config

REAL = helpers.TOOL / "sources.json"


def minimal(**over):
    obj = {"schema": 1, "user_agent": "x/1 (+https://e.test)", "keywords": helpers.KEYWORDS, "sources": [helpers.source("a")]}
    obj.update(over)
    return obj


class RealConfig(unittest.TestCase):
    def test_the_shipped_sources_json_is_valid(self):
        cfg = load_config(REAL)
        ids = [s.id for s in cfg.sources]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(cfg.enabled_sources())

    def test_it_watches_what_the_brief_names_plus_atlassian(self):
        cfg = load_config(REAL)
        on = {s.id for s in cfg.enabled_sources()}
        for needed in ("ai-hygiene-inspector", "better-content-archiving", "evergreen-ai-for-confluence", "atlassian-cloud-changes", "atlassian-rovo-confluence-guide"):
            self.assertIn(needed, on)

    def test_evergreen_is_the_kill_clause_subject_and_is_a_search_because_no_listing_was_found(self):
        cfg = load_config(REAL)
        e = next(s for s in cfg.sources if s.id == "evergreen-ai-for-confluence")
        self.assertTrue(e.kill_clause_subject)
        self.assertEqual(e.kind, "search")
        self.assertIn("NOT LOCATED", e.note)

    def test_leads_are_off_by_default(self):
        cfg = load_config(REAL)
        self.assertEqual({s.id for s in cfg.sources if s.role == "lead"}, {"freshpage", "evergreen-team"})
        self.assertFalse(any(s.enabled for s in cfg.sources if s.role == "lead"))

    def test_every_source_says_why_it_is_watched(self):
        for s in load_config(REAL).sources:
            self.assertTrue(s.provenance, s.id)

    def test_the_brief_keywords_are_covered(self):
        import re

        cfg = load_config(REAL)
        rx = re.compile("|".join(cfg.keywords["contradiction"]), re.I)
        for word in ("contradiction", "conflict", "inconsistent"):
            self.assertTrue(rx.search(word), word)


class Validation(unittest.TestCase):
    def problems(self, obj):
        with self.assertRaises(ConfigError) as cm:
            parse_config(obj)
        return str(cm.exception)

    def test_reports_every_problem_at_once_and_names_the_source(self):
        msg = self.problems(
            minimal(
                keywords={"contradiction": ["(unclosed"]},
                sources=[
                    helpers.source("a", urls=["http://insecure.test"]),
                    helpers.source("a"),
                    helpers.source("s", kind="search"),
                    helpers.source("Bad Id"),
                ],
            )
        )
        for fragment in ("not a valid regular expression", "keywords.change_time is required", "must be an https URL", "duplicate id", "needs expect_text", "id must be lower-case"):
            self.assertIn(fragment, msg)
        self.assertIn("sources[0] (a)", msg)

    def test_schema_and_user_agent_are_required(self):
        msg = self.problems(minimal(schema=2, user_agent=" "))
        self.assertIn("schema must be 1", msg)
        self.assertIn("user_agent", msg)

    def test_an_enabled_source_needs_a_url_a_disabled_one_does_not(self):
        self.assertIn("at least one url", self.problems(minimal(sources=[helpers.source("a", urls=[])])))
        parse_config(minimal(sources=[helpers.source("a", urls=[], enabled=False)]))

    def test_kinds_roles_and_issue_on_are_checked(self):
        msg = self.problems(minimal(issue_on="sometimes", sources=[helpers.source("a", kind="rss", role="friend")]))
        for fragment in ("kind must be", "role must be", "issue_on must be"):
            self.assertIn(fragment, msg)

    def test_mentions_need_an_id_and_terms(self):
        self.assertIn("each mention needs", self.problems(minimal(sources=[helpers.source("a", mentions=[{"id": "m"}])])))

    def test_not_json_and_missing_file(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"
            p.write_text("{nope", encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "not valid JSON"):
                load_config(p)
            with self.assertRaisesRegex(ConfigError, "does not exist"):
                load_config(Path(d) / "missing.json")
            p.write_text(json.dumps(minimal()), encoding="utf-8")
            self.assertEqual(load_config(p).sources[0].id, "a")


if __name__ == "__main__":
    unittest.main()

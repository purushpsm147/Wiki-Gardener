import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import helpers
from competitor_watch import cli

fixture, ok, bad = helpers.fixture, helpers.ok, helpers.bad

CFG = helpers.make_config(
    [
        helpers.source("hygiene", provenance="SYNTHETIC", optional_urls=["https://example.test/hygiene/pricing"]),
        helpers.source("evergreen", "search", name="Evergreen AI for Confluence", kill_clause_subject=True, expect_text="Evergreen", min_text_chars=0),
        helpers.source("atlassian", "page", role="atlassian", mentions=[{"id": "documentation-agent", "all": ["documentation agent"]}]),
    ]
)
WORLD = {
    "hygiene": fixture("listing_jsonld.html"),
    "evergreen": fixture("search_empty.html"),
    "atlassian": fixture("release_notes.html"),
}


def loader(world, failing=()):
    def load(url, sid, index):
        if sid in failing or index > 0:  # the optional pricing page does not exist in the fake world
            return bad(url, "HTTP 503" if sid in failing else "HTTP 404", 503 if sid in failing else 404)
        return ok(url, world[sid])

    return load


class Run(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.snaps = self.dir / "snapshots"
        self.out = self.dir / "out.txt"
        self.report = self.dir / "report.md"

    def go(self, world=WORLD, failing=(), now="2026-10-01T06:00:00Z", extra=()):
        args = cli.build_parser().parse_args(["run", "--snapshots", str(self.snaps), "--report", str(self.report), "--github-output", str(self.out), *extra])
        with contextlib.redirect_stdout(io.StringIO()):
            code = cli.run(args, CFG, loader=loader(world, failing), now=lambda: now)
        outputs = dict(line.split("=", 1) for line in self.out.read_text().splitlines())
        self.out.unlink()
        return code, outputs

    def latest(self):
        return json.loads((self.snaps / "latest.json").read_text())

    def test_the_first_run_is_a_baseline_and_writes_json_and_markdown(self):
        code, out = self.go()
        self.assertEqual(code, 0)
        self.assertEqual((out["baseline"], out["changed"], out["failed"], out["snapshot_changed"]), ("true", "false", "false", "true"))
        self.assertEqual(out["summary"], "baseline taken")
        snap = self.latest()
        self.assertEqual(set(snap["sources"]), {"hygiene", "evergreen", "atlassian"})
        self.assertEqual(snap["sources"]["hygiene"]["status"], "ok")
        self.assertEqual(snap["taken_at"], "2026-10-01T06:00:00Z")
        self.assertEqual(len([p for p in snap["sources"]["hygiene"]["pages"] if p["optional"]]), 1)
        self.assertIn("# Competitor snapshot", (self.snaps / "latest.md").read_text())
        self.assertIn("baseline taken", self.report.read_text())

    def test_the_json_is_stable_so_that_git_diffs_are_small(self):
        self.go()
        text = (self.snaps / "latest.json").read_text()
        self.assertEqual(text, json.dumps(json.loads(text), indent=2, sort_keys=True, ensure_ascii=False) + "\n")

    def test_the_same_world_a_week_later_writes_nothing_and_opens_nothing(self):
        self.go()
        before = (self.snaps / "latest.json").read_text()
        code, out = self.go(now="2026-10-08T06:00:00Z")
        self.assertEqual(code, 0)
        self.assertEqual((out["baseline"], out["changed"], out["snapshot_changed"]), ("false", "false", "false"))
        self.assertEqual((self.snaps / "latest.json").read_text(), before, "taken_at alone is not worth a commit")

    def test_a_new_contradiction_claim_opens_a_material_issue_and_updates_the_snapshot(self):
        self.go()
        world = dict(WORLD, hygiene=fixture("listing_jsonld.html").replace("Keeps your Confluence knowledge base clean", "Detects contradictions in your knowledge base"))
        code, out = self.go(world, now="2026-10-08T06:00:00Z")
        self.assertEqual((code, out["changed"], out["material"], out["snapshot_changed"]), (0, "true", "true", "true"))
        self.assertTrue(out["issue_title"].startswith("competitor-watch: 1 change(s), 1 material (2026-10-08)"))
        self.assertEqual(self.latest()["taken_at"], "2026-10-08T06:00:00Z")
        report = self.report.read_text()
        self.assertIn("(MATERIAL)", report)
        self.assertIn("new 'contradiction' mention", report)

    def test_a_routine_drift_below_the_threshold_changes_nothing(self):
        self.go()
        world = dict(WORLD, hygiene=fixture("listing_jsonld.html").replace("1,234 installs", "1,240 installs"))
        code, out = self.go(world, now="2026-10-08T06:00:00Z")
        self.assertEqual(out["changed"], "false")
        self.assertEqual(out["snapshot_changed"], "true", "the number did change, so the snapshot is kept current, quietly")

    def test_a_failing_source_exits_2_keeps_last_good_data_and_reports_no_false_changes(self):
        self.go()
        code, out = self.go(failing=("hygiene",), now="2026-10-08T06:00:00Z")
        self.assertEqual(code, 2)
        self.assertEqual((out["failed"], out["changed"]), ("true", "false"))
        e = self.latest()["sources"]["hygiene"]
        self.assertEqual((e["status"], e["stale"], e["last_good_at"]), ("failed", True, "2026-10-01T06:00:00Z"))
        self.assertEqual(e["fields"]["installs"]["value"], 1234)
        report = self.report.read_text()
        self.assertIn("FAILED hygiene (showing last good data from 2026-10-01T06:00:00Z)", report)
        code, out = self.go(now="2026-10-15T06:00:00Z")
        self.assertEqual(code, 0)
        self.assertNotIn("stale", self.latest()["sources"]["hygiene"])
        self.assertIn("RECOVERED hygiene", self.report.read_text())

    def test_a_first_run_where_a_source_fails_is_a_baseline_with_a_failed_entry_and_exit_2(self):
        code, out = self.go(failing=("atlassian",))
        self.assertEqual((code, out["baseline"], out["failed"]), (2, "true", "true"))
        self.assertEqual(self.latest()["sources"]["atlassian"]["status"], "failed")

    def test_when_every_source_fails_on_the_first_run_no_snapshot_is_written(self):
        code, out = self.go(failing=("hygiene", "evergreen", "atlassian"))
        self.assertEqual((code, out["baseline"], out["failed"], out["snapshot_changed"]), (2, "false", "true", "false"))
        self.assertEqual(out["summary"], "no baseline: every source failed")
        self.assertFalse(self.snaps.exists(), "an empty snapshot would be mistaken for a baseline and the next run would report everything as new")
        code, out = self.go(now="2026-10-08T06:00:00Z")
        self.assertEqual((code, out["baseline"], out["changed"]), (0, "true", "false"))

    def test_a_source_with_no_baseline_yet_does_not_flood_the_first_good_week(self):
        self.go(failing=("hygiene",))
        code, out = self.go(now="2026-10-08T06:00:00Z")
        self.assertEqual((code, out["changed"]), (0, "false"))
        self.assertEqual(self.latest()["sources"]["hygiene"]["status"], "ok")

    def test_dry_run_writes_no_snapshot(self):
        code, out = self.go(extra=["--dry-run"])
        self.assertEqual((code, out["snapshot_changed"]), (0, "false"))
        self.assertFalse(self.snaps.exists())

    def test_only_restricts_the_sources_and_an_unknown_id_is_an_error(self):
        code, _ = self.go(extra=["--only", "hygiene"])
        self.assertEqual(set(self.latest()["sources"]), {"hygiene"})
        args = cli.build_parser().parse_args(["run", "--snapshots", str(self.snaps), "--only", "nope"])
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(cli.run(args, CFG, loader=loader(WORLD)), 1)
        self.assertIn("unknown or disabled source id(s): nope", err.getvalue())

    def test_issue_on_material_ignores_routine_changes(self):
        cfg = helpers.make_config([helpers.source("hygiene")], issue_on="material")
        args = cli.build_parser().parse_args(["run", "--snapshots", str(self.snaps), "--github-output", str(self.out)])
        for now, html in (("2026-10-01T06:00:00Z", fixture("listing_jsonld.html")), ("2026-10-08T06:00:00Z", fixture("listing_jsonld.html").replace("1,234 installs", "1,400 installs"))):
            with contextlib.redirect_stdout(io.StringIO()):
                cli.run(args, cfg, loader=lambda url, sid, i, h=html: ok(url, h) if i == 0 else bad(url), now=lambda n=now: n)
        lines = dict(line.split("=", 1) for line in self.out.read_text().splitlines()[-7:])
        self.assertEqual(lines["changed"], "false")


class OfflineRoundTrip(unittest.TestCase):
    def test_pages_saved_with_raw_dir_can_be_replayed_with_from_dir(self):
        with tempfile.TemporaryDirectory() as d:
            raw, a, b = Path(d) / "raw", Path(d) / "a", Path(d) / "b"
            args = cli.build_parser().parse_args(["run", "--snapshots", str(a), "--raw-dir", str(raw)])
            with contextlib.redirect_stdout(io.StringIO()):
                cli.run(args, CFG, loader=loader(WORLD), now=lambda: "2026-10-01T06:00:00Z")
            self.assertEqual(sorted(p.name for p in raw.iterdir()), ["atlassian__0.html", "evergreen__0.html", "hygiene__0.html"])
            replay = cli.build_parser().parse_args(["run", "--snapshots", str(b), "--from-dir", str(raw)])
            with contextlib.redirect_stdout(io.StringIO()):
                code = cli.run(replay, CFG, now=lambda: "2026-10-01T06:00:00Z")
            self.assertEqual(code, 0)
            first, second = json.loads((a / "latest.json").read_text()), json.loads((b / "latest.json").read_text())
            for sid in ("hygiene", "evergreen", "atlassian"):
                self.assertEqual(first["sources"][sid]["fields"], second["sources"][sid]["fields"], sid)
                self.assertEqual(first["sources"][sid]["keywords"], second["sources"][sid]["keywords"], sid)

    def test_a_missing_saved_file_is_a_failure_that_names_the_file(self):
        with tempfile.TemporaryDirectory() as d:
            args = cli.build_parser().parse_args(["run", "--snapshots", str(Path(d) / "s"), "--from-dir", d])
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = cli.run(args, CFG, now=lambda: "2026-10-01T06:00:00Z")
            self.assertEqual(code, 2)
            self.assertIn("no saved file hygiene__0.html", out.getvalue())
            self.assertFalse((Path(d) / "s").exists(), "nothing usable, so no snapshot")

    def test_the_output_file_values_are_single_lines(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "o"
            cli.write_github_output(str(p), {"a": "x\ny  z"})
            self.assertEqual(p.read_text(), "a=x y z\n")


class Commands(unittest.TestCase):
    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_check_config_lists_sources(self):
        code, out, _ = self.run_main(["check-config", "--config", str(helpers.TOOL / "sources.json")])
        self.assertEqual(code, 0)
        self.assertIn("evergreen-ai-for-confluence", out)
        self.assertIn("off freshpage", out)

    def test_a_bad_config_is_reported_and_exits_1(self):
        with tempfile.TemporaryDirectory() as d:
            bad_path = Path(d) / "s.json"
            bad_path.write_text('{"schema": 2}', encoding="utf-8")
            code, _, err = self.run_main(["check-config", "--config", str(bad_path)])
        self.assertEqual(code, 1)
        self.assertIn("schema must be 1", err)

    def test_render_needs_a_baseline_and_can_write_the_markdown(self):
        with tempfile.TemporaryDirectory() as d:
            code, _, err = self.run_main(["render", "--config", str(helpers.TOOL / "sources.json"), "--snapshots", d])
            self.assertEqual(code, 1)
            self.assertIn("no baseline has been taken yet", err)

    def test_render_regenerates_latest_md_from_latest_json(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = helpers.make_config([helpers.source("hygiene")])
            args = cli.build_parser().parse_args(["run", "--snapshots", d])
            with contextlib.redirect_stdout(io.StringIO()):
                cli.run(args, cfg, loader=lambda url, sid, i: ok(url, fixture("listing_jsonld.html")), now=lambda: "2026-10-01T06:00:00Z")
            md = Path(d) / "latest.md"
            md.write_text("stale", encoding="utf-8")
            conf = Path(d) / "c.json"
            conf.write_text(json.dumps({"schema": 1, "user_agent": "u", "keywords": helpers.KEYWORDS, "sources": [helpers.source("hygiene")]}), encoding="utf-8")
            code, _, _ = self.run_main(["render", "--config", str(conf), "--snapshots", d, "--write"])
            self.assertEqual(code, 0)
            self.assertIn("# Competitor snapshot", md.read_text())


if __name__ == "__main__":
    unittest.main()

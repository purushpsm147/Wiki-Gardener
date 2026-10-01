import math
import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import budget as b  # noqa: E402
import report  # noqa: E402


class Storage(unittest.TestCase):
    def setUp(self) -> None:
        self.p = b.Params()

    def test_bytes_per_page_is_signature_plus_band_rows_plus_meta(self):
        self.assertEqual(b.bytes_per_page(self.p), 128 * 4 + 16 * 70 + 150)
        self.assertEqual(b.bytes_per_page(self.p), 1782)

    def test_storage_and_fraction(self):
        self.assertEqual(b.storage_bytes(self.p, 250_000), 1782 * 250_000)
        self.assertAlmostEqual(b.storage_fraction(self.p, 250_000), 1782 * 250_000 / 2**30)

    def test_max_pages_within_inverts_storage(self):
        n = b.max_pages_within(self.p, 0.5)
        self.assertEqual(n, math.floor(0.5 * 2**30 / 1782))
        self.assertLessEqual(b.storage_fraction(self.p, n), 0.5)
        self.assertGreater(b.storage_fraction(self.p, n + 1), 0.5)

    def test_rows_per_page(self):
        self.assertEqual(b.rows_per_page(self.p), 17)

    def test_compact_index_is_12_bytes_per_band_entry(self):
        self.assertEqual(b.compact_index_bytes(self.p, 250_000), 250_000 * 16 * 12)

    def test_g1_flips_when_band_rows_get_large(self):
        """G1 is the fragile criterion: it holds at 70 B rows and fails by 100 B rows."""
        self.assertLessEqual(b.storage_fraction(replace(self.p, band_row_bytes=70), 250_000), 0.5)
        self.assertGreater(b.storage_fraction(replace(self.p, band_row_bytes=100), 250_000), 0.5)


class Cpu(unittest.TestCase):
    def setUp(self) -> None:
        self.p = b.Params()
        self.bench = b.load_bench()

    def test_mix_weights_sum_to_one_and_words_match_the_bench(self):
        self.assertAlmostEqual(sum(w for _, w in self.p.mix), 1.0)
        sizes = {r["words"] for r in self.bench["fingerprint"]}
        self.assertTrue({w for w, _ in self.p.mix} <= sizes)

    def test_mean_words(self):
        self.assertAlmostEqual(b.mean_words(self.p), 0.6 * 300 + 0.3 * 1500 + 0.09 * 6000 + 0.01 * 20000)

    def test_sandbox_cost_is_the_weighted_median(self):
        heavy = {r["words"]: r["us_per_page_median"] for r in self.bench["fingerprint"] if r["markup"] == "heavy"}
        expected = sum(heavy[w] * wt for w, wt in self.p.mix)
        self.assertAlmostEqual(b.sandbox_us_per_page(self.p, self.bench), expected)

    def test_missing_markup_variant_is_an_error(self):
        with self.assertRaises(KeyError):
            b.sandbox_us_per_page(replace(self.p, markup="nonexistent"), self.bench)

    def test_cpu_share_scales_with_memory_and_caps_at_one(self):
        self.assertAlmostEqual(b.cpu_share(1024), 1024 / 1769)
        self.assertEqual(b.cpu_share(4096), 1.0)
        self.assertLess(b.cpu_share(512), b.cpu_share(1024))

    def test_forge_cost_is_sandbox_cost_over_cpu_share(self):
        self.assertAlmostEqual(b.forge_us_per_page(self.p, self.bench), b.sandbox_us_per_page(self.p, self.bench) / (1024 / 1769))
        slower = replace(self.p, core_ratio=0.5)
        self.assertAlmostEqual(b.forge_us_per_page(slower, self.bench), 2 * b.forge_us_per_page(self.p, self.bench))

    def test_batch_seconds_components(self):
        t = b.batch_seconds(self.p, self.bench, 50)
        self.assertEqual(t["fetch"], 5.0)                      # one request
        self.assertEqual(t["sql"], math.ceil(50 * 17 / 500) * 0.25)
        self.assertAlmostEqual(t["cpu"], 50 * b.forge_us_per_page(self.p, self.bench) / 1e6)
        self.assertAlmostEqual(t["total"], t["fetch"] + t["cpu"] + t["sql"])


class Quota(unittest.TestCase):
    def test_scan_points_is_one_per_page_plus_one_per_request(self):
        self.assertEqual(b.scan_points(50_000, 250), 200 + 50_000)
        self.assertEqual(b.scan_points(250_000, 250), 1_000 + 250_000)
        self.assertEqual(b.scan_points(10, 250), 1 + 10)

    def test_scan_hours_and_share(self):
        self.assertAlmostEqual(b.scan_hours(50_200, 65_000, 1.0), 50_200 / 65_000)
        self.assertAlmostEqual(b.scan_hours(50_200, 65_000, 0.2), 5 * 50_200 / 65_000)

    def test_tier2_pool(self):
        self.assertEqual(b.tier2_pool_per_hour(100_000, 10, 1000), 110_000)

    def test_tenants_per_day(self):
        self.assertAlmostEqual(b.tenants_onboarded_per_day(50_000, 65_000, 1.0), 65_000 * 24 / 50_200)

    def test_steady_state_points(self):
        self.assertAlmostEqual(b.steady_points_per_hour(1000, 50_000, 0.05, 8), 1000 * 50_000 * 0.05 * 8 / 730)

    def test_events_and_push_time(self):
        self.assertEqual(b.events_needed(50_000, 50), 1000)
        self.assertEqual(b.events_needed(50_001, 50), 1001)
        self.assertEqual(b.push_minutes(1000, 500), 2.0)

    def test_compute_bound_time_is_batches_times_batch_time_over_concurrency(self):
        p, bench = b.Params(), b.load_bench()
        per = b.batch_seconds(p, bench, 250)["total"]
        self.assertAlmostEqual(b.compute_bound_hours(p, bench, 50_000), 200 * per / 10 / 3600)


class Cost(unittest.TestCase):
    def setUp(self) -> None:
        self.prices = b.load_limits()["forge_prices"]

    def test_function_cost_and_free_allowance(self):
        self.assertAlmostEqual(b.function_cost(1250, self.prices), 1250 * 0.000025)
        self.assertEqual(b.function_cost(1250, self.prices, free=True), 0.0)
        self.assertAlmostEqual(b.function_cost(300_000, self.prices, free=True), 100_000 * 0.000025)

    def test_sql_cost_components(self):
        c = b.sql_cost(0.1, 2.0, 1_000_000, self.prices)
        self.assertAlmostEqual(c["storage"], 0.1 * 730 * 0.0007685)
        self.assertAlmostEqual(c["compute"], 2.0 * 0.143)
        self.assertAlmostEqual(c["requests"], 1.929)
        self.assertAlmostEqual(c["total"], c["storage"] + c["compute"] + c["requests"])

    def test_sql_free_allowance_never_goes_negative(self):
        c = b.sql_cost(0.01, 0.1, 10, self.prices, free=True)
        self.assertEqual(c["total"], 0.0)

    def test_steady_state_at_50k(self):
        p = b.Params()
        s = b.steady_state_monthly(p, self.prices, 50_000)
        self.assertEqual(s["edits"], 2500)
        self.assertAlmostEqual(s["functions"], 2500 * 1.0 * 0.5 * 0.000025)
        self.assertAlmostEqual(s["total"], s["functions"] + s["sql_storage"] + s["sql_compute"] + s["sql_requests"])

    def test_containers_reservation(self):
        c = b.load_limits()["containers"]
        self.assertAlmostEqual(b.containers_monthly(1.0, 2.0, c), 730 * (0.07177 + 2 * 0.00786))
        self.assertAlmostEqual(b.containers_monthly(1.0, 2.0, c, instances=3), 3 * b.containers_monthly(1.0, 2.0, c))


class PreRegistration(unittest.TestCase):
    """Parameters and thresholds were fixed before any number was computed. Changing one must be a deliberate edit."""

    def test_defaults_match_the_pre_registered_table(self):
        p = b.Params()
        self.assertEqual((p.k, p.bands, p.band_row_bytes, p.meta_bytes), (128, 16, 70, 150))
        self.assertEqual(p.mix, ((300, 0.60), (1500, 0.30), (6000, 0.09), (20000, 0.01)))
        self.assertAlmostEqual(b.mean_words(p), 1370)
        self.assertEqual((p.memory_mb, p.mb_per_vcpu, p.pages_per_request, p.request_seconds, p.concurrency),
                         (1024, 1769.0, 250, 5.0, 10))
        self.assertEqual((p.pool_share_best, p.pool_share_plan, p.users), (1.0, 0.20, 1000))
        self.assertEqual((p.monthly_edit_rate, p.edit_function_seconds, p.edit_function_gb, p.edit_sql_requests, p.edit_sql_compute_seconds),
                         (0.05, 1.0, 0.5, 20, 1.0))
        self.assertEqual(p.net_revenue, 830.0)

    def test_all_pre_registered_criteria_pass_and_are_g1_to_g6(self):
        res = b.evaluate(b.Params(), b.load_limits(), b.load_bench())
        self.assertEqual([r["id"] for r in res], ["G1", "G2", "G3", "G4", "G5", "G6"])
        self.assertTrue(all(r["pass"] for r in res), [r for r in res if not r["pass"]])

    def test_g1_fails_under_a_larger_row_overhead(self):
        res = b.evaluate(replace(b.Params(), band_row_bytes=100), b.load_limits(), b.load_bench())
        self.assertFalse(next(r for r in res if r["id"] == "G1")["pass"])

    def test_g3_fails_if_the_pool_share_collapses(self):
        res = b.evaluate(replace(b.Params(), pool_share_plan=0.01), b.load_limits(), b.load_bench())
        self.assertFalse(next(r for r in res if r["id"] == "G3")["pass"])

    def test_gate_sentence(self):
        s = b.gate_sentence(b.Params(), b.load_limits())
        self.assertIn("301k", s)
        self.assertIn("602k", s)
        self.assertIn("ESTIMATED", s)


class Inputs(unittest.TestCase):
    def test_every_limits_section_is_graded_and_sourced(self):
        limits = b.load_limits()
        for name, section in limits.items():
            if not isinstance(section, dict):
                continue
            self.assertTrue(section["evidence"].startswith(("ASSUMED", "VERIFIED")), name)
            if name != "manifest_schema":
                self.assertTrue(section["source"].startswith("https://"), name)

    def test_only_the_manifest_schema_is_verified(self):
        limits = b.load_limits()
        verified = [n for n, s in limits.items() if isinstance(s, dict) and s["evidence"].startswith("VERIFIED")]
        self.assertEqual(verified, ["manifest_schema"])

    def test_bench_shape(self):
        bench = b.load_bench()
        self.assertEqual((bench["meta"]["k"], bench["meta"]["bands"], bench["meta"]["rows"]), (128, 16, 8))
        self.assertIn("Not Forge", bench["meta"]["note"])
        for markup in ("light", "heavy"):
            words = sorted(r["words"] for r in bench["fingerprint"] if r["markup"] == markup)
            self.assertEqual(words, [300, 1500, 6000, 20000])
        heavy = [r for r in bench["fingerprint"] if r["markup"] == "heavy"]
        light = [r for r in bench["fingerprint"] if r["markup"] == "light"]
        self.assertGreater(min(r["storage_bytes_per_word"] for r in heavy), 2.5 * max(r["storage_bytes_per_word"] for r in light))
        self.assertTrue(all(r["us_per_page_median"] > 0 for r in bench["fingerprint"]))
        self.assertEqual([r["pages"] for r in bench["lsh_index_memory"]], [50_000, 100_000, 250_000])


class GeneratedReport(unittest.TestCase):
    def test_budget_file_is_not_stale(self):
        target = ROOT / "BUDGET.md"
        self.assertTrue(target.exists(), "run: python tools/compute-budget/run.py --write")
        self.assertEqual(target.read_text(encoding="utf-8"), report.render_report())

    def test_report_is_deterministic(self):
        self.assertEqual(report.render_report(), report.render_report())

    def test_report_has_every_section_and_the_gate_sentence(self):
        text = report.render_report()
        for needle in ("## 1.", "## 2.", "## 5.", "## 9.", "| G1 |", "| G6 |", "GATE-S2 sentence"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()

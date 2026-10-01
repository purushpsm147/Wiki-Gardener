import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cost_model as cm  # noqa: E402
import report  # noqa: E402


class ModelArithmetic(unittest.TestCase):
    def setUp(self) -> None:
        self.models = cm.load_models()
        self.base = report.base(self.models)

    def test_cost_per_call_is_tokens_times_price(self):
        # 3,000 in x $3/M + 300 out x $15/M
        self.assertAlmostEqual(self.base.cost_per_call, 0.009 + 0.0045, places=10)

    def test_candidate_pairs_is_pages_times_yield(self):
        self.assertEqual(self.base.candidate_pairs, 250)
        self.assertEqual(replace(self.base, pages=10_000, yield_rate=0.001).candidate_pairs, 10)
        self.assertEqual(replace(self.base, pages=250_000, yield_rate=0.02).candidate_pairs, 5_000)

    def test_pair_multiplier_scales_pairs(self):
        self.assertEqual(replace(self.base, pair_multiplier=5.0).candidate_pairs, 1_250)

    def test_backfill_and_monthly_cost(self):
        self.assertAlmostEqual(cm.backfill_llm_cost(self.base), 250 * 0.0135, places=9)
        self.assertAlmostEqual(cm.monthly_calls(self.base), 50)
        self.assertAlmostEqual(cm.monthly_llm_cost(self.base), 50 * 0.0135, places=9)

    def test_calls_per_pair_multiplies_everything(self):
        twice = replace(self.base, calls_per_pair=2.0)
        self.assertAlmostEqual(cm.monthly_llm_cost(twice), 2 * cm.monthly_llm_cost(self.base), places=9)
        self.assertAlmostEqual(cm.backfill_llm_cost(twice), 2 * cm.backfill_llm_cost(self.base), places=9)

    def test_compute_cost_is_gb_seconds_priced(self):
        per_call = 15 * 0.5 * 0.000025
        self.assertAlmostEqual(cm.compute_cost_per_call(self.base), per_call, places=12)
        self.assertAlmostEqual(cm.monthly_compute_cost(self.base), 50 * per_call, places=12)

    def test_revenue_and_share(self):
        self.assertAlmostEqual(cm.gross_revenue(self.base), 1_000)
        self.assertAlmostEqual(cm.net_revenue(self.base), 830)
        self.assertAlmostEqual(cm.llm_share_of_net(self.base), 0.675 / 830, places=9)
        self.assertAlmostEqual(cm.llm_share_of_gross(self.base), 0.675 / 1_000, places=9)

    def test_gross_margin(self):
        expected = (830 - 0.675 - 50 * 15 * 0.5 * 0.000025) / 830
        self.assertAlmostEqual(cm.gross_margin(self.base), expected, places=9)

    def test_breakeven_revenue_is_the_30_percent_point(self):
        be = cm.breakeven_net_revenue(self.base)
        self.assertAlmostEqual(cm.monthly_llm_cost(self.base) / be, 0.30, places=9)
        # a tenant paying exactly the break-even net revenue sits on the threshold
        price = be / (self.base.users * (1 - self.base.take_rate))
        at = replace(self.base, price_per_user=price)
        self.assertAlmostEqual(cm.llm_share_of_net(at), 0.30, places=9)
        self.assertFalse(cm.exceeds_threshold(replace(at, price_per_user=price * 1.01)))
        self.assertTrue(cm.exceeds_threshold(replace(at, price_per_user=price * 0.99)))

    def test_max_pairs_within_budget_inverts_the_cost(self):
        mp = cm.max_pairs_within_budget(self.base)
        cost_at_max = mp * self.base.monthly_churn * self.base.calls_per_pair * self.base.cost_per_call
        self.assertAlmostEqual(cost_at_max, 0.30 * cm.net_revenue(self.base), places=6)

    def test_zero_users_means_infinite_share_and_a_flag(self):
        s = replace(self.base, users=0)
        self.assertEqual(cm.llm_share_of_net(s), float("inf"))
        self.assertTrue(cm.exceeds_threshold(s))

    def test_costs_move_the_right_way(self):
        c = cm.monthly_llm_cost
        self.assertLess(c(self.base), c(replace(self.base, yield_rate=0.02)))
        self.assertLess(c(self.base), c(replace(self.base, profile=cm.PROFILES["T4"])))
        self.assertLess(c(self.base), c(replace(self.base, monthly_churn=1.0)))
        self.assertLess(c(replace(self.base, model=self.models["haiku-4.5"])), c(self.base))
        self.assertLess(c(self.base), c(replace(self.base, model=self.models["opus-4.6"])))


class Throughput(unittest.TestCase):
    def setUp(self) -> None:
        self.base = report.base(cm.load_models())

    def test_token_limit_binds_for_base_profile(self):
        # 250 calls x 3,300 tokens = 825,000 tokens at 50k/min = 16.5 min; requests: 250 / 100 = 2.5 min
        self.assertAlmostEqual(cm.backfill_minutes(self.base, 50_000, 100), 16.5)

    def test_request_limit_binds_for_tiny_prompts(self):
        tiny = replace(self.base, profile=cm.TokenProfile("x", "tiny", 10, 10), yield_rate=0.02)  # 1,000 calls
        self.assertAlmostEqual(cm.backfill_minutes(tiny, 50_000, 100), 10.0)


class PreRegistration(unittest.TestCase):
    """The base case and criteria were fixed before the model was run. Changing them must be a conscious edit."""

    def setUp(self) -> None:
        self.models = cm.load_models()

    def test_base_case_parameters(self):
        b = report.base(self.models)
        self.assertEqual((b.pages, b.yield_rate, b.monthly_churn, b.users, b.price_per_user, b.take_rate),
                         (50_000, 0.005, 0.20, 1_000, 1.00, 0.17))
        self.assertEqual((b.profile.input_tokens, b.profile.output_tokens), (3_000, 300))
        self.assertEqual((b.model.key, b.model.input_per_mtok, b.model.output_per_mtok), ("sonnet-4.5", 3.0, 15.0))
        self.assertEqual(cm.KILL_THRESHOLD, 0.30)

    def test_pre_registered_outcomes(self):
        self.assertFalse(cm.exceeds_threshold(report.base(self.models)), "K1")
        self.assertFalse(cm.exceeds_threshold(report.k2(self.models)), "K2")
        self.assertTrue(cm.exceeds_threshold(report.k3(self.models)), "K3 is the stress case and is expected to fail")
        lim = cm.load_prices()["forge_llm_limits"]
        minutes = cm.backfill_minutes(
            report.base(self.models), lim["tokens_per_minute_per_installation_per_model"], lim["requests_per_minute"]
        )
        self.assertLessEqual(minutes, 24 * 60, "K4")


class PriceTable(unittest.TestCase):
    def setUp(self) -> None:
        self.data = cm.load_prices()

    def test_every_price_is_graded_and_sourced(self):
        for m in self.data["models"]:
            self.assertTrue(m["evidence"].startswith(("ASSUMED", "VERIFIED")), m["key"])
            self.assertTrue(m["source"], m["key"])
        for section in ("forge_credits", "forge_platform", "forge_llm_limits", "billing_party", "marketplace_revenue_share"):
            self.assertTrue(self.data[section]["evidence"].startswith(("ASSUMED", "VERIFIED")), section)
            self.assertTrue(self.data[section]["source"], section)

    def test_credit_prices_are_consistent_with_dollar_prices(self):
        """The search summary said '10/30/50 credits'; only a per-token reading matches the dollar prices."""
        c = self.data["forge_credits"]
        by_key = {m["key"]: m for m in self.data["models"]}
        for key, credits in c["credits_per_token"].items():
            m = by_key[key]
            self.assertAlmostEqual(m["input_per_mtok"] / c["usd_per_million_input_credits"], credits, places=9, msg=key)
            self.assertAlmostEqual(m["output_per_mtok"] / c["usd_per_million_output_credits"], credits, places=9, msg=key)

    def test_models_load_into_dataclasses(self):
        models = cm.load_models()
        self.assertEqual(set(models), {"haiku-4.5", "sonnet-4.5", "sonnet-5", "opus-4.6"})
        self.assertTrue(all(isinstance(m, cm.ModelPrice) for m in models.values()))


class GeneratedReport(unittest.TestCase):
    def test_sensitivity_file_is_not_stale(self):
        target = ROOT / "SENSITIVITY.md"
        self.assertTrue(target.exists(), "run: python tools/cost-model/run.py --write")
        self.assertEqual(target.read_text(encoding="utf-8"), report.render_report())

    def test_report_is_deterministic(self):
        self.assertEqual(report.render_report(), report.render_report())

    def test_report_states_the_criteria_results(self):
        text = report.render_report()
        for needle in ("| K1 |", "| K2 |", "| K3 |", "| K4 |", "Pre-registered base case"):
            self.assertIn(needle, text)


class Formatting(unittest.TestCase):
    def test_pct_and_usd(self):
        self.assertEqual(report.pct(0.00001), "<0.01%")
        self.assertEqual(report.pct(0.0008), "0.08%")
        self.assertEqual(report.pct(5.0), "500%")
        self.assertEqual(report.pct(11.0), ">1000%")
        self.assertEqual(report.usd(0.675), "$0.675")
        self.assertEqual(report.usd(1234.4), "$1,234")
        self.assertEqual(report.margin_pct(0.99921), "99.92%")


if __name__ == "__main__":
    unittest.main()

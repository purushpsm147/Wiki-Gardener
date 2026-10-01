"""Cost model for the Conflict Radar LLM verdict stage (Spike S1).

Pure functions over a frozen ``Scenario``; stdlib only. Run ``python run.py`` for the sensitivity tables.

Terms
-----
candidate pair   a pair of pages (or passages) the classical funnel passes to the verdict stage
yield            candidate pairs per page. ``pages * yield`` is the pair count (an ASSUMED reading of the
                 brief's "0.1% / 0.5% / 2% of pages"; ``pair_multiplier`` covers the other reading in which
                 each flagged page brings several partners)
churn            fraction of candidate pairs that are new or changed in a month. ADR-005 caches verdicts on
                 (hash_a, hash_b, prompt, provider, model_version), so unchanged pairs never re-bill

What is NOT modelled: Forge storage (KVS/SQL), the classical pipeline's own compute (see Spike S2), payment
fees, support. Forge's free allowance is ignored (conservative per tenant). The result is the LLM stage only,
plus the Forge function time spent waiting on it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRICES_PATH = HERE / "prices.json"

KILL_THRESHOLD = 0.30  # brief: "exceeds ~30% of plausible revenue for that tier"


@dataclass(frozen=True)
class ModelPrice:
    key: str
    label: str
    input_per_mtok: float
    output_per_mtok: float
    evidence: str
    source: str


@dataclass(frozen=True)
class TokenProfile:
    key: str
    label: str
    input_tokens: int
    output_tokens: int


# Token profiles are ASSUMED. T1 is the shape the near-duplicate divergence detector (A3) makes possible,
# because it hands the verdict stage the exact differing spans instead of whole pages.
PROFILES: dict[str, TokenProfile] = {
    "T1": TokenProfile("T1", "two quoted spans + schema (A3-shaped)", 1_000, 150),
    "T2": TokenProfile("T2", "passage-level pair (base case)", 3_000, 300),
    "T3": TokenProfile("T3", "section-level pair", 12_000, 500),
    "T4": TokenProfile("T4", "two long pages", 20_000, 800),
}


@dataclass(frozen=True)
class Scenario:
    pages: int
    yield_rate: float
    profile: TokenProfile
    model: ModelPrice
    monthly_churn: float = 0.20
    calls_per_pair: float = 1.0
    pair_multiplier: float = 1.0
    # Forge function time spent waiting on the model (ASSUMED) and its memory (Forge default is 512 MB)
    llm_call_seconds: float = 15.0
    function_memory_gb: float = 0.5
    gb_second_price: float = 0.000025
    # revenue side. Marketplace price is per *user* of the host product, not per page.
    users: int = 1000
    price_per_user: float = 1.0
    take_rate: float = 0.17

    @property
    def candidate_pairs(self) -> int:
        return round(self.pages * self.yield_rate * self.pair_multiplier)

    @property
    def cost_per_call(self) -> float:
        p, m = self.profile, self.model
        return (p.input_tokens * m.input_per_mtok + p.output_tokens * m.output_per_mtok) / 1e6


def load_models(path: Path = PRICES_PATH) -> dict[str, ModelPrice]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        m["key"]: ModelPrice(
            m["key"], m["label"], m["input_per_mtok"], m["output_per_mtok"], m["evidence"], m["source"]
        )
        for m in data["models"]
    }


def load_prices(path: Path = PRICES_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---- cost ---------------------------------------------------------------------------------------------------


def backfill_calls(s: Scenario) -> float:
    return s.candidate_pairs * s.calls_per_pair


def monthly_calls(s: Scenario) -> float:
    return s.candidate_pairs * s.monthly_churn * s.calls_per_pair


def backfill_llm_cost(s: Scenario) -> float:
    return backfill_calls(s) * s.cost_per_call


def monthly_llm_cost(s: Scenario) -> float:
    return monthly_calls(s) * s.cost_per_call


def compute_cost_per_call(s: Scenario) -> float:
    """Forge function GB-seconds spent waiting on one model call, priced."""
    return s.llm_call_seconds * s.function_memory_gb * s.gb_second_price


def monthly_compute_cost(s: Scenario) -> float:
    return monthly_calls(s) * compute_cost_per_call(s)


# ---- revenue and margin -------------------------------------------------------------------------------------


def gross_revenue(s: Scenario) -> float:
    return s.users * s.price_per_user


def net_revenue(s: Scenario) -> float:
    return gross_revenue(s) * (1.0 - s.take_rate)


def llm_share_of_net(s: Scenario) -> float:
    rev = net_revenue(s)
    return float("inf") if rev <= 0 else monthly_llm_cost(s) / rev


def llm_share_of_gross(s: Scenario) -> float:
    rev = gross_revenue(s)
    return float("inf") if rev <= 0 else monthly_llm_cost(s) / rev


def gross_margin(s: Scenario) -> float:
    """(net revenue - LLM - Forge wait compute) / net revenue. Other COGS are not included."""
    rev = net_revenue(s)
    if rev <= 0:
        return float("-inf")
    return (rev - monthly_llm_cost(s) - monthly_compute_cost(s)) / rev


def breakeven_net_revenue(s: Scenario, threshold: float = KILL_THRESHOLD) -> float:
    """Smallest monthly net revenue at which the steady-state LLM cost is within ``threshold`` of it."""
    return monthly_llm_cost(s) / threshold


def max_pairs_within_budget(s: Scenario, threshold: float = KILL_THRESHOLD) -> float:
    """Candidate pairs the funnel may pass before LLM cost exceeds ``threshold`` of net revenue."""
    per_pair_month = s.monthly_churn * s.calls_per_pair * s.cost_per_call
    if per_pair_month <= 0:
        return float("inf")
    return threshold * net_revenue(s) / per_pair_month


def exceeds_threshold(s: Scenario, threshold: float = KILL_THRESHOLD) -> bool:
    return llm_share_of_net(s) > threshold


# ---- throughput ---------------------------------------------------------------------------------------------


def backfill_minutes(s: Scenario, tokens_per_minute: float, requests_per_minute: float) -> float:
    """Wall-clock minutes for the backfill if the per-installation, per-model limits are the bottleneck.

    ASSUMES the token limit counts input + output tokens.
    """
    tokens = backfill_calls(s) * (s.profile.input_tokens + s.profile.output_tokens)
    return max(tokens / tokens_per_minute, backfill_calls(s) / requests_per_minute)
